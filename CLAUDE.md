# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                          # one-time setup: creates .venv and installs everything
uv run quarto preview            # live local preview with auto-reload
uv run quarto render             # full build to _site/
uv run quarto publish gh-pages   # render locally, push to gh-pages branch
```

`uv run` executes inside the project's venv — no activation step needed.

## Architecture

This is a [Quarto](https://quarto.org) website published to GitHub Pages. Content is written in `.qmd` files (Quarto Markdown, a superset of Pandoc Markdown + code execution). Posts live under `posts/<slug>/index.qmd`.

**Key config files:**
- `_quarto.yml` — site-wide settings: navbar, theme, output dir, `execute: freeze: auto`
- `_brand.yml` — brand palette and typography (Libre Baskerville / Baskerville); Quarto ≥ 1.6 picks this up automatically. Does **not** style Plotly — that's handled separately.
- `posts/_metadata.yml` — front-matter defaults inherited by every post (author, toc, freeze).

**`blogkit/` — shared Python package:**
- Installed as an editable package so any notebook can `import blogkit`.
- `blogkit/brand_plotly.py` — registers a `"blog"` Plotly template and sets it as the default (`plotly_white+blog`). Import it once at the top of a notebook to get consistent styling. Exports semantic colour constants (`HERO`, `SECONDARY`, `ACCENT`) for use in individual figures.

**Freeze mechanism (`_freeze/`):**
- With `freeze: auto`, Quarto caches executed cell outputs in `_freeze/`. Subsequent renders skip re-execution unless the source file changes.
- `_freeze/` is committed intentionally — it lets the site rebuild on CI or a new machine without Python.
- `_site/` is git-ignored (built output pushed separately to `gh-pages`).

**Python dependencies** (managed by `uv`/`pyproject.toml`):
- `finlib` — public package from `github.com/jordanmckittrick/finlib`
- Standard scientific stack: numpy, scipy, pandas, matplotlib, plotly

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
---
```

For posts with heavy computation, put the math/simulation logic in a sibling `.py` file and import it in the notebook — see `posts/shannons-demon/` as the reference pattern (separate `coin_flip_with_riskless_asset_model.py` and `plotting_functions.py`).

## Theming

Light/dark SCSS overrides live in `theme/light.scss` and `theme/dark.scss`, applied on top of the `cosmo`/`darkly` Quarto base themes. `styles.css` and `ratings.css` add global and page-specific styles.
