"""Apply a rewrite of the China figure's words from china_figure_copy.xlsx to china_figure.py.

china_figure.py is the one source of every word the figure shows; ``uv run
python china_figure.py --export-copy`` lists them in china_figure_copy.xlsx,
one row each. Fill in "new text" where a row should change (in Excel, or in
Numbers, which saves china_figure_copy.numbers beside it), then:

    PYTHONPATH=../.. uv run python apply_copy.py            # check, then write china_figure.py
    PYTHONPATH=../.. uv run python apply_copy.py --dry-run  # check only, and say what would change
    PYTHONPATH=../.. uv run python apply_copy.py --book PATH  # another workbook (.xlsx or .numbers)

Without --book it reads whichever of china_figure_copy.numbers and
china_figure_copy.xlsx was saved last.

What a "new text" cell says:

* blank, or an em dash (—): keep the current text;
* a question for whoever applies the copy, the whole cell in square brackets
  ("[Do I need notes?]") or only question marks ("???"): nothing is changed,
  and the question is listed;
* anything else: the new text. A remark in square brackets inside it ("[I
  changed the year]") is taken out, and listed.

Nothing is written unless every changed row passes; otherwise each problem is listed and the script stops:

* an id the figure does not have;
* a placeholder that is unknown for that row, or malformed ({}, {x:.2f}, a stray brace);
* a box or a note that has lost its bold lead ("**1962–65** …", "**Sep 1988**: …");
* a picture card's text that would no longer leave its picture room at the full 920 px column.

Each string is rewritten where it stands in china_figure.py (found by
parsing the module, not by searching its text), as a plain string literal,
broken over lines as the module's own are. Run the module's checks after.
"""
from __future__ import annotations

import ast
import dataclasses
import re
import string
import sys
from pathlib import Path

HERE = Path(__file__).parent
MODULE = HERE / "china_figure.py"
WORKBOOK = HERE / "china_figure_copy.xlsx"
NUMBERS = HERE / "china_figure_copy.numbers"
KEEP = "—"                                                    # a cell that says only this keeps the current text
_QUESTION = re.compile(r"\A(\[.*\]|\?+)\Z", re.S)             # a cell that is a question, not copy
_REMARK = re.compile(r"\s*\[[^\[\]]*\]")                      # a remark inside new text

# How a row that joins two fields is split back into them: a box's bold lead and its text; a note's date and text.
_SPLIT = {("lead", "text"): re.compile(r"\A\*\*(.+?)\*\*\s+(.+)\Z", re.S),
          ("when", "text"): re.compile(r"\A\*\*(.+?)\*\*: (.+)\Z", re.S)}


# --------------------------------------------------------------------------- the module's source
def _assigned(tree: ast.Module, name: str) -> ast.expr:
    """The value assigned to a top-level name."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node.value
    raise KeyError(f"no top-level {name} in the module")


def _step(node: ast.expr, key, cf) -> ast.expr:
    """One step down a path: a list's or tuple's item, a dict's entry, a dataclass call's field."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return node.elts[key]
    if isinstance(node, ast.Dict):
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == key:
                return v
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id != "dict":
            fields = [f.name for f in dataclasses.fields(getattr(cf, node.func.id))]
            at = fields.index(key)
            if at < len(node.args):
                return node.args[at]
        for kw in node.keywords:
            if kw.arg == key:
                return kw.value
    raise KeyError(f"cannot find {key!r} in {ast.dump(node)[:80]}")


def resolve(tree: ast.Module, path: tuple, cf) -> list[ast.expr]:
    """The string literal(s) a row's path points at: one, or one per field where the path ends in a tuple of fields."""
    node = _assigned(tree, path[0])
    for key in path[1:-1] if isinstance(path[-1], tuple) else path[1:]:
        node = _step(node, key, cf)
    found = [_step(node, field, cf) for field in path[-1]] if isinstance(path[-1], tuple) else [node]
    for f in found:
        if not (isinstance(f, ast.JoinedStr) or (isinstance(f, ast.Constant) and isinstance(f.value, str))):
            raise TypeError(f"{path} does not point at a string literal")
    return found


