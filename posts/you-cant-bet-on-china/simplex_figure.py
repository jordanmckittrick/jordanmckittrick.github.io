"""The simplex figure for the log-optimal-investing post.

One interactive figure that makes the growth-rate decomposition (1.6) visible:
for three states and two tradable assets (one risk-free at gross return ``r``,
one risky at gross returns ``gamma``), it draws the risk-neutral segment ``Q``
and its image ``M_wstar`` inside the 2-simplex, over a family of KL contours,
and lets a native range slider walk a point ``q`` along ``Q`` while a boxed
two-line readout renders the decomposition ``D(p||q) = D(p||q*) + D(p||m(q, w*))``
as an arithmetic identity -- the first term (the edge) sitting still while the
other two move together.

The geometry, stated once and used everywhere below:

* ``Y(f)   = (1 - f) r + f gamma``            portfolio gross return (length 3)
* ``W(f)   = sum_i p_i log Y_i(f)``           growth rate, nats
* ``f*     = argmax_f W(f)``                  no closed form for three states
* ``q*     = r p / Y(f*)``                    the reverse info projection of p onto Q
* ``Q      = { q in the simplex : q . gamma = r }``     a line segment A--B
* ``m(q,f) = q Y(f) / r``                     the tilted measure
* ``M_wstar = { m(q, f*) : q in Q }``         a line segment

Adding an untradable third asset ``gamma2`` completes the market and fixes a
unique risk-neutral measure ``q~`` (with partner ``m~`` on ``M_wstar``); marking
those makes the figure illustrate the stranded-growth decomposition (3.3)/(3.4)
as well as (1.6).

Everything is derived from ``(r, gamma, p, gamma2)``; nothing about the running
example is baked in. Colour follows ``_brand.yml``: orange ("look here") for
``p``, periwinkle ("attainable reality") for ``q*``, lime ("unattainable") for
``q~`` and ``m~``, navy (neutral-but-coloured) for the KL contour family, and
ink (scaffolding) for ``Q``, ``M_wstar`` and the moving pair ``q``/``m`` -- with
the dashed pointers and the triangle frame a reduced-opacity tint of ink.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import scipy.optimize as opt

# Importing the brand module registers "plotly_white+blog" as the default
# template (font, ink, paper, gridless neutrals) and gives us the semantic
# palette. HERO is the house periwinkle, ACCENT the burnt orange.
from blogkit.brand_plotly import HERO, SECONDARY, ACCENT, HERMES, INK, LABEL, PAPER, with_alpha

_LN2 = np.log(2.0)

# The three simplex vertices in the plane: delta_1 bottom-left, delta_2
# bottom-right, delta_3 apex. A probability vector maps to the plane by q @ V.
_V = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, np.sqrt(3.0) / 2.0]])


# --------------------------------------------------------------------------- #
#  Pure functions -- the model, with everything derived from (r, gamma, p)
# --------------------------------------------------------------------------- #
def _portfolio_return(f: float, r: float, gamma: np.ndarray) -> np.ndarray:
    """Portfolio gross return ``Y(f) = (1 - f) r + f gamma`` in every state."""
    return (1.0 - f) * r + f * np.asarray(gamma, dtype=float)


def growth_rate(f: float, r: float, gamma: np.ndarray, p: np.ndarray) -> float:
    """Growth rate ``W(f) = sum_i p_i log Y_i(f)`` in nats.

    The expected log gross return of the portfolio ``w = (1 - f, f)``; the
    quantity whose maximiser is the log-optimal (Kelly) allocation.
    """
    y = _portfolio_return(f, r, gamma)
    return float(np.sum(np.asarray(p, dtype=float) * np.log(y)))


def admissible_f_range(r: float, gamma: np.ndarray) -> tuple[float, float]:
    """The open interval of ``f`` on which ``Y(f) > 0`` in every state.

    Below the lower end the best state's return has been shorted into
    negativity; above the upper end the worst state's has. At each end one
    component of ``Y`` vanishes, so a portfolio there is on the edge of ruin.
    """
    gamma = np.asarray(gamma, dtype=float)
    f_lo = -r / (gamma.max() - r)
    f_hi = r / (r - gamma.min())
    return float(f_lo), float(f_hi)


def optimal_fraction(r: float, gamma: np.ndarray, p: np.ndarray) -> float:
    """The growth-optimal risky fraction ``f* = argmax_f W(f)``.

    Solved numerically: with three states there is no closed form. ``W`` is
    strictly concave on the admissible interval and its derivative
    ``W'(f) = sum_i p_i (gamma_i - r) / Y_i(f)`` runs from ``+inf`` at the
    lower edge to ``-inf`` at the upper, so a bracketed root of ``W'`` is the
    unique maximiser.
    """
    gamma = np.asarray(gamma, dtype=float)
    p = np.asarray(p, dtype=float)
    f_lo, f_hi = admissible_f_range(r, gamma)
    span = f_hi - f_lo

    def dW(f: float) -> float:
        y = _portfolio_return(f, r, gamma)
        return float(np.sum(p * (gamma - r) / y))

    eps = 1e-12 * span
    return float(opt.brentq(dW, f_lo + eps, f_hi - eps, xtol=1e-15, rtol=1e-15))


def manufactured_measure(
    f: float, r: float, gamma: np.ndarray, p: np.ndarray
) -> np.ndarray:
    """The measure ``q = r p / Y(f)`` the first-order condition manufactures.

    Evaluated at ``f = f*`` this is ``q*``, the risk-neutral measure the growth
    maximisation produces (equation (1.2)); it is a genuine probability vector
    that sums to one and is risk-neutral (``q . gamma = r``) only there.
    """
    return r * np.asarray(p, dtype=float) / _portfolio_return(f, r, gamma)


def tilted_measure(
    q: np.ndarray, f: float, r: float, gamma: np.ndarray
) -> np.ndarray:
    """The tilted measure ``m(q, f) = q Y(f) / r`` (equation (1.4)).

    Reweights ``q`` by the portfolio's state returns. When ``q`` is
    risk-neutral the result sums to one automatically, so ``m`` maps ``Q`` into
    the simplex with no renormalisation.
    """
    return np.asarray(q, dtype=float) * _portfolio_return(f, r, gamma) / r


def kl_divergence(a: np.ndarray, b: np.ndarray) -> float:
    """Kullback-Leibler divergence ``D(a||b) = sum_i a_i log(a_i / b_i)``, nats.

    Uses the convention ``0 log 0 = 0``; diverges to ``+inf`` where ``a_i > 0``
    but ``b_i = 0``.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(a > 0.0, a * np.log(a / b), 0.0)
    return float(np.sum(terms))


def risk_neutral_segment_endpoints(
    r: float, gamma: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """The two endpoints ``A``, ``B`` of the risk-neutral segment ``Q``.

    ``Q = { q in the simplex : q . gamma = r }`` is a line whose two ends lie
    on faces of the simplex. For each ``k`` set ``q_k = 0`` and solve
    ``q . gamma = r`` with ``sum q = 1`` for the other two coordinates; under
    no arbitrage exactly two of the three candidates land in ``[0, 1]^3``.
    They are returned in state order (the endpoint on the ``q_1 = 0`` face
    before the one on the ``q_2 = 0`` face, and so on).
    """
    gamma = np.asarray(gamma, dtype=float)
    endpoints = []
    for k in range(3):
        others = [i for i in range(3) if i != k]
        i, j = others
        # Solve  q_i + q_j = 1  and  gamma_i q_i + gamma_j q_j = r.
        det = gamma[i] - gamma[j]
        if det == 0.0:
            continue
        q = np.zeros(3)
        q[i] = (r - gamma[j]) / det
        q[j] = (gamma[i] - r) / det
        if np.all(q >= -1e-12) and np.all(q <= 1.0 + 1e-12):
            endpoints.append(np.clip(q, 0.0, 1.0))
    if len(endpoints) != 2:
        raise ValueError(
            f"expected exactly two no-arbitrage endpoints of Q, got {len(endpoints)}"
        )
    return endpoints[0], endpoints[1]


def barycentric_to_cartesian(q: np.ndarray) -> np.ndarray:
    """Map a probability vector (or a stack of them) into the plane by ``q @ V``.

    ``V`` places ``delta_1`` bottom-left, ``delta_2`` bottom-right and
    ``delta_3`` at the apex. Accepts a single ``(3,)`` vector, returning
    ``(2,)``, or an ``(N, 3)`` array, returning ``(N, 2)``.
    """
    return np.asarray(q, dtype=float) @ _V


def optimal_slider_interval(
    r: float,
    gamma: np.ndarray,
    p: np.ndarray,
    kl_window: float,
) -> tuple[float, float, float]:
    """The sub-interval of ``s`` where ``D(p||q(s)) <= kl_window * D(p||q*)``.

    ``q(s) = A + s (B - A)`` walks ``Q`` from ``A`` (``s = 0``) to ``B``
    (``s = 1``). ``D(p||q(s))`` is convex with its minimum ``D(p||q*)`` at
    ``s*``; it diverges at both ends of ``Q``. Returns ``(s_lo, s_hi, s_star)``
    with ``s_lo < s_star < s_hi``. Retained for the verification harness; the
    figure itself now clips ``s`` to a fixed ``[0.01, 0.99]`` instead.
    """
    gamma = np.asarray(gamma, dtype=float)
    p = np.asarray(p, dtype=float)
    A, B = risk_neutral_segment_endpoints(r, gamma)
    f_star = optimal_fraction(r, gamma, p)
    q_star = manufactured_measure(f_star, r, gamma, p)
    d_star = kl_divergence(p, q_star)

    def q_of_s(s: float) -> np.ndarray:
        return A + s * (B - A)

    # s* is where q(s) = q*; solve on the coordinate with the widest spread so
    # the projection is well conditioned whatever the geometry.
    k = int(np.argmax(np.abs(B - A)))
    s_star = float((q_star[k] - A[k]) / (B[k] - A[k]))

    target = kl_window * d_star

    def gap(s: float) -> float:
        return kl_divergence(p, q_of_s(s)) - target

    # Bracket each root between s* (where gap < 0) and an end (where gap -> +inf).
    eps = 1e-9
    s_lo = float(opt.brentq(gap, eps, s_star, xtol=1e-15, rtol=1e-15))
    s_hi = float(opt.brentq(gap, s_star, 1.0 - eps, xtol=1e-15, rtol=1e-15))
    return s_lo, s_hi, s_star


# An orthonormal basis for the sum-zero plane (the plane the simplex lives in),
# used to sweep ray directions when tracing KL level curves.
_SUMZERO_B1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2.0)
_SUMZERO_B2 = np.array([1.0, 1.0, -2.0]) / np.sqrt(6.0)


def _kl_level_curve(p: np.ndarray, level: float, n_theta: int = 360) -> np.ndarray:
    """The closed curve ``{ q in the simplex : D(p||q) = level }``, barycentric.

    ``D(p||.)`` is strictly convex, zero at ``p``, and diverges at the boundary,
    so along every ray from ``p`` it increases from 0 to ``+inf`` and attains
    ``level`` exactly once. We sweep the ray direction over ``n_theta`` angles
    in the sum-zero plane, bisect for the crossing on each ray, then take a few
    Newton steps so the returned point sits on the level to machine precision,
    and close the loop. Returns an ``(n_theta + 1, 3)`` array of probability
    vectors, computed exactly -- no grid, no marching squares.
    """
    p = np.asarray(p, dtype=float)
    thetas = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    pts = np.empty((n_theta, 3))
    for k, th in enumerate(thetas):
        u = np.cos(th) * _SUMZERO_B1 + np.sin(th) * _SUMZERO_B2
        neg = u < 0.0
        t_max = float(np.min(-p[neg] / u[neg])) if np.any(neg) else np.inf
        t = opt.brentq(lambda t: kl_divergence(p, p + t * u) - level,
                       0.0, t_max * (1.0 - 1e-12), xtol=1e-15, rtol=1e-15)
        # Newton polish on g(t) = D(t) - level, with g'(t) = -sum p_i u_i / q_i.
        for _ in range(4):
            q = p + t * u
            resid = kl_divergence(p, q) - level
            deriv = -float(np.sum(p * u / q))
            if deriv <= 0.0:
                break
            t_new = min(max(t - resid / deriv, 0.0), t_max * (1.0 - 1e-15))
            if t_new == t:
                break
            t = t_new
        pts[k] = p + t * u
    return np.vstack([pts, pts[0]])


# --------------------------------------------------------------------------- #
#  Figure styling
# --------------------------------------------------------------------------- #
def _mix(hex_a: str, hex_b: str, t: float) -> str:
    """Blend two ``#rrggbb`` colours, ``t`` of the way from ``a`` to ``b``."""
    a = np.array([int(hex_a.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)])
    b = np.array([int(hex_b.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)])
    c = np.round((1.0 - t) * a + t * b).astype(int)
    return "#{:02x}{:02x}{:02x}".format(*c)


