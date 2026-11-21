#!/usr/bin/env python3
"""Layout checks for the built site: does each page fit the screen it is read on?

Usage::

    uv run python tools/check_layout.py                          # every non-draft post
    uv run python tools/check_layout.py --pages shannons-demon stranded
    uv run python tools/check_layout.py --out _layout/after --diff-against _layout/before
    uv run python tools/check_layout.py --sweep-only --pages stranded   # every 10 px, 320-1440

It serves ``_site/`` (build it first: ``uv run quarto render``) on a local port
and loads each page in headless Chromium (Playwright) at viewport widths of
1440, 1180, 820, 390 and 360 px, in light mode and in dark mode. Dark mode is
switched on the way a reader does it: by clicking the navbar toggle (opening
the collapsed navbar first on narrow screens). Each load is a fresh browser
context, so nothing carries over between widths or modes.

What it measures, per page, width and mode:

* the page's ``scrollWidth`` against the viewport width;
* the left and right edges of the text column (``main``'s content box);
* for every figure (each ``div#fig-*``, plus any unlabelled code-cell output
  holding a plot or image): the left and right edges of its plot (the Plotly
  div, or else its image), of its caption, and of its overlay labels (the HTML
  labels a figure draws over or around its plot, such as the simplex's point,
  line, vertex and contour labels, its readout and its slider labels: see
  ``OVERLAY_LABELS``; hidden ones are skipped), and whether any of them lies
  outside the column;
* the number of ``mjx-container`` elements (MathJax 3) and ``.MathJax_SVG``
  elements (MathJax 2), the ``<script>`` tags that load MathJax 2, and those
  that load plotly.js (by URL, or inlined as a bundle);
* console errors and uncaught page errors;
* when the page is wider than the viewport, the outermost elements that make it
  so (anything inside a scrolling or clipping box is skipped, since it cannot
  widen the page).

What it writes, under ``--out`` (default ``_layout/latest/``; ``_layout/`` is
git-ignored):

* ``figures/<post>_<figure>_<width>_<mode>.png``: each figure with its caption,
  framed by the text column so overflow past either edge shows;
* ``plots/<post>_<figure>_<width>_<mode>.png``: the plot (or image) alone,
  for pixel diffs: pinned to the top of the viewport at its measured size, so
  that its pixels do not depend on where it sits on the page (see ``PIN_JS``);
  one too big for the viewport is cropped in place instead;
* ``<post>_contact.png``: one contact sheet per post (rows are figures, columns
  are widths, light and dark side by side);
* ``measurements.json`` (everything above) and ``summary.md`` (the same as
  tables).

The width sweep (``--sweep``, or ``--sweep-only``) loads each page afresh at
every viewport width from 320 to 1440 px in steps of 10 (``SWEEP_WIDTHS``), in
light mode, and measures only: no screenshots. It applies the same width
checks as above (page width; plot, caption and overlay labels inside the
column), so a band of widths between the five fixed ones can't hide a failure,
and reports the failing widths as bands. It takes several minutes, so it is
not part of the default run.

The resize check loads each page at the widest width, resizes the viewport
down through the other widths and back up, and compares every figure's plot
(and, for a Plotly figure, the SVG drawn in it) and caption edges and height at
each step with a fresh load at that width; back at the widest width it also
pixel-diffs each plot against the fresh load's crop. Skip it with
``--no-resize-check``.

``--diff-against DIR`` compares every ``plots/`` crop with the one of the same
name in an earlier run and reports the number of differing pixels; nonzero
diffs are written to ``plots-diff/``. The diff is a report, not a failure.

It exits 1 if, on any page at any width or mode:

* the page is wider than the viewport;
* a figure's plot, caption or overlay labels lie outside the text column
  (0.5 px tolerance), at any of the five widths or, with ``--sweep``, any width
  of the sweep;
* MathJax 2 is on the page (a script tag, or ``.MathJax_SVG`` output);
* plotly.js is loaded more than once;
* the resize check finds a figure that does not return to its fresh layout.

Console errors are reported but do not fail the run. Needs network access:
pages load MathJax and plotly.js from their CDNs. Setup, once::

    uv sync && uv run playwright install chromium
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_post  # noqa: E402  (front-matter reader, for draft status)

WIDTHS = (1440, 1180, 820, 390, 360)
SWEEP_WIDTHS = tuple(range(320, 1441, 10))
MODES = ("light", "dark")
VIEWPORT_HEIGHT = 900
TOLERANCE_PX = 0.5
# HTML labels a figure draws over or around its plot: Stranded's simplex draws
# every label, its readout and its slider labels as HTML positioned over the
# plot, and these can reach past the plot (and the column) where Plotly's own
# text would be clipped. Each must lie inside the text column.
OVERLAY_LABELS = (".simplex-olabel, .simplex-readout, .simplex-landmark, "
                  ".simplex-q-label, .simplex-thumb-label")


# --------------------------------------------------------------------------- #
#  Pages
# --------------------------------------------------------------------------- #
def is_draft(qmd: Path) -> bool:
    d = check_post.load_doc(qmd.resolve()).front_value("draft")
    return d is not None and check_post.yaml_scalar(d[1]).lower() == "true"


def default_pages(root: Path) -> list[str]:
    """Slugs of every post whose ``draft:`` is not true."""
    return [q.parent.name for q in sorted((root / "posts").glob("*/index.qmd"))
            if not is_draft(q)]


def page_path(spec: str) -> tuple[str, str]:
    """(name, site-relative URL path) for a slug, a post folder/qmd, or an .html path."""
    s = spec.strip().rstrip("/")
    if s.endswith(".html"):
        name = Path(s).parent.name if Path(s).name == "index.html" else Path(s).stem
        return name or "index", s.lstrip("/")
    if s.endswith(".qmd"):
        s = str(Path(s).parent)
    slug = Path(s).name
    return slug, f"posts/{slug}/index.html"


# --------------------------------------------------------------------------- #
#  A static file server for _site/
# --------------------------------------------------------------------------- #
class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 - silence per-request logging
        pass


class SiteServer:
    def __init__(self, directory: Path):
        handler = functools.partial(_QuietHandler, directory=str(directory))
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


# --------------------------------------------------------------------------- #
#  In-page JavaScript
# --------------------------------------------------------------------------- #
# Resolves once fonts, MathJax (2 or 3) and every Plotly div have finished.
SETTLE_JS = """
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  await document.fonts.ready;
  for (let i = 0; i < 100; i++) {           // MathJax 3 may not exist yet (defer)
    const MJ = window.MathJax;
    if (MJ && ((MJ.startup && MJ.startup.promise) || MJ.Hub)) break;
    await sleep(100);
  }
  const MJ = window.MathJax;
  try {
    if (MJ && MJ.startup && MJ.startup.promise) await MJ.startup.promise;
    if (MJ && MJ.Hub && MJ.Hub.Queue) await new Promise(r => MJ.Hub.Queue(r));
  } catch (e) {}
  for (let i = 0; i < 200; i++) {
    const gds = [...document.querySelectorAll('.plotly-graph-div')];
    if (gds.every(gd => gd._fullLayout && gd.querySelector('.main-svg'))) break;
    await sleep(100);
  }
  await document.fonts.ready;
  await frame();
  await sleep(400);
  await frame();
  return true;
}
"""

MEASURE_JS = """
([tol, overlaySel]) => {
  const de = document.documentElement;
  const vw = de.clientWidth;
  const box = (el) => {
    const b = el.getBoundingClientRect();
    return {left: b.left + scrollX, right: b.right + scrollX,
            top: b.top + scrollY, bottom: b.bottom + scrollY};
  };
  const union = (rs) => rs.length ? {
    left: Math.min(...rs.map(r => r.left)), right: Math.max(...rs.map(r => r.right)),
    top: Math.min(...rs.map(r => r.top)), bottom: Math.max(...rs.map(r => r.bottom))} : null;
  const nonEmpty = (el) => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
  const out = {viewport: vw, innerWidth: innerWidth,
               scrollWidth: Math.max(de.scrollWidth, document.body.scrollWidth),
               dark: document.body.classList.contains('quarto-dark')};

  // Text column: main's content box.
  const main = document.querySelector('main#quarto-document-content') || document.querySelector('main');
  let col = null;
  if (main) {
    const s = getComputedStyle(main), b = box(main);
    col = {left: b.left + parseFloat(s.paddingLeft) + parseFloat(s.borderLeftWidth),
           right: b.right - parseFloat(s.paddingRight) - parseFloat(s.borderRightWidth)};
  }
  out.column = col;

  // Figures: every div#fig-*, plus unlabelled code-cell output with a plot/image.
  const containers = [...document.querySelectorAll('div[id^="fig-"]')];
  document.querySelectorAll('.cell-output-display').forEach(d => {
    if (!d.closest('div[id^="fig-"]') && d.querySelector('.plotly-graph-div, img')) containers.push(d);
  });
  const set = new Set(containers);
  const owner = (e) => { let a = e.parentElement; while (a && !set.has(a)) a = a.parentElement; return a; };
  const outside = (r) => !!(col && r && (r.left < col.left - tol || r.right > col.right + tol));
  let cellN = 0;
  out.figures = containers.map(c => {
    const owned = (sel) => [...c.querySelectorAll(sel)].filter(e => owner(e) === c && nonEmpty(e));
    let media = owned('.plotly-graph-div'), kind = 'plotly';
    if (!media.length) { media = owned('img'); kind = 'img'; }
    if (!media.length) { media = owned('svg'); kind = 'svg'; }
    const cap = owned('figure > figcaption').filter(f => f.parentElement.parentElement === c ||
                                                       owner(f.parentElement) === c)[0];
    const fid = c.id || ('cell-' + (cellN + 1));
    c.setAttribute('data-layout-fig', fid);
    media.forEach(m => m.setAttribute('data-layout-media', fid));
    const plot = union(media.map(box));
    // What plotly.js drew (its SVG), which need not fill the div it sits in.
    const drawn = kind === 'plotly' ? union(media.map(m => m.querySelector('.main-svg')).filter(Boolean).map(box)) : null;
    const caption = cap ? box(cap) : null;
    // Overlay labels: visible ones only (a hidden contour value can't be cut off).
    const shown = (e) => {
      if (!nonEmpty(e)) return false;
      for (let a = e; a && a !== c; a = a.parentElement) {
        const s = getComputedStyle(a);
        if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) return false;
      }
      return true;
    };
    const labelEls = [...c.querySelectorAll(overlaySel)].filter(e => owner(e) === c && shown(e));
    const labelBoxes = labelEls.map(box);
    const labels = union(labelBoxes);
    const labels_outside = labelEls.map((e, k) => ({e, b: labelBoxes[k]})).filter(x => outside(x.b))
      .map(x => ({text: (x.e.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 40),
                  left: Math.round(x.b.left * 10) / 10, right: Math.round(x.b.right * 10) / 10}));
    // Extent of the figure's HTML (not SVG) content, for framing screenshots:
    // overlay labels can reach past the plot, while SVG paths can run far
    // outside a clipped plot area and would mislead.
    const html = [c, ...c.querySelectorAll('*')].filter(e => !(e instanceof SVGElement) && nonEmpty(e));
    const ink = union(html.map(box));
    if (!c.id) ++cellN;
    return {id: fid, kind, n_media: media.length,
            plot, drawn, caption, ink, labels, n_labels: labelEls.length, labels_outside,
            plot_outside: outside(plot), caption_outside: outside(caption)};
  });

  // MathJax and plotly.js.
  const scripts = [...document.scripts];
  out.mjx_container = document.querySelectorAll('mjx-container').length;
  out.mathjax_svg = document.querySelectorAll('.MathJax_SVG').length;
  out.mathjax2_scripts = scripts.map(s => s.src).filter(u => /mathjax\\/2\\.|\\/MathJax\\.js(\\?|$)/i.test(u));
  const plotlyRe = /(^|\\/)plotly(-[a-z]+)?(-[0-9.]+|-latest)?(\\.min)?\\.js(\\?|$)/i;
  out.plotly_scripts = scripts.map(s => s.src).filter(u => u && plotlyRe.test(new URL(u).pathname))
    .concat(scripts.filter(s => !s.src && /plotly\\.js v\\d/.test(s.text.slice(0, 400))).map(() => '(inline bundle)'));

  // What makes the page wider than the viewport: the outermost overflowing
  // elements that no scrolling/clipping ancestor contains.
  out.overflowing = [];
  if (out.scrollWidth > vw) {
    // Only the right edge can widen a page: nothing left of 0 is scrollable.
    const over = (b) => b.right > vw + tol;
    for (const el of document.body.querySelectorAll('*')) {
      const b = el.getBoundingClientRect();
      if ((b.width === 0 && b.height === 0) || !over(b)) continue;
      const p = el.parentElement;
      if (p && p !== document.body && over(p.getBoundingClientRect())) {
        // the parent overflows too; report only if the parent is a clipper
        if (getComputedStyle(p).overflowX === 'visible') continue;
      }
      let a = el.parentElement, clipped = false;
      while (a && a !== document.body && a !== de) {
        const s = getComputedStyle(a);
        if (s.overflowX !== 'visible' || s.position === 'fixed') { clipped = true; break; }
        a = a.parentElement;
      }
      if (clipped || getComputedStyle(el).position === 'fixed') continue;
      const fig = el.closest('div[id^="fig-"]');
      out.overflowing.push({
        tag: el.tagName.toLowerCase(), id: el.id || null,
        cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60) || null,
        in_figure: fig ? fig.id : null,
        // MathJax 3 draws glyphs with CSS, so take an equation's text from its
        // container (which carries the assistive MathML).
        text: ((el.closest('mjx-container') || el).textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 70),
        left: Math.round(b.left * 10) / 10, right: Math.round(b.right * 10) / 10});
      if (out.overflowing.length >= 40) break;
    }
  }
  return out;
}
"""

DARK_JS_STATE = "() => document.body.classList.contains('quarto-dark')"

# Pin a figure's plot to the top of the viewport, for a crop that can be
# compared pixel for pixel with the same plot from another build. In place, a
# plot's pixels depend on where it sits on the page, not only on what is in it:
# Chrome rasterizes the page in tiles, and moving content by a few pixels (text
# above it changing height, say) moves the tile seams across it and changes a
# row or a patch of anti-aliased pixels. Even an unchanged image differs. So the
# plot (each media element, at its measured size) is taken out of the flow and
# fixed at the viewport's top edge, at a whole-pixel left edge and on the page's
# background colour, which puts it in the same place for every build. Returns
# its box in viewport pixels, or null if it does not fit in the viewport (the
# caller then crops it in place). `unpin` restores it.
PIN_JS = """
(id) => {
  const ms = [...document.querySelectorAll(`[data-layout-media="${id}"]`)];
  if (!ms.length) return null;
  const bs = ms.map(m => m.getBoundingClientRect());
  const L = Math.min(...bs.map(b => b.left)), T = Math.min(...bs.map(b => b.top));
  const W = Math.max(...bs.map(b => b.right)) - L, H = Math.max(...bs.map(b => b.bottom)) - T;
  const vw = document.documentElement.clientWidth;
  if (W > vw || H > innerHeight) return null;
  const x0 = Math.min(Math.max(0, Math.round(L)), Math.floor(vw - W));
  const bg = getComputedStyle(document.body).backgroundColor;
  ms.forEach((m, i) => {
    const b = bs[i];
    m.dataset.layoutSaved = m.getAttribute('style') || '';
    m.style.cssText += `;position:fixed !important;left:${x0 + b.left - L}px !important;` +
      `top:${b.top - T}px !important;width:${b.width}px !important;height:${b.height}px !important;` +
      `margin:0 !important;max-width:none !important;z-index:2147483647 !important;background:${bg} !important;`;
  });
  return {left: x0, top: 0, right: x0 + W, bottom: H};
}
"""
UNPIN_JS = """
(id) => {
  document.querySelectorAll(`[data-layout-media="${id}"]`).forEach(m => {
    if (m.dataset.layoutSaved === undefined) return;
    m.setAttribute('style', m.dataset.layoutSaved);
    delete m.dataset.layoutSaved;
  });
}
"""


# --------------------------------------------------------------------------- #
#  One page load
# --------------------------------------------------------------------------- #
@dataclass
class Load:
    page: str
    width: int
    mode: str
    data: dict = field(default_factory=dict)
    console_errors: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def _switch_to_dark(page) -> None:
    """Click the navbar's colour-scheme toggle, opening a collapsed navbar first."""
    toggle = page.locator("header .quarto-color-scheme-toggle").first
    opened = False
    if not toggle.is_visible():
        page.locator("header .navbar-toggler").first.click()
        opened = True
        toggle.wait_for(state="visible", timeout=5000)
    toggle.click()
    page.wait_for_function(DARK_JS_STATE, timeout=5000)
    if opened:
        page.locator("header .navbar-toggler").first.click()
        page.wait_for_function(
            "() => !document.querySelector('header .navbar-collapse.show, header .navbar-collapse.collapsing')",
            timeout=5000)
    page.mouse.move(0, 0)
    page.evaluate("() => new Promise(r => setTimeout(r, 300))")