def literal_value(source: str, node: ast.expr) -> str:
    """What a string literal in the source says. (An f-string with nothing to fill in, only {{ }}: its text.)"""
    if isinstance(node, ast.Constant):
        return node.value
    if all(isinstance(part, ast.Constant) for part in node.values):
        return "".join(part.value for part in node.values)
    return ast.get_source_segment(source, node)


def _literal(text: str, column: int, width: int = 110, enclosed: bool = False) -> str:
    """Source for a string literal standing at ``column``: one line if it fits, else parts on aligned lines.

    Parts on several lines are put in parentheses, unless the literal already
    stands alone inside some (``enclosed``), where they would be doubled.
    """
    quote = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if column + len(quote(text)) <= width:
        return quote(text)
    parts, current = [], ""
    for piece in re.split(r"(?<= )", text):          # each piece keeps the space that ends it
        if current and column + 1 + len(quote(current + piece)) > width:
            parts.append(current)
            current = piece
        else:
            current += piece
    parts.append(current)
    if enclosed:
        return ("\n" + " " * column).join(quote(p) for p in parts)
    return "(" + ("\n" + " " * (column + 1)).join(quote(p) for p in parts) + ")"


def rewrite(source: str, edits: dict[tuple, str], cf) -> str:
    """The module's source with each path's literal replaced by its new text. ``edits``: path -> text."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))

    def offset(lineno: int, col: int) -> int:                       # ast columns are UTF-8 bytes
        return starts[lineno - 1] + len(lines[lineno - 1].encode()[:col].decode())

    spans = []
    for path, text in edits.items():
        (node,) = resolve(tree, path, cf)
        a, z = offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset)
        # (Alone inside parentheses already, as an argument or a parenthesized string: no second pair.)
        enclosed = source[:a].rstrip().endswith("(") and source[z:].lstrip().startswith(")")
        spans.append((a, z, _literal(text, a - starts[node.lineno - 1], enclosed=enclosed)))
    for a, z, new in sorted(spans, reverse=True):
        source = source[:a] + new + source[z:]
    return source


# --------------------------------------------------------------------------- the workbook
def latest_book() -> Path:
    """The workbook saved last: the Numbers copy, if it is newer than the Excel one."""
    books = [p for p in (WORKBOOK, NUMBERS) if p.exists()]
    return max(books, key=lambda p: p.stat().st_mtime) if books else WORKBOOK


def _sheet_rows(path: Path) -> list[list]:
    """The "Copy" sheet's rows, the header first, from an Excel or a Numbers workbook."""
    if Path(path).suffix == ".numbers":
        from numbers_parser import Document
        return [list(r) for r in Document(str(path)).sheets["Copy"].tables[0].rows(values_only=True)]
    from openpyxl import load_workbook
    return [list(r) for r in load_workbook(path)["Copy"].iter_rows(values_only=True)]