# Colour by meaning (semantics from _brand.yml; palette from brand_plotly):
_P_COLOR = ACCENT                      # orange, "look here": p
_QSTAR_COLOR = HERO                    # periwinkle, "attainable reality": q*
_UNATTAIN = SECONDARY                  # lime, "unattainable": q~ and m~
_CONTOUR = HERMES                      # navy, neutral-but-coloured: contours + labels
_NEUTRAL = INK                         # ink scaffolding: Q, M_wstar, and moving q, m
_SCAFFOLD = with_alpha(INK, 0.35)      # ink at 35%: the dashed legs + triangle frame

# A white ring around every point marker, so a dot sitting on a dark line
# (q, q~ on Q; m, m~ on M_wstar) reads as a separate object, not a thickening.
# Set to 0.0 to drop it everywhere without touching anything else.
MARKER_OUTLINE_PX = 1.5

_CONTOUR_FAINT = with_alpha(_CONTOUR, 0.40)
_CONTOUR_TANGENT = with_alpha(_CONTOUR, 0.70)
_CONTOUR_LABEL = with_alpha(_CONTOUR, 0.60)
_CONTOUR_LABEL_TANGENT = with_alpha(_CONTOUR, 0.85)

# Overlay-label font sizes (px). One scale, three tiers: 19 for every symbol the
# reader reads (point labels, the two line labels, the three slider labels and
# the readout), 17 for the grey vertex reference labels, 14 for the contour
# values. Each label's math is scaled by the body-math percentage in the browser,
# so N px renders exactly as body math would at N px, regardless of container.
_READOUT_FONT = 19                     # the boxed decomposition readout
_LINE_FONT = 19                        # line labels Q, M_wstar
_POINT_FONT = 19                       # the six point labels
_VERTEX_FONT = 17                      # vertex labels delta_i (grey reference)
_CONTOUR_FONT = 14                     # contour value labels

_MARKER_SIZE = 11                      # one size for all six points; colour carries meaning
# Slider dots match the simplex markers exactly. Plotly centres the white outline
# on the marker edge, so the drawn diameter is core + one outline width. This is
# the single source of truth for the slider thumb/tick size, in CSS and JS.
_DOT_D_PX = _MARKER_SIZE + MARKER_OUTLINE_PX   # 12.5 px drawn diameter

# ---- Figure geometry -------------------------------------------------------
# Axis ranges leave a little room outside the triangle for the vertex labels.
# The fixed pixel height is DERIVED so the plot-area aspect equals the range
# aspect: the (undistorted, scaleratio=1) triangle then fills the column width
# instead of rendering narrow inside a too-wide plot with dead side margins.
# The resize script in ``simplex_figure_html`` reads _ASPECT/_X_RANGE/_Y_RANGE
# through f-string interpolation, so it tracks these automatically.
_X_RANGE = (-0.10, 1.10)               # width 1.20
_Y_RANGE = (-0.06, 0.95)               # height 1.01 (lower bound lifted to trim dead space)
_LINE_LABEL_OFFSET = 0.02              # how far outside the edge Q / M_wstar labels sit
_X_SPAN = _X_RANGE[1] - _X_RANGE[0]
_Y_SPAN = _Y_RANGE[1] - _Y_RANGE[0]
_ASPECT = _Y_SPAN / _X_SPAN            # plot height / width = 0.8833...
_MARGIN_PX = 8
_REF_WIDTH = 920                       # Quarto grid body-width; the assertion harness's
                                       # reference column (the JS fit() measures the real one)
_WIDTH_FRACTION = 0.90                 # render at 90% of the measured column, centred, so the
                                       # figure clears a laptop viewport and keeps the caption on
_COLUMN_PX = 613                       # measured Quarto body column; used only to size the
                                       # text-fit checks to the narrowest common render


def _figure_height() -> int:
    """Fixed height (px) that makes the plot-area aspect match the range aspect."""
    plot_w = _REF_WIDTH - 2 * _MARGIN_PX
    return round(plot_w * _ASPECT + 2 * _MARGIN_PX)


# The readout is no longer a Plotly trace: it is an HTML element over the plot,
# typeset by the page's own MathJax (stage 1 of moving labels out of Plotly). The
# box is measured live in the browser; only its padding is fixed here (shared by
# the CSS and the contour-label avoid estimate).
_READOUT_PAD_PX = 10.0  # box padding on all four sides (CSS ``padding``)


def _fmt_gamma(x: float) -> str:
    """Format a gamma value with at least one decimal (2 -> ``2.0``, 0.45 kept)."""
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"


def _furthest_index(cand_xy: np.ndarray, avoid_xy: np.ndarray) -> int:
    """Index of the candidate point furthest (max-min distance) from an avoid set."""
    d2 = ((cand_xy[:, None, :] - avoid_xy[None, :, :]) ** 2).sum(axis=-1)
    return int(np.argmax(d2.min(axis=1)))


# ---- Overlay label placement (Stage 2: every label is HTML typeset by MathJax) ----
# Labels are positioned in the browser from their MEASURED rendered boxes, so the
# only geometry Python still owns is the gap and the flip rule. _LABEL_GAP_PX is
# the gap from a marker's OUTER edge (radius _DOT_D_PX / 2) to its label, in CSS
# px; one constant for every point label and the slider labels (item 1b/1d).
_LABEL_GAP_PX = 3.0
# INK BOXES (rev 12, item 1). A MathJax label's element box is a line box: it
# reserves ascent/descent the glyphs may not use (p, q, m have no ascender, so the
# empty band above their x-height made "below" labels sit visibly low). Each point
# label is therefore placed and audited from its INK box -- the element box shrunk
# by these per-glyph insets. The four insets (top, bottom, left, right) are in em
# so they hold at any font size; the browser multiplies them by the label's
# measured container font size. Measured by rendering each label and reading the
# ink extent (MathJax SVG glyph geometry) against its element box and text
# baseline; see scratchpad/ink_svg.html + ink_chtml.html. Left/right can be
# slightly negative where an italic glyph overhangs its advance box.
_INK_INSETS_EM = {
    "p":      dict(t=0.4973, b=0.0719, l=-0.0353, r=0.0030),
    "qstar":  dict(t=0.2716, b=0.0719, l=0.0299,  r=0.0141),
    "qtilde": dict(t=0.3093, b=0.0719, l=0.0299,  r=-0.0211),
    "mtilde": dict(t=0.3093, b=0.2376, l=0.0190,  r=0.0195),
    "q":      dict(t=0.4975, b=0.0719, l=0.0299,  r=-0.0004),
    "m":      dict(t=0.4975, b=0.2375, l=0.0190,  r=0.0195),
}
# q sits just right of q* along Q, and the superscript star of q*'s label sits up
# and to the right -- directly in q's path. Shift q*'s label LEFT by this many px
# so the star's INK clears q's marker disk in every frame (item 3). Re-derived with
# ink boxes on the faithful probe (see the browser sweep); p gets no nudge.
_QSTAR_NUDGE_PX = 7.0
# q~'s label is placed BELOW-LEFT of its marker (the side away from Q, which runs
# down-and-right from q~), so no rightward nudge is needed (item 2). If its ink box
# still grazes m's label near the q~ landmark at the narrow width, it is shifted
# further LEFT by this many px (never right, never toward Q); 0 means no shift was
# needed. Capped at 8 px by contract.
_QTILDE_LEFT_PX = 0.0


# ---- The fixed flip rule for m (item 2/4) -----------------------------------
# Static points (p, q*, q~, m~) label BELOW; the moving pair label ABOVE, so
# "below vs above" reads as "fixed vs moving". q is ALWAYS "top right". m is
# "top right" until the slider's index fraction reaches _M_FLIP, then it tucks
# just UNDER M_wstar, lower-left of its marker ("undertuck", item 4a). The switch
# happens once, at a fixed frame, so nothing flickers. _M_FLIP is re-verified at
# the current 19 px sizes by the browser audit (item 5): the largest fraction for
# which "top right" is collision-free before it is >= 0.74, so 0.74 stands.
_M_FLIP = 0.74


def _m_place(index_fraction: float) -> str:
    """m's overlay placement: 'topright' before the flip, 'undertuck' after."""
    return "topright" if index_fraction < _M_FLIP else "undertuck"


