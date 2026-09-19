"""The simplex figure for the log-optimal-investing post.

One interactive figure that makes the growth-rate decomposition (1.6) visible:
for three states and two tradable assets (one risk-free at gross return ``r``,
one risky at gross returns ``gamma``), it draws the risk-neutral segment ``Q``
and its image ``M_wstar`` inside the 2-simplex, over a family of KL contours,
and lets a slider walk a point ``q`` along ``Q`` while a slim horizontal bar
splits its divergence from the belief ``p`` into the part every portfolio pays
(the "edge", ``D(p||q*)``) and the part geometry wastes (the "unspanned"
remainder, ``D(p||m(q,w*))``).

The geometry, stated once and used everywhere below:

* ``Y(f)   = (1 - f) r + f gamma``            portfolio gross return (length 3)
* ``W(f)   = sum_i p_i log Y_i(f)``           growth rate, nats
* ``f*     = argmax_f W(f)``                  no closed form for three states
* ``q*     = r p / Y(f*)``                    the reverse info projection of p onto Q
* ``Q      = { q in the simplex : q . gamma = r }``     a line segment A--B
* ``m(q,f) = q Y(f) / r``                     the tilted measure
* ``M_wstar = { m(q, f*) : q in Q }``         a line segment

Everything the figure needs is derived from ``(r, gamma, p)``; nothing about
the running example is baked in. Colour comes from the brand module
(``blogkit.brand_plotly``) and is assigned three semantic roles: burnt orange
for the fixed anchors ``p`` and ``q*``, lime for the moving pair ``q`` and
``m`` (and the pointers to them), periwinkle for the KL contour family and the
edge, and a neutral dark grey for ``Q``, ``M_wstar`` and the triangle outline.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy.optimize as opt

# Importing the brand module registers "plotly_white+blog" as the default
# template (font, ink, paper, gridless neutrals) and gives us the semantic
# palette. HERO is the house periwinkle, SECONDARY the lime, ACCENT the orange.
from blogkit.brand_plotly import HERO, SECONDARY, ACCENT, INK, LABEL, PAPER, with_alpha

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
    """The slider's ``s`` interval, and the ``s*`` that lands on ``q*``.

    ``q(s) = A + s (B - A)`` walks ``Q`` from ``A`` (``s = 0``) to ``B``
    (``s = 1``). ``D(p||q(s))`` is convex with its minimum ``D(p||q*)`` at
    ``s*``; it diverges at both ends of ``Q``, so the slider is clipped to the
    sub-interval where ``D(p||q(s)) <= kl_window * D(p||q*)`` -- a rule that
    adapts to ``r``, ``gamma`` and ``p`` rather than hard-coding a range.
    Returns ``(s_lo, s_hi, s_star)`` with ``s_lo < s_star < s_hi``.
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


# Three semantic roles (hue = meaning):
_ANCHOR = ACCENT                       # burnt orange: the fixed spine p, q*
_MOVING = SECONDARY                    # lime: the moving pair q, m and its pointers
_CONTOUR = HERO                        # periwinkle: the KL contour family and the edge
_LINE_GREY = _mix(INK, LABEL, 0.55)    # neutral dark grey: Q, M_wstar
_OUTLINE = with_alpha(LABEL, 0.5)      # a lighter grey for the triangle frame

_CONTOUR_FAINT = with_alpha(_CONTOUR, 0.34)
_CONTOUR_TANGENT = with_alpha(_CONTOUR, 0.75)
_CONTOUR_LABEL = with_alpha(_mix(_CONTOUR, INK, 0.25), 0.8)
_CONTOUR_LABEL_TANGENT = _mix(_CONTOUR, INK, 0.35)

_EDGE_COLOR = HERO                     # the edge you keep: periwinkle
_UNSPANNED_COLOR = with_alpha(LABEL, 0.55)   # the part geometry wastes: grey

