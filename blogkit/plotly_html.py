"""Plotly figures as HTML we write ourselves, for Quarto pages.

Left to itself, a Plotly figure reaches a Quarto page through Plotly's notebook
renderer, which brings its own baggage with every figure: a ``<script>`` tag
for plotly.js and another for MathJax 2. A post with five figures loads each of
them five times, and MathJax 2 takes over ``window.MathJax``, so the page's
equations end up typeset by MathJax 2 instead of the site's MathJax 3.

This module writes the figure's HTML itself:

* plotly.js is loaded once per page, however many figures there are: every
  figure waits on one shared promise (``window.blogkitPlotly``), and the first
  figure on the page to run inserts the one ``<script>`` tag (the same CDN
  build and SRI hash Plotly's own ``include_plotlyjs="cdn"`` uses);
* MathJax is never loaded: the page's own MathJax 3 typesets the page;
* the figure's ``fig-alt`` is passed through as ``role="img"`` plus an
  ``aria-label`` on the figure's outer ``<div>``, since Quarto puts ``fig-alt``
  only on images;
* a figure with a fixed ``layout.width`` is drawn at that width (its design
  width) or the text column's, whichever is narrower: the div gets
  ``width: <design width>px; max-width: 100%``, and ``layout.width`` is left
  out so that plotly.js sizes the plot to the div, and re-sizes it when the
  window changes (``config.responsive``). Its height stays fixed. With
  ``styles.css``'s grid rule for code-cell figures, the caption wraps at the
  plot's edge at every width;
* such a figure also has a compact layout, for when its plot is narrower than
  :data:`COMPACT_BELOW_PX` (a phone, or a tablet with a table of contents
  beside the text): see "The compact layout" below.

Otherwise the figure is serialized exactly as :func:`plotly.io.to_html` does it
(``to_json_plotly`` on the figure dict; a div sized from ``layout.width`` and
``layout.height``; ``config`` defaulting ``responsive`` to true), so at its
design width it renders the same as it did through the notebook renderer.

Usage, in a figure builder::

    from blogkit.plotly_html import page_figure
    return page_figure(fig, alt=alt)

The result is still the ``go.Figure`` (its class is swapped in place, nothing is
copied); only how a notebook displays it changes. In a post, read the cell's
``fig-alt`` back with :func:`fig_alt`.

The compact layout
------------------
A figure laid out for an 841 px column does not survive being squeezed into a
339 px one: labels run off the edge or into each other, and Plotly's drag-to-
zoom catches the swipe a phone reader meant as a scroll. So a figure drawn at
the column's width (``fit_column``) has two layouts: its own, the desktop
layout, and a compact override that applies while its plot is narrower than
:data:`COMPACT_BELOW_PX`. At that width or wider the figure is exactly as
built.

The override is a dict of plotly.js attribute strings (as
``Plotly.relayout`` takes them) to values; edits to items of a layout array
(``annotations[2]``, ``annotations[3].text``) are sent as one value for the
whole array, since ``Plotly.relayout`` mis-indexes a mix of the two::

    page_figure(fig, alt=alt, compact={
        "layout": {"height": 480, "margin.r": 16, "annotations[2].ax": -40},
        "traces": {7: {"visible": False}},
    })

``layout`` entries are applied with ``Plotly.relayout``; ``traces`` maps a
trace's index in ``fig.data`` to style attributes applied with
``Plotly.restyle`` (both in one ``Plotly.update``). Use ``traces`` for
attributes such as ``visible`` or ``textposition``, never for a trace's data:
the data are the same in both layouts. Every compact layout also turns off
drag-to-zoom (``dragmode: false`` and every axis ``fixedrange``) and hides the
mode bar, so a swipe that starts on the figure scrolls the page; hover is
left as it is.

Leaving the compact layout puts back the desktop value of every attribute
the override set (one it had not set is reset to plotly.js's default), so the
figure returns exactly to its desktop layout. A small script shared by every
figure on the page does the switching: before the first draw it picks the
layout for the plot's width, so a phone never draws the desktop layout
first; afterwards a ``ResizeObserver`` switches whenever the plot's width
crosses the threshold. A ``height`` in the override also resizes the plot's
div, so the page reserves the right space before plotly.js has loaded.

The switch also asks plotly.js to size the plot to its div (``autosize``),
as its own window-resize handler does. Without that, the switch runs before
the handler has noticed the new width, so the plot is drawn at its old width,
and the axis ranges plotly.js widens to fit annotations at that width stay
widened when the handler redraws it at the new one.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import html
import json
import re
from functools import lru_cache
from pathlib import Path

import plotly.graph_objects as go
from plotly.io.json import to_json_plotly
from plotly.offline import get_plotlyjs, get_plotlyjs_version


# --------------------------------------------------------------------------- #
#  plotly.js, once per page
# --------------------------------------------------------------------------- #
def plotly_js_url() -> str:
    """The CDN build matching the plotly.js bundled with the Python package."""
    return f"https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js"


@lru_cache(maxsize=None)
def plotly_js_integrity() -> str:
    """SRI hash of that build (the bundled copy is byte-identical to the CDN's)."""
    digest = hashlib.sha256(get_plotlyjs().encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def _loader_js() -> str:
    """A promise for ``window.Plotly``, shared by every figure on the page.

    The first figure to run creates it and inserts the one ``<script>`` tag;
    the rest find it already there. If plotly.js is already on the page (a
    figure written another way loaded it first), that copy is used.
    ``PlotlyConfig.MathJaxConfig = 'local'`` keeps plotly.js from reconfiguring
    the page's MathJax, as Plotly's own HTML does.
    """
    return (
        "window.blogkitPlotly = window.blogkitPlotly || new Promise(function (resolve, reject) {\n"
        "  if (window.Plotly) { resolve(window.Plotly); return; }\n"
        "  window.PlotlyConfig = window.PlotlyConfig || {MathJaxConfig: 'local'};\n"
        "  var s = document.createElement('script');\n"
        f"  s.src = {json.dumps(plotly_js_url())};\n"
        f"  s.integrity = {json.dumps(plotly_js_integrity())};\n"
        "  s.crossOrigin = 'anonymous';\n"
        "  s.charset = 'utf-8';\n"
        "  s.onload = function () { resolve(window.Plotly); };\n"
        "  s.onerror = function () { reject(new Error('plotly.js failed to load: ' + s.src)); };\n"
        "  document.head.appendChild(s);\n"
        "});\n"
    )


# --------------------------------------------------------------------------- #
#  The compact layout
# --------------------------------------------------------------------------- #
#: A figure whose plot is narrower than this (px) takes its compact layout.
#: Bootstrap's "sm" breakpoint: below it is a phone.
COMPACT_BELOW_PX = 576

_PATH_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")
# An edit to one item of a layout array: "annotations[3]" or "shapes[0].x0".
_ARRAY_ITEM = re.compile(r"(annotations|shapes|images)\[(\d+)\](?:\.(.+))?")


def _get_path(obj, path: str):
    """The value at a plotly.js attribute string (``"annotations[2].font.size"``),
    or None where the figure does not set it."""
    for key, index in _PATH_TOKEN.findall(path):
        try:
            obj = obj[int(index)] if index else obj[key]
        except (KeyError, IndexError, TypeError):
            return None
    return obj


def _set_path(obj, path: str, value) -> None:
    """Set the value at a plotly.js attribute string, making dicts on the way."""
    keys = [int(i) if i else k for k, i in _PATH_TOKEN.findall(path)]
    for k in keys[:-1]:
        if isinstance(obj, dict):
            obj = obj.setdefault(k, {})
        else:
            obj = obj[k]
    obj[keys[-1]] = value


def _whole_arrays(layout: dict, edits: dict) -> dict:
    """``edits`` with every edit to an item of a layout array (``annotations[2]``,
    ``annotations[3].text``, ...) folded into one value for the whole array.

    Plotly.relayout mis-indexes when one call both replaces an item of an
    array and edits a property of another (the edited annotation ends up on
    the wrong item), so each array the override touches is sent whole: the
    desktop array with the edits applied, in order.
    """
    out, arrays = {}, {}
    for k, v in edits.items():
        m = _ARRAY_ITEM.fullmatch(k)
        if not m:
            out[k] = v
            continue
        name, i, sub = m.group(1), int(m.group(2)), m.group(3)
        items = arrays.setdefault(name, copy.deepcopy(layout.get(name, [])))
        if sub is None:
            if i == len(items):
                items.append(v)
            else:
                items[i] = v
        else:
            _set_path(items[i], sub, v)
    out.update(arrays)
    return out


def _compact_spec(fig_dict: dict, compact: dict | None) -> dict:
    """The compact override and the desktop values it replaces, for the script.

    ``on`` is the compact layout: the interaction every compact figure gets,
    then the figure's own ``compact["layout"]``; ``off`` holds the desktop
    value of each attribute ``on`` sets (None, which plotly.js reads as
    "reset to default", where the desktop layout leaves it unset). Trace
    attributes are laid out as ``Plotly.update`` takes them: one list per
    attribute, aligned with ``indices``.
    """
    compact = compact or {}
    layout = fig_dict.get("layout", {})
    data = fig_dict.get("data", [])

    axes = {k for k in layout if re.fullmatch(r"[xy]axis\d*", k)} | {"xaxis", "yaxis"}
    on_layout = {"dragmode": False}
    on_layout.update({f"{ax}.fixedrange": True for ax in sorted(axes)})
    on_layout.update(_whole_arrays(layout, compact.get("layout", {})))
    if "height" in on_layout:
        # Given a height, Plotly.relayout also writes the plot's current width
        # into the layout, which stops plotly.js sizing the plot to its div: a
        # figure switched at 537 px would stay 537 px wide at any width after.
        # An explicit width: null in the same call prevents that (both ways).
        on_layout["width"] = None
    off_layout = {k: _get_path(layout, k) for k in on_layout}

    traces = {int(i): attrs for i, attrs in compact.get("traces", {}).items()}
    indices = sorted(traces)
    on_traces, off_traces = {}, {}
    for attr in sorted({a for attrs in traces.values() for a in attrs}):
        off_traces[attr] = [_get_path(data[i], attr) for i in indices]
        on_traces[attr] = [traces[i].get(attr, off) for i, off in zip(indices, off_traces[attr])]

    return {
        "below": COMPACT_BELOW_PX,
        "indices": indices,
        "on": {"layout": on_layout, "traces": on_traces,
               "height": on_layout.get("height", layout.get("height"))},
        "off": {"layout": off_layout, "traces": off_traces, "height": layout.get("height")},
    }


def _compact_js() -> str:
    """``window.blogkitCompact``: the switching script, shared by every figure.

    ``narrow`` says whether a plot div should be compact (a div with no width
    yet, such as one in a hidden tab, is not: it switches once it is shown);
    ``mark`` sets the div's class (which hides the mode bar) and height;
    ``prepare`` merges the compact override into the figure before its first
    draw; ``watch`` switches the drawn figure whenever its width crosses the
    threshold.
    """
    return (
        "window.blogkitCompact = window.blogkitCompact || (function () {\n"
        "  var css = document.createElement('style');\n"
        "  css.textContent = '.plotly-graph-div.blogkit-compact .modebar-container { display: none !important; }';\n"
        "  document.head.appendChild(css);\n"
        "  function setPath(obj, path, value) {\n"
        "    var t = [];\n"
        "    path.replace(/([^.\\[\\]]+)|\\[(\\d+)\\]/g, function (m, key, i) { t.push(key !== undefined ? key : +i); });\n"
        "    for (var j = 0; j < t.length - 1; j++) {\n"
        "      if (obj[t[j]] == null) obj[t[j]] = typeof t[j + 1] === 'number' ? [] : {};\n"
        "      obj = obj[t[j]];\n"
        "    }\n"
        "    if (value === null) delete obj[t[t.length - 1]]; else obj[t[t.length - 1]] = value;\n"
        "  }\n"
        "  function narrow(gd, spec) {\n"
        "    var w = gd.getBoundingClientRect().width;\n"
        "    return w > 0 && w < spec.below;\n"
        "  }\n"
        "  function mark(gd, spec, on) {\n"
        "    var s = on ? spec.on : spec.off;\n"
        "    gd.classList.toggle('blogkit-compact', on);\n"
        "    if (s.height != null) gd.style.height = s.height + 'px';\n"
        "  }\n"
        "  return {\n"
        "    narrow: narrow,\n"
        "    mark: mark,\n"
        "    prepare: function (gd, spec, data, layout) {\n"
        "      var on = narrow(gd, spec);\n"
        "      mark(gd, spec, on);\n"
        "      if (on) {\n"
        "        Object.keys(spec.on.layout).forEach(function (k) { setPath(layout, k, spec.on.layout[k]); });\n"
        "        Object.keys(spec.on.traces).forEach(function (k) {\n"
        "          spec.indices.forEach(function (i, j) { setPath(data[i], k, spec.on.traces[k][j]); });\n"
        "        });\n"
        "      }\n"
        "      return on;\n"
        "    },\n"
        "    watch: function (gd, spec, on) {\n"
        "      new ResizeObserver(function () {\n"
        "        var want = narrow(gd, spec);\n"
        "        if (want === on) return;\n"
        "        on = want;\n"
        "        var s = on ? spec.on : spec.off;\n"
        "        mark(gd, spec, on);\n"
        "        Plotly.update(gd, s.traces, Object.assign({autosize: true}, s.layout), spec.indices);\n"
        "      }).observe(gd);\n"
        "    }\n"
        "  };\n"
        "})();\n"
    )


# --------------------------------------------------------------------------- #
#  One figure
# --------------------------------------------------------------------------- #
def _css_size(v, default: str) -> str:
    if v is None:
        return default
    try:
        return f"{float(v):g}px"
    except (TypeError, ValueError):
        return str(v)


def figure_html(
    fig: go.Figure,
    *,
    alt: str | None = None,
    div_id: str | None = None,
    config: dict | None = None,
    post_script: str | None = None,
    fit_column: bool = True,
    compact: dict | None = None,
) -> str:
    """The HTML for one figure: an optional labelled wrapper, the plot div, a script.

    Parameters
    ----------
    fig
        The figure. Serialized as :func:`plotly.io.to_html` does.
    alt
        The figure's text alternative (the cell's ``fig-alt``). Becomes
        ``role="img"`` and ``aria-label`` on the outer ``<div>``.
    div_id
        The plot div's id. Defaults to one derived from the figure's content,
        so re-rendering an unchanged figure writes identical HTML (and an
        unchanged ``_freeze/``).
    config
        plotly.js config, over the default ``{"responsive": True}``.
    post_script
        JavaScript run once the plot exists, with ``gd`` bound to the plot div.
    fit_column
        Draw a figure with a fixed ``layout.width`` at that width or the
        column's, whichever is narrower (see the module docstring). False keeps
        the fixed width at every window size.
    compact
        The figure's compact override (see "The compact layout" in the module
        docstring): ``{"layout": {...}, "traces": {index: {...}}}``. Applies
        only to a figure drawn at the column's width; one with no override of
        its own still gets the compact interaction.
    """
    fig_dict = fig.to_dict()
    layout = fig_dict.get("layout", {})
    template_layout = layout.get("template", {}).get("layout", {})
    max_width = ""
    if fit_column and layout.get("width") is not None and layout.get("autosize") is not False:
        design_width = layout.pop("width")   # plotly.js now takes the width from the div
        max_width = " max-width:100%;"
    jdata = to_json_plotly(fig_dict.get("data", []))
    jlayout = to_json_plotly(layout)
    jframes = to_json_plotly(fig_dict["frames"]) if fig_dict.get("frames") else None
    cfg = {"responsive": True}
    cfg.update(config or {})
    jconfig = json.dumps(cfg)
    jspec = to_json_plotly(_compact_spec(fig_dict, compact)) if max_width else None
    if div_id is None:
        h = hashlib.sha1((jdata + jlayout + (jframes or "") + jconfig + (jspec or "")).encode("utf-8")).hexdigest()
        div_id = f"plotly-{h[:12]}"
    if max_width:
        width = _css_size(design_width, "100%")
    else:
        width = _css_size(layout.get("width", template_layout.get("width")), "100%")
    height = _css_size(layout.get("height", template_layout.get("height")), "100%")

    then = ""
    if jframes:
        then += f".then(function (gd) {{ return Plotly.addFrames(gd, {jframes}).then(function () {{ return gd; }}); }})"
    if post_script:
        then += f".then(function (gd) {{\n{post_script}\n  return gd;\n}})"
    jid = json.dumps(div_id)
    if jspec:
        # The div's height is set as soon as it is parsed, so the page reserves
        # the right space before plotly.js arrives; the layout is chosen again
        # at the first draw, in case the width has changed since.
        script = (
            "(function () {\n"
            + _loader_js()
            + _compact_js()
            + "window.PLOTLYENV = window.PLOTLYENV || {};\n"
            f"var spec = {jspec};\n"
            f"var div = document.getElementById({jid});\n"
            "if (div) window.blogkitCompact.mark(div, spec, window.blogkitCompact.narrow(div, spec));\n"
            "window.blogkitPlotly.then(function (Plotly) {\n"
            f"  var gd = document.getElementById({jid});\n"
            "  if (!gd) return;\n"
            f"  var data = {jdata};\n"
            f"  var layout = {jlayout};\n"
            "  var compact = window.blogkitCompact.prepare(gd, spec, data, layout);\n"
            f"  return Plotly.newPlot(gd, data, layout, {jconfig})"
            ".then(function (gd) { window.blogkitCompact.watch(gd, spec, compact); return gd; })"
            f"{then};\n"
            "});\n"
            "})();"
        )
    else:
        script = (
            "(function () {\n"
            + _loader_js()
            + "window.PLOTLYENV = window.PLOTLYENV || {};\n"
            "window.blogkitPlotly.then(function (Plotly) {\n"
            f"  var gd = document.getElementById({jid});\n"
            "  if (!gd) return;\n"
            f"  return Plotly.newPlot(gd, {jdata}, {jlayout}, {jconfig}){then};\n"
            "});\n"
            "})();"
        )
    attrs = f' role="img" aria-label="{html.escape(alt, quote=True)}"' if alt else ""
    return (f"<div{attrs}>\n"
            f'<div id="{div_id}" class="plotly-graph-div" style="height:{height}; width:{width};{max_width}"></div>\n'
            f"<script>\n{script}\n</script>\n"
            "</div>")


class PageFigure(go.Figure):
    """A ``go.Figure`` that a notebook (and so Quarto) displays as :func:`figure_html`.

    Make one with :func:`page_figure`. Only the display hooks change: the
    figure is otherwise an ordinary ``go.Figure``. Both hooks are overridden,
    since Plotly's own ``_ipython_display_`` goes through ``pio.show`` and its
    notebook renderer, which would bring plotly.js and MathJax 2 back.
    """

    _blogkit_html: dict

    def _repr_mimebundle_(self, *args, **kwargs):
        return {"text/html": figure_html(self, **getattr(self, "_blogkit_html", {}))}

    def _ipython_display_(self):
        from IPython.display import display
        display(self._repr_mimebundle_(), raw=True)


def page_figure(
    fig: go.Figure,
    *,
    alt: str | None = None,
    config: dict | None = None,
    post_script: str | None = None,
    fit_column: bool = True,
    compact: dict | None = None,
) -> PageFigure:
    """``fig`` itself (not a copy), displayed through :func:`figure_html`.

    The arguments are :func:`figure_html`'s, kept on the figure until it is
    displayed.
    """
    fig.__class__ = PageFigure
    fig._blogkit_html = dict(alt=alt, config=config, post_script=post_script,
                             fit_column=fit_column, compact=compact)
    return fig


# --------------------------------------------------------------------------- #
#  A cell's fig-alt
# --------------------------------------------------------------------------- #
def fig_alt(label: str, qmd: str | Path = "index.qmd") -> str:
    """The ``#| fig-alt:`` text of the code cell labelled ``label`` in ``qmd``.

    Quarto strips a cell's ``#|`` options before the code reaches the kernel,
    so a cell cannot see its own ``fig-alt``; this reads it back from the post
    (the kernel runs in the post's folder, so the default path finds it), so
    the text lives in one place. Raises if the cell or its ``fig-alt`` is
    missing, which fails the render rather than shipping an unlabelled figure.
    """
    lines = Path(qmd).read_text(encoding="utf-8").split("\n")
    try:
        i = lines.index(f"#| label: {label}")
    except ValueError:
        raise ValueError(f"no cell labelled {label!r} in {qmd}") from None
    j, k = i, i
    while j > 0 and lines[j - 1].startswith("#|"):
        j -= 1
    while k + 1 < len(lines) and lines[k + 1].startswith("#|"):
        k += 1
    for ln in lines[j:k + 1]:
        m = re.match(r"#\|\s*fig-alt:\s*(.*)$", ln)
        if m:
            v = m.group(1).strip()
            return json.loads(v) if v.startswith('"') else v
    raise ValueError(f"cell {label!r} in {qmd} has no #| fig-alt")