# --------------------------------------------------------------------------- #
#  The figure
# --------------------------------------------------------------------------- #
def build_simplex_figure(
    r: float,
    gamma: np.ndarray,
    p: np.ndarray,
    gamma2: np.ndarray = (0.5, 0.7, 1.7),
    n_frames: int = 540,
) -> go.Figure:
    """Assemble the single-panel simplex figure for the belief ``p``.

    A triangle sized to fill the column. It carries the KL contour family of
    ``q -> D(p||q)`` (navy, faint, behind everything; the level tangent to ``Q``
    at ``q*`` drawn stronger), the segment ``Q`` and its image ``M_wstar`` (both
    solid ink at the same 1.5 px weight, ``M_wstar`` drawn with a gap for the
    ``p -> m`` leg), the fixed anchors ``p`` (orange) and ``q*`` (periwinkle),
    the complete-market measure ``q~`` and its partner ``m~`` (lime, from the
    untradable third asset ``gamma2``), and a slider-driven moving pair ``q`` on
    ``Q`` and ``m`` on ``M_wstar`` (ink) joined to ``p`` by dashed pointers. A
    boxed two-line readout renders the decomposition (1.6). Point labels follow a
    fixed rule: static points label below, the moving pair above (:data:`_M_FLIP`).

    The named frames ``s0000..s0539`` drive the native range input that
    :func:`simplex_figure_html` emits; there is no Plotly slider and no hover
    beyond the six labelled points.

    Parameters
    ----------
    r
        Risk-free gross return, the same in every state.
    gamma
        Length-3 gross returns of the tradable risky asset.
    p
        Length-3 belief, all strictly positive.
    gamma2
        Length-3 gross returns of the untradable third asset. With the risk-free
        asset and ``gamma`` it completes the market, fixing ``q~`` as the unique
        risk-neutral measure of ``G3 = [ r 1 | gamma | gamma2 ]``.
    n_frames
        Number of animation frames along ``Q``.

    Returns
    -------
    go.Figure
        A responsive-width figure whose height fills the column; ``layout.meta``
        carries ``n_frames``, ``start_index`` and the two slider landmarks.
    """
    gamma = np.asarray(gamma, dtype=float)
    gamma2 = np.asarray(gamma2, dtype=float)
    p = np.asarray(p, dtype=float)

    # ---- Core quantities, all derived ----
    f_star = optimal_fraction(r, gamma, p)
    q_star = manufactured_measure(f_star, r, gamma, p)
    d_star = kl_divergence(p, q_star)

    A, B = risk_neutral_segment_endpoints(r, gamma)
    # Orient Q so s = 0 is its LEFTMOST end (the function returns them in state
    # order, which for the running example puts A bottom-right, so dragging the
    # slider right would walk q left). Swap without touching the pinned function.
    if barycentric_to_cartesian(A)[0] > barycentric_to_cartesian(B)[0]:
        A, B = B, A

    # q~: the unique risk-neutral measure once the untradable third asset gamma2
    # completes the market (G3^T q~ = r 1). m~ = m(q~, w*) is its M_wstar partner.
    G3 = np.column_stack([r * np.ones(3), gamma, gamma2])
    q_tilde = np.linalg.solve(G3.T, r * np.ones(3))
    m_tilde = tilted_measure(q_tilde, f_star, r, gamma)

    # Parameters along Q (q(s) = A + s (B - A)) of q* and q~.
    k = int(np.argmax(np.abs(B - A)))

    def s_of(qq: np.ndarray) -> float:
        return float((qq[k] - A[k]) / (B[k] - A[k]))

    s_star = s_of(q_star)
    s_tilde = s_of(q_tilde)
    # Open midway between q~ and q* so all six points are visible on load (on q*
    # the moving q would hide the static q* marker).
    s_open = 0.5 * (s_tilde + s_star)

    s_grid = np.linspace(0.01, 0.99, n_frames)
    # Snap each landmark s onto its nearest grid point so the slider can land on
    # it exactly (otherwise a landmark falls between frames and is unreachable).
    idx_tilde = int(np.argmin(np.abs(s_grid - s_tilde)))
    s_grid[idx_tilde] = s_tilde
    idx_star = int(np.argmin(np.abs(s_grid - s_star)))
    s_grid[idx_star] = s_star
    start_index = int(np.argmin(np.abs(s_grid - s_open)))
    s_grid[start_index] = s_open
    assert len({idx_tilde, idx_star, start_index}) == 3, "landmark indices collide"
    # After the orientation swap q* sits left of q~ on the track, matching their
    # left-to-right order on the simplex (q* upper-left, q~ lower-right).
    assert idx_star < idx_tilde, "q* should precede q~ on the slider after the swap"

    def q_of_s(s: float) -> np.ndarray:
        return A + s * (B - A)

    xy_p = barycentric_to_cartesian(p)
    xy_qstar = barycentric_to_cartesian(q_star)
    xy_qtilde = barycentric_to_cartesian(q_tilde)
    xy_mtilde = barycentric_to_cartesian(m_tilde)
    xy_A, xy_B = barycentric_to_cartesian(A), barycentric_to_cartesian(B)
    xy_mA = barycentric_to_cartesian(tilted_measure(A, f_star, r, gamma))
    xy_mB = barycentric_to_cartesian(tilted_measure(B, f_star, r, gamma))

    def _frame_state(s: float) -> dict:
        q = q_of_s(s)
        m = tilted_measure(q, f_star, r, gamma)
        return dict(q=q, m=m, s=s, d_pq=kl_divergence(p, q), d_pm=kl_divergence(p, m),
                    xq=barycentric_to_cartesian(q), xm=barycentric_to_cartesian(m))

    st0 = _frame_state(s_grid[start_index])

    fig = go.Figure()

    # ------------------------------------------------------------------ #
    #  (1) KL contours -- navy (hermes), faint, behind everything.
    # ------------------------------------------------------------------ #
    contour_mults = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
    contour_curves = {}
    for mult in contour_mults:
        level = mult * d_star
        curve = barycentric_to_cartesian(_kl_level_curve(p, level))
        contour_curves[mult] = curve
        tangent = mult == 1.0
        fig.add_trace(go.Scatter(
            x=curve[:, 0], y=curve[:, 1], mode="lines",
            line=dict(color=_CONTOUR_TANGENT if tangent else _CONTOUR_FAINT,
                      width=1.4 if tangent else 1.0),
            hoverinfo="skip", showlegend=False, name=""))

    # The readout is now an HTML/MathJax overlay (see simplex_figure_html), not a
    # Plotly trace. Its box sits in the upper-left, top edge on the apex; keep a
    # conservative data-space footprint so the contour-label placer never lands a
    # label under it. (No contour actually reaches this region, but the estimate
    # makes that explicit and survives changes to the contours.)
    readout_avoid = np.array([[x, y]
                              for x in np.linspace(_X_RANGE[0], 0.40, 4)
                              for y in np.linspace(0.71, np.sqrt(3.0) / 2.0, 3)])

    # Triangle outline -- ink at 35% (scaffolding).
    tri = barycentric_to_cartesian(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0]]))
    fig.add_trace(go.Scatter(x=tri[:, 0], y=tri[:, 1], mode="lines",
        line=dict(color=_SCAFFOLD, width=1.2), hoverinfo="skip", showlegend=False))

    # ------------------------------------------------------------------ #
    #  (6) Q -- solid ink. Same weight as M_wstar now that the outside labels
    #  identify each line, so the weight distinction has no remaining job.
    # ------------------------------------------------------------------ #
    fig.add_trace(go.Scatter(x=[xy_A[0], xy_B[0]], y=[xy_A[1], xy_B[1]], mode="lines",
        line=dict(color=_NEUTRAL, width=1.5), hoverinfo="skip", showlegend=False, name="Q"))

    # ------------------------------------------------------------------ #
    #  (3) M_wstar -- two solid ink segments with a gap, and the p -> m leg in
    #  the gap. p = m(q*, w*) lies exactly on M_wstar, so the leg is a sub-segment
    #  of the line; the gap keeps the dashed leg from hiding under the solid one.
    #  point(s) is linear in s, with p at s_star and m at the frame's s.
    # ------------------------------------------------------------------ #
    def mw_point(s):
        return xy_mA + s * (xy_mB - xy_mA)

    def mw_pieces(s):
        lo, hi = (s_star, s) if s_star <= s else (s, s_star)
        p_lo, p_hi = mw_point(lo), mw_point(hi)
        return (mw_point(0.0), p_lo), (p_hi, mw_point(1.0)), (p_lo, p_hi)

    def _seg(a_b, color, width, dash=None):
        (x0, y0), (x1, y1) = a_b
        return go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines",
                          line=dict(color=color, width=width, dash=dash),
                          hoverinfo="skip", showlegend=False)

    seg1_0, seg2_0, leg_pm_0 = mw_pieces(st0["s"])
    fig.add_trace(_seg(seg1_0, _NEUTRAL, 1.5)); idx_seg1 = len(fig.data) - 1
    fig.add_trace(_seg(seg2_0, _NEUTRAL, 1.5)); idx_seg2 = len(fig.data) - 1

    # Dashed legs from p (the only dashed elements): p -> m (in the M_wstar gap)
    # and p -> q (an ordinary chord, since p is not on Q).
    fig.add_trace(_seg(leg_pm_0, _SCAFFOLD, 1.1, "dash")); idx_leg_pm = len(fig.data) - 1
    fig.add_trace(_seg((xy_p, st0["xq"]), _SCAFFOLD, 1.1, "dash")); idx_leg_pq = len(fig.data) - 1

    # ------------------------------------------------------------------ #
    #  Contour + line label annotations (constant every frame; rotated, with a
    #  plot-background that punches a hole in the curve behind the text).
    # ------------------------------------------------------------------ #
    def _angle_deg(dx: float, dy: float) -> float:
        ta = -np.degrees(np.arctan2(dy, dx))     # textangle is clockwise-positive
        if ta > 90.0:
            ta -= 180.0
        elif ta < -90.0:
            ta += 180.0
        return float(ta)

    def _tangent_angle(curve_closed: np.ndarray, idx: int) -> float:
        n = len(curve_closed) - 1                # closed: last == first
        a = curve_closed[(idx - 1) % n]
        b = curve_closed[(idx + 1) % n]
        return _angle_deg(b[0] - a[0], b[1] - a[1])

    q_samples = barycentric_to_cartesian(np.array([q_of_s(s) for s in np.linspace(0, 1, 24)]))
    m_samples = barycentric_to_cartesian(
        np.array([tilted_measure(q_of_s(s), f_star, r, gamma) for s in np.linspace(0, 1, 24)]))
    tri_v = barycentric_to_cartesian(np.eye(3))
    markers_xy = np.vstack([xy_p, xy_qstar, xy_qtilde, xy_mtilde])
    # Contour labels must dodge the OTHER labels' boxes, not just the markers, now
    # that all labels are 19 px. Approximate each point label's footprint by a
    # point offset from its marker/path: static labels sit below their markers,
    # the moving pair's "top right" labels sit up-and-right of their paths.
    _ppu_ref = (_REF_WIDTH - 2 * _MARGIN_PX) / _X_SPAN
    _off_below = (_DOT_D_PX / 2 + _LABEL_GAP_PX + _POINT_FONT * 0.55) / _ppu_ref
    _off_diag = (_DOT_D_PX / 2 + _LABEL_GAP_PX + _POINT_FONT * 0.45) / _ppu_ref
    _static_lab = markers_xy - np.array([0.0, _off_below])
    _q_lab = q_samples + np.array([_off_diag, _off_diag])
    _m_lab = m_samples + np.array([_off_diag, _off_diag])
    _label_avoid = np.vstack([markers_xy, _static_lab, q_samples, _q_lab, m_samples, _m_lab])
    base_avoid = np.vstack([_label_avoid, tri_v, readout_avoid])

    # (10)/(5) Contour and line labels are now HTML/MathJax overlay elements
    # (Stage 2), but their PLACES are still chosen here. Contours: the same
    # furthest-point positions and tangent angles as before; the tangent level a
    # touch darker. CSS rotate() is clockwise-positive like Plotly textangle, so
    # the angle carries over unchanged. Line labels: just outside the upper-left
    # edge (the A end after the orientation swap), right-aligned so the text runs
    # away from the triangle.
    # Min clearance (data units) the tangent label keeps from every avoid point.
    # It must dodge the OTHER contour labels too (they are placed first, into
    # ``placed``); 0.08 data-units ~= a full contour-label box at the narrow ppu,
    # so the tangent cannot land on top of the 0.06 label near q*.
    _TANGENT_CLEAR = 0.08
    contour_labels = []
    placed = []
    for mult in [m for m in contour_mults if m != 1.0] + [1.0]:   # tangent last
        curve = contour_curves[mult]
        open_curve = curve[:-1]
        if mult == 1.0:
            avoid_pts = np.vstack([_label_avoid] + ([np.array(placed)] if placed else []))
            clear = np.sqrt(((open_curve[:, None, :] - avoid_pts[None, :, :]) ** 2)
                            .sum(-1)).min(axis=1)
            ok = (open_curve[:, 0] >= xy_p[0]) & (clear >= _TANGENT_CLEAR)
            cand = np.where(ok)[0]
            if len(cand) == 0:                    # relax clearance if nothing qualifies
                cand = np.where(open_curve[:, 0] >= xy_p[0])[0]
            d_to_qstar = np.hypot(open_curve[cand, 0] - xy_qstar[0],
                                  open_curve[cand, 1] - xy_qstar[1])
            idx = int(cand[int(np.argmin(d_to_qstar))])
        else:
            avoid = np.vstack([base_avoid] + ([np.array(placed)] if placed else []))
            idx = _furthest_index(open_curve, avoid)
        px, py = open_curve[idx]
        placed.append([px, py])
        tangent = mult == 1.0
        contour_labels.append(dict(
            tex=f"{mult * d_star:.2f}", fb=f"{mult * d_star:.2f}",
            xy=[float(px), float(py)], angle=float(_tangent_angle(curve, idx)),
            place="rotated", size=_CONTOUR_FONT,
            color=_CONTOUR_LABEL_TANGENT if tangent else _CONTOUR_LABEL))

    _EDGE_NORMAL = np.array([-np.sqrt(3.0) / 2.0, 0.5])   # outward unit normal
    def _line_anchor(exit_xy):
        return [float(v) for v in np.asarray(exit_xy) + _LINE_LABEL_OFFSET * _EDGE_NORMAL]
    line_labels = [
        dict(tex=r"\mathcal{Q}", fb="\U0001D4AC", xy=_line_anchor(xy_A),
             place="outside-right", size=_LINE_FONT, color=_NEUTRAL),
        dict(tex=r"\mathcal{M}_{w^{*}}", fb="ℳ<sub><i>w</i>*</sub>", xy=_line_anchor(xy_mA),
             place="outside-right", size=_LINE_FONT, color=_NEUTRAL),
    ]

    # ------------------------------------------------------------------ #
    #  Point markers -- all filled circles; colour, not shape, carries meaning.
    #  A white ring lifts a dot off any line it sits on. Hover shows barycentric
    #  coordinates only (the readout carries the divergences).
    # ------------------------------------------------------------------ #
    def _hover(sym: str) -> str:
        return (f"{sym} = (%{{customdata[0]:.3f}}, %{{customdata[1]:.3f}}, "
                f"%{{customdata[2]:.3f}})<extra></extra>")

    def _add_point(xy, bary, color, sym):        # markers only; the label is an overlay
        fig.add_trace(go.Scatter(
            x=[xy[0]], y=[xy[1]], mode="markers",
            marker=dict(color=color, size=_MARKER_SIZE, symbol="circle",
                        line=dict(color=PAPER, width=MARKER_OUTLINE_PX)),
            customdata=[list(map(float, bary))], hovertemplate=_hover(sym),
            showlegend=False))
        return len(fig.data) - 1

    idx_p = _add_point(xy_p, p, _P_COLOR, "p")
    idx_qstar = _add_point(xy_qstar, q_star, _QSTAR_COLOR, "q*")
    idx_qtilde = _add_point(xy_qtilde, q_tilde, _UNATTAIN, "q&#771;")
    idx_mtilde = _add_point(xy_mtilde, m_tilde, _UNATTAIN, "m&#771;")

    def _add_moving(xy, bary, sym):
        fig.add_trace(go.Scatter(
            x=[xy[0]], y=[xy[1]], mode="markers",
            marker=dict(color=_NEUTRAL, size=_MARKER_SIZE, symbol="circle",
                        line=dict(color=PAPER, width=MARKER_OUTLINE_PX)),
            customdata=[list(map(float, bary))], hovertemplate=_hover(sym),
            showlegend=False))
        return len(fig.data) - 1

    idx_q = _add_moving(st0["xq"], st0["q"], "q")
    idx_m = _add_moving(st0["xm"], st0["m"], "m")

    # ------------------------------------------------------------------ #
    #  Overlay label specs -- static point labels (below), the moving pair
    #  (above, q "top right"; m "top right" then "undertuck"), and the vertex
    #  labels at their current anchors/alignments. All positioned in the browser
    #  from their MEASURED boxes; the fallback strings render before MathJax.
    # ------------------------------------------------------------------ #
    static_labels = [
        dict(key="p", tex="p", fb="<i>p</i>", xy=[float(v) for v in xy_p],
             place="below", size=_POINT_FONT, color=INK, ink=_INK_INSETS_EM["p"]),
        dict(key="qstar", tex="q^{*}", fb="<i>q</i><sup>*</sup>",
             xy=[float(v) for v in xy_qstar], place="below", size=_POINT_FONT,
             color=INK, dx=-_QSTAR_NUDGE_PX, ink=_INK_INSETS_EM["qstar"]),  # nudged LEFT off q's path
        dict(key="qtilde", tex=r"\tilde{q}", fb="<i>q&#771;</i>",
             xy=[float(v) for v in xy_qtilde], place="bottomleft", size=_POINT_FONT,
             color=INK, dx=-_QTILDE_LEFT_PX, ink=_INK_INSETS_EM["qtilde"]),  # below-left, away from Q
        dict(key="mtilde", tex=r"\tilde{m}", fb="<i>m&#771;</i>",
             xy=[float(v) for v in xy_mtilde], place="below", size=_POINT_FONT, color=INK,
             ink=_INK_INSETS_EM["mtilde"]),
    ]
    moving_labels = dict(
        q=dict(key="q", tex="q", fb="<i>q</i>", place="topright", size=_POINT_FONT,
               color=INK, ink=_INK_INSETS_EM["q"]),
        m=dict(key="m", tex="m", fb="<i>m</i>", size=_POINT_FONT, color=INK,
               ink=_INK_INSETS_EM["m"]),  # place per _M_FLIP
    )
    vx = barycentric_to_cartesian(np.eye(3))
    def _vfb(i):
        return (f"<i>&#948;</i><sub>{i}</sub> (<i>&#947;</i><sub>{i}</sub> "
                f"= {_fmt_gamma(gamma[i - 1])})")
    vertex_labels = [
        dict(tex=rf"\delta_{{1}}\,(\gamma_{{1}} = {_fmt_gamma(gamma[0])})", fb=_vfb(1),
             xy=[float(vx[0, 0]), float(vx[0, 1] - 0.02)], place="vbl",
             size=_VERTEX_FONT, color=LABEL),
        dict(tex=rf"\delta_{{2}}\,(\gamma_{{2}} = {_fmt_gamma(gamma[1])})", fb=_vfb(2),
             xy=[float(vx[1, 0]), float(vx[1, 1] - 0.02)], place="vbr",
             size=_VERTEX_FONT, color=LABEL),
        dict(tex=rf"\delta_{{3}}\,(\gamma_{{3}} = {_fmt_gamma(gamma[2])})", fb=_vfb(3),
             xy=[float(vx[2, 0]), float(vx[2, 1] + 0.018)], place="vtc",
             size=_VERTEX_FONT, color=LABEL),
    ]

    # ------------------------------------------------------------------ #
    #  Frames -- one per s, named "s0000".. Plotly.animate re-appends the SVG
    #  group of every trace a frame lists, pushing it to the top of the stack, so
    #  the FOUR STATIC markers are included too (with unchanged coordinates) and
    #  the list is ordered so re-append leaves lines under markers, and the moving
    #  pair q, m on top of everything. frame.data[i] applies to frame.traces[i],
    #  so the two lists are built in the same order. The readout is no longer a
    #  trace (it is an HTML/MathJax overlay); readout_values carries its per-frame
    #  numbers -- D(p||q) and D(p||m) at 4 decimals -- for the overlay to swap in.
    # ------------------------------------------------------------------ #
    frame_names = [f"s{i:04d}" for i in range(n_frames)]
    frames, readout_values, q_coords, m_coords = [], [], [], []
    for i, (name, s) in enumerate(zip(frame_names, s_grid)):
        state = _frame_state(s)
        s1, s2, lpm = mw_pieces(s)
        readout_values.append([f"{state['d_pq']:.4f}", f"{max(state['d_pm'], 0.0):.4f}"])
        q_coords.append([round(float(state["xq"][0]), 5), round(float(state["xq"][1]), 5)])
        m_coords.append([round(float(state["xm"][0]), 5), round(float(state["xm"][1]), 5)])
        frames.append(go.Frame(
            name=name,
            data=[
                go.Scatter(x=[s1[0][0], s1[1][0]], y=[s1[0][1], s1[1][1]]),          # seg1  (data 0)
                go.Scatter(x=[s2[0][0], s2[1][0]], y=[s2[0][1], s2[1][1]]),          # seg2  (data 1)
                go.Scatter(x=[lpm[0][0], lpm[1][0]], y=[lpm[0][1], lpm[1][1]]),      # p->m  (data 2)
                go.Scatter(x=[xy_p[0], state["xq"][0]], y=[xy_p[1], state["xq"][1]]),  # p->q (data 3)
                go.Scatter(x=[xy_qtilde[0]], y=[xy_qtilde[1]]),                      # q~ static (data 4)
                go.Scatter(x=[xy_mtilde[0]], y=[xy_mtilde[1]]),                      # m~ static (data 5)
                go.Scatter(x=[xy_p[0]], y=[xy_p[1]]),                                # p static  (data 6)
                go.Scatter(x=[xy_qstar[0]], y=[xy_qstar[1]]),                        # q* static (data 7)
                go.Scatter(x=[state["xq"][0]], y=[state["xq"][1]],                   # q moving  (data 8)
                           customdata=[list(map(float, state["q"]))]),
                go.Scatter(x=[state["xm"][0]], y=[state["xm"][1]],                   # m moving  (data 9)
                           customdata=[list(map(float, state["m"]))]),
            ],
            traces=[idx_seg1, idx_seg2, idx_leg_pm, idx_leg_pq,
                    idx_qtilde, idx_mtilde, idx_p, idx_qstar, idx_q, idx_m]))
    fig.frames = frames
    q_frame_pos, m_frame_pos = 8, 9     # q and m positions in each frame's data list

    # Everything the overlay JS needs: label specs, the M_wstar segment (for m's
    # left-wedge vertical centring), and the per-frame q, m coordinates.
    label_spec = dict(
        gap=_LABEL_GAP_PX, radius=_DOT_D_PX / 2.0, m_flip=_M_FLIP,
        statics=static_labels, moving=moving_labels, lines=line_labels,
        vertices=vertex_labels, contours=contour_labels,
        mseg=[[float(v) for v in xy_mA], [float(v) for v in xy_mB]],
        qseg=[[float(v) for v in xy_A], [float(v) for v in xy_B]],   # Q, for the audit
        tri=[[float(v) for v in vx[k]] for k in range(3)],           # triangle vertices
        p=[float(v) for v in xy_p],                                  # for the p->q / p->m legs
        q_coords=q_coords, m_coords=m_coords)

    # ------------------------------------------------------------------ #
    #  Axes and layout -- single panel, explicit domains, equal aspect, height
    #  derived so the plot-area aspect matches the range aspect.
    # ------------------------------------------------------------------ #
    fig.update_xaxes(range=list(_X_RANGE), domain=[0.0, 1.0],
                     showgrid=False, zeroline=False,
                     showticklabels=False, visible=False)
    fig.update_yaxes(range=list(_Y_RANGE), domain=[0.0, 1.0],
                     scaleanchor="x", scaleratio=1.0,
                     showgrid=False, zeroline=False, showticklabels=False, visible=False)
    fig.update_layout(
        autosize=True, height=_figure_height(),
        margin=dict(l=_MARGIN_PX, r=_MARGIN_PX, t=_MARGIN_PX, b=_MARGIN_PX),
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        hovermode="closest",
        hoverlabel=dict(bgcolor=PAPER, bordercolor=with_alpha(INK, 0.35),
                        font=dict(size=11, color=INK)),
        dragmode=False, showlegend=False,   # no Plotly annotations: every label is an overlay
        # The slider places each tick/label at its landmark's INDEX FRACTION F =
        # idx/(n_frames-1); the CSS turns F into a pixel position that accounts
        # for thumb travel. Carry F (not a percentage) and the indices (for the
        # snap-on-release script). readout_values / d_star_str feed the readout
        # overlay; label_spec feeds every other overlay label; q_frame_pos /
        # m_frame_pos let the checks find the moving markers without hardcoding.
        meta=dict(n_frames=n_frames, start_index=start_index,
                  idx_qtilde=idx_tilde, idx_qstar=idx_star,
                  q_frame_pos=q_frame_pos, m_frame_pos=m_frame_pos,
                  readout_values=readout_values, d_star_str=f"{d_star:.4f}",
                  label_spec=label_spec,
                  frac_qtilde=idx_tilde / (n_frames - 1),
                  frac_qstar=idx_star / (n_frames - 1)),
    )
    return fig


