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