_POINT_FONT = 13                       # one convention for point labels p, q*, q, m
_LINE_FONT = 12.5                      # a second for the line labels Q, M_wstar


def _fmt_gamma(x: float) -> str:
    """Format a gamma value with at least one decimal (2 -> ``2.0``, 0.45 kept)."""
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"


def _point_hovertemplate(symbol: str, div_label: str | None) -> str:
    """Hover for a labelled point: its own symbol, coordinates, an optional div."""
    lines = [
        f"<b>{symbol}</b>",
        f"{symbol} = (%{{customdata[0]:.3f}}, %{{customdata[1]:.3f}}, %{{customdata[2]:.3f}})",
    ]
    if div_label is not None:
        lines.append(f"{div_label} = %{{customdata[3]:.4f}} nats")
    return "<br>".join(lines) + "<extra></extra>"


def _furthest_index(cand_xy: np.ndarray, avoid_xy: np.ndarray) -> int:
    """Index of the candidate point furthest (max-min distance) from an avoid set."""
    d2 = ((cand_xy[:, None, :] - avoid_xy[None, :, :]) ** 2).sum(axis=-1)
    return int(np.argmax(d2.min(axis=1)))


# --------------------------------------------------------------------------- #
#  The figure
# --------------------------------------------------------------------------- #
def build_simplex_figure(
    r: float,
    gamma: np.ndarray,
    p: np.ndarray,
    n_frames: int = 60,
    kl_window: float = 4.0,
) -> go.Figure:
    """Assemble the simplex figure for the belief ``p``.

    A large triangle over a slim horizontal decomposition bar. The triangle
    carries the KL contour family of ``q -> D(p||q)`` (periwinkle, with the
    level equal to the edge drawn stronger because it is tangent to ``Q`` at
    ``q*``), the segments ``Q`` (solid grey) and ``M_wstar`` (dashed grey), the
    fixed anchors ``p`` and ``q*`` (orange), and a slider-driven moving pair
    ``q`` on ``Q`` and ``m(q, w*)`` on ``M_wstar`` (lime) joined to ``p`` by
    thin pointers. The bar splits ``D(p||q)`` into the fixed "edge"
    ``D(p||q*)`` and the growing "unspanned" remainder ``D(p||m(q, w*))``.

    Parameters
    ----------
    r
        Risk-free gross return, the same in every state.
    gamma
        Length-3 risky gross returns, one per state.
    p
        Length-3 belief (true state probabilities), all strictly positive.
    n_frames
        Number of animation frames across the slider interval.
    kl_window
        The slider spans ``{ s : D(p||q(s)) <= kl_window * D(p||q*) }``; the
        contour levels and the bar axis share the same window.

    Returns
    -------
    go.Figure
        A single responsive figure, roughly 560 px tall, no title (the caption
        lives in the ``.qmd``).
    """
    gamma = np.asarray(gamma, dtype=float)
    p = np.asarray(p, dtype=float)

    # ---- Core quantities, all derived ----
    f_star = optimal_fraction(r, gamma, p)
    q_star = manufactured_measure(f_star, r, gamma, p)
    d_star = kl_divergence(p, q_star)               # the edge; fixed per figure
    w_star_nats = growth_rate(f_star, r, gamma, p)
    w_star_bits = w_star_nats / _LN2

    A, B = risk_neutral_segment_endpoints(r, gamma)
    s_lo, s_hi, s_star = optimal_slider_interval(r, gamma, p, kl_window)
    s_grid = np.linspace(s_lo, s_hi, n_frames)
    start_index = int(np.argmin(np.abs(s_grid - s_star)))

    def q_of_s(s: float) -> np.ndarray:
        return A + s * (B - A)

    def q3_of_s(s: float) -> float:
        return float(A[2] + s * (B[2] - A[2]))

    # Bar x-axis: fixed [0, max total] so the blocks resize, not the axis.
    totals = np.array([
        d_star + kl_divergence(p, tilted_measure(q_of_s(s), f_star, r, gamma))
        for s in s_grid
    ])
    bar_xmax = float(totals.max())

    xy_p = barycentric_to_cartesian(p)
    xy_qstar = barycentric_to_cartesian(q_star)

    # Readout block geometry (top-left, on empty canvas): fixed here so the
    # contour labels can also steer clear of it.
    _READ_X = -0.11
    _READ_Y = np.array([1.03, 0.965, 0.90, 0.835, 0.77])

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.88, 0.12], vertical_spacing=0.04,
        specs=[[{"type": "xy"}], [{"type": "bar"}]],
    )

    # ------------------------------------------------------------------ #
    #  (1) KL contours -- exact polylines, one go.Scatter line per level.
    #  Levels are multiples of the edge D(p||q*), so they track (r, gamma, p).
    # ------------------------------------------------------------------ #
    contour_mults = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
    contour_curves = {}   # mult -> Cartesian curve, kept for label placement
    for mult in contour_mults:
        level = mult * d_star
        curve = barycentric_to_cartesian(_kl_level_curve(p, level))
        contour_curves[mult] = curve
        tangent = mult == 1.0
        fig.add_trace(
            go.Scatter(
                x=curve[:, 0], y=curve[:, 1], mode="lines",
                line=dict(
                    color=_CONTOUR_TANGENT if tangent else _CONTOUR_FAINT,
                    width=1.4 if tangent else 1.0,
                ),
                hovertemplate=f"D(p&#8741;&#183;) = {level:.4f} nats<extra></extra>",
                showlegend=False, name="",
            ),
            row=1, col=1,
        )

    # ------------------------------------------------------------------ #
    #  Triangle outline -- quiet frame, no hover
    # ------------------------------------------------------------------ #
    tri = barycentric_to_cartesian(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0]]))
    fig.add_trace(
        go.Scatter(
            x=tri[:, 0], y=tri[:, 1], mode="lines",
            line=dict(color=_OUTLINE, width=1.2),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  (3) Q (solid) and M_wstar (dashed) -- thin neutral grey, exact ends.
    #  No colour ramp: the contour family already reads off D(p||q) along Q and
    #  D(p||m) along M_wstar, so a second encoding would be redundant.
    # ------------------------------------------------------------------ #
    xy_A, xy_B = barycentric_to_cartesian(A), barycentric_to_cartesian(B)
    xy_mA = barycentric_to_cartesian(tilted_measure(A, f_star, r, gamma))
    xy_mB = barycentric_to_cartesian(tilted_measure(B, f_star, r, gamma))
    fig.add_trace(
        go.Scatter(
            x=[xy_A[0], xy_B[0]], y=[xy_A[1], xy_B[1]], mode="lines",
            line=dict(color=_LINE_GREY, width=1.6),
            hoverinfo="skip", showlegend=False, name="Q",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[xy_mA[0], xy_mB[0]], y=[xy_mA[1], xy_mB[1]], mode="lines",
            line=dict(color=_LINE_GREY, width=1.6, dash="dash"),
            hoverinfo="skip", showlegend=False, name="M_wstar",
        ),
        row=1, col=1,
    )

    # Line labels, at whichever end has the most clear space, nudged
    # perpendicular to the line so they sit just off it.
    def _line_label(P0, P1, text, avoid):
        P0, P1 = np.asarray(P0), np.asarray(P1)
        d = P1 - P0
        n = np.array([-d[1], d[0]])
        n = n / (np.hypot(*n) + 1e-12)
        # Pick the endpoint furthest from the avoid set, then push outward.
        ends = np.array([P0 + 0.06 * (P0 - P1), P1 + 0.06 * (P1 - P0)])
        j = _furthest_index(ends, avoid)
        base = ends[j]
        # Offset perpendicular, on the side away from the avoid centroid.
        centroid = avoid.mean(axis=0)
        side = np.sign(np.dot(base + 0.001 * n - centroid, n)) or 1.0
        pos = base + side * 0.045 * n
        return go.Scatter(
            x=[pos[0]], y=[pos[1]], mode="text", text=[text],
            textposition="middle center", textfont=dict(size=_LINE_FONT, color=_LINE_GREY),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        )

    _line_avoid = np.vstack([xy_p, xy_qstar, xy_A, xy_B, xy_mA, xy_mB])
    fig.add_trace(_line_label(xy_A, xy_B, "<i>Q</i>", _line_avoid), row=1, col=1)
    fig.add_trace(_line_label(xy_mA, xy_mB, "<i>M</i><sub>w*</sub>", _line_avoid), row=1, col=1)

    # ------------------------------------------------------------------ #
    #  Contour value labels -- placed where each curve is least crowded, i.e.
    #  the curve point furthest from every other drawn element (and from labels
    #  already placed, so they spread out). The tangent level is labelled more
    #  prominently -- it is the one contour the eye should find.
    # ------------------------------------------------------------------ #
    q_samples = barycentric_to_cartesian(np.array([q_of_s(s) for s in np.linspace(0, 1, 24)]))
    m_samples = barycentric_to_cartesian(
        np.array([tilted_measure(q_of_s(s), f_star, r, gamma) for s in np.linspace(0, 1, 24)])
    )
    tri_v = barycentric_to_cartesian(np.eye(3))
    readout_anchor = np.array([[_READ_X, _READ_Y[0]], [_READ_X, _READ_Y[-1]]])
    base_avoid = np.vstack([xy_p[None, :], xy_qstar[None, :], q_samples, m_samples,
                            tri_v, readout_anchor])

    # Pass 1: the five faint labels, greedy furthest-from-everything so they
    # spread out. Pass 2: the tangent label, into the emptiest spot that remains.
    placed = []
    faint_x, faint_y, faint_t = [], [], []
    for mult in contour_mults:
        if mult == 1.0:
            continue
        curve = contour_curves[mult][:-1]     # drop the duplicated closing point
        avoid = np.vstack([base_avoid] + ([np.array(placed)] if placed else []))
        px, py = curve[_furthest_index(curve, avoid)]
        placed.append([px, py])
        faint_x.append(px)
        faint_y.append(py)
        faint_t.append(f"{mult * d_star:.4f}")
    fig.add_trace(
        go.Scatter(
            x=faint_x, y=faint_y, mode="text", text=faint_t,
            textposition="middle center", textfont=dict(size=9, color=_CONTOUR_LABEL),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    tangent_curve = contour_curves[1.0][:-1]
    tpx, tpy = tangent_curve[_furthest_index(tangent_curve, np.vstack([base_avoid, np.array(placed)]))]
    fig.add_trace(
        go.Scatter(
            x=[tpx], y=[tpy], mode="text",
            text=[f"D(p&#8741;q*) = {d_star:.4f}"],
            textposition="middle center",
            textfont=dict(size=11, color=_CONTOUR_LABEL_TANGENT),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  (3c) Pointers: static p -> q* (heavier dash, orange), and the moving
    #  p -> q and p -> m (lime). Pointers, not magnitudes: thin and subordinate.
    # ------------------------------------------------------------------ #
    def _frame_state(s: float) -> dict:
        q = q_of_s(s)
        m = tilted_measure(q, f_star, r, gamma)
        return dict(
            q=q, m=m, q3=q3_of_s(s),
            d_pq=kl_divergence(p, q), d_pm=kl_divergence(p, m),
            xq=barycentric_to_cartesian(q), xm=barycentric_to_cartesian(m),
        )

    st0 = _frame_state(s_grid[start_index])

    fig.add_trace(   # static edge pointer p -> q*
        go.Scatter(
            x=[xy_p[0], xy_qstar[0]], y=[xy_p[1], xy_qstar[1]], mode="lines",
            line=dict(color=with_alpha(_ANCHOR, 0.55), width=1.2, dash="longdash"),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    fig.add_trace(   # moving pointer p -> q
        go.Scatter(
            x=[xy_p[0], st0["xq"][0]], y=[xy_p[1], st0["xq"][1]], mode="lines",
            line=dict(color=with_alpha(_MOVING, 0.85), width=1.2, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    idx_leg_pq = len(fig.data) - 1
    fig.add_trace(   # moving pointer p -> m
        go.Scatter(
            x=[xy_p[0], st0["xm"][0]], y=[xy_p[1], st0["xm"][1]], mode="lines",
            line=dict(color=with_alpha(_MOVING, 0.85), width=1.2, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    idx_leg_pm = len(fig.data) - 1

    # ------------------------------------------------------------------ #
    #  (4/5) Static anchors p and q* (orange), moving pair q and m (lime).
    #  Point labels share one convention: same font, a fixed vertical offset,
    #  anchors above their marker and movers below (so the start frame, where
    #  q sits on q* and m on p, does not stack two labels).
    # ------------------------------------------------------------------ #
    fig.add_trace(
        go.Scatter(
            x=[xy_p[0]], y=[xy_p[1]], mode="markers+text",
            marker=dict(color=_ANCHOR, size=12, symbol="circle",
                        line=dict(color=PAPER, width=1.5)),
            text=["<b><i>p</i></b>"], textposition="top center",
            textfont=dict(size=_POINT_FONT, color=INK),
            customdata=[[p[0], p[1], p[2]]],
            hovertemplate=_point_hovertemplate("p", None),
            showlegend=False,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[xy_qstar[0]], y=[xy_qstar[1]], mode="markers+text",
            marker=dict(color=_ANCHOR, size=15, symbol="star",
                        line=dict(color=PAPER, width=1.0)),
            text=["<b><i>q</i>*</b>"], textposition="top center",
            textfont=dict(size=_POINT_FONT, color=INK),
            customdata=[[q_star[0], q_star[1], q_star[2], d_star]],
            hovertemplate=_point_hovertemplate("q*", "D(p&#8741;q*)"),
            showlegend=False,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[st0["xq"][0]], y=[st0["xq"][1]], mode="markers+text",
            marker=dict(color=_MOVING, size=11, symbol="circle",
                        line=dict(color=PAPER, width=1.5)),
            text=["<i>q</i>"], textposition="bottom center",
            textfont=dict(size=_POINT_FONT, color=_mix(_MOVING, INK, 0.35)),
            customdata=[[st0["q"][0], st0["q"][1], st0["q"][2], st0["d_pq"]]],
            hovertemplate=_point_hovertemplate("q", "D(p&#8741;q)"),
            showlegend=False,
        ),
        row=1, col=1,
    )
    idx_q = len(fig.data) - 1
    fig.add_trace(
        go.Scatter(
            x=[st0["xm"][0]], y=[st0["xm"][1]], mode="markers+text",
            marker=dict(color=_MOVING, size=10, symbol="diamond",
                        line=dict(color=PAPER, width=1.5)),
            text=["<i>m</i>"], textposition="bottom center",
            textfont=dict(size=_POINT_FONT, color=_mix(_MOVING, INK, 0.35)),
            customdata=[[st0["m"][0], st0["m"][1], st0["m"][2], st0["d_pm"]]],
            hovertemplate=_point_hovertemplate("m", "D(p&#8741;m)"),
            showlegend=False,
        ),
        row=1, col=1,
    )
    idx_m = len(fig.data) - 1

    # ------------------------------------------------------------------ #
    #  Vertex labels, just outside the triangle (one trace, per-point anchor).
    # ------------------------------------------------------------------ #
    vx = barycentric_to_cartesian(np.eye(3))
    fig.add_trace(
        go.Scatter(
            x=[vx[0, 0], vx[1, 0], vx[2, 0]],
            y=[vx[0, 1] - 0.02, vx[1, 1] - 0.02, vx[2, 1] + 0.03],
            mode="text",
            text=[
                f"&#948;<sub>1</sub> (&#947; = {_fmt_gamma(gamma[0])})",
                f"&#948;<sub>2</sub> (&#947; = {_fmt_gamma(gamma[1])})",
                f"&#948;<sub>3</sub> (&#947; = {_fmt_gamma(gamma[2])})",
            ],
            textposition=["bottom left", "bottom right", "top center"],
            textfont=dict(size=12, color=LABEL),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  Readout -- a left-aligned text block in the top-left, OUT of the
    #  triangle and out of layout.annotations (a text trace, updated per frame,
    #  so a slider step never triggers a relayout).
    # ------------------------------------------------------------------ #
    def _readout_lines(state: dict) -> list[str]:
        return [
            f"<i>q</i><sub>3</sub> = {state['q3']:.4f}",
            f"D(p&#8741;q) = {state['d_pq']:.4f}",
            f"D(p&#8741;q*) = {d_star:.4f}",
            f"D(p&#8741;m(q,w*)) = {state['d_pm']:.4f}",
            f"W(w*) = {w_star_nats:.4f} nats ( = {w_star_bits:.4f} bits )",
        ]

    fig.add_trace(
        go.Scatter(
            x=[_READ_X] * len(_READ_Y), y=list(_READ_Y), mode="text",
            text=_readout_lines(st0), textposition="middle right",
            textfont=dict(size=11, color=INK),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    idx_readout = len(fig.data) - 1

    # ------------------------------------------------------------------ #
    #  Bottom row: the slim horizontal stacked decomposition bar (nats).
    #  Left "edge" block is identical in every frame; only "unspanned" grows.
    # ------------------------------------------------------------------ #
    fig.add_trace(
        go.Bar(
            x=[d_star], y=[0], orientation="h", name="edge",
            marker=dict(color=_EDGE_COLOR, line=dict(width=0)),
            text=["edge"], textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color=PAPER), constraintext="inside",
            hovertemplate="edge  D(p&#8741;q*) = %{x:.4f} nats<extra></extra>",
            showlegend=False,
        ),
        row=2, col=1,
    )
    # (the edge block is invariant across frames, so it is never re-sent)
    fig.add_trace(
        go.Bar(
            x=[st0["d_pm"]], y=[0], orientation="h", name="unspanned",
            marker=dict(color=_UNSPANNED_COLOR, line=dict(width=0)),
            text=["unspanned"], textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color=INK), constraintext="inside",
            hovertemplate="unspanned  D(p&#8741;m(q,w*)) = %{x:.4f} nats<extra></extra>",
            showlegend=False,
        ),
        row=2, col=1,
    )
    idx_unspanned = len(fig.data) - 1

    # Running total D(p||q) at the right end of the bar.
    fig.add_trace(
        go.Scatter(
            x=[st0["d_pq"]], y=[0], mode="text",
            text=[f"  D(p&#8741;q) = {st0['d_pq']:.4f}"],
            textposition="middle right", textfont=dict(size=11, color=INK),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        ),
        row=2, col=1,
    )
    idx_total = len(fig.data) - 1

    # ------------------------------------------------------------------ #
    #  Frames -- one per s, explicitly named "s000".."s0NN". Each declares the
    #  exact traces it touches, so a step never replaces the contours.
    # ------------------------------------------------------------------ #
    frame_names = [f"s{i:03d}" for i in range(n_frames)]
    frames = []
    for name, s in zip(frame_names, s_grid):
        state = _frame_state(s)
        frames.append(
            go.Frame(
                name=name,
                data=[
                    go.Scatter(x=[xy_p[0], state["xq"][0]], y=[xy_p[1], state["xq"][1]]),
                    go.Scatter(x=[xy_p[0], state["xm"][0]], y=[xy_p[1], state["xm"][1]]),
                    go.Scatter(
                        x=[state["xq"][0]], y=[state["xq"][1]],
                        customdata=[[state["q"][0], state["q"][1], state["q"][2], state["d_pq"]]],
                    ),
                    go.Scatter(
                        x=[state["xm"][0]], y=[state["xm"][1]],
                        customdata=[[state["m"][0], state["m"][1], state["m"][2], state["d_pm"]]],
                    ),
                    go.Scatter(
                        x=[_READ_X] * len(_READ_Y), y=list(_READ_Y),
                        text=_readout_lines(state),
                    ),
                    go.Bar(x=[state["d_pm"]], y=[0]),
                    go.Scatter(x=[state["d_pq"]], y=[0],
                               text=[f"  D(p&#8741;q) = {state['d_pq']:.4f}"]),
                ],
                traces=[idx_leg_pq, idx_leg_pm, idx_q, idx_m,
                        idx_readout, idx_unspanned, idx_total],
            )
        )
    fig.frames = frames

    # ------------------------------------------------------------------ #
    #  Slider -- driven by named frames. Labelled by q_3 (the market's
    #  probability of state 3), which parametrises Q and means something; the
    #  rail shows only a handful of tick labels, and the live value rides in the
    #  readout block, so the currentvalue box is suppressed.
    # ------------------------------------------------------------------ #
    label_at = set(np.linspace(0, n_frames - 1, 5).round().astype(int).tolist())
    slider_steps = []
    for i, (name, s) in enumerate(zip(frame_names, s_grid)):
        slider_steps.append(
            dict(
                method="animate",
                label=f"{q3_of_s(s):.2f}" if i in label_at else "",
                # redraw=True: with the contours now light polylines a full
                # repaint per step is cheap, and redraw=False corrupts the
                # stacked bar (it drops the static "edge" block on animate).
                args=[[name], dict(mode="immediate",
                                   frame=dict(duration=0, redraw=True),
                                   transition=dict(duration=0))],
            )
        )
    slider = dict(
        active=start_index,
        x=0.0, xanchor="left", y=-0.14, yanchor="top", len=1.0,
        pad=dict(t=4, b=4),
        currentvalue=dict(visible=False),
        tickcolor=with_alpha(LABEL, 0.3),
        font=dict(size=10, color=LABEL),
        steps=slider_steps,
    )

    # ------------------------------------------------------------------ #
    #  Axes and layout
    # ------------------------------------------------------------------ #
    # Triangle: equal aspect, no axes; range inset at top-left to seat the
    # readout on empty canvas above/left of the triangle.
    fig.update_xaxes(
        range=[-0.13, 1.13], showgrid=False, zeroline=False,
        showticklabels=False, visible=False, row=1, col=1,
    )
    fig.update_yaxes(
        range=[-0.10, 1.07], scaleanchor="x", scaleratio=1.0,
        showgrid=False, zeroline=False, showticklabels=False, visible=False,
        row=1, col=1,
    )
    # Bar: nats on x (fixed range), y hidden entirely.
    fig.update_xaxes(
        range=[0.0, bar_xmax * 1.34], title_text="nats per period",
        title_font=dict(size=12, color=LABEL), title_standoff=6,
        tickfont=dict(size=9, color=LABEL),
        showgrid=False, zeroline=False,
        ticks="outside", ticklen=3, tickcolor=with_alpha(LABEL, 0.5),
        row=2, col=1,
    )
    fig.update_yaxes(
        range=[-0.6, 0.6], showgrid=False, zeroline=False,
        showticklabels=False, visible=False, row=2, col=1,
    )

    fig.update_layout(
        barmode="stack", bargap=0.35,
        autosize=True, height=560,
        margin=dict(t=18, r=16, b=104, l=16),
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        hovermode="closest", hoverlabel=dict(namelength=-1),
        showlegend=False,
        sliders=[slider],
    )
    return fig


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


if __name__ == "__main__":
    _run_checks()
    _check_contours()
