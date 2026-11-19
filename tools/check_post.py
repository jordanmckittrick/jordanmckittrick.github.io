#!/usr/bin/env python3
"""Pre-publish checks for the blog's posts: mechanical errors only.

Usage::

    uv run python tools/check_post.py posts/<slug>/index.qmd   # one post (or several)
    uv run python tools/check_post.py --all                     # every post

Prints one line per problem, ``path:line: [ERROR|WARN] rule: message``, and
exits 1 if there is any ERROR (0 otherwise). A count goes to stderr. Standard
library only.

ERROR rules (the word before the colon in each message):

* ``math``         a paragraph with an odd number of inline ``$`` (``\\$`` and
                   ``$$`` ignored), or an unclosed ``$$`` display block.
* ``link``         ``](@`` anywhere; a space between ``]`` and ``(`` before a
                   link target (``] (#``, ``] (http``, ``] (../``); a ``(#id)``
                   or relative link that points nowhere.
* ``xref``         ``@eq-``/``@fig-``/``@tbl-`` (and Quarto's other crossref
                   prefixes) with no matching label in the same file.
* ``sec-ref``      a bare ``@sec-...``: headings aren't numbered on this site, so
                   it renders as "Section 4.0.6". Use ``[Title](#sec-...)``.
* ``cite``         a citation key that isn't in the root ``references.bib``.
* ``placeholder``  ``INSERT``, ``TODO``, ``FIXME``, ``???`` or a standalone ``TK``.
* ``image``        a missing image file; an image or figure cell with no
                   ``fig-alt``; a ``fig-alt`` that is empty, a placeholder, or
                   LaTeX (``$`` or ``\\cmd``, which screen readers read aloud).
* ``indent``       an indented line that starts a heading (``#``) or a fenced
                   div (``:::``); Pandoc renders it as literal text.
* ``front-matter`` a ``bibliography:`` field (posts use the shared one through
                   ``posts/_metadata.yml``).

WARN rules:

* ``unused-bib``     a ``references.bib`` entry no post cites (``--all`` only).
* ``draft``          each post's ``draft:`` value (``--all`` only).
* ``nested-parens``  a parenthetical citation ``[@...]`` inside your own
                     parentheses, which renders as "((Author 2026))".

What is skipped: front matter (except ``bibliography:``, ``image:``, ``draft:``
and ``nocite:``), code cells and other fenced blocks, inline code spans, and
HTML comments. A code cell's ``#| fig-cap:``, ``#| tbl-cap:`` and
``#| fig-alt:`` values are rendered text, so they are checked like prose.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent

# Quarto's cross-reference prefixes. Anything else after "@" is a citation key.
XREF_PREFIXES = {
    "fig", "tbl", "eq", "sec", "lst", "thm", "lem", "cor", "prp", "cnj", "def",
    "exm", "exr", "sol", "rem", "alg", "nte", "tip", "wrn", "imp", "cau",
}
# Pandoc's citation key: starts with a word character; internal punctuation is
# allowed only when a word character follows (so a trailing "." is not part of it).
_KEY = r"(?:\{(?P<bkey>[^}\s]+)\}|(?P<key>\w(?:\w|[:.#$%&\-+?<>~/](?=\w))*))"
CITE_RE = re.compile(r"(?<![\w\\@])@" + _KEY)
PLACEHOLDER_RE = re.compile(r"\b(?:INSERT|TODO|FIXME)\b|\?\?\?|(?<!\w)TK(?!\w)")
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
# Pandoc's markdown takes a heading or div fence only at the left margin; an
# indented one is a paragraph line (or an indented code block) and shows as text.
HEADING_RE = re.compile(r"^(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
DIV_FENCE_RE = re.compile(r"^:{3,}")
INDENTED_BLOCK_RE = re.compile(r"^[ \t]+(?:#{1,6}(?:[ \t]|$)|:{3,})")
ATTR_ID_RE = re.compile(r"(?:^|\s)#([^\s#.{}=\"']+)")
LINK_TARGET_RE = re.compile(r"\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
LATEX_RE = re.compile(r"\$|\\[A-Za-z]+")
CAPTION_OPTIONS = ("fig-cap", "tbl-cap", "fig-alt")


@dataclass(frozen=True, order=True)
class Problem:
    path: str
    line: int
    severity: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.severity}] {self.message}"


@dataclass
class Cell:
    """A fenced block: a code cell, a raw ``{=html}`` block, or plain code."""
    start: int                                   # 0-based line of the opening fence
    info: str                                    # text after the fence, e.g. "{python}"
    lines: list[tuple[int, str]] = field(default_factory=list)
    options: dict[str, tuple[int, str]] = field(default_factory=dict)   # "#|" options


@dataclass
class Block:
    """Prose Pandoc reads as one unit: a paragraph, a heading, or a caption option."""
    start: int                                   # 0-based line of its first line
    text: str                                    # its lines joined by "\n"
    heading: bool = False
    alt: bool = False                            # a cell's fig-alt value


# ---------------------------------------------------------------------------
# Masking: replace spans with spaces, keeping offsets and newlines intact.
# ---------------------------------------------------------------------------

def _blank(m: re.Match) -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def mask_code(s: str) -> str:
    """Inline code spans: a run of n backticks up to the next run of exactly n."""
    return re.sub(r"(?<!`)(`+)(?!`)[\s\S]+?(?<!`)\1(?!`)", _blank, s)


def mask_math(s: str) -> str:
    """``\\$``, then ``$$...$$``, then ``$...$`` pairs. A lone ``$`` survives."""
    s = s.replace("\\$", "  ")
    s = re.sub(r"\$\$[\s\S]*?\$\$", _blank, s)
    return re.sub(r"\$[^$]*\$", _blank, s)


def mask_targets(s: str) -> str:
    """Link targets ``](...)``, autolinks, bare URLs and ``{...}`` attribute blocks."""
    s = re.sub(r"(?<=\])\([^)]*\)", _blank, s)
    s = re.sub(r"<[A-Za-z][A-Za-z0-9+.\-]*:[^>\s]*>", _blank, s)
    s = re.sub(r"https?://\S+", _blank, s)
    return re.sub(r"\{[^{}\n]*\}", _blank, s)


def yaml_scalar(v: str) -> str:
    """The value of a one-line YAML scalar, quotes and escapes resolved."""
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        try:
            return json.loads(v)
        except ValueError:
            return v[1:-1]
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return v


def auto_id(title: str) -> str:
    """Pandoc's automatic heading identifier for a heading's text."""
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", title)          # links -> their text
    t = re.sub(r"(?<!\w)[*_]+|[*_]+(?!\w)", "", t)                 # emphasis markers
    t = "".join(c for c in t if c.isalnum() or c in "_-." or c.isspace())
    t = re.sub(r"\s", "-", t.strip()).lower()
    while t and not t[0].isalpha():
        t = t[1:]
    return t or "section"


# ---------------------------------------------------------------------------
# Parsing a .qmd
# ---------------------------------------------------------------------------

class Doc:
    """A .qmd split into front matter, fenced blocks and prose blocks."""

    def __init__(self, path: Path):
        self.path = path
        self.lines = path.read_text(encoding="utf-8").split("\n")
        self.front: dict[str, tuple[int, str]] = {}   # top-level key -> (line, raw value)
        self.front_end = -1                          # last front-matter line (0-based)
        self.cells: list[Cell] = []
        self.blocks: list[Block] = []
        self._parse()
        self.labels = self._labels()                 # crossref targets in this file
        self.sec_titles = self._sec_titles()         # explicit {#sec-...} -> heading text
        self.anchors = self._anchors()               # every id a "#..." link can reach

    def _parse(self) -> None:
        lines, n = self.lines, len(self.lines)
        prose = [True] * n
        i = 0
        if n and lines[0].strip() == "---":
            j = 1
            while j < n and lines[j].strip() not in ("---", "..."):
                m = re.match(r"^([A-Za-z][\w-]*)[ \t]*:(.*)$", lines[j])
                if m:
                    self.front[m.group(1)] = (j, m.group(2).strip())
                j += 1
            self.front_end = min(j, n - 1)
            for k in range(self.front_end + 1):
                prose[k] = False
            i = self.front_end + 1

        cell = None
        fence = ""
        while i < n:
            ln = lines[i]
            if cell is None:
                m = FENCE_RE.match(ln)
                if m:
                    fence = m.group(1)
                    cell = Cell(i, m.group(2).strip())
                    self.cells.append(cell)
                    prose[i] = False
            else:
                prose[i] = False
                if re.match(rf"^[ \t]*{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$", ln):
                    cell = None
                else:
                    cell.lines.append((i, ln))
            i += 1

        for c in self.cells:                         # "#|" options at the top of a cell
            last = None
            for idx, ln in c.lines:
                m = re.match(r"^#\|[ \t]*([\w-]+)[ \t]*:(.*)$", ln)
                if m:
                    last = m.group(1)
                    c.options[last] = (idx, yaml_scalar(m.group(2)))
                elif ln.startswith("#|") and last:   # continuation of a block scalar
                    j, v = c.options[last]
                    v = "" if v in ("|", ">", "|-", ">-") else v
                    c.options[last] = (j, (v + " " + ln[2:].strip()).strip())
                else:
                    break

        # Prose text with code and front matter blanked, then HTML comments masked.
        text = "\n".join(ln if prose[k] else "" for k, ln in enumerate(lines))
        text = re.sub(r"<!--[\s\S]*?-->", _blank, text)
        masked = text.split("\n")

        start, buf = None, []

        def flush() -> None:
            nonlocal start, buf
            if buf:
                self.blocks.append(Block(start, "\n".join(buf)))
            start, buf = None, []

        for k, ln in enumerate(masked):
            if not ln.strip():
                flush()
            elif HEADING_RE.match(ln) or DIV_FENCE_RE.match(ln):
                flush()
                self.blocks.append(Block(k, ln, heading=bool(HEADING_RE.match(ln))))
            else:
                if start is None:
                    start = k
                buf.append(ln)
        flush()

        for c in self.cells:                         # captions and alt text are prose
            for key in CAPTION_OPTIONS:
                if key in c.options:
                    idx, val = c.options[key]
                    self.blocks.append(Block(idx, val, alt=key == "fig-alt"))
        self.blocks.sort(key=lambda b: b.start)

    def _attr_ids(self) -> list[str]:
        ids = []
        for b in self.blocks:
            for attrs in re.findall(r"\{([^{}]*)\}", mask_math(mask_code(b.text))):
                ids += ATTR_ID_RE.findall(attrs)
        return ids

    def _labels(self) -> set[str]:
        labels = set(self._attr_ids())
        for c in self.cells:
            if "label" in c.options:
                labels.add(c.options["label"][1])
        return labels

    def _headings(self) -> list[tuple[int, str, str | None]]:
        """(line, title, explicit id or None) for every heading."""
        out = []
        for b in self.blocks:
            if not b.heading:
                continue
            title = HEADING_RE.match(b.text).group(2) or ""
            m = re.search(r"\s*\{([^{}]*)\}\s*$", title)
            explicit = None
            if m:
                ids = ATTR_ID_RE.findall(m.group(1))
                explicit = ids[0] if ids else None
                title = title[:m.start()]
            out.append((b.start, title.strip(), explicit))
        return out

    def _sec_titles(self) -> dict[str, str]:
        return {i: t for _, t, i in self._headings() if i and i.startswith("sec-")}

    def _anchors(self) -> set[str]:
        anchors = set(self.labels)
        seen: dict[str, int] = {}
        for _, title, explicit in self._headings():
            if explicit:
                continue
            a = auto_id(title)
            if a in seen:
                seen[a] += 1
                a = f"{a}-{seen[a]}"
            else:
                seen[a] = 0
            anchors.add(a)
        for c in self.cells:                         # ids in raw HTML blocks
            for _, ln in c.lines:
                anchors.update(re.findall(r"\bid=[\"']([^\"']+)[\"']", ln))
        return anchors

    def front_value(self, key: str) -> tuple[int, str] | None:
        return self.front.get(key)

    def nocite(self) -> set[str]:
        """Keys in a ``nocite:`` field (``*`` means every entry)."""
        if "nocite" not in self.front:
            return set()
        j = self.front["nocite"][0]
        chunk = [self.lines[j].split(":", 1)[1]]
        for k in range(j + 1, self.front_end):
            if re.match(r"^[A-Za-z]", self.lines[k]):
                break
            chunk.append(self.lines[k])
        text = " ".join(chunk)
        keys = {m.group("key") or m.group("bkey") for m in CITE_RE.finditer(text)}
        if "@*" in text:
            keys.add("*")
        return keys


@lru_cache(maxsize=None)
def load_doc(path: Path) -> Doc:
    return Doc(path)


def read_bib(path: Path) -> dict[str, int]:
    """Entry key -> 1-based line in the .bib file."""
    keys = {}
    for i, ln in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = re.match(r"^\s*@(\w+)\s*[{(]\s*([^,\s]+)\s*,", ln)
        if m and m.group(1).lower() not in ("comment", "string", "preamble"):
            keys[m.group(2)] = i
    return keys


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _line_of(block: Block, offset: int) -> int:
    """1-based file line of a character offset within a block."""
    return block.start + block.text.count("\n", 0, offset) + 1


def _find_images(p2: str):
    """Yield (start, target, target_span, attrs_span or None) for each ``![...](...)``.

    Brackets are matched on text with code and math masked, so a ``]`` inside
    ``$[0, 1]$`` in a caption doesn't end it early.
    """
    for m in re.finditer(r"!\[", p2):
        i, depth = m.end(), 1
        while i < len(p2) and depth:
            depth += {"[": 1, "]": -1}.get(p2[i], 0)
            i += 1
        if depth or i >= len(p2) or p2[i] != "(":
            continue
        t0, j, angle = i, i + 1, False
        while j < len(p2) and (angle or p2[j] != ")"):
            angle = {"<": True, ">": False}.get(p2[j], angle)
            j += 1
        if j >= len(p2):
            continue
        target = p2[t0 + 1:j].strip()
        target = target[1:target.index(">")] if target.startswith("<") else target.split()[0] if target else ""
        attrs = None
        if j + 1 < len(p2) and p2[j + 1] == "{":
            k, quote = j + 2, None
            while k < len(p2) and (quote or p2[k] != "}"):
                if p2[k] in "\"'" and (quote is None or quote == p2[k]):
                    quote = None if quote else p2[k]
                k += 1
            attrs = (j + 2, k)
        yield m.start(), target, (t0, j + 1), attrs


def _fig_alt(attrs: str) -> str | None:
    m = re.search(r"(?:^|\s)fig-alt=(?:\"((?:[^\"\\]|\\.)*)\"|'([^']*)')", attrs)
    if not m:
        return None
    return re.sub(r"\\(.)", r"\1", m.group(1)) if m.group(1) is not None else m.group(2)


def _alt_problems(alt: str | None, what: str) -> list[str]:
    if alt is None:
        return [f"image: {what} has no fig-alt"]
    if not alt.strip():
        return [f"image: {what} has an empty fig-alt"]
    if "INSERT" in alt:
        return [f"image: {what} has a placeholder fig-alt"]
    if LATEX_RE.search(alt):
        return [f"image: {what} has LaTeX in its fig-alt ($ or a \\command), which screen "
                f"readers read aloud; write it in plain words"]
    return []


def _local_file(target: str, base: Path, root: Path) -> Path | None:
    """The local file a link or image target names, or None for URLs and fragments."""
    if not target or target.startswith("#") or URL_SCHEME_RE.match(target):
        return None
    t = unquote(re.split(r"[?#]", target, maxsplit=1)[0])
    return (root / t.lstrip("/")) if t.startswith("/") else (base / t)


def _resolve_page(p: Path) -> Path | None:
    """A link's file, allowing for rendered names: ``x.html`` and ``dir/`` mean ``.qmd``."""
    if p.is_dir():
        p = p / "index.qmd"
    if p.exists():
        return p
    if p.suffix == ".html" and p.with_suffix(".qmd").exists():
        return p.with_suffix(".qmd")
    return None