def simplex_figure_html(fig: go.Figure) -> str:
    """The figure, a native range slider, and the few lines that wire them.

    Returns one HTML string for a Quarto cell to render (via ``IPython.HTML``):
    the Plotly figure div (plotly.js from CDN, modebar and scroll-zoom off), a
    native ``<input type="range">`` whose ``input`` event animates the named
    frame, and a resize handler that fills the column. There is deliberately no
    Plotly slider (its handle sticks in a drag state and tracks the cursor
    without a click). The track is labelled ``Q``, carries coloured landmark
    dots (lime q~, periwinkle q*) with ink labels, and snaps to a landmark on
    release.
    """
    import json
    import plotly.io as pio

    meta = dict(fig.layout.meta or {})
    n = int(meta.get("n_frames", len(fig.frames)))
    start = int(meta.get("start_index", 0))
    f_qt = float(meta.get("frac_qtilde", 0.42))     # landmark index fractions
    f_qs = float(meta.get("frac_qstar", 0.79))
    idx_qt = int(meta.get("idx_qtilde", 0))
    idx_qs = int(meta.get("idx_qstar", 0))
    apex = float(np.sqrt(3.0) / 2.0)
    # Readout overlay data: per-frame [D(p||q), D(p||m)] strings, the constant
    # edge D(p||q*), and the LaTeX (identical to the post's caption: `\|` for the
    # double bar). An array typesets the numbers under their symbols. Everything is
    # json.dumps'd so backslashes reach the JS string intact, no hand-escaping.
    values = list(meta.get("readout_values", []))
    d_star_str = str(meta.get("d_star_str", "0.0000"))
    values_json = json.dumps(values, separators=(",", ":"))
    js_dstar = json.dumps(d_star_str)
    # The overlay label spec (static/moving point labels, line, vertex and contour
    # labels, the M_wstar segment, and per-frame q/m coordinates). One JSON object.
    label_spec_json = json.dumps(dict(meta.get("label_spec", {})), separators=(",", ":"))
    # Slider labels move to MathJax too (item 1a): the same TeX as everywhere else.
    js_slider_qt = json.dumps(r"\tilde{q}")
    js_slider_qs = json.dumps(r"q^{*}")
    js_slider_q = json.dumps(r"\mathcal{Q}")
    # Ink TOP inset (em) for the two slider landmark labels, so the dot-to-label gap
    # matches the simplex (rev 12, item 1): the browser lifts each label by its ink
    # top so the GAP is measured to the ink, not the reserved font ascent.
    js_qt_inktop = _INK_INSETS_EM["qtilde"]["t"]
    js_qs_inktop = _INK_INSETS_EM["qstar"]["t"]
    # \underset stacks each number (and each operator) under its symbol while the
    # = and + keep the SAME inline spacing the prose uses -- unlike an array, whose
    # column padding (MathJax ignores @{...}/\arraycolsep) doubled it. The number
    # row now carries its own = and +, wrapped in \mathrel/\mathbin so the stacked
    # operator keeps the prose spacing class. \textstyle keeps everything full
    # size; the \rule strut opens ~half a line between the rows (all five
    # under-args share it, so the rows stay level).
    strut = r"\rule{0pt}{1.35em}"
    js_us_a = json.dumps(r"\underset{\textstyle " + strut + " ")
    js_us_b = json.dumps(r"}{D(p \| q)} \mathrel{\underset{\textstyle " + strut
                         + r" =}{=}} \underset{\textstyle " + strut + " ")
    js_us_c = json.dumps(r"}{D(p \| q^{*})} \mathbin{\underset{\textstyle " + strut
                         + r" +}{+}} \underset{\textstyle " + strut + " ")
    js_us_d = json.dumps(r"}{D(p \| m)}")
    d0, m0 = (values[start] if start < len(values) else ("0.0000", "0.0000"))
    # Plain-HTML readout shown until MathJax is ready (or if it never loads).
    fallback_html = (f'<span class="ro-fallback"><i>D</i>(<i>p</i>&#8741;<i>q</i>) = '
                     f'<i>D</i>(<i>p</i>&#8741;<i>q</i><sup>*</sup>) + '
                     f'<i>D</i>(<i>p</i>&#8741;<i>m</i>)<br>{d0} = {d_star_str} + {m0}</span>')
    # Each tick/label sits at its landmark's index fraction, mapped to a pixel
    # position that accounts for thumb travel (a range thumb's centre runs from
    # d/2 to W-d/2, not 0 to W).
    left_qt = f"calc(var(--thumb-d) / 2 + {f_qt:.5f} * (100% - var(--thumb-d)))"
    left_qs = f"calc(var(--thumb-d) / 2 + {f_qs:.5f} * (100% - var(--thumb-d)))"
    div_id = "simplex-figure"
    fig_html = pio.to_html(
        fig, include_plotlyjs="cdn", full_html=False, div_id=div_id,
        auto_play=False,   # otherwise the frames run once on load, off the open frame
        config={"displayModeBar": False, "scrollZoom": False})

    # The track is a straightened copy of Q: the thumb is q (ink dot, white ring
    # -- it already matches the simplex q marker), the two landmark ticks are
    # coloured dots (lime q~, periwinkle q*) with white rings like the simplex
    # markers, their labels are ink like the simplex point labels, and a "Q"
    # label sits to the left. The ticks/labels/label are absolutely positioned so
    # the wrapper's JS-set width and centring are untouched.
    return f"""<div class="simplex-readout-slot"></div>
<div class="simplex-fig-wrap">
{fig_html}
<div class="simplex-label-layer"></div>
<div class="simplex-readout-layer"><div class="simplex-readout" id="simplex-readout">{fallback_html}</div></div>
</div>
<div class="simplex-slider-wrap">
  <span class="simplex-q-label">&#x1D4AC;</span>
  <input type="range" class="simplex-slider"
    min="0" max="{n - 1}" value="{start}" step="1" aria-label="Move q along the segment Q">
  <span class="simplex-tick simplex-tick-qt" style="left: {left_qt};"></span>
  <span class="simplex-tick simplex-tick-qs" style="left: {left_qs};"></span>
  <span class="simplex-landmark simplex-landmark-qt" style="left: {left_qt};">q&#771;</span>
  <span class="simplex-landmark simplex-landmark-qs" style="left: {left_qs};">q<sup>*</sup></span>
</div>
<style>
/* The delta_1 / delta_2 corner labels are drawn with cliponaxis=False and, being
   fixed-pixel text, reach a little past the plot's SVG box -- more so now the
   figure renders at {_WIDTH_FRACTION:.0%} width. Let them show in the centring
   margin instead of being clipped by Plotly's main-svg overflow:hidden. */
#{div_id} .main-svg {{ overflow: visible; }}
/* The figure lives in a position:relative wrapper (centred, width set by fit()).
   The readout is a SIBLING of the graph div -- Plotly owns the graph div's
   children -- in an overlay that covers the plot and lets clicks/hover through. */
.simplex-fig-wrap {{ position: relative; margin: 0 auto; --sx-paper: {PAPER}; }}
.simplex-readout-layer {{ position: absolute; inset: 0; pointer-events: none; overflow: visible; }}
.simplex-readout-slot:empty {{ display: none; }}
/* Every figure label is an HTML element in this layer, typeset by MathJax and
   positioned from its measured box. A white halo (multi-direction text-shadow in
   PAPER) erases lines behind the letters, the cartographic treatment, so a label
   over Q, M_wstar, a leg, a contour or an edge never looks crossed. */
.simplex-label-layer {{ position: absolute; inset: 0; pointer-events: none; overflow: visible; }}
.simplex-olabel {{ position: absolute; left: 0; top: 0; line-height: 1; white-space: nowrap;
  will-change: transform; }}
.simplex-olabel, .simplex-landmark, .simplex-q-label {{
  text-shadow: -1.5px 0 var(--sx-paper, #fff), 1.5px 0 var(--sx-paper, #fff),
    0 -1.5px var(--sx-paper, #fff), 0 1.5px var(--sx-paper, #fff),
    -1.1px -1.1px var(--sx-paper, #fff), 1.1px -1.1px var(--sx-paper, #fff),
    -1.1px 1.1px var(--sx-paper, #fff), 1.1px 1.1px var(--sx-paper, #fff); }}
.simplex-olabel mjx-container {{ margin: 0 !important; }}
/* Contour labels sit ON their curve: a solid PAPER background (rotates with the
   label) cuts a clean gap in the line; no halo (the background does its job). */
.simplex-contour-label {{ background: {PAPER}; padding: 2px; text-shadow: none; }}
/* The readout box: a real CSS border in the triangle-outline colour/width, PAPER
   fill, INK text set explicitly (the site has a dark mode; the figure stays a
   white card, but text would otherwise inherit a light page colour). Font size
   1rem matches the body math. Position (overlay) or centring (block) is set by
   fit()/roPlace(); block mode drops it into normal flow above the figure. */
.simplex-readout {{ box-sizing: border-box; white-space: nowrap;
  border: 1.2px solid {_SCAFFOLD}; background: {PAPER}; color: {INK};
  padding: {_READOUT_PAD_PX:.0f}px; font-size: {_READOUT_FONT}px; line-height: 1; }}
.simplex-readout mjx-container {{ margin: 0 !important; }}
.simplex-readout .ro-fallback {{ display: inline-block; text-align: left; font-style: normal; }}
.simplex-readout.ro-block {{ position: static; display: table; margin: 0 auto .6rem; }}
.simplex-readout:not(.ro-block) {{ position: absolute; }}
/* --thumb-d is the single source of truth for the drawn dot diameter, derived
   from the simplex markers (_MARKER_SIZE + MARKER_OUTLINE_PX), with the ring at
   MARKER_OUTLINE_PX and box-sizing:border-box so thumb and ticks agree in WebKit
   and Firefox. The input is taller than the dot (a generous hit target); the
   track, ticks and thumb stay vertically centred. Ticks/labels use the same
   d/2 + F*(track - d) travel formula as the thumb. */
.simplex-slider-wrap {{ --thumb-d: {_DOT_D_PX}px; position: relative; height: 28px; line-height: 0;
  margin: .3rem auto 2.2rem; width: 83%; }}
.simplex-slider-wrap::before {{ content: ""; position: absolute; left: 0; top: 50%;
  width: 100%; height: 3px; border-radius: 2px; transform: translateY(-50%);
  background: var(--bs-border-color, #cfd3d8); z-index: 0; }}
.simplex-slider {{ -webkit-appearance: none; appearance: none; position: absolute;
  left: 0; top: 50%; width: 100%; height: 28px; transform: translateY(-50%);
  margin: 0; background: transparent; outline: none; cursor: pointer; z-index: 2; }}
.simplex-slider::-webkit-slider-thumb {{ -webkit-appearance: none; appearance: none;
  box-sizing: border-box; width: var(--thumb-d); height: var(--thumb-d); border-radius: 50%;
  background: var(--bs-body-color, #1f2328); border: {MARKER_OUTLINE_PX}px solid var(--bs-body-bg, #fff); }}
.simplex-slider::-moz-range-thumb {{ box-sizing: border-box; width: var(--thumb-d); height: var(--thumb-d);
  border: {MARKER_OUTLINE_PX}px solid var(--bs-body-bg, #fff); border-radius: 50%; background: var(--bs-body-color, #1f2328); }}
.simplex-tick {{ box-sizing: border-box; position: absolute; top: 50%;
  width: var(--thumb-d); height: var(--thumb-d); border-radius: 50%;
  transform: translate(-50%, -50%); border: {MARKER_OUTLINE_PX}px solid var(--bs-body-bg, #fff);
  z-index: 1; pointer-events: none; }}
.simplex-tick-qt {{ background: #84cc16; }}
.simplex-tick-qs {{ background: #7575f7; }}
/* Top = dot bottom + _LABEL_GAP_PX, so the label's TOP (its accent/superscript,
   the tallest part of the measured MathJax box) sits the same gap below the dot
   as a simplex label below its marker -- fixes the star/tilde hiding behind the
   dot (item 1d). Horizontal centring stays with the calc()-set left. */
.simplex-landmark {{ position: absolute;
  top: calc(50% + var(--thumb-d) / 2 + {_LABEL_GAP_PX}px); transform: translate(-50%, 0);
  font-size: {_POINT_FONT}px; font-style: italic; color: var(--bs-body-color, #1f2328);
  pointer-events: none; white-space: nowrap; }}
.simplex-q-label {{ position: absolute; right: 100%; top: 50%; transform: translateY(-50%);
  margin-right: 12px; font-size: {_LINE_FONT}px;
  color: var(--bs-body-color, #1f2328); pointer-events: none; }}
</style>
<script>
(function () {{
  var MARG = {_MARGIN_PX}, WFRAC = {_WIDTH_FRACTION}, THUMB_D = {_DOT_D_PX};
  var XSPAN = {_X_SPAN:.6f}, X0 = {_X_RANGE[0]}, Y1 = {_Y_RANGE[1]}, APEX = {apex:.10f};
  var gd = document.getElementById("{div_id}");
  var figWrap = gd.closest(".simplex-fig-wrap");
  var scope = figWrap.parentNode;
  var sliderWrap = scope.querySelector(".simplex-slider-wrap");
  var layer = figWrap.querySelector(".simplex-readout-layer");
  var slot = scope.querySelector(".simplex-readout-slot");
  var readout = scope.querySelector(".simplex-readout");
  var input = sliderWrap.querySelector(".simplex-slider");
  var frame = function (i) {{ return "s" + String(i).padStart(4, "0"); }};
  function animate(i) {{
    if (window.Plotly) Plotly.animate(gd, [frame(i)],
      {{mode: "immediate", frame: {{duration: 0, redraw: false}}, transition: {{duration: 0}}}});
  }}

  // ---- Readout overlay: an HTML element typeset by the page's own MathJax ----
  var VALUES = {values_json};
  var DSTAR = {js_dstar}, US_A = {js_us_a}, US_B = {js_us_b}, US_C = {js_us_c}, US_D = {js_us_d};
  var mjReady = false, roCache = {{}}, roFrame = {start}, coldMs = null, warmed = false;
  // Every label (and the readout) is set at N px in the CSS/spec, then its math is
  // scaled by the body-math percentage (MathJax's matchFontHeight, e.g. "90.5%"),
  // so N px renders exactly as body math would at N px, whatever the container
  // inherits. Captured once MathJax is ready.
  var bodyPct = null;
  function scaleMath(el) {{ if (!bodyPct) return; var c = el.querySelector("mjx-container"); if (c) c.style.fontSize = bodyPct; }}
  function roTex(i) {{
    var v = VALUES[i] || ["", ""];
    return US_A + v[0] + US_B + DSTAR + US_C + v[1] + US_D;
  }}
  function roNode(i) {{                         // cached per frame; cold cost timed once
    if (roCache[i]) return roCache[i];
    var t0 = performance.now();
    var node = MathJax.tex2chtml(roTex(i), {{display: false}});
    if (bodyPct) node.style.fontSize = bodyPct;
    if (coldMs === null) coldMs = performance.now() - t0;
    roCache[i] = node;
    return node;
  }}
  function roRenderMath(i) {{
    var miss = !roCache[i];
    readout.replaceChildren(roNode(i));
    if (miss) {{ MathJax.startup.document.clear(); MathJax.startup.document.updateDocument(); }}
    roPlace();
  }}
  function roRenderFallback(i) {{
    var v = VALUES[i] || ["", ""];
    readout.innerHTML = '<span class="ro-fallback"><i>D</i>(<i>p</i>&#8741;<i>q</i>) = '
      + '<i>D</i>(<i>p</i>&#8741;<i>q</i><sup>*</sup>) + <i>D</i>(<i>p</i>&#8741;<i>m</i>)<br>'
      + v[0] + " = " + DSTAR + " + " + v[1] + "</span>";
    roPlace();
  }}
  function roShow(i) {{ roFrame = i; if (mjReady) roRenderMath(i); else roRenderFallback(i); }}
  function ppuNow() {{ var w = figWrap.clientWidth || gd.clientWidth || 0; return (w - 2 * MARG) / XSPAN; }}
  function roPlace() {{
    var ppu = ppuNow();
    if (ppu <= 0) return;
    // Overlay first: top edge on the apex, left edge 1px inside the plot area.
    readout.classList.remove("ro-block");
    if (readout.parentNode !== layer) layer.appendChild(readout);
    readout.style.left = (MARG + 1) + "px";
    readout.style.top = (MARG + (Y1 - APEX) * ppu) + "px";
    var br = readout.getBoundingClientRect(), fr = figWrap.getBoundingClientRect();
    var boxRight = X0 + (br.right - fr.left - MARG) / ppu;
    var boxBottom = Y1 - (br.bottom - fr.top - MARG) / ppu;
    var edgeX = boxBottom / Math.sqrt(3.0);            // triangle left edge at box bottom
    if ((edgeX - boxRight) * ppu < 6) {{               // crowds the triangle -> block mode
      readout.classList.add("ro-block");
      readout.style.left = readout.style.top = "";
      if (readout.parentNode !== slot) slot.appendChild(readout);
    }}
  }}
  // MathJax loads with `defer`, so it may not exist when this script runs; poll
  // for its startup promise, then swap the fallback for typeset math.
  function whenMathJax(cb) {{
    if (window.MathJax && MathJax.startup && MathJax.startup.promise
        && typeof MathJax.tex2chtml === "function") {{
      MathJax.startup.promise.then(cb);
    }} else {{
      setTimeout(function () {{ whenMathJax(cb); }}, 50);
    }}
  }}
  whenMathJax(function () {{
    mjReady = true;
    // The percentage MathJax puts on in-text math (matchFontHeight); applied to
    // every label's mjx-container so each renders at its N px as body math would.
    var bodyC = document.querySelector("p mjx-container, .cell mjx-container, li mjx-container");
    bodyPct = (bodyC && bodyC.style.fontSize) ? bodyC.style.fontSize : null;
    roRenderMath(roFrame);
    typesetLabels();                       // swap every label's fallback for typeset math
    positionStatics(); frameLabels(roFrame);
    if (coldMs !== null && coldMs > 8 && window.requestIdleCallback && !warmed) {{
      warmed = true;                                   // pre-warm the cache in idle time
      var i = 0;
      requestIdleCallback(function step(dl) {{
        while (i < VALUES.length && dl.timeRemaining() > 3) roNode(i++);
        if (i < VALUES.length) requestIdleCallback(step);
      }});
    }}
  }});
  // Coalesce per-frame work (readout numbers + moving labels) to one animation
  // frame, so the dots, the readout and the q/m labels always agree.
  var roPending = null, roRaf = 0;
  function updateFrame(i) {{ roShow(i); if (mjReady || Lq) frameLabels(i); }}
  function roSchedule(i) {{
    roPending = i;
    if (!roRaf) roRaf = requestAnimationFrame(function () {{
      roRaf = 0; var j = roPending; roPending = null; updateFrame(j);
    }});
  }}

  // ---- Overlay labels: every figure label, typeset by MathJax, placed from its
  //      measured box; a white halo (CSS) erases lines behind the letters ----
  var SPEC = {label_spec_json};
  var GAP = SPEC.gap, RAD = SPEC.radius, MFLIP = SPEC.m_flip;
  var MSEG = SPEC.mseg, QCO = SPEC.q_coords, MCO = SPEC.m_coords;
  var labelLayer = figWrap.querySelector(".simplex-label-layer");
  function pxx(x, ppu) {{ return MARG + (x - X0) * ppu; }}
  function pyy(y, ppu) {{ return MARG + (Y1 - y) * ppu; }}
  function mkLabel(spec) {{
    var el = document.createElement("div");
    // Contour labels sit ON their curve, so they get a solid PAPER background
    // that cuts a clean gap in the line (a halo only clears each glyph's strokes,
    // letting the curve show through the gaps between characters); every other
    // label gets a halo, for lines that merely pass behind it.
    el.className = "simplex-olabel" + (spec.place === "rotated" ? " simplex-contour-label" : "");
    el.style.fontSize = spec.size + "px";
    el.style.color = spec.color;
    el.innerHTML = spec.fb;                    // fallback until MathJax is ready
    labelLayer.appendChild(el);
    return {{el: el, spec: spec, w: 0, h: 0}};
  }}
  var STATIC_LABELS = [].concat(SPEC.statics, SPEC.lines, SPEC.vertices, SPEC.contours).map(mkLabel);
  var Lq = mkLabel(SPEC.moving.q), Lm = mkLabel(SPEC.moving.m);
  var sLabels = [
    {{el: sliderWrap.querySelector(".simplex-landmark-qt"), tex: {js_slider_qt}, inkTop: {js_qt_inktop}}},
    {{el: sliderWrap.querySelector(".simplex-landmark-qs"), tex: {js_slider_qs}, inkTop: {js_qs_inktop}}},
    {{el: sliderWrap.querySelector(".simplex-q-label"), tex: {js_slider_q}}}
  ];
  function measure(L) {{ L.w = L.el.offsetWidth; L.h = L.el.offsetHeight;
    var c = L.el.querySelector("mjx-container");
    L.fs = c ? parseFloat(getComputedStyle(c).fontSize) : L.spec.size; }}
  // Ink insets (em, from _INK_INSETS_EM) in CSS px for THIS label's container size.
  // The ink box is the element box shrunk by {{l,r}} horizontally, {{t,b}} vertically.
  function inkOff(L) {{ var k = L.spec.ink, f = L.fs || L.spec.size;
    return k ? {{t: k.t * f, b: k.b * f, l: k.l * f, r: k.r * f}} : {{t: 0, b: 0, l: 0, r: 0}}; }}
  function placeStatic(L, ppu) {{
    var s = L.spec, ax = pxx(s.xy[0], ppu), ay = pyy(s.xy[1], ppu), tf = "", left, top, io = inkOff(L);
    if (s.place === "below") {{                    // ink TOP = marker bottom + GAP; ink centred on ax
      left = ax - L.w / 2 + (io.r - io.l) / 2 + (s.dx || 0);
      top = ay + RAD + GAP - io.t;
    }} else if (s.place === "bottomleft") {{        // mirror of "top right": ink top-right corner off the marker, down-left
      var d = (RAD + GAP) / Math.SQRT2;
      left = ax - d - L.w + io.r + (s.dx || 0);    // dx (<= 0) shifts further LEFT, away from Q
      top = ay + d - io.t;
    }} else if (s.place === "outside-right") {{ left = ax - L.w; top = ay - L.h / 2; }}
    else if (s.place === "vbl") {{ left = ax - L.w; top = ay; }}
    else if (s.place === "vbr") {{ left = ax; top = ay; }}
    else if (s.place === "vtc") {{ left = ax - L.w / 2; top = ay - L.h; }}
    else if (s.place === "rotated") {{ left = ax; top = ay; tf = "translate(-50%,-50%) rotate(" + s.angle + "deg)"; }}
    L.el.style.left = left + "px"; L.el.style.top = top + "px"; L.el.style.transform = tf;
  }}
  function mLineY(x) {{ return MSEG[0][1] + (x - MSEG[0][0]) / (MSEG[1][0] - MSEG[0][0]) * (MSEG[1][1] - MSEG[0][1]); }}
  function placeMoving(L, xy, place, ppu, qxy) {{
    var mx = pxx(xy[0], ppu), my = pyy(xy[1], ppu), left, top, io = inkOff(L);
    var inkW = L.w - io.l - io.r, inkH = L.h - io.t - io.b;
    if (place === "undertuck") {{                 // tucked just under M_wstar, lower-left of m (INK box)
      var ir = mx - RAD - GAP;                     // ink RIGHT edge: GAP left of m's marker
      var xRight = X0 + (ir - MARG) / ppu;         // data x at the ink right edge
      var inkTop = pyy(mLineY(xRight), ppu) + GAP; // ink TOP: GAP below M_wstar there
      var qx, qy, haveQ = !!qxy;
      if (haveQ) {{ qx = pxx(qxy[0], ppu); qy = pyy(qxy[1], ppu); }}
      // Left of m's marker by GAP, but near delta_2 q converges onto m: drop the
      // ink below q's marker if it would otherwise cover it.
      if (haveQ && qx - RAD - GAP < ir && inkTop < qy + RAD + GAP && inkTop + inkH > qy - RAD) inkTop = qy + RAD + GAP;
      var inkFloor = pyy(0, ppu) - GAP - inkH;     // lowest ink top keeping GAP above the base
      if (inkTop > inkFloor) {{ inkTop = inkFloor; L._baseClamped = true; }}
      else L._baseClamped = false;
      // Base-clamped against the floor we cannot drop below q, so if q's marker
      // still sits in the ink's vertical band and left of m, tuck the ink's RIGHT
      // edge left of q's disk too -- the label then clears both markers.
      if (L._baseClamped && haveQ && qx < mx && inkTop < qy + RAD && inkTop + inkH > qy - RAD && qx - RAD - GAP < ir) {{
        ir = qx - RAD - GAP;
      }}
      left = ir + io.r - L.w;                      // element left from the ink right edge
      top = inkTop - io.t;                         // element top from the ink top
    }} else {{                                      // "top right": ink bottom-left corner off the edge
      var d = (RAD + GAP) / Math.SQRT2;
      left = mx + d - io.l;                         // ink bottom-left corner at (mx + d, my - d)
      top = my - d - L.h + io.b;
    }}
    L.el.style.transform = "translate(" + left + "px, " + top + "px)";
  }}
  function mPlace(i) {{ return (i / (N - 1) < MFLIP) ? "topright" : "undertuck"; }}
  function frameLabels(i) {{
    var ppu = ppuNow(); if (ppu <= 0) return;
    placeMoving(Lq, QCO[i], "topright", ppu);
    placeMoving(Lm, MCO[i], mPlace(i), ppu, QCO[i]);
  }}
  function positionStatics() {{
    var ppu = ppuNow(); if (ppu <= 0) return;
    for (var i = 0; i < STATIC_LABELS.length; i++) placeStatic(STATIC_LABELS[i], ppu);
  }}
  function typesetLabels() {{
    var all = STATIC_LABELS.concat([Lq, Lm]);
    for (var i = 0; i < all.length; i++) {{
      all[i].el.replaceChildren(MathJax.tex2chtml(all[i].spec.tex, {{display: false}})); scaleMath(all[i].el);
    }}
    for (var j = 0; j < sLabels.length; j++) if (sLabels[j].el) {{
      sLabels[j].el.replaceChildren(MathJax.tex2chtml(sLabels[j].tex, {{display: false}})); scaleMath(sLabels[j].el);
      if (sLabels[j].inkTop != null) {{                 // lift by the ink top so the dot-to-label gap == GAP
        var sc = sLabels[j].el.querySelector("mjx-container");
        var sf = sc ? parseFloat(getComputedStyle(sc).fontSize) : {_POINT_FONT};
        sLabels[j].el.style.top = "calc(50% + var(--thumb-d) / 2 + " + (GAP - sLabels[j].inkTop * sf) + "px)";
      }}
    }}
    MathJax.startup.document.clear(); MathJax.startup.document.updateDocument();
    for (i = 0; i < all.length; i++) measure(all[i]);
  }}
  for (var _li = 0; _li < STATIC_LABELS.length; _li++) measure(STATIC_LABELS[_li]);
  measure(Lq); measure(Lm);                    // fallback dimensions until MathJax swaps in

  // ---- Slider ----
  input.addEventListener("input", function () {{ animate(input.value); roSchedule(+input.value); }});
  // Snap onto a landmark on release ("change"); ~SNAP_PX CSS px wide at any track
  // width (px -> frames from the thumb's usable travel, recomputed per release).
  var LANDMARKS = [{idx_qt}, {idx_qs}], SNAP_PX = 4, N = {n};
  function snapTol() {{
    var travel = input.getBoundingClientRect().width - THUMB_D;
    return Math.max(1, Math.round(SNAP_PX * (N - 1) / travel));
  }}
  input.addEventListener("change", function () {{
    var v = parseInt(input.value, 10), tol = snapTol();
    for (var i = 0; i < LANDMARKS.length; i++) {{
      if (Math.abs(v - LANDMARKS[i]) <= tol) {{ input.value = LANDMARKS[i]; animate(LANDMARKS[i]); break; }}
    }}
    roSchedule(parseInt(input.value, 10));             // keep the readout in step with the snap
  }});

  // ---- Fit: fill the column at WFRAC width, centred; keep aspect; place readout ----
  function host() {{ return gd.closest(".cell-output-display") || gd.parentElement; }}
  function fit() {{
    if (!window.Plotly) {{ return setTimeout(fit, 30); }}
    var measured = (host() && host().clientWidth) || gd.offsetWidth;
    if (!measured) {{ return setTimeout(fit, 30); }}
    var w = Math.round(measured * WFRAC);
    var h = Math.round((w - 2 * MARG) * {_ASPECT:.6f} + 2 * MARG);
    figWrap.style.width = w + "px";                    // centre the wrapper (CSS margin:auto)
    Plotly.relayout(gd, {{
      width: w, height: h, autosize: false,
      "xaxis.range": [{_X_RANGE[0]}, {_X_RANGE[1]}],
      "yaxis.range": [{_Y_RANGE[0]}, {_Y_RANGE[1]}]
    }}).then(function () {{
      // Plotly resizes the SVG but leaves the graph-div's inline height at the
      // build-time default; pull it down so no dead whitespace below the triangle.
      gd.style.height = gd._fullLayout.height + "px";
      roPlace();                                       // reposition the readout for the new width
      positionStatics(); frameLabels(roFrame);         // and every overlay label
    }});
    sliderWrap.style.width = Math.round((w - 2 * MARG) / {_X_SPAN:.4f}) + "px";
  }}

  // ---- Audit (?simplex-audit): step all frames, measure every label + marker ----
  function runAudit() {{
    var ppu = ppuNow(); if (ppu <= 0) return setTimeout(runAudit, 100);
    var fr = figWrap.getBoundingClientRect();
    function boxOf(el) {{ var b = el.getBoundingClientRect();
      return {{l: b.left - fr.left, t: b.top - fr.top, r: b.right - fr.left, bo: b.bottom - fr.top}}; }}
    // Collision box: the INK box for point labels (element box shrunk by the ink
    // insets), the element box for everything else (lines, vertices, contours).
    function cbox(L) {{ var b = boxOf(L.el); if (!L.spec.ink) return b;
      var f = L.fs || L.spec.size, k = L.spec.ink;
      return {{l: b.l + k.l * f, t: b.t + k.t * f, r: b.r - k.r * f, bo: b.bo - k.b * f}}; }}
    function mk(xy) {{ return {{x: pxx(xy[0], ppu), y: pyy(xy[1], ppu)}}; }}
    function seg(a, b) {{ return [pxx(a[0], ppu), pyy(a[1], ppu), pxx(b[0], ppu), pyy(b[1], ppu)]; }}
    function boxDisk(bx, c) {{ var cx = Math.max(bx.l, Math.min(c.x, bx.r)), cy = Math.max(bx.t, Math.min(c.y, bx.bo));
      return Math.hypot(c.x - cx, c.y - cy) - RAD; }}                        // < 0 => overlap
    function boxBox(a, b) {{ return !(a.r <= b.l || b.r <= a.l || a.bo <= b.t || b.bo <= a.t); }}
    function segBox(s, bx) {{ for (var t = 0; t <= 1; t += 0.02) {{
      var x = s[0] + (s[2] - s[0]) * t, y = s[1] + (s[3] - s[1]) * t;
      if (x >= bx.l && x <= bx.r && y >= bx.t && y <= bx.bo) return true; }} return false; }}
    var contours = [];
    for (var ci = 0; ci < 6; ci++) if (gd.data[ci] && gd.data[ci].x) contours.push(gd.data[ci]);
    function contourBox(bx) {{ for (var c = 0; c < contours.length; c++) {{ var C = contours[c];
      for (var k = 0; k < C.x.length; k += 3) {{ var x = pxx(C.x[k], ppu), y = pyy(C.y[k], ppu);
        if (x >= bx.l && x <= bx.r && y >= bx.t && y <= bx.bo) return true; }} }} return false; }}
    positionStatics();
    var TRI = SPEC.tri, P = SPEC.p, Ln = {{Q: seg(SPEC.qseg[0], SPEC.qseg[1]), M: seg(MSEG[0], MSEG[1]),
      e0: seg(TRI[0], TRI[1]), e1: seg(TRI[1], TRI[2]), e2: seg(TRI[2], TRI[0])}};
    var sMk = SPEC.statics.map(function (s) {{ return mk(s.xy); }});
    var sBx = STATIC_LABELS.map(function (L) {{ return {{box: cbox(L), key: L.spec.key || L.spec.place, ink: !!L.spec.ink}}; }});
    var hard = [], minDisk = 1e9, tol = {{Q: 0, M: 0, leg: 0, edge: 0, contour: 0}}, baseClamp = [], staticLine = [];
    // Static point labels must NOT touch Q or M_wstar (rev 12, item 4): unlike the
    // moving pair (whose halo covers a crossing), a fixed label on a line reads as
    // sitting on it. Statics don't move, so this is checked once.
    for (var si = 0; si < sBx.length; si++) if (sBx[si].ink) {{
      if (segBox(Ln.Q, sBx[si].box)) staticLine.push(sBx[si].key + "/Q");
      if (segBox(Ln.M, sBx[si].box)) staticLine.push(sBx[si].key + "/M");
    }}
    for (si = 0; si < staticLine.length; si++)
      hard.push({{f: "static", t: "label-line", label: staticLine[si]}});
    for (var i = 0; i < N; i++) {{
      placeMoving(Lq, QCO[i], "topright", ppu);
      var mp = mPlace(i); placeMoving(Lm, MCO[i], mp, ppu, QCO[i]);
      var mv = [{{box: cbox(Lq), key: "q"}}, {{box: cbox(Lm), key: "m"}}];
      var marks = sMk.concat([mk(QCO[i]), mk(MCO[i])]);
      var boxes = sBx.concat(mv);
      for (var a = 0; a < mv.length; a++) {{
        for (var b = 0; b < marks.length; b++) {{ var cl = boxDisk(mv[a].box, marks[b]);
          minDisk = Math.min(minDisk, cl);
          if (cl < -0.5) hard.push({{f: i, t: "label-marker", label: mv[a].key, mark: b, clr: +cl.toFixed(1)}}); }}
        for (b = 0; b < boxes.length; b++) {{ if (boxes[b] === mv[a]) continue;
          if (boxBox(mv[a].box, boxes[b].box)) hard.push({{f: i, t: "label-label", a: mv[a].key, b: boxes[b].key}}); }}
        var bx = mv[a].box;
        if (segBox(Ln.Q, bx)) tol.Q++;
        if (segBox(Ln.M, bx)) tol.M++;
        if (segBox(seg(P, QCO[i]), bx) || segBox(seg(P, MCO[i]), bx)) tol.leg++;
        if (segBox(Ln.e0, bx) || segBox(Ln.e1, bx) || segBox(Ln.e2, bx)) tol.edge++;
        if (contourBox(bx)) tol.contour++;
      }}
      if (mp === "undertuck" && Lm._baseClamped) baseClamp.push(i);
    }}
    for (a = 0; a < sBx.length; a++) for (b = a + 1; b < sBx.length; b++)
      if (boxBox(sBx[a].box, sBx[b].box)) hard.push({{f: "static", t: "label-label", a: sBx[a].key, b: sBx[b].key}});
    // Re-derive f_max for m's "top right": the first frame where FORCED top right
    // has a HARD violation (q marker, any static label, or q's box). _M_FLIP must
    // not exceed this fraction.
    var trFail = null;
    for (var j = 0; j < N; j++) {{
      placeMoving(Lm, MCO[j], "topright", ppu); placeMoving(Lq, QCO[j], "topright", ppu);
      var mb = cbox(Lm), bad = boxDisk(mb, mk(QCO[j])) < -0.5;
      for (var s = 0; s < sBx.length && !bad; s++) if (boxBox(mb, sBx[s].box)) bad = true;
      if (!bad && boxBox(mb, cbox(Lq))) bad = true;
      if (bad) {{ trFail = j; break; }}
    }}
    frameLabels(roFrame);
    var out = {{width: Math.round(figWrap.clientWidth), hardCount: hard.length, hard: hard.slice(0, 40),
      minLabelMarkerClearPx: +minDisk.toFixed(2), tolerated: tol, staticLine: staticLine,
      toprightFmax: trFail === null ? 1.0 : +(trFail / (N - 1)).toFixed(4), toprightFirstFail: trFail,
      baseClamp: baseClamp.length ? (baseClamp[0] + ".." + baseClamp[baseClamp.length - 1] + " (" + baseClamp.length + ")") : "none"}};
    window.__SIMPLEX_AUDIT__ = out; console.log("SIMPLEX-AUDIT " + JSON.stringify(out));
    return out;
  }}
  if (location.search.indexOf("simplex-audit") >= 0) whenMathJax(function () {{ setTimeout(runAudit, 400); }});

  if (window.ResizeObserver) {{ new ResizeObserver(fit).observe(host()); }}
  window.addEventListener("resize", fit);
  setTimeout(fit, 0);
}})();
</script>"""


