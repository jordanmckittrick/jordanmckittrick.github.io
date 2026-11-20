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
  plot's edge at every width.

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
"""

from __future__ import annotations

import base64
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
    if div_id is None:
        h = hashlib.sha1((jdata + jlayout + (jframes or "") + jconfig).encode("utf-8")).hexdigest()
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
    script = (
        "(function () {\n"
        + _loader_js()
        + "window.PLOTLYENV = window.PLOTLYENV || {};\n"
        "window.blogkitPlotly.then(function (Plotly) {\n"
        f"  var gd = document.getElementById({json.dumps(div_id)});\n"
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
) -> PageFigure:
    """``fig`` itself (not a copy), displayed through :func:`figure_html`.

    The arguments are :func:`figure_html`'s, kept on the figure until it is
    displayed.
    """
    fig.__class__ = PageFigure
    fig._blogkit_html = dict(alt=alt, config=config, post_script=post_script, fit_column=fit_column)
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