def _shoot(page, load: Load, out: Path, figs: list[dict], col: dict | None, scroll_w: int) -> None:
    """Save each figure (framed by the column) and its plot alone."""
    page.add_style_tag(content="#quarto-header, .headroom { visibility: hidden !important; }")
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    for f in figs:
        ink = f["ink"]
        if not ink:
            continue
        stem = f"{load.page}_{f['id']}_{load.width}_{load.mode}.png"
        left = min(ink["left"], col["left"]) if col else ink["left"]
        right = max(ink["right"], col["right"]) if col else ink["right"]
        x0, x1 = max(0, left - 8), min(scroll_w, right + 8)
        clip = dict(x=round(x0), y=round(ink["top"] - 8),
                    width=round(x1 - x0), height=round(ink["bottom"] - ink["top"] + 16))
        page.screenshot(path=str(out / "figures" / stem), clip=clip, full_page=True)
        pinned = page.evaluate(PIN_JS, f["id"])
        if pinned:
            clip = dict(x=pinned["left"], y=0, width=round(pinned["right"] - pinned["left"]),
                        height=round(pinned["bottom"]))
            page.screenshot(path=str(out / "plots" / stem), clip=clip)
            page.evaluate(UNPIN_JS, f["id"])
            continue
        p = f["plot"]                      # too big to pin: crop it where it is
        if p and p["right"] > p["left"]:
            x0, x1 = max(0, p["left"]), min(scroll_w, p["right"])
            clip = dict(x=round(x0), y=round(p["top"]),
                        width=round(x1) - round(x0), height=round(p["bottom"]) - round(p["top"]))
            if clip["width"] > 0 and clip["height"] > 0:
                page.screenshot(path=str(out / "plots" / stem), clip=clip, full_page=True)


