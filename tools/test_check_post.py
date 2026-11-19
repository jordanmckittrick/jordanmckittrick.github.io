"""Tests for tools/check_post.py. Run with ``uv run python -m pytest tools/``.

Each fixture post under ``_fixtures/site/posts/`` holds one example of one rule
(``err-*`` for errors, ``warn-*`` for warnings). ``clean`` holds none but is
full of things the checker must NOT flag; ``linked`` is a second clean post
that the others link into. ``_fixtures/site/references.bib`` is the fixture
bibliography.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_post  # noqa: E402

SITE = Path(__file__).resolve().parent / "_fixtures" / "site"


def post(name: str) -> Path:
    return SITE / "posts" / name / "index.qmd"


def found(name: str) -> set[tuple[int, str, str]]:
    """(line, severity, rule) for every problem in one fixture post."""
    return {(p.line, p.severity, p.message.split(":", 1)[0])
            for p in check_post.run([post(name)], SITE, all_mode=False)}


@pytest.mark.parametrize("name", ["clean", "linked"])
def test_clean_posts_have_no_problems(name):
    assert check_post.run([post(name)], SITE, all_mode=False) == []


@pytest.mark.parametrize("name, expected", [
    ("err-math", {(5, "ERROR", "math"),        # odd number of inline $
                  (7, "ERROR", "math"),        # $$ block split by a blank line (reported once)
                  (14, "ERROR", "math")}),     # $$ never closed
    ("err-link", {(7, "ERROR", "link"),        # ](@sec-intro)
                  (9, "ERROR", "link")}),      # [Intro] (#sec-intro)
    ("err-xref", {(7, "ERROR", "xref"),        # @eq-missing
                  (9, "ERROR", "link"),        # (#sec-missing)
                  (11, "ERROR", "link"),       # ../linked/index.qmd#no-such-anchor
                  (13, "ERROR", "link")}),     # ../no-such-post/index.qmd
    ("err-sec-ref", {(7, "ERROR", "sec-ref")}),
    ("err-cite", {(5, "ERROR", "cite")}),
    ("err-placeholder", {(5, "ERROR", "placeholder"),    # INSERT
                         (7, "ERROR", "placeholder"),    # TODO
                         (9, "ERROR", "placeholder"),    # FIXME
                         (11, "ERROR", "placeholder"),   # ???
                         (13, "ERROR", "placeholder")}), # TK
    ("err-image", {(5, "ERROR", "image"),      # file missing
                   (7, "ERROR", "image"),      # no fig-alt
                   (9, "ERROR", "image"),      # empty fig-alt
                   (11, "ERROR", "image"),     # INSERT in fig-alt
                   (13, "ERROR", "image"),     # LaTeX in fig-alt
                   (16, "ERROR", "image")}),   # figure cell with no #| fig-alt
    ("err-indent", {(7, "ERROR", "indent"),    # "  # References"
                    (9, "ERROR", "indent")}),  # "  ::: {#refs}"
    ("err-front-matter", {(3, "ERROR", "front-matter")}),
    ("warn-nested-parens", {(5, "WARN", "nested-parens")}),
])
def test_each_rule_fires_exactly_where_expected(name, expected):
    assert found(name) == expected


def test_one_problem_per_line_here():
    """No rule double-reports another's problem on these lines (e.g. `](@` as a missing file)."""
    probs = check_post.run([post("err-link"), post("err-image")], SITE, all_mode=False)
    keys = [(p.path, p.line) for p in probs]
    assert len(keys) == len(set(keys))


def test_messages_name_the_fix():
    msgs = {p.message for p in check_post.run([post("err-sec-ref")], SITE, all_mode=False)}
    assert any("[Intro](#sec-intro)" in m for m in msgs)


def test_all_mode_reports_drafts_and_unused_entries():
    posts = sorted((SITE / "posts").glob("*/index.qmd"))
    probs = check_post.run(posts, SITE, all_mode=True)
    drafts = {(Path(p.path).parent.name, p.message) for p in probs if p.message.startswith("draft:")}
    assert ("clean", "draft: false (a publish puts this post online)") in drafts
    assert ("linked", "draft: true (held back from a publish)") in drafts
    assert ("err-cite", "draft: no draft field; a publish puts this post online") in drafts
    assert len(drafts) == len(posts)
    unused = [p for p in probs if p.message.startswith("unused-bib:")]
    assert [(p.line, p.message) for p in unused] == [(18, "unused-bib: @unused2019entry is cited by no post")]
    assert all(p.severity == "WARN" for p in unused)


def test_single_file_mode_has_no_site_wide_warnings():
    probs = check_post.run([post("clean")], SITE, all_mode=False)
    assert not [p for p in probs if p.message.split(":")[0] in ("draft", "unused-bib")]


def test_cli_output_format_and_exit_code(capsys):
    assert check_post.main(["--root", str(SITE), str(post("clean"))]) == 0
    assert capsys.readouterr().out == ""

    assert check_post.main(["--root", str(SITE), str(post("err-cite"))]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines and all(re.fullmatch(r".+:\d+: \[(ERROR|WARN)\] [\w-]+: .+", ln) for ln in lines)

    # Warnings alone don't fail the run.
    assert check_post.main(["--root", str(SITE), str(post("warn-nested-parens"))]) == 0


@pytest.mark.parametrize("title, anchor", [
    ("The connection to information theory", "the-connection-to-information-theory"),
    ("An alternative characterization of $q^*$", "an-alternative-characterization-of-q"),
    ("1. *Emphasis*, `code` and [a link](x)", "emphasis-code-and-a-link"),
])
def test_auto_heading_ids_follow_pandoc(title, anchor):
    assert check_post.auto_id(title) == anchor