def check_doc(doc: Doc, root: Path, bib: dict[str, int]) -> tuple[list[tuple[int, str, str]], set[str]]:
    """All single-file checks. Returns ((line, severity, message), ...) and the cited keys."""
    out: list[tuple[int, str, str]] = []
    cited: set[str] = set()
    base = doc.path.parent

    def err(line: int, msg: str) -> None:
        out.append((line, "ERROR", msg))

    def warn(line: int, msg: str) -> None:
        out.append((line, "WARN", msg))

    # 9. Front matter.
    for k in range(doc.front_end + 1):
        if re.match(r"^\s*bibliography\s*:", doc.lines[k]):
            err(k + 1, "front-matter: remove `bibliography:`; posts use the shared "
                       "references.bib through posts/_metadata.yml")
    if "image" in doc.front:
        k, v = doc.front["image"]
        f = _local_file(yaml_scalar(v), base, root)
        if f is not None and not f.exists():
            err(k + 1, f"image: listing image '{yaml_scalar(v)}' does not exist")

    # 8. Indentation (raw lines, so the indentation is still there).
    in_cell = {idx for c in doc.cells for idx in [c.start] + [i for i, _ in c.lines]}
    for b in doc.blocks:
        for off, ln in enumerate(b.text.split("\n")):
            if b.start + off in in_cell:
                continue
            if INDENTED_BLOCK_RE.match(ln):
                kind = "heading" if ln.lstrip().startswith("#") else "fenced div"
                err(b.start + off + 1, f"indent: indented {kind} renders as literal text; "
                                       f"remove the leading spaces")

    # 7b. Figure cells need their own alt text.
    for c in doc.cells:
        label = c.options.get("label", (None, ""))[1]
        if label.startswith("fig-"):
            line = c.options["label"][0] + 1
            alt = c.options.get("fig-alt")
            for msg in _alt_problems(alt[1] if alt else None, f"figure cell '{label}'"):
                err((alt[0] if alt else line - 1) + 1, msg)

    odd_dd: list[tuple[Block, int, int]] = []        # blocks with an odd number of $$
    for b in doc.blocks:
        p1 = mask_code(b.text)
        p2 = mask_math(p1)
        p3 = mask_targets(p2)

        # 1. Math delimiters.
        t = p1.replace("\\$", "  ")
        dd = [m.start() for m in re.finditer(r"\$\$", t)]
        if len(dd) % 2:
            odd_dd.append((b, _line_of(b, dd[0]), _line_of(b, dd[-1])))
        t = re.sub(r"\$\$[\s\S]*?\$\$", _blank, t).replace("$$", "  ")
        singles = t.count("$")
        if singles % 2:
            last = b.start + b.text.count("\n") + 1
            span = f"line {b.start + 1}" if last == b.start + 1 else f"lines {b.start + 1}-{last}"
            err(b.start + 1, f"math: odd number of inline $ ({singles}) in the paragraph at "
                             f"{span}; close it, or write \\$ for a dollar sign")

        # 7a. Images.
        image_spans, attr_spans = [], []
        for start, target, tspan, aspan in _find_images(p2):
            image_spans.append(tspan)
            if aspan:
                attr_spans.append(aspan)
            line = _line_of(b, start)
            f = _local_file(target, base, root)
            if f is not None and not f.exists():
                err(line, f"image: file '{target}' does not exist")
            alt = _fig_alt(p1[aspan[0]:aspan[1]]) if aspan else None
            for msg in _alt_problems(alt, f"image '{target}'"):
                err(line, msg)

        # 2 and 3. Link syntax and link targets.
        for m in re.finditer(r"\]\(@", p1):
            err(_line_of(b, m.start()), "link: `](@...)` goes nowhere; a link to a label "
                                        "is `](#label)`")
        for m in re.finditer(r"\][ \t\n]+\((?=#|https?://|\.\.?/|mailto:|@)", p1):
            err(_line_of(b, m.start()), "link: a space between `]` and `(` breaks the link")
        for m in LINK_TARGET_RE.finditer(p1):
            if any(s <= m.start() + 1 < e for s, e in image_spans):
                continue
            target = m.group(1).strip("<>")
            line = _line_of(b, m.start())
            if target.startswith("#sec-"):
                if target[1:] not in doc.sec_titles:
                    err(line, f"link: no heading has {{{target}}} in this file")
            elif target.startswith("@"):
                continue                              # reported above as `](@`
            elif target.startswith("#"):
                if target[1:] not in doc.anchors:
                    err(line, f"link: no element has id '{target[1:]}' in this file")
            else:
                f = _local_file(target, base, root)
                if f is None:
                    continue
                page = _resolve_page(f)
                if page is None:
                    err(line, f"link: '{target}' does not exist")
                elif "#" in target and page.suffix == ".qmd":
                    anchor = target.split("#", 1)[1]
                    if anchor and anchor not in load_doc(page.resolve()).anchors:
                        err(line, f"link: '{target}': no heading or element there has "
                                  f"id '{anchor}'")

        # 3, 4 and 5. Cross-references, bare @sec, citations.
        for m in CITE_RE.finditer(p3):
            key = m.group("key") or m.group("bkey")
            line = _line_of(b, m.start())
            prefix = key.split("-", 1)[0] if "-" in key else ""
            if prefix == "sec":
                title = doc.sec_titles.get(key)
                hint = (f"[{title}](#{key})" if title else f"[Title](#{key})")
                note = "" if title else f" (and no heading has {{#{key}}})"
                err(line, f"sec-ref: bare @{key} renders as an unfindable section number; "
                          f"write {hint}{note}")
            elif prefix in XREF_PREFIXES:
                if key not in doc.labels:
                    err(line, f"xref: @{key} has no matching label in this file")
            else:
                cited.add(key)
                if key not in bib:
                    err(line, f"cite: @{key} is not in references.bib")

        # 6. Placeholders.
        for m in PLACEHOLDER_RE.finditer(p2):
            if b.alt or any(s <= m.start() < e for s, e in attr_spans):
                continue                              # reported above as a fig-alt problem
            err(_line_of(b, m.start()), f"placeholder: '{m.group(0)}' left in the text")

        # 12. Parenthetical citation inside the author's own parentheses.
        for m in re.finditer(r"\[[^\[\]]*\]", p3):
            if not CITE_RE.search(m.group(0)):
                continue
            nxt = p1[m.end():m.end() + 1]
            if nxt in ("(", "[", "{"):
                continue                              # a link or span, not a citation
            depth = 0
            for ch in p3[:m.start()]:
                depth = depth + 1 if ch == "(" else max(0, depth - 1) if ch == ")" else depth
            if depth:
                warn(_line_of(b, m.start()), "nested-parens: a parenthetical citation inside "
                                             "parentheses renders as '((Author Year))'; drop "
                                             "your parentheses and move the words into the "
                                             "brackets ([see @key]), or cite as @key")

    # 1b. Report each broken $$ block once. A blank line inside display math
    # leaves an odd $$ in the paragraph before it and in the one after.
    i = 0
    while i < len(odd_dd):
        b, _, opener = odd_dd[i]
        if i + 1 < len(odd_dd):
            b2, closer, _ = odd_dd[i + 1]
            gap = doc.lines[b.start + b.text.count("\n") + 1:b2.start]
            if gap and all(not g.strip() for g in gap):
                err(opener, f"math: the $$ display block opened here is split by a blank "
                            f"line before its closing $$ (line {closer})")
                i += 2
                continue
        err(opener, "math: unclosed $$ display block")
        i += 1

    cited |= doc.nocite()
    return out, cited