def measure(browser, base_url: str, name: str, path: str, width: int, mode: str,
            out: Path, shots: bool) -> Load:
    load = Load(name, width, mode)
    ctx = browser.new_context(viewport={"width": width, "height": VIEWPORT_HEIGHT},
                              device_scale_factor=1, color_scheme="light")
    page = ctx.new_page()
    def on_console(m):
        if m.type == "error":
            url = (m.location or {}).get("url", "")
            load.console_errors.append(m.text[:300] + (f" [{url[:200]}]" if url else ""))
    page.on("console", on_console)
    page.on("pageerror", lambda e: load.console_errors.append(f"pageerror: {str(e)[:300]}"))
    try:
        page.goto(base_url + path, wait_until="load", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.mouse.move(0, 0)
        page.evaluate(SETTLE_JS)
        if mode == "dark":
            _switch_to_dark(page)
            page.evaluate(SETTLE_JS)
        load.data = page.evaluate(MEASURE_JS, [TOLERANCE_PX, OVERLAY_LABELS])
        if shots:
            _shoot(page, load, out, load.data["figures"], load.data["column"], load.data["scrollWidth"])
    finally:
        ctx.close()

    d = load.data
    if mode == "dark" and not d.get("dark"):
        load.failures.append("dark mode did not switch on")
    load.failures += width_failures(d)
    if d["mathjax2_scripts"] or d["mathjax_svg"]:
        load.failures.append(f"MathJax 2 on the page ({len(d['mathjax2_scripts'])} script(s), "
                             f"{d['mathjax_svg']} .MathJax_SVG)")
    if len(d["plotly_scripts"]) > 1:
        load.failures.append(f"plotly.js loaded {len(d['plotly_scripts'])} times")
    return load


def width_failures(d: dict) -> list[str]:
    """The checks that depend on the viewport width: the page is no wider than the
    viewport, and every figure's plot, caption and overlay labels lie inside the
    text column."""
    out = []
    if d["scrollWidth"] > d["viewport"]:
        out.append(f"page is {d['scrollWidth']} px wide in a {d['viewport']} px viewport")
    col = d["column"]
    for f in d["figures"]:
        if f["plot_outside"]:
            out.append(f"{f['id']}: plot outside the column")
        if f["caption_outside"]:
            out.append(f"{f['id']}: caption outside the column")
        if f["labels_outside"]:
            worst = max(max(col["left"] - x["left"], x["right"] - col["right"]) for x in f["labels_outside"])
            names = ", ".join(repr(x["text"]) for x in f["labels_outside"][:4])
            out.append(f"{f['id']}: {len(f['labels_outside'])} overlay label(s) outside the column, "
                       f"by up to {worst:.1f} px ({names})")
    return out


def bands(widths: list[int], step: int) -> str:
    """Sorted widths as runs: [620, 630, 640, 700] (step 10) -> "620–640, 700"."""
    runs: list[list[int]] = []
    for w in sorted(widths):
        if runs and w - runs[-1][-1] == step:
            runs[-1].append(w)
        else:
            runs.append([w])
    return ", ".join(f"{r[0]}–{r[-1]}" if len(r) > 1 else f"{r[0]}" for r in runs)


def sweep(browser, base_url: str, name: str, path: str, widths) -> list[dict]:
    """Load one page afresh at each width (light mode) and apply the width checks.

    One browser context per page, so plotly.js and MathJax come from its HTTP
    cache after the first load; each width is a new page. Returns, per width,
    the viewport and column widths and the failures.
    """
    ctx = browser.new_context(viewport={"width": widths[0], "height": VIEWPORT_HEIGHT},
                              device_scale_factor=1, color_scheme="light")
    rows = []
    try:
        for w in widths:
            page = ctx.new_page()
            page.set_viewport_size({"width": w, "height": VIEWPORT_HEIGHT})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(f"pageerror: {str(e)[:300]}"))
            try:
                page.goto(base_url + path, wait_until="load", timeout=60000)
                page.mouse.move(0, 0)
                page.evaluate(SETTLE_JS)
                d = page.evaluate(MEASURE_JS, [TOLERANCE_PX, OVERLAY_LABELS])
            finally:
                page.close()
            col = d["column"]
            rows.append(dict(width=w, column=round(col["right"] - col["left"], 1) if col else None,
                             scrollWidth=d["scrollWidth"], failures=width_failures(d), errors=errors,
                             figures={f["id"]: dict(plot=f["plot"], caption=f["caption"], labels=f["labels"],
                                                    labels_outside=f["labels_outside"])
                                      for f in d["figures"]}))
    finally:
        ctx.close()
    return rows