# --------------------------------------------------------------------------- #
#  Assertions and a spot-value table (run: uv run python simplex_figure.py)
# --------------------------------------------------------------------------- #
def _run_checks() -> None:
    r = 0.97
    gamma = np.array([2.0, 1.0, 0.4])
    p = np.array([0.5, 0.2, 0.3])

    def close(a, b, tol=1e-9, msg=""):
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        assert np.all(np.abs(a - b) <= tol), f"{msg}: {a} != {b} (tol {tol})"

    f_star = optimal_fraction(r, gamma, p)
    y_star = _portfolio_return(f_star, r, gamma)
    q_star = manufactured_measure(f_star, r, gamma, p)
    w_star = growth_rate(f_star, r, gamma, p)
    d_pq_star = kl_divergence(p, q_star)

    close(f_star, 0.722765201113, 1e-9, "f*")
    close(y_star, [1.71444816, 0.99168296, 0.55802384], 1e-7, "Y(f*)")
    close(q_star, [0.28288986, 0.19562704, 0.52148310], 1e-7, "q*")
    close(np.sum(q_star), 1.0, 1e-12, "sum(q*)")
    close(np.dot(q_star, gamma), r, 1e-12, "dot(q*, gamma) = r")
    close(w_star, 0.092869182037, 1e-9, "W(f*) nats")
    close(w_star / _LN2, 0.133981908377, 1e-9, "W(f*) bits")
    close(np.log(r), -0.030459207485, 1e-9, "log(r)")
    close(d_pq_star, 0.123328389522, 1e-9, "D(p||q*)")
    close(w_star - np.log(r), d_pq_star, 1e-12, "W(f*) - log(r) = D(p||q*)")
    close(tilted_measure(q_star, f_star, r, gamma), p, 1e-9, "m(q*, f*) = p")

    A, B = risk_neutral_segment_endpoints(r, gamma)
    close(A, [0.0, 0.95, 0.05], 1e-12, "A")
    close(B, [0.35625, 0.0, 0.64375], 1e-12, "B")

    m_A = tilted_measure(A, f_star, r, gamma)
    m_B = tilted_measure(B, f_star, r, gamma)
    close(m_A, [0.0, 0.97123588, 0.02876412], 1e-7, "m(A, f*)")
    close(m_B, [0.62966202, 0.0, 0.37033798], 1e-7, "m(B, f*)")

    f_lo, f_hi = admissible_f_range(r, gamma)
    close(f_lo, -0.9417475728, 1e-9, "f_lo")
    close(f_hi, 1.7017543860, 1e-9, "f_hi")
    close(tilted_measure(q_star, f_lo, r, gamma), [0.0, 0.18992916, 0.81007084], 1e-7, "M_qstar at f_lo")
    close(tilted_measure(q_star, f_hi, r, gamma), [0.79407680, 0.20592320, 0.0], 1e-7, "M_qstar at f_hi")
    close(tilted_measure(q_star, 0.0, r, gamma), q_star, 1e-12, "M_qstar at f=0 = q*")
    close(tilted_measure(q_star, f_star, r, gamma), p, 1e-9, "M_qstar at f=f* = p")

    # Geometry reference positions.
    close(barycentric_to_cartesian(p), [0.350000, 0.259808], 1e-6, "xy(p)")
    close(barycentric_to_cartesian(q_star), [0.456369, 0.451618], 1e-6, "xy(q*)")
    close(barycentric_to_cartesian(A), [0.975000, 0.043301], 1e-6, "xy(A)")
    close(barycentric_to_cartesian(B), [0.321875, 0.557504], 1e-6, "xy(B)")
    close(barycentric_to_cartesian(m_A), [0.985618, 0.024910], 1e-6, "xy(m(A,f*))")
    close(barycentric_to_cartesian(m_B), [0.185169, 0.320722], 1e-6, "xy(m(B,f*))")
    close(barycentric_to_cartesian(tilted_measure(q_star, f_lo, r, gamma)),
          [0.594965, 0.701542], 1e-6, "xy(M_qstar at f_lo)")
    close(barycentric_to_cartesian(tilted_measure(q_star, f_hi, r, gamma)),
          [0.205923, 0.000000], 1e-6, "xy(M_qstar at f_hi)")

    # Decomposition: D(p||q(s)) = D(p||q*) + D(p||m(q(s), f*)) across the interior.
    for s in np.linspace(0.05, 0.95, 12):
        q = A + s * (B - A)
        m = tilted_measure(q, f_star, r, gamma)
        lhs = kl_divergence(p, q)
        rhs = d_pq_star + kl_divergence(p, m)
        close(lhs, rhs, 1e-9, f"decomposition at s={s:.3f}")

    # Slider interval brackets q*.
    s_lo, s_hi, s_star = optimal_slider_interval(r, gamma, p, 4.0)
    assert s_lo < s_star < s_hi, f"q* not inside slider interval: {s_lo} !< {s_star} !< {s_hi}"

    # Spot values by third coordinate t = q_3.
    spot = {0.150000: 0.993332806, 0.300000: 0.399666220, 0.521483: 0.123328390,
            0.580000: 0.163173580, 0.620000: 0.304263821}
    print("\n  spot values  (t = q_3)")
    print("  " + "-" * 34)
    print(f"  {'t':>10}   {'D(p||q)':>14}")
    for t, expected in spot.items():
        s = (t - A[2]) / (B[2] - A[2])
        q = A + s * (B - A)
        d = kl_divergence(p, q)
        flag = "ok" if abs(d - expected) < 1e-6 else "MISMATCH"
        print(f"  {t:>10.6f}   {d:>14.9f}   {flag}")
        close(d, expected, 1e-6, f"spot t={t}")

    print("\n  All assertions passed.\n")
    print(f"  f*        = {f_star:.12f}")
    print(f"  q*        = ({q_star[0]:.8f}, {q_star[1]:.8f}, {q_star[2]:.8f})")
    print(f"  D(p||q*)  = {d_pq_star:.12f} nats   (the edge)")
    print(f"  W(w*)     = {w_star:.12f} nats = {w_star / _LN2:.12f} bits")
    print(f"  Q: A      = ({A[0]:.5f}, {A[1]:.5f}, {A[2]:.5f})")
    print(f"     B      = ({B[0]:.5f}, {B[1]:.5f}, {B[2]:.5f})")
    print(f"  slider s in [{s_lo:.6f}, {s_hi:.6f}], s* = {s_star:.6f}")


