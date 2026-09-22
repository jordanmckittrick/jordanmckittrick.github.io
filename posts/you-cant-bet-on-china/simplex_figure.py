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


def _cartesian_to_barycentric(xy: np.ndarray) -> np.ndarray:
    """Invert :func:`barycentric_to_cartesian` for points in the plane.

    ``xy`` is ``(..., 2)``; returns ``(..., 3)`` barycentric coordinates, which
    are a valid probability vector exactly where all three are non-negative.
    """
    x = xy[..., 0]
    y = xy[..., 1]
    q3 = y / (np.sqrt(3.0) / 2.0)
    q2 = x - 0.5 * q3
    q1 = 1.0 - q2 - q3
    return np.stack([q1, q2, q3], axis=-1)


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

# Font sizes, all named here: the figure renders ~750 px wide, so these are
# sized for that, not for the ~300 px draft they were first chosen at. (The
# readout is no longer here -- it is an HTML/MathJax overlay sized in the CSS.)
_LINE_FONT = 17                        # line labels Q, M_wstar
_VERTEX_FONT = 17                      # vertex labels delta_i
_POINT_FONT = 17                       # the six point labels
_CONTOUR_FONT = 13                     # contour value labels

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


# ---- Point-label boxes (for the fixed above/below placement rule and its checks) ----
_LABEL_GAP_PX = 4.0          # anchor->box gap (px), on top of the marker radius
# Label boxes are measured in data units at the NARROWEST common render,
# _WIDTH_FRACTION * _COLUMN_PX (= 0.9 * 613 = 552 px), the same basis
# _readout math uses. That is where fixed-pixel text is largest in data units, so
# every clearance check below is done where space is tightest -- genuinely
# conservative (the earlier 0.8 * _REF_WIDTH basis was ~1.34x too generous).
_BOX_PX_PER_UNIT = (_WIDTH_FRACTION * _COLUMN_PX - 2 * _MARGIN_PX) / _X_SPAN
# q lies ON Q and m lies ON M_wstar, so each line passes through its label's
# anchor. A label whose box comes within this of either line clips it; the fixed
# rule (item 2) is chosen so both labels keep at least this clearance everywhere.
_LINE_CLEARANCE = 2.5 / _BOX_PX_PER_UNIT


def _label_box(anchor_xy: np.ndarray, textpos: str, n_chars: float,
               font_px: float) -> tuple[np.ndarray, np.ndarray]:
    """A text label's box (center, half-extents) in data units, from font metrics.

    Exact text metrics are not needed -- only enough to keep boxes apart. The box
    sits one marker-radius plus a small gap off the anchor, on the named side, and
    is sized in data units at ``_BOX_PX_PER_UNIT`` (the narrowest render).
    """
    mr, gap = _MARKER_SIZE / 2.0, _LABEL_GAP_PX
    tw, th = n_chars * 0.55 * font_px, float(font_px)
    dx, dy = mr + gap + tw / 2.0, mr + gap + th / 2.0
    off = {"bottom center": (0.0, -dy), "top center": (0.0, dy),
           "middle left": (-dx, 0.0), "middle right": (dx, 0.0),
           "top left": (-dx, dy), "top right": (dx, dy),
           "bottom left": (-dx, -dy), "bottom right": (dx, -dy)}[textpos]
    center = np.asarray(anchor_xy, float) + np.array(off) / _BOX_PX_PER_UNIT
    half = np.array([tw / 2.0, th / 2.0]) / _BOX_PX_PER_UNIT
    return center, half


def _pt_box_dist(pt: np.ndarray, center: np.ndarray, half: np.ndarray) -> float:
    """Distance from a point to an axis-aligned box (0 if inside)."""
    d = np.maximum(np.abs(np.asarray(pt, float) - center) - half, 0.0)
    return float(np.hypot(d[0], d[1]))


def _seg_pt_dist(a: np.ndarray, b: np.ndarray, pt: np.ndarray) -> float:
    """Distance from a point to the segment a--b."""
    a, b, pt = np.asarray(a, float), np.asarray(b, float), np.asarray(pt, float)
    ab = b - a
    t = np.clip(np.dot(pt - a, ab) / (np.dot(ab, ab) + 1e-12), 0.0, 1.0)
    return float(np.hypot(*(a + t * ab - pt)))