def sweep_markdown(results: dict[str, list[dict]], step: int) -> str:
    lines = ["", "## Width sweep", "",
             f"Fresh loads every {step} px, light mode, measurements only.", ""]
    for name, rows in results.items():
        bad = [r for r in rows if r["failures"]]
        lines.append(f"{name}: {len(rows)} widths, {rows[0]['width']}–{rows[-1]['width']} px: "
                     + ("all pass" if not bad else f"{len(bad)} fail"))
        kinds: dict[str, list[int]] = {}
        for r in bad:
            for x in r["failures"]:
                kind = x.split(" by up to")[0].split(" (")[0]
                kind = kind if "page is" not in kind else "page wider than the viewport"
                kinds.setdefault(kind, []).append(r["width"])
        for kind, ws in kinds.items():
            cols = [r["column"] for r in rows if r["width"] in ws]
            lines.append(f"- {kind}: viewport {bands(ws, step)} px (column {min(cols):.1f}–{max(cols):.1f} px)")
        errs = sorted({e for r in rows for e in r["errors"]})
        lines += [f"- page error: `{e}`" for e in errs]
        lines.append("")
    lines += ["Per width (failures only):", ""]
    for name, rows in results.items():
        for r in rows:
            for x in r["failures"]:
                lines.append(f"- {name} {r['width']} (column {r['column']}): {x}")
    return "\n".join(lines) + "\n"