def _check_contours() -> None:
    """New in the revision: every emitted KL level curve sits on its level."""
    r = 0.97
    gamma = np.array([2.0, 1.0, 0.4])
    p = np.array([0.5, 0.2, 0.3])
    d_star = kl_divergence(p, manufactured_measure(optimal_fraction(r, gamma, p), r, gamma, p))

    worst = 0.0
    for mult in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
        level = mult * d_star
        curve = _kl_level_curve(p, level)
        for q in curve[::29]:                     # a sample of points on the curve
            err = abs(kl_divergence(p, q) - level)
            worst = max(worst, err)
            assert err <= 1e-9, f"contour {mult}x off level: {err:.2e}"
    print(f"  contour level curves on-level to {worst:.2e}  (all six levels).")


def _check_layout_aspect() -> None:
    """New: the derived height makes the plot-area aspect match the range aspect."""
    height = _figure_height()
    plot_w = _REF_WIDTH - 2 * _MARGIN_PX
    plot_h = height - 2 * _MARGIN_PX
    ratio_plot = plot_w / plot_h
    ratio_range = _X_SPAN / _Y_SPAN
    rel = abs(ratio_plot - ratio_range) / ratio_range
    assert rel < 0.01, (
        f"plot-area aspect {ratio_plot:.4f} != range aspect {ratio_range:.4f} "
        f"(rel {rel:.2%})"
    )
    print(f"  layout: plot-area aspect {ratio_plot:.4f} vs range {ratio_range:.4f} "
          f"(rel {rel:.3%}); build-time div height {height} px.")
    # What the reader actually sees: the figure renders at _WIDTH_FRACTION of the
    # column, so scale the reference and the real column by it before reporting.
    for col in (_REF_WIDTH, _COLUMN_PX):
        eff_w = _WIDTH_FRACTION * col
        eff_h = (eff_w - 2 * _MARGIN_PX) * _ASPECT + 2 * _MARGIN_PX
        tri_w = (eff_w - 2 * _MARGIN_PX) / _X_SPAN     # data x-span is 1.0
        print(f"  @ {col} px column: figure {eff_w:.0f} x {eff_h:.0f} px "
              f"(x{_WIDTH_FRACTION:.2f}), drawn triangle width {tri_w:.0f} px.")

    # Largest divergence the slider can reach, at s in {0.01, 0.99}.
    r, gamma, p = 0.97, np.array([2.0, 1.0, 0.4]), np.array([0.5, 0.2, 0.3])
    A, B = risk_neutral_segment_endpoints(r, gamma)
    d_ends = [kl_divergence(p, A + s * (B - A)) for s in (0.01, 0.99)]
    print(f"  largest reachable D(p||q) = {max(d_ends):.4f} nats "
          f"(at the slider extremes s = 0.01, 0.99).")

    f_star = optimal_fraction(r, gamma, p)
    q_star = manufactured_measure(f_star, r, gamma, p)
    d_star = kl_divergence(p, q_star)
    xy_p = barycentric_to_cartesian(p)
    xy_qstar = barycentric_to_cartesian(q_star)

    # Every figure label is an HTML/MathJax overlay now (Stage 2), positioned from
    # its measured box, so label placement is checked in the browser, not here. The
    # one readout invariant Python still owns is that the number row keeps a
    # constant width, which holds while D(p||q) < 10 (a single integer digit).
    d_max = max(d_ends)
    assert d_max < 10.0, f"D(p||q) reaches {d_max:.3f} >= 10; the readout number row would widen"
    print(f"  readout + all labels: HTML/MathJax overlay; geometry checked in the "
          f"browser (?simplex-audit). D_max = {d_max:.3f} < 10 (number row constant-width).")

    fig = build_simplex_figure(r, gamma, p)
    mt = dict(fig.layout.meta)
    spec = dict(mt["label_spec"])
    # Landmark snapping: three distinct grid indices.
    idxs = (int(mt["idx_qtilde"]), int(mt["idx_qstar"]), int(mt["start_index"]))
    assert len(set(idxs)) == 3, f"landmark indices collide: {idxs}"
    print(f"  landmark indices: q~ = {idxs[0]}, q* = {idxs[1]}, open = {idxs[2]} "
          f"(of {mt['n_frames']}); index frac q~ = {float(mt['frac_qtilde']):.3f}, "
          f"q* = {float(mt['frac_qstar']):.3f}.")
    # The tangent contour label is still positioned in Python: near q*, right of p.
    tang = [c for c in spec["contours"] if c["tex"] == f"{d_star:.2f}"]
    tx, ty = tang[-1]["xy"]
    print(f"  tangent contour label '{d_star:.2f}' at ({tx:.3f}, {ty:.3f}), "
          f"{np.hypot(tx - xy_qstar[0], ty - xy_qstar[1]):.3f} du from q*; "
          f"x >= x_p ({xy_p[0]:.3f}): {tx >= xy_p[0]}.")


