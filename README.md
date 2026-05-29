# My Quarto portfolio

Source for my personal website, built with [Quarto](https://quarto.org) and
published to GitHub Pages.

## One-time setup

```bash
uv sync          # creates .venv and installs the Python stack (uv handles Python too)
```

## Daily workflow

```bash
uv run quarto preview     # live local preview; edits reload automatically
```

`uv run` executes the command inside this project's environment automatically —
no need to "activate" anything.

To add a package later (e.g. seaborn):

```bash
uv add seaborn
```

## Publishing

```bash
uv run quarto publish gh-pages    # renders locally and pushes to the gh-pages branch
```

## Structure

- `_quarto.yml` — site-wide config (navbar, theme, formatting).
- `index.qmd` — homepage.
- `blog.qmd` — auto-generated listing of everything in `posts/`.
- `about.qmd` — longer bio.
- `posts/<slug>/index.qmd` — one folder per post.
- `theme/` — light/dark SCSS.

## New post

```bash
mkdir -p posts/my-new-post
$EDITOR posts/my-new-post/index.qmd
```

Minimum front matter:

```yaml
---
title: "Title"
date: 2026-06-01
categories: [some, tags]
---
```