def _edges(f: dict) -> dict:
    return {k: (None if f[k] is None else (round(f[k]["left"], 1), round(f[k]["right"], 1),
                                           round(f[k]["bottom"] - f[k]["top"], 1)))
            for k in ("plot", "drawn", "caption")}


def resize_check(browser, base_url: str, name: str, path: str, loads: list[Load],
                 out: Path, shots: bool) -> tuple[list[str], list[str]]:
    """Resize one page down through the widths and back, as a reader turning a tablet does.

    Loads the page (light mode) at the widest width, steps the viewport down
    through every other width and back up again, and at each step compares
    every figure's plot and caption (left and right edges, and height) with a
    fresh load at that width; for a Plotly figure, also the SVG plotly.js drew,
    which can come out a different size from its div. A figure that does not
    come back to its fresh layout -- a width that ratchets down, say -- is a
    failure. Back at the widest width, each plot is cropped again
    (``plots-resized/``) and pixel-diffed against the fresh load's crop.
    Returns (log lines, failures).
    """
    fresh = {l.width: l.data for l in loads if l.page == name and l.mode == loads[0].mode}
    ws = sorted(fresh, reverse=True)
    steps = ws + ws[-2::-1]
    log, failures = [f"sequence: {' → '.join(map(str, steps))} px ({loads[0].mode})"], []
    ctx = browser.new_context(viewport={"width": steps[0], "height": VIEWPORT_HEIGHT},
                              device_scale_factor=1, color_scheme="light")
    page = ctx.new_page()
    try:
        page.goto(base_url + path, wait_until="load", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.mouse.move(0, 0)
        page.evaluate(SETTLE_JS)
        if loads[0].mode == "dark":
            _switch_to_dark(page)
        for i, w in enumerate(steps):
            if i:
                page.set_viewport_size({"width": w, "height": VIEWPORT_HEIGHT})
                page.wait_for_timeout(700)          # plotly.js debounces its resize by 100 ms
                page.evaluate(SETTLE_JS)
            d = page.evaluate(MEASURE_JS, [TOLERANCE_PX, OVERLAY_LABELS])
            ref = {f["id"]: _edges(f) for f in fresh[w]["figures"]}
            bad = []
            for f in d["figures"]:
                e = _edges(f)
                r = ref.get(f["id"])
                if r is None:
                    continue
                for k in ("plot", "drawn", "caption"):
                    if e[k] and r[k] and any(abs(a - b) > TOLERANCE_PX for a, b in zip(e[k], r[k])):
                        bad.append(f"{f['id']} {k} {e[k][0]}–{e[k][1]} (h {e[k][2]}) "
                                   f"vs fresh {r[k][0]}–{r[k][1]} (h {r[k][2]})")
            log.append(f"step {i + 1}, {w} px: " + ("matches a fresh load" if not bad else "; ".join(bad)))
            failures += [f"resize, step {i + 1} ({w} px): {b}" for b in bad]
        if shots:
            (out / "plots-resized").mkdir(parents=True, exist_ok=True)
            page.add_style_tag(content="#quarto-header, .headroom { visibility: hidden !important; }")
            res = []
            for f in page.evaluate(MEASURE_JS, [TOLERANCE_PX, OVERLAY_LABELS])["figures"]:
                stem = f"{name}_{f['id']}_{steps[-1]}_{loads[0].mode}.png"
                pinned = page.evaluate(PIN_JS, f["id"])
                if not pinned:
                    continue
                clip = dict(x=pinned["left"], y=0, width=round(pinned["right"] - pinned["left"]),
                            height=round(pinned["bottom"]))
                page.screenshot(path=str(out / "plots-resized" / stem), clip=clip)
                page.evaluate(UNPIN_JS, f["id"])
                if (out / "plots" / stem).exists():
                    r = _diff_pair(out / "plots-resized" / stem, out / "plots" / stem)
                    res.append(f"{f['id']}: {r}")
                    if r != "identical":
                        failures.append(f"resize, back at {steps[-1]} px: {f['id']} plot {r}")
            if res:
                log.append(f"back at {steps[-1]} px, plot pixels against the fresh load: " + "; ".join(res))
    finally:
        ctx.close()
    return log, failures


# --------------------------------------------------------------------------- #
#  Reports
# --------------------------------------------------------------------------- #
def _e(r: dict | None) -> str:
    if not r:
        return "-"
    return f"{r['left']:.1f}–{r['right']:.1f} ({r['right'] - r['left']:.1f})"


def summary_markdown(loads: list[Load]) -> str:
    lines: list[str] = []
    for name in dict.fromkeys(l.page for l in loads):
        mine = [l for l in loads if l.page == name]
        lines += [f"## {name}", "",
                  "| width | mode | scrollWidth | column | mjx-container | .MathJax_SVG "
                  "| MathJax 2 scripts | plotly.js scripts | console errors | failures |",
                  "|--:|:--|--:|:--|--:|--:|--:|--:|--:|:--|"]
        for l in mine:
            d = l.data
            lines.append(
                f"| {l.width} | {l.mode} | {d['scrollWidth']} | {_e(d['column'])} | {d['mjx_container']} "
                f"| {d['mathjax_svg']} | {len(d['mathjax2_scripts'])} | {len(d['plotly_scripts'])} "
                f"| {len(l.console_errors)} | {len(l.failures)} |")
        figs = list(dict.fromkeys(f["id"] for l in mine for f in l.data["figures"]))
        lines += ["", "Figures, light mode (plot | caption; left–right (width), page px). "
                  "`!` = outside the column; `*` = dark mode's edges differ.", ""]
        widths = list(dict.fromkeys(l.width for l in mine))
        lines.append("| figure | " + " | ".join(f"{w}" for w in widths) + " |")
        lines.append("|:--|" + "|".join(":--" for _ in widths) + "|")
        for fid in figs:
            cells = []
            for w in widths:
                by_mode = {l.mode: next((f for f in l.data["figures"] if f["id"] == fid), None)
                           for l in mine if l.width == w}
                f = by_mode.get("light") or next(iter(by_mode.values()))
                if f is None:
                    cells.append("-")
                    continue
                differs = len({json.dumps([[round(r[k], 1) for k in ("left", "right")] if r else None
                                           for r in (g["plot"], g["caption"])])
                               for g in by_mode.values() if g}) > 1
                cells.append(f"{_e(f['plot'])}{'!' if f['plot_outside'] else ''} \\| "
                             f"{_e(f['caption'])}{'!' if f['caption_outside'] else ''}"
                             f"{' *' if differs else ''}")
            lines.append(f"| {fid} | " + " | ".join(cells) + " |")
        past = []
        for l in mine:
            c = l.data["column"]
            for f in l.data["figures"]:
                k = f["ink"]
                if c and k and (k["left"] < c["left"] - TOLERANCE_PX or k["right"] > c["right"] + TOLERANCE_PX):
                    past.append(f"- {l.width} {l.mode}: {f['id']} reaches {k['left']:.1f}–{k['right']:.1f} "
                                f"(column {c['left']:.1f}–{c['right']:.1f})")
        if past:
            lines += ["", "Figure content (any HTML in the figure, e.g. overlay labels) past the column, "
                      "whether or not it is clipped:", ""] + past
        over = [(l, o) for l in mine for o in l.data.get("overflowing", [])]
        if over:
            lines += ["", "Wider than the viewport, because of:", ""]
            seen = set()
            for l, o in over:
                key = (l.width, l.mode, o["tag"], o["id"], o["cls"], o["text"])
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"- {l.width} {l.mode}: `<{o['tag']}{' #' + o['id'] if o['id'] else ''}"
                             f"{' .' + o['cls'] if o['cls'] else ''}>` {o['left']}–{o['right']}"
                             f"{' in ' + o['in_figure'] if o['in_figure'] else ''}: {o['text']!r}")
        errs = sorted({e for l in mine for e in l.console_errors})
        if errs:
            lines += ["", "Console errors (all widths and modes):", ""] + [f"- `{e}`" for e in errs]
        fails = [(l, x) for l in mine for x in l.failures]
        if fails:
            lines += ["", "Failures:", ""] + [f"- {l.width} {l.mode}: {x}" for l, x in fails]
        lines.append("")
    return "\n".join(lines)


