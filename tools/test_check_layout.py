"""Tests for the parts of tools/check_layout.py that need no browser.

Run with ``uv run python -m pytest tools/``. The browser-driven measurements
are exercised by running the tool itself on a built site.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_layout  # noqa: E402

SITE = Path(__file__).resolve().parent / "_fixtures" / "site"


def test_page_path_forms():
    assert check_layout.page_path("stranded") == ("stranded", "posts/stranded/index.html")
    assert check_layout.page_path("posts/stranded/") == ("stranded", "posts/stranded/index.html")
    assert check_layout.page_path("posts/stranded/index.qmd") == ("stranded", "posts/stranded/index.html")
    assert check_layout.page_path("about.html") == ("about", "about.html")
    assert check_layout.page_path("posts/stranded/index.html") == ("stranded", "posts/stranded/index.html")


def test_default_pages_skip_drafts(tmp_path):
    for slug, draft in (("kept", "false"), ("held", "true"), ("unset", None)):
        d = tmp_path / "posts" / slug
        d.mkdir(parents=True)
        front = f"draft: {draft}\n" if draft else ""
        (d / "index.qmd").write_text(f"---\ntitle: \"{slug}\"\n{front}---\n\nText.\n")
    assert check_layout.default_pages(tmp_path) == ["kept", "unset"]


def test_bands():
    assert check_layout.bands([], 10) == ""
    assert check_layout.bands([700, 620, 640, 630, 900, 710], 10) == "620–640, 700–710, 900"


def test_sweep_widths_cover_320_to_1440_every_10():
    ws = check_layout.SWEEP_WIDTHS
    assert ws[0] == 320 and ws[-1] == 1440 and len(ws) == 113
    assert all(b - a == 10 for a, b in zip(ws, ws[1:]))


def test_width_failures():
    col = {"left": 100.0, "right": 500.0}
    fig = dict(id="fig-a", plot_outside=False, caption_outside=False, labels_outside=[])
    ok = dict(scrollWidth=600, viewport=600, column=col, figures=[fig])
    assert check_layout.width_failures(ok) == []
    wide = dict(ok, scrollWidth=640)
    assert check_layout.width_failures(wide) == ["page is 640 px wide in a 600 px viewport"]
    labels = [{"text": "δ1 (a1 = 2.0)", "left": 88.0, "right": 190.0},
              {"text": "δ2 (a2 = 1.0)", "left": 410.0, "right": 512.5}]
    out = check_layout.width_failures(dict(ok, figures=[dict(fig, labels_outside=labels, caption_outside=True)]))
    assert out[0] == "fig-a: caption outside the column"
    assert out[1].startswith("fig-a: 2 overlay label(s) outside the column, by up to 12.5 px")


def test_diff_against(tmp_path):
    from PIL import Image
    a, b = tmp_path / "a" / "plots", tmp_path / "b" / "plots"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    Image.new("RGB", (4, 3), (255, 255, 255)).save(a / "same.png")
    Image.new("RGB", (4, 3), (255, 255, 255)).save(b / "same.png")
    im = Image.new("RGB", (4, 3), (255, 255, 255))
    im.putpixel((1, 1), (250, 255, 255))
    im.save(a / "changed.png")
    Image.new("RGB", (4, 3), (255, 255, 255)).save(b / "changed.png")
    Image.new("RGB", (5, 3), (255, 255, 255)).save(a / "resized.png")
    Image.new("RGB", (4, 3), (255, 255, 255)).save(b / "resized.png")
    res = dict(check_layout.diff_against(tmp_path / "a", tmp_path / "b"))
    assert res["same.png"] == "identical"
    assert res["changed.png"].startswith("1 pixel(s) differ (max channel delta 5)")
    assert res["resized.png"].startswith("size differs")