def run(posts: list[Path], root: Path, all_mode: bool) -> list[Problem]:
    bib_path = root / "references.bib"
    problems: list[Problem] = []
    if not bib_path.exists():
        problems.append(Problem(_rel(bib_path), 1, "ERROR", "cite: references.bib not found"))
        bib = {}
    else:
        bib = read_bib(bib_path)

    cited_all: set[str] = set()
    for post in posts:
        doc = load_doc(post.resolve())
        found, cited = check_doc(doc, root.resolve(), bib)
        cited_all |= cited
        problems += [Problem(_rel(post), ln, sev, msg) for ln, sev, msg in found]
        if all_mode:
            d = doc.front_value("draft")
            if d is None:
                problems.append(Problem(_rel(post), 1, "WARN",
                                        "draft: no draft field; a publish puts this post online"))
            else:
                v = yaml_scalar(d[1]).lower()
                note = ("held back from a publish" if v == "true"
                        else "a publish puts this post online")
                problems.append(Problem(_rel(post), d[0] + 1, "WARN", f"draft: {v} ({note})"))

    if all_mode and "*" not in cited_all:
        for key, line in bib.items():
            if key not in cited_all:
                problems.append(Problem(_rel(bib_path), line, "WARN",
                                        f"unused-bib: @{key} is cited by no post"))
    return sorted(set(problems))


def _rel(p: Path) -> str:
    try:
        return os.path.relpath(p)
    except ValueError:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mechanical pre-publish checks for blog posts.")
    ap.add_argument("posts", nargs="*", type=Path, help="post .qmd files to check")
    ap.add_argument("--all", action="store_true", help="check every posts/*/index.qmd")
    ap.add_argument("--root", type=Path, default=REPO_ROOT,
                    help="site root holding references.bib and posts/ (default: this repo)")
    args = ap.parse_args(argv)
    if not args.all and not args.posts:
        ap.error("give one or more post files, or --all")
    posts = list(args.posts)
    if args.all:
        posts += sorted((args.root / "posts").glob("*/index.qmd"))
    missing = [p for p in posts if not p.is_file()]
    if missing:
        ap.error(f"no such file: {missing[0]}")

    problems = run(posts, args.root, args.all)
    for p in problems:
        print(p)
    errors = sum(p.severity == "ERROR" for p in problems)
    warns = len(problems) - errors
    print(f"{errors} error(s), {warns} warning(s) in {len(posts)} file(s)", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