def contact_sheet(out: Path, name: str, loads: list[Load]) -> Path | None:
    from PIL import Image, ImageDraw, ImageFont
    mine = [l for l in loads if l.page == name]
    cols = [(l.width, l.mode) for l in mine]
    figs = list(dict.fromkeys(f["id"] for l in mine for f in l.data["figures"]))
    if not figs:
        return None
    target = 420                                       # cell width cap; phones at 1:1
    grid: dict[tuple[str, int, str], Image.Image] = {}
    for fid in figs:
        for w, m in cols:
            p = out / "figures" / f"{name}_{fid}_{w}_{m}.png"
            if p.exists():
                im = Image.open(p).convert("RGB")
                s = min(1.0, target / im.width)
                grid[(fid, w, m)] = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                                              Image.LANCZOS) if s < 1 else im
    if not grid:
        return None
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    gap, head = 12, 28
    col_w = [max((grid[(f, w, m)].width for f in figs if (f, w, m) in grid), default=60) for w, m in cols]
    row_h = [max((grid[(f, w, m)].height for w, m in cols if (f, w, m) in grid), default=40) + head
             for f in figs]
    W = sum(col_w) + gap * (len(cols) + 1)
    H = head + sum(row_h) + gap * (len(figs) + 1)
    sheet = Image.new("RGB", (W, H), (200, 200, 205))
    draw = ImageDraw.Draw(sheet)
    x = gap
    for (w, m), cw in zip(cols, col_w):
        draw.text((x, 6), f"{w} px · {m}", fill=(0, 0, 0), font=font)
        x += cw + gap
    y = head + gap
    for f, rh in zip(figs, row_h):
        draw.text((gap, y), f, fill=(0, 0, 0), font=font)
        x = gap
        for (w, m), cw in zip(cols, col_w):
            im = grid.get((f, w, m))
            if im is not None:
                sheet.paste(im, (x, y + head))
            x += cw + gap
        y += rh + gap
    path = out / f"{name}_contact.png"
    sheet.save(path, optimize=True)
    return path