def _check_qtilde() -> None:
    """New: the complete-market measure q~ and its partner m~ (equation (3.3))."""
    r = 0.97
    gamma = np.array([2.0, 1.0, 0.4])
    gamma2 = np.array([0.5, 0.7, 1.7])
    p = np.array([0.5, 0.2, 0.3])

    def close(a, b, tol=1e-9, msg=""):
        a, b = np.asarray(a, float), np.asarray(b, float)
        assert np.all(np.abs(a - b) <= tol), f"{msg}: {a} != {b} (tol {tol})"

    f_star = optimal_fraction(r, gamma, p)
    q_star = manufactured_measure(f_star, r, gamma, p)
    d_star = kl_divergence(p, q_star)
    A, B = risk_neutral_segment_endpoints(r, gamma)

    G3 = np.column_stack([r * np.ones(3), gamma, gamma2])
    q_tilde = np.linalg.solve(G3.T, r * np.ones(3))
    m_tilde = tilted_measure(q_tilde, f_star, r, gamma)
    sigma = kl_divergence(p, m_tilde)
    d_pqt = kl_divergence(p, q_tilde)

    close(np.linalg.det(G3), -0.853600, 1e-6, "det(G3)")
    close(q_tilde, [0.15, 0.55, 0.30], 1e-9, "q~")
    assert np.all(q_tilde > 0.0), "q~ not strictly positive"
    close(np.sum(q_tilde), 1.0, 1e-12, "sum(q~)")
    close(np.dot(q_tilde, gamma), r, 1e-12, "q~ on Q: dot(q~, gamma) = r")
    close(m_tilde, [0.265121, 0.562294, 0.172585], 1e-6, "m~")
    close(np.sum(m_tilde), 1.0, 1e-12, "sum(m~)")
    close(d_pqt, 0.399666, 1e-6, "D(p||q~)")
    close(sigma, 0.276338, 1e-6, "sigma = D(p||m~)")
    close(d_star + sigma, d_pqt, 1e-9, "D(p||q*) + sigma = D(p||q~)")

    # s parameters, and both strictly inside the clipped slider range.
    k = int(np.argmax(np.abs(B - A)))
    s_tilde = (q_tilde[k] - A[k]) / (B[k] - A[k])
    s_star = (q_star[k] - A[k]) / (B[k] - A[k])
    close(s_tilde, 0.4211, 1e-3, "s(q~)")
    close(s_star, 0.7941, 1e-3, "s(q*)")
    assert 0.01 < s_tilde < 0.99 and 0.01 < s_star < 0.99, "landmarks not inside slider range"

    # Cartesian positions for sanity.
    close(barycentric_to_cartesian(q_tilde), [0.700000, 0.259808], 1e-6, "xy(q~)")
    close(barycentric_to_cartesian(m_tilde), [0.648587, 0.149463], 1e-6, "xy(m~)")

    print(f"  q~ = ({q_tilde[0]:.6f}, {q_tilde[1]:.6f}, {q_tilde[2]:.6f}), "
          f"D(p||q~) = {d_pqt:.6f}, sigma = {sigma:.6f}.")
    print(f"  landmarks: s(q~) = {s_tilde:.4f}, s(q*) = {s_star:.4f} "
          f"(both inside [0.01, 0.99]).")