def read_book(path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """What the workbook asks for: (edits, questions, remarks).

    ``edits``: id -> new text, with any [remarks] taken out; ``questions``:
    id -> a cell that is a question rather than copy; ``remarks``: id -> the
    remarks taken out of its new text. Blank cells and em dashes are left out.
    """
    rows = _sheet_rows(path)
    head = [str(c).strip() if c is not None else "" for c in rows[0]]
    at_id, at_new = head.index("id"), head.index("new text")
    edits, questions, remarks, seen = {}, {}, {}, set()
    for row in rows[1:]:
        if row[at_id] is None:
            continue
        id_, new = str(row[at_id]), row[at_new]
        if id_ in seen:
            raise ValueError(f"id {id_} is in the workbook twice")
        seen.add(id_)
        if new is None or not str(new).strip() or str(new).strip() == KEEP:
            continue
        new = str(new).strip()
        if _QUESTION.match(new):
            questions[id_] = new
            continue
        found = _REMARK.findall(new)
        if found:
            remarks[id_] = [r.strip() for r in found]
            new = _REMARK.sub("", new).strip()
        edits[id_] = new
    return edits, questions, remarks


def read_new_text(path: Path = WORKBOOK) -> dict[str, str]:
    """Every row of the workbook with new text: id -> new text (blank cells, em dashes and questions left out)."""
    return read_book(path)[0]


def problems(rows: dict[str, dict], edits: dict[str, str], cf) -> list[str]:
    """Everything wrong with a set of edits (id -> new text): empty if they can all be applied."""
    found = []
    words = None
    for id_, new in edits.items():
        row = rows.get(id_)
        if row is None:
            found.append(f"{id_}: no such id")
            continue
        try:
            fields = [(f, spec, conv) for _, f, spec, conv in string.Formatter().parse(new) if f is not None]
        except ValueError as err:
            found.append(f"{id_}: malformed placeholder ({err})")
            continue
        for f, spec, conv in fields:
            if not f.isidentifier() or spec or conv:
                found.append(f"{id_}: malformed placeholder {{{f}{'!' + conv if conv else ''}{':' + spec if spec else ''}}}"
                             " (write {name} only)")
            elif f not in row["allowed"]:
                found.append(f"{id_}: unknown placeholder {{{f}}} (this row may use: "
                             f"{', '.join(sorted(row['allowed'])[:12]) or 'none'}{' …' if len(row['allowed']) > 12 else ''})")
        joined = row["path"][-1] if isinstance(row["path"][-1], tuple) else None
        if joined and not _SPLIT[joined].match(new):
            shape = "**lead** text" if joined == ("lead", "text") else "**date**: text"
            found.append(f"{id_}: has lost its bold lead (write it as {shape})")
        if row["picture"] and row["room"] and not any(id_ in p for p in found):
            if words is None:
                words = cf.default_plan()[2]
            lead, text = _SPLIT[joined].match(new).groups()
            said = f"{lead} {text}".format(**words)
            if len(said) > row["room"]:
                found.append(f"{id_}: a picture card of {len(said)} characters no longer leaves its picture room at "
                             f"920 px (room for {row['room']}; about {len(said.split()) * row['room'] // len(said)} words)")
    return found


def edits_by_path(rows: dict[str, dict], edits: dict[str, str]) -> dict[tuple, str]:
    """Each edit as the literals it changes: a joined row split back into its fields; a shared one in every place."""
    out = {}
    for id_, new in edits.items():
        row = rows[id_]
        for path in row["paths"]:
            if isinstance(path[-1], tuple):
                for field, part in zip(path[-1], _SPLIT[path[-1]].match(new).groups()):
                    out[path[:-1] + (field,)] = part.strip()
            else:
                out[path] = new
    return out


def main(argv: list[str]) -> int:
    sys.path.insert(0, str(HERE))
    import china_figure as cf

    dry = "--dry-run" in argv
    flag = "--book" if "--book" in argv else "--xlsx" if "--xlsx" in argv else None
    book = Path(argv[argv.index(flag) + 1]) if flag else latest_book()
    rows = {r["id"]: r for r in cf.copy_rows()}
    edits, questions, remarks = read_book(book)
    print(f"Reading {book.name}.")
    for id_, cell in questions.items():
        print(f"  question, nothing changed: {id_}: {cell}")
    for id_, found in remarks.items():
        print(f"  remark taken out of {id_}: {' '.join(found)}")
    # (A row that says what it already says is no change.)
    edits = {id_: new for id_, new in edits.items() if id_ not in rows or rows[id_]["text"] != new}
    if not edits:
        print(f"{book.name}: no new text; nothing to do.")
        return 0
    found = problems(rows, edits, cf)
    if found:
        print(f"{book.name}: {len(found)} problem{'s' if len(found) > 1 else ''}; china_figure.py is unchanged.")
        for p in found:
            print("  " + p)
        return 1
    source = MODULE.read_text(encoding="utf-8")
    changed = edits_by_path(rows, edits)
    new_source = rewrite(source, changed, cf)
    # What was written says what was asked, and the module still parses.
    tree = ast.parse(new_source)
    for path, text in changed.items():
        (node,) = resolve(tree, path, cf)
        assert ast.literal_eval("(" + ast.get_source_segment(new_source, node) + ")") == text, f"{path} was not rewritten as asked"
    for id_, new in edits.items():
        print(f"  {id_}: {rows[id_]['text'][:60]!r} -> {new[:60]!r}")
    if dry:
        print(f"{len(edits)} row(s) would change ({len(changed)} literal(s)); --dry-run: china_figure.py is unchanged.")
        return 0
    MODULE.write_text(new_source, encoding="utf-8")
    print(f"{len(edits)} row(s) applied ({len(changed)} literal(s)) to china_figure.py. "
          "Now run its checks: PYTHONPATH=../.. uv run python china_figure.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
