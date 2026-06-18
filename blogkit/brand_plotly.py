
"""The blog's Plotly plot brand, as a registered template.

Importing this module registers the "blog" template and makes
"plotly_white+blog" the default, so every figure built afterwards inherits
the brand's font, ink, background, gridlines, and categorical colourway
without repeating styling. The per-trace *semantic* colours (hero = the
quantity you keep, etc.) are still set explicitly in each figure and are
exported here so there is a single source of truth.

The page (via _brand.yml or your theme SCSS) must load the actual font;
this template only names it. Baskerville is a system font on Apple devices,
with Libre Baskerville as the web fallback the page should load elsewhere.
"""
import plotly.graph_objects as go
import plotly.io as pio

# --- Typography (named here, loaded by the page) ---
FONT = "Baskerville, 'Libre Baskerville', Georgia, serif"

# --- Neutrals: near-black ink, a quiet grey ramp, white paper ---
INK = "#1c1c22"     # titles / primary text
LABEL = "#5b5f66"   # axis labels & ticks (recede below titles)
GRID = "#e9ebef"    # gridlines that whisper
PAPER = "#ffffff"

# --- Semantic accent colourway (import these into plot functions) ---
HERO = "rgba(117, 117, 247, 1.0)"   # the quantity you keep
SECONDARY = "#84cc16"               # its Jensen-overstating sibling
ACCENT = "#f4511e"                  # optima / "look here" marks


def with_alpha(color: str, alpha: float) -> str:
    """Return ``color`` as an ``rgba(...)`` string at the given ``alpha``.

    Accepts either a hex string (``"#rrggbb"``) or an existing
    ``"rgb(...)"``/``"rgba(...)"`` string, so it works on every colour this
    module exports (the neutrals and SECONDARY/ACCENT are hex; HERO is rgba).
    """
    c = color.strip()
    if c.startswith("#"):
        c = c.lstrip("#")
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    elif c.startswith("rgb"):
        r, g, b = (float(v) for v in c[c.index("(") + 1:c.index(")")].split(",")[:3])
    else:
        raise ValueError(f"Unrecognized color format: {color!r}")
    return f"rgba({r:.0f}, {g:.0f}, {b:.0f}, {alpha})"

_axis = dict(
    gridcolor=GRID, zerolinecolor=GRID, linecolor=LABEL,
    tickfont=dict(color=LABEL), title=dict(font=dict(color=LABEL)),
)

pio.templates["blog"] = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, size=14, color=INK),
        title=dict(font=dict(family=FONT, size=18, color=INK)),
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        colorway=[HERO, SECONDARY, ACCENT],
        xaxis=_axis,
        yaxis=_axis,
        legend=dict(font=dict(color=INK)),
    )
)

# Layer the brand on top of plotly_white's sensible base.
pio.templates.default = "plotly_white+blog"