def _check_labels() -> None:
    """Stage 2: label geometry is now MEASURED live in the browser (the audit at
    ``?simplex-audit``), so Python only checks what it still owns -- the m flip
    rule and the per-frame data handed to the overlay JS. The browser sweep is the
    authoritative collision check; run it at 0.9 x 613 px and 0.9 x 920 px.
    """
    r, gamma, p = 0.97, np.array([2.0, 1.0, 0.4]), np.array([0.5, 0.2, 0.3])
    fig = build_simplex_figure(r, gamma, p)
    n = len(fig.frames)
    mt = dict(fig.layout.meta)
    spec = dict(mt["label_spec"])
    q_pos, m_pos = int(mt["q_frame_pos"]), int(mt["m_frame_pos"])

    # (1) The flip rule: 'topright' below _M_FLIP, 'undertuck' at/above -- once.
    places = [_m_place(i / (n - 1)) for i in range(n)]
    flip = places.index("undertuck")
    assert all(pl == "topright" for pl in places[:flip]), "m flips before _M_FLIP"
    assert all(pl == "undertuck" for pl in places[flip:]), "m flips more than once"
    assert abs(flip / (n - 1) - _M_FLIP) <= 1.0 / (n - 1) + 1e-9, "flip frame off _M_FLIP"

    # (2) The per-frame q/m coordinates sent to JS match the moving markers.
    qc, mc = list(spec["q_coords"]), list(spec["m_coords"])
    assert len(qc) == n and len(mc) == n, "coord arrays wrong length"
    worst = 0.0
    for i, fr in enumerate(fig.frames):
        dq, dm = fr.data[q_pos], fr.data[m_pos]
        worst = max(worst, abs(qc[i][0] - dq.x[0]), abs(qc[i][1] - dq.y[0]),
                    abs(mc[i][0] - dm.x[0]), abs(mc[i][1] - dm.y[0]))
    assert worst < 1e-4, f"q/m coords disagree with the frame markers by {worst:.2e}"

    # (3) Every label class is present and nothing text-bearing remains in Plotly.
    counts = {k: len(list(spec[k])) for k in ("statics", "lines", "vertices", "contours")}
    assert counts == {"statics": 4, "lines": 2, "vertices": 3, "contours": 6}, counts
    assert not fig.layout.annotations, "Plotly annotations must be empty (labels are overlay)"
    assert not any(tr.mode and "text" in tr.mode for tr in fig.data), "a trace still carries text"

    # (4) Every point label (the four statics + the moving pair) carries ink insets
    # (rev 12, item 1), and q~ is placed below-left with no rightward nudge (item 2).
    point_specs = list(spec["statics"]) + [spec["moving"]["q"], spec["moving"]["m"]]
    for s in point_specs:
        assert set(s["ink"]) == {"t", "b", "l", "r"}, f"{s.get('key')} missing ink insets"
    qt = next(s for s in spec["statics"] if s["key"] == "qtilde")
    assert qt["place"] == "bottomleft", "q~ must be placed below-left (away from Q)"
    assert qt.get("dx", 0.0) <= 0.0, "q~ must never be nudged right (toward Q)"
    assert _QTILDE_LEFT_PX <= 8.0, "q~ left shift exceeds the 8 px contract cap"

    print(f"  flip rule: m 'topright' frames 0..{flip - 1}, 'undertuck' {flip}..{n - 1} "
          f"(fraction {flip / (n - 1):.4f} vs _M_FLIP {_M_FLIP}).")
    print(f"  per-frame q/m coords match the frame markers to {worst:.1e}; label classes "
          f"{counts}; no Plotly annotations or marker text remain.")
    print(f"  ink insets on all 6 point labels; q~ placed 'bottomleft', left shift "
          f"{_QTILDE_LEFT_PX} px; q* nudge {_QSTAR_NUDGE_PX} px, gap {spec['gap']} px, "
          f"radius {spec['radius']} px. Authoritative collision check: ?simplex-audit.")


if __name__ == "__main__":
    _run_checks()
    _check_contours()
    _check_layout_aspect()
    _check_qtilde()
    _check_labels()