def _seg_box_dist(a: np.ndarray, b: np.ndarray, center: np.ndarray,
                  half: np.ndarray, n: int = 40) -> float:
    """Minimum distance from segment a--b to an axis-aligned box (0 if it crosses).

    Sampling ~40 points along the segment and taking the least point-to-box
    distance is accurate enough here and simpler than the analytic form. A box
    can clip a line while its CENTRE scores as clear, so the scorer uses this,
    not ``_seg_pt_dist``, for the lines and edges a label must avoid.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    ts = np.linspace(0.0, 1.0, n)[:, None]
    pts = a[None, :] + ts * (b - a)[None, :]                 # (n, 2)
    d = np.maximum(np.abs(pts - center) - half, 0.0)         # per-point box gap
    return float(np.min(np.hypot(d[:, 0], d[:, 1])))


# How far (in barycentric units) a conservative label box may poke past an edge
# and still count as "inside". Used only by the checks now (the fixed rule of
# item 2 does no inside test): _check_labels reports the first frame q's box
# leaves the triangle -- expected, since q's "top right" label sits in the empty
# margin past the delta_2 end -- and uses the base edge directly for m's
# base-crossing report. The box is an over-estimate, so a graze of a few px into
# the white margin still reads as inside; 0.035 absorbs that.
_INSIDE_MARGIN = 0.035


def _box_inside_triangle(center: np.ndarray, half: np.ndarray) -> bool:
    """True iff all four box corners lie inside the 2-simplex (up to a margin)."""
    corners = center + half * np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]])
    return bool(np.all(_cartesian_to_barycentric(corners) >= -_INSIDE_MARGIN))


# ---- The fixed above/below placement rule (item 2) --------------------------
# Static points (p, q*, q~, m~) label BELOW ("bottom center"); the moving pair
# labels ABOVE, so "below vs above" itself reads as "fixed vs moving". A fixed
# rule beats a greedy placer here: a label that jumps around as the reader drags
# is worse than a small inefficiency. q is ALWAYS "top right": Q slopes down at
# ~38 deg, so its upward normal points up-and-right and "top right" sets the
# label straight off the line. m is "top right" too until the slider's index
# fraction reaches _M_FLIP, then "bottom left" -- the mirror image across
# M_wstar -- so the single switch looks like the label crossing the line. It
# happens once, at a fixed frame, so nothing can flicker.
#
# _M_FLIP is VERIFIED, not assumed. The largest index fraction f_max for which
# m's "top right" box clears both lines by _LINE_CLEARANCE, clears q's marker
# disk, and does not overlap q's box on EVERY earlier frame is 0.744 -- it first
# fails at frame 401, where the Q/M_wstar gap by the delta_2 corner squeezes m's
# upward box. Since 0.744 < the author's preferred 0.80, _M_FLIP is f_max rounded
# DOWN to two decimals. (_check_labels recomputes f_max and asserts it.)
_M_FLIP = 0.74


def _m_textpos(index_fraction: float) -> str:
    """m's textposition under the fixed rule: 'top right' before the flip, else 'bottom left'."""
    return "top right" if index_fraction < _M_FLIP else "bottom left"


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
    base_avoid = np.vstack([markers_xy, q_samples, m_samples, tri_v, readout_avoid])

    _TANGENT_CLEAR = 0.05   # min clearance (data units) the tangent label keeps
    annotations = []
    placed = []
    for mult in [m for m in contour_mults if m != 1.0] + [1.0]:   # tangent last
        curve = contour_curves[mult]
        open_curve = curve[:-1]
        if mult == 1.0:
            # (10) The tangent contour kisses Q at q*, so label it NEAR the
            # tangency, not far from it: among curve points at or right of p's x
            # and clear of every marker and both lines, take the one closest to q*.
            avoid_pts = np.vstack([markers_xy, q_samples, m_samples])
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
        annotations.append(dict(
            x=float(px), y=float(py), xref="x", yref="y",
            text=f"{mult * d_star:.2f}", textangle=_tangent_angle(curve, idx),
            showarrow=False, bgcolor=PAPER, borderpad=1,
            font=dict(size=_CONTOUR_FONT,
                      color=_CONTOUR_LABEL_TANGENT if tangent else _CONTOUR_LABEL)))

    # (5) Q and M_wstar labels -- just OUTSIDE the triangle, beside where each
    # line exits the upper-left edge (delta_1--delta_3). After the orientation
    # swap the exit is the A end, so anchor on A / m(A, w*). Offset outward along
    # that edge's normal, right-anchored so the text runs left away from the
    # triangle, horizontal, no arrows. The letters are the Unicode script
    # capitals (U+1D4AC, U+2133) to match the post's \mathcal{Q}, \mathcal{M};
    # they are already slanted, so they are NOT wrapped in <i>. U+1D4AC is above
    # the BMP, so it goes in as a literal character (Plotly may not decode a
    # numeric entity that high).
    _EDGE_NORMAL = np.array([-np.sqrt(3.0) / 2.0, 0.5])   # outward unit normal
    def _outside_label(exit_xy, text):
        pos = np.asarray(exit_xy) + _LINE_LABEL_OFFSET * _EDGE_NORMAL
        return dict(x=float(pos[0]), y=float(pos[1]), xref="x", yref="y", text=text,
                    xanchor="right", yanchor="middle", showarrow=False,
                    font=dict(size=_LINE_FONT, color=_NEUTRAL))

    annotations.append(_outside_label(xy_A, "\U0001D4AC"))
    annotations.append(_outside_label(xy_mA, "ℳ<sub><i>w</i>*</sub>"))

    # ------------------------------------------------------------------ #
    #  The moving q, m label sides per frame, by the FIXED rule (item 2): q is
    #  always "top right"; m is "top right" until the index fraction reaches
    #  _M_FLIP, then "bottom left". No per-frame search, so the label never
    #  wanders while the reader drags.
    # ------------------------------------------------------------------ #
    tp_q_list = ["top right"] * n_frames
    tp_m_list = [_m_textpos(i / (n_frames - 1)) for i in range(n_frames)]

    # ------------------------------------------------------------------ #
    #  Point markers -- all filled circles; colour, not shape, carries meaning.
    #  A white ring lifts a dot off any line it sits on. Hover shows barycentric
    #  coordinates only (the readout carries the divergences).
    # ------------------------------------------------------------------ #
    def _hover(sym: str) -> str:
        return (f"{sym} = (%{{customdata[0]:.3f}}, %{{customdata[1]:.3f}}, "
                f"%{{customdata[2]:.3f}})<extra></extra>")

    def _add_point(xy, bary, color, label, textpos, sym):
        fig.add_trace(go.Scatter(
            x=[xy[0]], y=[xy[1]], mode="markers+text",
            marker=dict(color=color, size=_MARKER_SIZE, symbol="circle",
                        line=dict(color=PAPER, width=MARKER_OUTLINE_PX)),
            text=[label], textposition=textpos, textfont=dict(size=_POINT_FONT, color=INK),
            customdata=[list(map(float, bary))], hovertemplate=_hover(sym),
            showlegend=False))
        return len(fig.data) - 1

    # The four static markers label below ("bottom center"); the two moving
    # markers label above by the fixed rule (tp_q_list / tp_m_list). q* takes a
    # superscript star to match the post's q^*.
    idx_p = _add_point(xy_p, p, _P_COLOR, "<i>p</i>", "bottom center", "p")
    idx_qstar = _add_point(xy_qstar, q_star, _QSTAR_COLOR, "<i>q</i><sup>*</sup>", "bottom center", "q*")
    idx_qtilde = _add_point(xy_qtilde, q_tilde, _UNATTAIN, "<i>q&#771;</i>", "bottom center", "q&#771;")
    idx_mtilde = _add_point(xy_mtilde, m_tilde, _UNATTAIN, "<i>m&#771;</i>", "bottom center", "m&#771;")

    fig.add_trace(go.Scatter(
        x=[st0["xq"][0]], y=[st0["xq"][1]], mode="markers+text",
        marker=dict(color=_NEUTRAL, size=_MARKER_SIZE, symbol="circle",
                    line=dict(color=PAPER, width=MARKER_OUTLINE_PX)),
        text=["<i>q</i>"], textposition=tp_q_list[start_index],
        textfont=dict(size=_POINT_FONT, color=INK),
        customdata=[list(map(float, st0["q"]))], hovertemplate=_hover("q"),
        showlegend=False))
    idx_q = len(fig.data) - 1
    fig.add_trace(go.Scatter(
        x=[st0["xm"][0]], y=[st0["xm"][1]], mode="markers+text",
        marker=dict(color=_NEUTRAL, size=_MARKER_SIZE, symbol="circle",
                    line=dict(color=PAPER, width=MARKER_OUTLINE_PX)),
        text=["<i>m</i>"], textposition=tp_m_list[start_index],
        textfont=dict(size=_POINT_FONT, color=INK),
        customdata=[list(map(float, st0["m"]))], hovertemplate=_hover("m"),
        showlegend=False))
    idx_m = len(fig.data) - 1

    # Vertex labels, just outside the triangle (one trace, per-point anchor).
    vx = barycentric_to_cartesian(np.eye(3))
    fig.add_trace(go.Scatter(
        x=[vx[0, 0], vx[1, 0], vx[2, 0]],
        y=[vx[0, 1] - 0.02, vx[1, 1] - 0.02, vx[2, 1] + 0.018],
        mode="text",
        text=[
            f"<i>&#948;</i><sub>1</sub> (<i>&#947;</i><sub>1</sub> = {_fmt_gamma(gamma[0])})",
            f"<i>&#948;</i><sub>2</sub> (<i>&#947;</i><sub>2</sub> = {_fmt_gamma(gamma[1])})",
            f"<i>&#948;</i><sub>3</sub> (<i>&#947;</i><sub>3</sub> = {_fmt_gamma(gamma[2])})",
        ],
        textposition=["bottom left", "bottom right", "top center"],
        textfont=dict(size=_VERTEX_FONT, color=LABEL),
        cliponaxis=False, hoverinfo="skip", showlegend=False))

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
    frames, readout_values = [], []
    for i, (name, s) in enumerate(zip(frame_names, s_grid)):
        state = _frame_state(s)
        s1, s2, lpm = mw_pieces(s)
        readout_values.append([f"{state['d_pq']:.4f}", f"{max(state['d_pm'], 0.0):.4f}"])
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
                           textposition=tp_q_list[i],
                           customdata=[list(map(float, state["q"]))]),
                go.Scatter(x=[state["xm"][0]], y=[state["xm"][1]],                   # m moving  (data 9)
                           textposition=tp_m_list[i],
                           customdata=[list(map(float, state["m"]))]),
            ],
            traces=[idx_seg1, idx_seg2, idx_leg_pm, idx_leg_pq,
                    idx_qtilde, idx_mtilde, idx_p, idx_qstar, idx_q, idx_m]))
    fig.frames = frames
    q_frame_pos, m_frame_pos = 8, 9     # q and m positions in each frame's data list

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
        dragmode=False, showlegend=False, annotations=annotations,
        # The slider places each tick/label at its landmark's INDEX FRACTION F =
        # idx/(n_frames-1); the CSS turns F into a pixel position that accounts
        # for thumb travel. Carry F (not a percentage) and the indices (for the
        # snap-on-release script). readout_values / d_star_str feed the HTML
        # readout overlay; q_frame_pos / m_frame_pos let the checks find the
        # moving markers without hardcoding a shifting index.
        meta=dict(n_frames=n_frames, start_index=start_index,
                  idx_qtilde=idx_tilde, idx_qstar=idx_star,
                  q_frame_pos=q_frame_pos, m_frame_pos=m_frame_pos,
                  readout_values=readout_values, d_star_str=f"{d_star:.4f}",
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
    # A 5-column array puts the numbers directly under their symbols with the
    # operators lined up. MathJax ignores array `@{...}` column separators, so the
    # operators are real columns; \mkern-5mu trims the wide default \arraycolsep
    # back to roughly the spacing of an inline a = b + c.
    js_arr_open = json.dumps(r"\begin{array}{ccccc}")
    js_sym_row = json.dumps(r"D(p \| q) & \mkern-5mu=\mkern-5mu & D(p \| q^{*})"
                            r" & \mkern-5mu+\mkern-5mu & D(p \| m) \\ ")
    js_eq = json.dumps(r" & \mkern-5mu=\mkern-5mu & ")
    js_plus = json.dumps(r" & \mkern-5mu+\mkern-5mu & ")
    js_arr_close = json.dumps(r"\end{array}")
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
.simplex-fig-wrap {{ position: relative; margin: 0 auto; }}
.simplex-readout-layer {{ position: absolute; inset: 0; pointer-events: none; overflow: visible; }}
.simplex-readout-slot:empty {{ display: none; }}
/* The readout box: a real CSS border in the triangle-outline colour/width, PAPER
   fill, INK text set explicitly (the site has a dark mode; the figure stays a
   white card, but text would otherwise inherit a light page colour). Font size
   1rem matches the body math. Position (overlay) or centring (block) is set by
   fit()/roPlace(); block mode drops it into normal flow above the figure. */
.simplex-readout {{ box-sizing: border-box; white-space: nowrap;
  border: 1.2px solid {_SCAFFOLD}; background: {PAPER}; color: {INK};
  padding: {_READOUT_PAD_PX:.0f}px; font-size: 1rem; line-height: 1; }}
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
.simplex-landmark {{ position: absolute; top: 20px; transform: translate(-50%, 0);
  font-size: 15px; font-style: italic; color: var(--bs-body-color, #1f2328);
  pointer-events: none; white-space: nowrap; }}
.simplex-q-label {{ position: absolute; right: 100%; top: 50%; transform: translateY(-50%);
  margin-right: 12px; font-size: 17px;
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
  var DSTAR = {js_dstar}, A_OPEN = {js_arr_open}, SYM = {js_sym_row};
  var EQ = {js_eq}, PLUS = {js_plus}, A_CLOSE = {js_arr_close};
  var mjReady = false, roCache = {{}}, roFrame = {start}, coldMs = null, warmed = false;
  function roTex(i) {{
    var v = VALUES[i] || ["", ""];
    return A_OPEN + SYM + v[0] + EQ + DSTAR + PLUS + v[1] + A_CLOSE;
  }}
  function roNode(i) {{                         // cached per frame; cold cost timed once
    if (roCache[i]) return roCache[i];
    var t0 = performance.now();
    var node = MathJax.tex2chtml(roTex(i), {{display: false}});
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
    // Match the body math's size: MathJax gives in-place body math an inline
    // font-size (matchFontHeight, e.g. "90.5%") that a detached tex2chtml node
    // does not get. Copy it onto the readout container so its math is the same
    // size as the prose's -- and small enough to keep overlay mode at desktop.
    var bodyC = document.querySelector("p mjx-container, .cell mjx-container, li mjx-container");
    if (bodyC && bodyC.style.fontSize) readout.style.fontSize = bodyC.style.fontSize;
    roRenderMath(roFrame);
    if (coldMs !== null && coldMs > 8 && window.requestIdleCallback && !warmed) {{
      warmed = true;                                   // pre-warm the cache in idle time
      var i = 0;
      requestIdleCallback(function step(dl) {{
        while (i < VALUES.length && dl.timeRemaining() > 3) roNode(i++);
        if (i < VALUES.length) requestIdleCallback(step);
      }});
    }}
  }});
  // Coalesce readout updates to one per animation frame (fast drags skip frames).
  var roPending = null, roRaf = 0;
  function roSchedule(i) {{
    roPending = i;
    if (!roRaf) roRaf = requestAnimationFrame(function () {{
      roRaf = 0; var j = roPending; roPending = null; roShow(j);
    }});
  }}

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
    }});
    sliderWrap.style.width = Math.round((w - 2 * MARG) / {_X_SPAN:.4f}) + "px";
  }}
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

    # (5) Outside line labels: assert each anchor, minus an estimate of its
    # rendered text width, stays inside _X_RANGE (they are right-anchored, so the
    # text runs left). If M_wstar overflows, reduce _LINE_LABEL_OFFSET.
    edge_n = np.array([-np.sqrt(3.0) / 2.0, 0.5])
    px_per_x = plot_w / _X_SPAN
    for exit_bary, nchars, name in ((B, 1, "Q"),
                                    (tilted_measure(B, f_star, r, gamma), 4, "M_wstar")):
        anchor_x = (barycentric_to_cartesian(exit_bary) + _LINE_LABEL_OFFSET * edge_n)[0]
        left_x = anchor_x - nchars * 0.60 * _LINE_FONT / px_per_x   # ~0.6 em/glyph
        assert left_x >= _X_RANGE[0], (
            f"'{name}' label overflows x-range: left edge {left_x:.3f} < {_X_RANGE[0]}"
        )
        print(f"  line label '{name}': anchor x = {anchor_x:.3f}, est. left edge "
              f"{left_x:.3f} (inside [{_X_RANGE[0]}, {_X_RANGE[1]}]).")

    # (7) delta_1 / delta_2 labels anchor at y = -0.02 with text below; check the
    # text clears the new y-range bottom.
    text_h_data = _VERTEX_FONT / (plot_h / _Y_SPAN)
    vlabel_bottom = -0.02 - text_h_data
    assert vlabel_bottom > _Y_RANGE[0], "vertex labels overflow the y-range bottom"
    print(f"  vertex labels: anchor y = -0.020, text bottom ~ {vlabel_bottom:.3f}, "
          f"y-range bottom {_Y_RANGE[0]} (clearance {vlabel_bottom - _Y_RANGE[0]:.3f}).")

    # (5) apex label delta_3 (top center at +0.018): its top edge must fit _Y_RANGE.
    apex_anchor_y = barycentric_to_cartesian(np.array([0.0, 0.0, 1.0]))[1] + 0.018
    apex_top = apex_anchor_y + text_h_data
    assert apex_top < _Y_RANGE[1], "apex label overflows the y-range top"
    print(f"  apex label: anchor y = {apex_anchor_y:.3f}, top edge ~ {apex_top:.3f}, "
          f"y-range top {_Y_RANGE[1]} (clearance {_Y_RANGE[1] - apex_top:.3f}).")

    # (4) Readout: now an HTML/MathJax overlay, so its box is measured live in the
    # browser (box size, apex alignment and edge clearance are reported there, not
    # asserted here). The one invariant that stays a Python assertion is that the
    # number row "x.xxxx = x.xxxx + x.xxxx" keeps a constant width, which holds
    # while D(p||q) < 10 (a single integer digit).
    d_max = max(d_ends)
    assert d_max < 10.0, f"D(p||q) reaches {d_max:.3f} >= 10; the readout number row would widen"
    print(f"  readout: HTML/MathJax overlay; box geometry checked in the browser. "
          f"D_max = {d_max:.3f} < 10 (number row stays constant-width).")
    fig = build_simplex_figure(r, gamma, p)
    mt = dict(fig.layout.meta)

    # (9) Landmark snapping: three distinct grid indices; (10) tangent label.
    idxs = (int(mt["idx_qtilde"]), int(mt["idx_qstar"]), int(mt["start_index"]))
    assert len(set(idxs)) == 3, f"landmark indices collide: {idxs}"
    print(f"  landmark indices: q~ = {idxs[0]}, q* = {idxs[1]}, open = {idxs[2]} "
          f"(of {mt['n_frames']}); index frac q~ = {float(mt['frac_qtilde']):.3f}, "
          f"q* = {float(mt['frac_qstar']):.3f}.")
    tang = [a for a in fig.layout.annotations if a.text == f"{d_star:.2f}"]
    tx, ty = float(tang[0].x), float(tang[0].y)
    print(f"  tangent label '{d_star:.2f}' at ({tx:.3f}, {ty:.3f}), "
          f"{np.hypot(tx - xy_qstar[0], ty - xy_qstar[1]):.3f} data units from q*; "
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
    """The fixed above/below rule (item 2): hard collision checks + diagnostics.

    HARD (asserted, every frame): q and m each clear both lines by _LINE_CLEARANCE
    and clear each other's marker disk and each other's box; q clears all four
    static labels and m clears p, q* and m~; q stays in the plot area and clears
    the delta_2 vertex label. REPORTED (by design, not asserted): q leaves the
    triangle near delta_2; q and m graze the left edge at the far left; m's
    'bottom left' box crosses the base near the far right; and -- the one
    rule-induced collision -- m's 'top right' label overlaps the q~ static label
    around the q~/m~ landmark. Also re-derives f_max and asserts _M_FLIP <= f_max.
    """
    r, gamma, p = 0.97, np.array([2.0, 1.0, 0.4]), np.array([0.5, 0.2, 0.3])
    gamma2 = np.array([0.5, 0.7, 1.7])
    fig = build_simplex_figure(r, gamma, p)
    n = len(fig.frames)
    mt = dict(fig.layout.meta)
    q_pos, m_pos = int(mt["q_frame_pos"]), int(mt["m_frame_pos"])   # not hardcoded (indices shift)
    f_star = optimal_fraction(r, gamma, p)
    q_star = manufactured_measure(f_star, r, gamma, p)
    q_tilde = np.linalg.solve(np.column_stack([r * np.ones(3), gamma, gamma2]).T, r * np.ones(3))
    m_tilde = tilted_measure(q_tilde, f_star, r, gamma)
    xy = barycentric_to_cartesian
    snames = ["p", "q*", "q~", "m~"]
    static_boxes = [_label_box(xy(p), "bottom center", 1, _POINT_FONT),
                    _label_box(xy(q_star), "bottom center", 2, _POINT_FONT),
                    _label_box(xy(q_tilde), "bottom center", 1.3, _POINT_FONT),
                    _label_box(xy(m_tilde), "bottom center", 1.3, _POINT_FONT)]
    mr_data = (_MARKER_SIZE / 2.0) / _BOX_PX_PER_UNIT

    A, B = risk_neutral_segment_endpoints(r, gamma)
    if xy(A)[0] > xy(B)[0]:
        A, B = B, A
    lines = {"Q": (xy(A), xy(B)),
             "M_wstar": (xy(tilted_measure(A, f_star, r, gamma)),
                         xy(tilted_measure(B, f_star, r, gamma)))}
    # delta_2 vertex label box (bottom right, ~"delta_2 (gamma_2 = 1.0)", 13 glyphs).
    d2_box = _label_box(np.array([1.0, -0.02]), "bottom right", 13, _VERTEX_FONT)
    base_edge = (np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    left_edge = (np.array([0.0, 0.0]), np.array([0.5, np.sqrt(3.0) / 2.0]))

    def _overlap(b1, b2):
        (c1, h1), (c2, h2) = b1, b2
        return bool(np.all(np.abs(c1 - c2) < (h1 + h2)))

    def _gap(b1, b2):
        (c1, h1), (c2, h2) = b1, b2
        d = np.maximum(np.abs(c1 - c2) - (h1 + h2), 0.0)
        return float(np.hypot(d[0], d[1]))

    def _in_plot(box):
        c, h = box
        return bool(c[0] - h[0] >= _X_RANGE[0] and c[0] + h[0] <= _X_RANGE[1]
                    and c[1] - h[1] >= _Y_RANGE[0] and c[1] + h[1] <= _Y_RANGE[1])

    w = {"qstat": (1e9, -1, ""), "mstat": (1e9, -1, ""), "marker": (1e9, -1),
         "mutual": (1e9, -1), "qline": (1e9, -1), "mline": (1e9, -1)}
    tp_count = {"q": {}, "m": {}}
    q_leaves = m_base = fmax_fail = None
    q_left = m_left = (1e9, -1)
    mqt_overlap, mqt_gap = [], 1e9

    for i, fr in enumerate(fig.frames):
        dq, dm = fr.data[q_pos], fr.data[m_pos]     # q, m moving (positions from meta)
        mkq, mkm = np.array([dq.x[0], dq.y[0]]), np.array([dm.x[0], dm.y[0]])
        bq = _label_box(mkq, dq.textposition, 1, _POINT_FONT)
        bm = _label_box(mkm, dm.textposition, 1, _POINT_FONT)
        tp_count["q"][dq.textposition] = tp_count["q"].get(dq.textposition, 0) + 1
        tp_count["m"][dm.textposition] = tp_count["m"].get(dm.textposition, 0) + 1

        for cl in (_pt_box_dist(mkm, *bq) - mr_data, _pt_box_dist(mkq, *bm) - mr_data):
            if cl < w["marker"][0]:
                w["marker"] = (cl, i)
            assert cl >= -1e-9, f"frame {i}: a moving box overlaps the other's marker disk"
        g_mut = _gap(bq, bm)
        if g_mut < w["mutual"][0]:
            w["mutual"] = (g_mut, i)
        assert not _overlap(bq, bm), f"frame {i}: q and m boxes overlap"

        for key, box in (("qline", bq), ("mline", bm)):
            lc = min(_seg_box_dist(*seg, *box) for seg in lines.values())
            if lc < w[key][0]:
                w[key] = (lc, i)
            assert lc >= _LINE_CLEARANCE - 1e-9, (
                f"frame {i}: {key[0]} box clips a line ({lc:.4f} < {_LINE_CLEARANCE:.4f})")

        for j, sb in enumerate(static_boxes):
            gq = _gap(bq, sb)
            if gq < w["qstat"][0]:
                w["qstat"] = (gq, i, snames[j])
            assert not _overlap(bq, sb), f"frame {i}: q overlaps static {snames[j]}"
            if snames[j] == "q~":                   # m vs q~: reported, not asserted
                if _overlap(bm, sb):
                    mqt_overlap.append(i)
                mqt_gap = min(mqt_gap, _gap(bm, sb))
            else:
                gm = _gap(bm, sb)
                if gm < w["mstat"][0]:
                    w["mstat"] = (gm, i, snames[j])
                assert not _overlap(bm, sb), f"frame {i}: m overlaps static {snames[j]}"

        assert _in_plot(bq), f"frame {i}: q box leaves the plot area"
        assert not _overlap(bq, d2_box), f"frame {i}: q box overlaps the delta_2 label"

        if q_leaves is None and not _box_inside_triangle(*bq):
            q_leaves = i
        cq, cm = _seg_box_dist(*left_edge, *bq), _seg_box_dist(*left_edge, *bm)
        if cq < q_left[0]:
            q_left = (cq, i)
        if cm < m_left[0]:
            m_left = (cm, i)
        if (m_base is None and dm.textposition == "bottom left"
                and _seg_box_dist(*base_edge, *bm) <= 1e-9):
            m_base = i
        bm_tr = _label_box(mkm, "top right", 1, _POINT_FONT)   # f_max re-derivation
        if fmax_fail is None and (
                min(_seg_box_dist(*seg, *bm_tr) for seg in lines.values()) < _LINE_CLEARANCE
                or _pt_box_dist(mkq, *bm_tr) - mr_data < 0.0 or _overlap(bm_tr, bq)):
            fmax_fail = i

    f_max = 1.0 if fmax_fail is None else fmax_fail / (n - 1)
    assert _M_FLIP <= f_max + 1e-9, f"_M_FLIP {_M_FLIP} exceeds verified f_max {f_max:.4f}"

    print(f"  fixed rule: f_max(m 'top right') = {f_max:.4f} (first fail frame {fmax_fail}); "
          f"_M_FLIP = {_M_FLIP}, flip at frame {int(np.ceil(_M_FLIP * (n - 1)))}.")
    print(f"  HARD minima: q/static {w['qstat'][0]:.4f}@{w['qstat'][1]}({w['qstat'][2]}), "
          f"m/static(p,q*,m~) {w['mstat'][0]:.4f}@{w['mstat'][1]}({w['mstat'][2]}); "
          f"marker {w['marker'][0]:.4f}@{w['marker'][1]}; mutual {w['mutual'][0]:.4f}@{w['mutual'][1]}; "
          f"line q {w['qline'][0]:.4f}@{w['qline'][1]}, m {w['mline'][0]:.4f}@{w['mline'][1]} "
          f"(>= {_LINE_CLEARANCE:.4f}).")
    print(f"  q textpos: {dict(tp_count['q'])};  m textpos: {dict(tp_count['m'])}.")
    print(f"  DIAG: q first leaves triangle @ frame {q_leaves} (intended -- q's 'top right' "
          f"sits in the margin past delta_2). left-edge clearance: q "
          f"{q_left[0] * _BOX_PX_PER_UNIT:.1f}px@{q_left[1]}, m {m_left[0] * _BOX_PX_PER_UNIT:.1f}px@{m_left[1]}.")
    print(f"  DIAG: m 'bottom left' box first crosses the base @ frame {m_base}.")
    band = (f"{mqt_overlap[0]}..{mqt_overlap[-1]} ({len(mqt_overlap)} frames)"
            if mqt_overlap else "none")
    print(f"  REPORT (rule-induced, NOT asserted): m 'top right' overlaps the q~ static label "
          f"on frames {band}, min gap {mqt_gap:.4f} du. q~ sits up-right of m~, so m's upward "
          f"label points at it near the q~/m~ landmark; the author decides whether to accept it.")


if __name__ == "__main__":
    _run_checks()
    _check_contours()
    _check_layout_aspect()
    _check_qtilde()
    _check_labels()