def _diff_pair(p: Path, q: Path, mask: Path | None = None) -> str:
    """'identical', or how image ``p`` differs from reference ``q`` (mask of changes to ``mask``)."""
    import numpy as np
    from PIL import Image
    a, b = Image.open(p).convert("RGB"), Image.open(q).convert("RGB")
    if a.size != b.size:
        return f"size differs: {a.size} vs reference {b.size}"
    d = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))
    changed = d.max(axis=2) > 0
    n = int(changed.sum())
    if not n:
        return "identical"
    if mask is not None:
        Image.fromarray(np.where(changed, 255, 0).astype(np.uint8)).save(mask)
    return f"{n} pixel(s) differ (max channel delta {int(d.max())})"


def diff_against(out: Path, ref: Path) -> list[tuple[str, str]]:
    """(crop name, result) for every plots/ crop present in both runs."""
    results = []
    (out / "plots-diff").mkdir(exist_ok=True)
    for p in sorted((out / "plots").glob("*.png")):
        q = ref / "plots" / p.name
        if not q.exists():
            results.append((p.name, "no reference"))
            continue
        results.append((p.name, _diff_pair(p, q, out / "plots-diff" / p.name)))
    return results


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Layout checks on the built site, in headless Chromium.")
    ap.add_argument("--pages", nargs="+", metavar="PAGE",
                    help="post slugs, post folders or .qmd files, or site-relative .html paths "
                         "(default: every non-draft post)")
    ap.add_argument("--site", type=Path, default=REPO_ROOT / "_site", help="built site (default: _site)")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "_layout" / "latest",
                    help="output folder (default: _layout/latest)")
    ap.add_argument("--widths", nargs="+", type=int, default=list(WIDTHS))
    ap.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    ap.add_argument("--no-screenshots", action="store_true", help="measure only")
    ap.add_argument("--diff-against", type=Path, metavar="DIR",
                    help="an earlier run's folder: pixel-diff each plot crop against it")
    ap.add_argument("--no-resize-check", action="store_true",
                    help="skip resizing each page down through the widths and back")
    ap.add_argument("--sweep", action="store_true",
                    help="also load each page at every width from 320 to 1440 px in 10 px steps "
                         "(light mode, measurements only); takes several minutes")
    ap.add_argument("--sweep-only", action="store_true", help="run only the width sweep")
    args = ap.parse_args(argv)

    from playwright.sync_api import sync_playwright

    specs = args.pages or default_pages(REPO_ROOT)
    pages = [page_path(s) for s in specs]
    missing = [p for _, p in pages if not (args.site / p).is_file()]
    if missing:
        ap.error(f"not in {args.site}: {missing[0]} (render the site first)")
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    loads: list[Load] = []
    resized: dict[str, tuple[list[str], list[str]]] = {}
    swept: dict[str, list[dict]] = {}
    with SiteServer(args.site) as srv, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            if args.sweep or args.sweep_only:
                for name, path in pages:
                    swept[name] = sweep(browser, srv.url, name, path, list(SWEEP_WIDTHS))
                    bad = [r["width"] for r in swept[name] if r["failures"]]
                    print(f"{name} sweep: " + ("ok" if not bad else f"fails at {bands(bad, 10)} px"),
                          file=sys.stderr)
            for name, path in ([] if args.sweep_only else pages):
                for w in args.widths:
                    for m in args.modes:
                        load = measure(browser, srv.url, name, path, w, m, out, not args.no_screenshots)
                        loads.append(load)
                        status = "ok" if not load.failures else f"{len(load.failures)} failure(s)"
                        print(f"{name} {w} {m}: scrollWidth {load.data['scrollWidth']}, "
                              f"mjx {load.data['mjx_container']}, MathJax_SVG {load.data['mathjax_svg']}, "
                              f"plotly.js {len(load.data['plotly_scripts'])}: {status}", file=sys.stderr)
            if not args.no_resize_check and len(args.widths) > 1 and not args.sweep_only:
                for name, path in pages:
                    log, fails = resize_check(browser, srv.url, name, path, loads, out,
                                              not args.no_screenshots)
                    resized[name] = (log, fails)
                    print(f"{name} resize check: {'ok' if not fails else f'{len(fails)} failure(s)'}",
                          file=sys.stderr)
        finally:
            browser.close()

    (out / "measurements.json").write_text(json.dumps(
        [dict(page=l.page, width=l.width, mode=l.mode, console_errors=l.console_errors,
              failures=l.failures, **l.data) for l in loads], indent=1))
    if swept:
        (out / "sweep.json").write_text(json.dumps(swept, indent=1))
    md = summary_markdown(loads) if loads else ""
    if swept:
        md += sweep_markdown(swept, 10)
    if resized:
        md += "\n## Resize check\n"
        for name, (log, fails) in resized.items():
            md += f"\n{name}:\n\n" + "\n".join(f"- {x}" for x in log) + "\n"
    if not args.no_screenshots and loads:
        sheets = [contact_sheet(out, n, loads) for n, _ in pages]
        md += "\nContact sheets: " + ", ".join(str(s.relative_to(out)) for s in sheets if s) + "\n"
    if args.diff_against:
        res = diff_against(out, args.diff_against)
        md += f"\n## Plot pixel diff against {args.diff_against}\n\n" + "\n".join(
            f"- {n}: {r}" for n, r in res) + "\n"
    (out / "summary.md").write_text(md)
    print(md)

    failures = [(l, f) for l in loads for f in l.failures]
    failures += [(None, f) for _, fails in resized.values() for f in fails]
    failures += [(None, f) for rows in swept.values() for r in rows for f in r["failures"]]
    n_sweep = sum(len(rows) for rows in swept.values())
    print(f"{len(failures)} failure(s) in {len(loads)} page load(s), the resize check"
          + (f" and {n_sweep} sweep load(s)" if swept else "") + f"; output in {out}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
