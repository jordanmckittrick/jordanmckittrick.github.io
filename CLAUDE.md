# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                               # one-time setup: creates .venv and installs everything
uv run quarto preview                                 # live local preview with auto-reload
uv run quarto render                                  # full build to _site/
uv run quarto publish gh-pages                        # render locally, push to gh-pages branch (only when asked; see below)
uv run python tools/check_post.py posts/<slug>/index.qmd   # mechanical checks on one post
uv run python tools/check_post.py --all               # every post, plus draft status and unused bib entries
uv run python -m pytest tools/                        # tests for the checker
uv run playwright install chromium                    # one-time setup for the layout check
uv run python tools/check_layout.py                   # layout of every non-draft post on the built _site/: 1440–360 px, light and dark
uv run python tools/check_layout.py --pages <slug> --out _layout/<run> --diff-against _layout/<earlier-run>
```

`uv run` executes inside the project's venv — no activation step needed.

## Architecture

This is a [Quarto](https://quarto.org) website published to GitHub Pages. Content is written in `.qmd` files (Quarto Markdown, a superset of Pandoc Markdown + code execution). Posts live under `posts/<slug>/index.qmd`.

**Key config files:**
- `_quarto.yml` — site-wide settings: navbar, theme, output dir, `execute: freeze: auto`
- `_brand.yml` — brand palette and typography (Libre Baskerville / Baskerville); Quarto ≥ 1.6 picks this up automatically. Does **not** style Plotly — that's handled separately.
- `posts/_metadata.yml` — front-matter defaults inherited by every post (author, toc, freeze, and `bibliography: ../references.bib`).

**`blogkit/` — shared Python package:**
- Installed as an editable package so any notebook can `import blogkit`.
- `blogkit/brand_plotly.py` — registers a `"blog"` Plotly template and sets it as the default (`plotly_white+blog`). Import it once at the top of a notebook to get consistent styling. Exports semantic colour constants (`HERO`, `SECONDARY`, `ACCENT`) for use in individual figures.
- `blogkit/plotly_html.py` — writes a Plotly figure's HTML itself instead of going through Plotly's notebook renderer: plotly.js loads once per page, no MathJax 2 (which would take over the page's MathJax 3), and the cell's `fig-alt` becomes `role="img"` plus `aria-label`. A fixed `layout.width` is the design width: the figure is drawn at that width or the column's, whichever is narrower, at its fixed height. Below 576 px (a phone) it switches to a compact layout: no drag-to-zoom or mode bar, plus the builder's own `compact=` override (plotly.js attribute strings), applied and reverted by a shared script as the width crosses 576 px. On a touch screen (`(hover: none) and (pointer: coarse)`) every figure, at every width, has no drag-to-zoom or mode bar, so a swipe on it scrolls the page; the layout still follows the width. Return `page_figure(fig, alt=fig_alt("fig-…"), compact=…)` from a figure builder.

**`tools/` — pre-publish checks:**
- `tools/check_post.py` — standard-library checker for mechanical errors (math delimiters, link syntax, unresolved cross-references, bare `@sec-` references, unknown citation keys, placeholders, image files and alt text, indented headings/divs, a post-level `bibliography:`). Prints `path:line: [ERROR|WARN] rule: message` and exits non-zero on any ERROR. Its docstring lists every rule.
- `tools/test_check_post.py` — pytest suite; fixture posts live in `tools/_fixtures/site/`. The leading underscore keeps Quarto from rendering them as site pages — keep it.
- `tools/check_layout.py` — serves `_site/` and loads pages in headless Chromium (Playwright) at 1440, 1180, 820, 390 and 360 px, light and dark. Measures page width, the text column, each figure's plot and caption edges, MathJax and plotly.js script counts, and console errors; writes screenshots, contact sheets and `summary.md` to `_layout/` (git-ignored). Also resizes each page down through the widths and back, checking every figure returns to its fresh layout. Exits non-zero if a page is wider than the viewport, a figure or caption leaves the column, MathJax 2 is on the page, plotly.js loads more than once, or a figure fails the resize check. Its docstring has the details.

**Freeze mechanism (`_freeze/`):**
- With `freeze: auto`, Quarto caches executed cell outputs in `_freeze/`. Subsequent renders skip re-execution unless the post's `.qmd` changes, so editing a post that has code re-executes it on the next render. (Editing only a sibling `.py` module does not; force it with `uv run quarto render posts/<slug>/index.qmd`.)
- `_freeze/` is committed intentionally — it lets the site rebuild on CI or a new machine without Python. Commit `_freeze/` together with the source change that produced it.
- Stop `quarto preview` before bulk edits: a running preview re-renders on every save and can freeze outputs from a half-edited file.
- `_site/` is git-ignored (built output pushed separately to `gh-pages`).

**Python dependencies** (managed by `uv`/`pyproject.toml`):
- `finlib` — public package from `github.com/jordanmckittrick/finlib`
- Standard scientific stack: numpy, scipy, pandas, matplotlib, plotly
- Dev only: `pytest` and `playwright` (in the `dev` dependency group)

## Bibliography

- One shared `references.bib` at the repo root, wired into every post through `posts/_metadata.yml`. Posts have **no** `bibliography:` line of their own (the checker flags one).
- Keys follow `authorYEARfirstword` (e.g. `breiman1961optimal`), and every entry has a `% VERIFIED:` comment above it saying what it was checked against.

## Checks

Run `uv run python tools/check_post.py <post>` after every batch of edits to a post, and before any commit that touches a post. Fix every ERROR; read every WARN. Before a publish, run it with `--all` to see each post's `draft:` value, and run `tools/check_layout.py` on a fresh `uv run quarto render`.

## Git and publishing

- Commit straight to `main` (the normal practice here).
- Never push, publish (`quarto publish gh-pages`) or deploy without asking first.
- Every unfinished post must be `draft: true` before anyone runs `quarto publish gh-pages`.

## Conventions

House conventions (notation, citation syntax, link syntax, alt text, epigraphs) are kept in a document in the owner's Claude project. The key mechanical rules:

- Section links are `[Title](#sec-…)`. Never a bare `@sec-…` (headings aren't numbered, so it renders as "Section 4.0.6"), and never `](@sec-…)`.
- Citations use their own brackets: write `[@key]`, not `(… [@key])`, which renders as "((Author 2026))".
- `fig-alt` is plain language: no LaTeX, no `$`, no placeholders. HTML figures (e.g. Plotly) need it passed through as an `aria-label` too, since Quarto only puts `fig-alt` on images.
- Numbers in the prose are asserted by code: a number stated in the text is recomputed and `assert`ed in a code cell.

## Adding a new post

```bash
mkdir -p posts/my-new-post
# create posts/my-new-post/index.qmd with front matter:
```

```yaml
---
title: "Title"
date: 2026-06-01
categories: [tag1, tag2]
draft: true
---
```

For posts with heavy computation, put the math/simulation logic in a sibling `.py` file and import it in the notebook — see `posts/shannons-demon/` as the reference pattern (separate `coin_flip_with_riskless_asset_model.py` and `plotting_functions.py`).

## Theming

Light/dark SCSS overrides live in `theme/light.scss` and `theme/dark.scss`, applied on top of the `cosmo`/`darkly` Quarto base themes. `theme/fonts.scss` is listed in both theme arrays in `_quarto.yml` and is the one place the body and heading font stack is set (Apple's Baskerville first, then Libre Baskerville), so both modes use the same font; it overrides `_brand.yml`'s typography. `styles.css` and `ratings.css` add global and page-specific styles.
