"""Generate ``wealth_tree.svg`` -- the two-state wealth tree for the setup section.

Run manually (needs a LaTeX install, for real Computer Modern math):

    uv run python posts/shannons_demon_part_1/make_wealth_tree.py

The structure (branches, nodes, plain words, period axis) is hand-authored SVG
in the brand serif and brand colours. The three *math* labels are rendered with
matplotlib + usetex (so they match the MathJax body maths and get proper
``\\big`` brackets), then embedded as self-contained ``<image>`` data-URIs. This
keeps prose in Baskerville and maths in LaTeX -- the same split as the post.
"""
import base64
import io
import re
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

plt.rcParams["text.usetex"] = True
plt.rcParams["svg.fonttype"] = "path"   # glyphs as paths -> self-contained, font-free

INK = "#1c1c22"
HERO = "#7575f7"      # periwinkle: every wealth node
GREY = "#5b5f66"      # words, axis
FONT = "Baskerville, 'Libre Baskerville', Georgia, serif"


def render_math(tex: str, fontsize: int = 24, color: str = INK):
    """Render a LaTeX string to (base64 svg, width_pt, height_pt), tight & transparent."""
    fig = plt.figure()
    fig.text(0.5, 0.5, tex, fontsize=fontsize, color=color, ha="center", va="center")
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.01, transparent=True)
    plt.close(fig)
    svg = buf.getvalue().decode("utf-8")
    head = svg[: svg.index(">", svg.index("<svg"))]
    w = float(re.search(r'width="([0-9.]+)pt"', head).group(1))
    h = float(re.search(r'height="([0-9.]+)pt"', head).group(1))
    return base64.b64encode(svg.encode()).decode(), w, h


# --- the three maths labels (\big for the subtly larger outer brackets) ---
root = render_math(r"$S_0$")
up = render_math(r"$S_0\big((1-f)r + f\gamma_h\big)$")
dn = render_math(r"$S_0\big((1-f)r + f\gamma_t\big)$")

# Scale every label by one factor so relative sizes are preserved; the factor is
# chosen so the expressions stand ~26 user-units tall in the 720-wide viewBox.
s = 26.0 / up[2]


def image(lbl, x, y, anchor):
    """<image> for a rendered label, vertically centred on node y."""
    b64, w, h = lbl
    W, H = w * s, h * s
    ix = x if anchor == "left" else x - W
    return (f'<image x="{ix:.1f}" y="{y - H / 2:.1f}" width="{W:.1f}" height="{H:.1f}" '
            f'href="data:image/svg+xml;base64,{b64}"/>')


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 380" font-family="{FONT}">
  <rect x="0" y="0" width="720" height="380" fill="#ffffff"/>

  <!-- Branches (periwinkle). Heads sits farther above S0 than tails below, since f*gamma_h > f*gamma_t. -->
  <g stroke="{HERO}" stroke-width="2.2" stroke-linecap="round" fill="none">
    <line x1="110" y1="180" x2="380" y2="88"/>
    <line x1="110" y1="180" x2="380" y2="252"/>
  </g>

  <!-- Branch labels (brand serif, upright) -->
  <g fill="{GREY}" font-size="13" text-anchor="middle">
    <text x="240" y="120">heads</text>
    <text x="240" y="232">tails</text>
  </g>

  <!-- Nodes: every wealth state periwinkle; the origin is marked only by a slightly larger dot. -->
  <g stroke="#ffffff" stroke-width="1.5">
    <circle cx="380" cy="88"  r="5" fill="{HERO}"/>
    <circle cx="380" cy="252" r="5" fill="{HERO}"/>
    <circle cx="110" cy="180" r="6.5" fill="{HERO}"/>
  </g>

  <!-- Maths labels (LaTeX, embedded) -->
  {image(root, 92, 180, "right")}
  {image(up, 398, 88, "left")}
  {image(dn, 398, 252, "left")}

  <!-- Period axis -->
  <g stroke="{GREY}" stroke-width="1">
    <line x1="110" y1="320" x2="400" y2="320"/>
    <line x1="110" y1="315" x2="110" y2="325"/>
    <line x1="380" y1="315" x2="380" y2="325"/>
  </g>
  <g fill="{GREY}" font-size="13" text-anchor="middle">
    <text x="110" y="340">0</text>
    <text x="380" y="340">1</text>
  </g>
  <text x="245" y="362" fill="{GREY}" font-size="12" text-anchor="middle">period, n</text>
</svg>
"""

out = Path(__file__).with_name("wealth_tree.svg")
out.write_text(svg)
print(f"wrote {out}  (scale={s:.3f}, expr {up[1]:.1f}x{up[2]:.1f}pt)")
