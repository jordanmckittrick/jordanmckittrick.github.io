"""The simplex figure for the log-optimal-investing post.

One interactive figure that makes the growth-rate decomposition (1.6) visible:
for three states and two tradable assets (one risk-free at gross return ``r``,
one risky at gross returns ``gamma``), it draws the risk-neutral segment
``Q`` and its two companion segments inside the 2-simplex, and lets a slider
walk a point ``q`` along ``Q`` while a stacked bar splits its divergence from
the belief ``p`` into the part every portfolio pays (the "edge",
``D(p||q*)``) and the part geometry wastes (the "unspanned" remainder,
``D(p||m(q,w*))``).

The geometry, stated once and used everywhere below:

* ``Y(f)   = (1 - f) r + f gamma``            portfolio gross return (length 3)
* ``W(f)   = sum_i p_i log Y_i(f)``           growth rate, nats
* ``f*     = argmax_f W(f)``                  no closed form for three states
* ``q*     = r p / Y(f*)``                    the reverse info projection of p onto Q
* ``Q      = { q in the simplex : q . gamma = r }``     a line segment A--B
* ``m(q,f) = q Y(f) / r``                     the tilted measure
* ``M_wstar = { m(q, f*) : q in Q }``         a line segment
* ``M_qstar = { m(q*, f) : f admissible }``   a line segment

Everything the figure needs is derived from ``(r, gamma, p)``; nothing about
the running example is baked in. Colour comes from the brand module
(``blogkit.brand_plotly``), which also registers the default Plotly template,
so no hex value is hard-coded here beyond the periwinkle *ramp* built from the
house hue ``HERO``.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy.optimize as opt

# Importing the brand module registers "plotly_white+blog" as the default
# template (font, ink, paper, gridless neutrals) and gives us the semantic
# palette. HERO is the house periwinkle.
from blogkit.brand_plotly import HERO, ACCENT, INK, LABEL, PAPER, with_alpha

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


# --------------------------------------------------------------------------- #
#  Figure styling helpers
# --------------------------------------------------------------------------- #
def _mix(hex_a: str, hex_b: str, t: float) -> str:
    """Blend two ``#rrggbb`` colours, ``t`` of the way from ``a`` to ``b``."""
    a = np.array([int(hex_a.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)])
    b = np.array([int(hex_b.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)])
    c = np.round((1.0 - t) * a + t * b).astype(int)
    return "#{:02x}{:02x}{:02x}".format(*c)


# A sequential periwinkle ramp built from the house hue. Clipped at both ends:
# the light end stays a visible periwinkle (never white-out), the dark end a
# deep periwinkle rather than black, so a value never vanishes into the paper.
_RAMP_LIGHT = _mix(HERO, "#ffffff", 0.55)
_RAMP_DARK = _mix(HERO, INK, 0.50)
_PERIWINKLE_RAMP = [[0.0, _RAMP_LIGHT], [0.5, HERO], [1.0, _RAMP_DARK]]

# Neutral for the KL contours: reference geometry with no semantic hue, so it
# recedes as grey texture and never competes with the periwinkle segments.
_CONTOUR_FAINT = with_alpha(LABEL, 0.28)
_CONTOUR_TANGENT = with_alpha(LABEL, 0.55)

_SCRIM = "rgba(255, 255, 255, 0.82)"          # lifts the readout off the lines
_EDGE_COLOR = HERO                            # the edge you keep: periwinkle
_UNSPANNED_COLOR = with_alpha(LABEL, 0.55)    # the part geometry wastes: grey
_MOVING = INK                                 # the cursor pair q and m


def _fmt_gamma(x: float) -> str:
    """Format a gamma value with at least one decimal (2 -> ``2.0``, 0.45 kept)."""
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"


def _bary_hovertemplate(name: str, div_label: str | None) -> str:
    """Hover text: a name, three barycentric coordinates, an optional divergence."""
    lines = [
        f"<b>{name}</b>",
        "q = (%{customdata[0]:.3f}, %{customdata[1]:.3f}, %{customdata[2]:.3f})",
    ]
    if div_label is not None:
        lines.append(f"{div_label} = %{{customdata[3]:.4f}} nats")
    return "<br>".join(lines) + "<extra></extra>"


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
    """Assemble the two-panel simplex figure for the belief ``p``.

    Left: the 2-simplex with the KL contours of ``q -> D(p||q)``, the three
    segments ``M_qstar`` (dotted), ``Q`` (solid) and ``M_wstar`` (dashed) --
    the last two coloured by their own divergence from ``p`` on one periwinkle
    ramp -- the static landmarks ``p`` and ``q*``, and a slider-driven point
    ``q`` on ``Q`` with its partner ``m(q, w*)`` on ``M_wstar``. Right: a
    stacked bar splitting ``D(p||q)`` into the fixed "edge" ``D(p||q*)`` and
    the growing "unspanned" remainder ``D(p||m(q, w*))``.

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
        The slider spans ``{ s : D(p||q(s)) <= kl_window * D(p||q*) }`` and the
        colour ramp and bar axis share the same ``kl_window * D(p||q*)`` cap.

    Returns
    -------
    go.Figure
        A single responsive figure, roughly 520 px tall, no title (the caption
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
    cap = kl_window * d_star                          # shared colour/bar cap

    A, B = risk_neutral_segment_endpoints(r, gamma)
    f_lo, f_hi = admissible_f_range(r, gamma)
    s_lo, s_hi, s_star = optimal_slider_interval(r, gamma, p, kl_window)
    s_grid = np.linspace(s_lo, s_hi, n_frames)
    start_index = int(np.argmin(np.abs(s_grid - s_star)))

    def q_of_s(s: float) -> np.ndarray:
        return A + s * (B - A)

    xy_p = barycentric_to_cartesian(p)
    xy_qstar = barycentric_to_cartesian(q_star)

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.72, 0.28],
        horizontal_spacing=0.08,
        specs=[[{"type": "xy"}, {"type": "xy"}]],
    )

    # ------------------------------------------------------------------ #
    #  (1) KL contours -- faint level sets of q -> D(p||q), background texture
    # ------------------------------------------------------------------ #
    n_grid = 260
    gx = np.linspace(0.0, 1.0, n_grid)
    gy = np.linspace(0.0, np.sqrt(3.0) / 2.0, n_grid)
    GX, GY = np.meshgrid(gx, gy)
    bary = _cartesian_to_barycentric(np.stack([GX, GY], axis=-1))
    inside = np.all(bary > 1e-9, axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        Z = np.sum(np.where(bary > 0.0, p * np.log(p / bary), 0.0), axis=-1)
    Z = np.where(inside, Z, np.nan)

    # Levels as multiples of the edge D(p||q*), not hard numbers, so they track
    # (r, gamma, p). The level equal to the edge is drawn darker: it is tangent
    # to Q at q*, the visual proof that q* is the nearest point of Q to p.
    for mult in (0.25, 0.5, 1.0, 2.0, 4.0):
        level = mult * d_star
        tangent = mult == 1.0
        color = _CONTOUR_TANGENT if tangent else _CONTOUR_FAINT
        fig.add_trace(
            go.Contour(
                x=gx, y=gy, z=Z,
                contours=dict(
                    start=level, end=level, size=level,
                    coloring="lines", showlabels=False,
                ),
                line=dict(width=1.4 if tangent else 1.0),
                colorscale=[[0.0, color], [1.0, color]],
                showscale=False, hoverinfo="skip",
                connectgaps=False, name="", showlegend=False,
            ),
            row=1, col=1,
        )

    # ------------------------------------------------------------------ #
    #  Triangle outline -- quiet definition, no hover
    # ------------------------------------------------------------------ #
    tri = barycentric_to_cartesian(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0]]))
    fig.add_trace(
        go.Scatter(
            x=tri[:, 0], y=tri[:, 1], mode="lines",
            line=dict(color=with_alpha(LABEL, 0.45), width=1.2),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  (2) M_qstar -- the chord { m(q*, f) }, lowest in the hierarchy
    # ------------------------------------------------------------------ #
    f_line = np.linspace(f_lo, f_hi, 160)
    m_qstar = np.array([tilted_measure(q_star, f, r, gamma) for f in f_line])
    xy_mq = barycentric_to_cartesian(m_qstar)
    fig.add_trace(
        go.Scatter(
            x=xy_mq[:, 0], y=xy_mq[:, 1], mode="lines",
            line=dict(color=with_alpha(LABEL, 0.6), width=1.1, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  (3) Q (solid) and M_wstar (dashed) -- one ramp, distinguished by style
    #
    #  Each is a SINGLE markers trace of ~150 densely spaced points coloured by
    #  its own divergence from p, on the shared periwinkle ramp (cmin=0,
    #  cmax=cap). Q reads solid via full opacity; M_wstar reads dashed via a
    #  periodic opacity pattern -- style, not hue, tells them apart. Colour is
    #  deliberately non-monotone (D is convex along Q, minimal at q*), so the
    #  same shade appears on both sides of q*: it conveys magnitude only.
    # ------------------------------------------------------------------ #
    n_seg = 150
    s_seg = np.linspace(0.0, 1.0, n_seg)
    q_seg = np.array([q_of_s(s) for s in s_seg])
    xy_q = barycentric_to_cartesian(q_seg)
    d_q = np.array([kl_divergence(p, q) for q in q_seg])

    m_seg = np.array([tilted_measure(q, f_star, r, gamma) for q in q_seg])
    xy_m = barycentric_to_cartesian(m_seg)
    d_m = np.array([kl_divergence(p, m) for m in m_seg])

    # Dash pattern for M_wstar: three markers shown, two hidden, repeating.
    dash_opacity = np.where((np.arange(n_seg) % 5) < 3, 1.0, 0.0)

    fig.add_trace(
        go.Scatter(
            x=xy_q[:, 0], y=xy_q[:, 1], mode="markers",
            marker=dict(
                color=d_q, colorscale=_PERIWINKLE_RAMP, cmin=0.0, cmax=cap,
                size=6.5, line=dict(width=0), showscale=False,
            ),
            hoverinfo="skip", showlegend=False, name="Q",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=xy_m[:, 0], y=xy_m[:, 1], mode="markers",
            marker=dict(
                color=d_m, colorscale=_PERIWINKLE_RAMP, cmin=0.0, cmax=cap,
                size=6.0, opacity=dash_opacity, line=dict(width=0),
                showscale=False,
            ),
            hoverinfo="skip", showlegend=False, name="M_wstar",
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  Segment labels (text traces, static) -- Q, M(w*), M(q*)
    # ------------------------------------------------------------------ #
    def _label_at(frac_seg, xy_seg, text, color, dy=0.0, dx=0.0):
        i = int(round(frac_seg * (len(xy_seg) - 1)))
        return go.Scatter(
            x=[xy_seg[i, 0] + dx], y=[xy_seg[i, 1] + dy], mode="text",
            text=[text], textposition="middle center",
            textfont=dict(size=12.5, color=color),
            cliponaxis=False, hoverinfo="skip", showlegend=False,
        )

    fig.add_trace(_label_at(0.10, xy_q, "<i>Q</i>", _mix(HERO, INK, 0.35), dy=0.035), row=1, col=1)
    fig.add_trace(_label_at(0.12, xy_m, "<i>M</i><sub>w*</sub>", _mix(HERO, INK, 0.35), dy=-0.04), row=1, col=1)
    fig.add_trace(_label_at(0.82, xy_mq, "<i>M</i><sub>q*</sub>", LABEL, dy=0.035), row=1, col=1)

    # ------------------------------------------------------------------ #
    #  (4) Static landmarks -- p (the belief) and q* (the projection)
    # ------------------------------------------------------------------ #
    fig.add_trace(
        go.Scatter(
            x=[xy_p[0]], y=[xy_p[1]], mode="markers+text",
            marker=dict(color=ACCENT, size=12, symbol="circle",
                        line=dict(color=PAPER, width=1.5)),
            text=["<b><i>p</i></b>"], textposition="top center",
            textfont=dict(size=14, color=INK),
            customdata=[[p[0], p[1], p[2], 0.0]],
            hovertemplate=_bary_hovertemplate("p  (belief)", "D(p&#8741;p)"),
            showlegend=False,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[xy_qstar[0]], y=[xy_qstar[1]], mode="markers+text",
            marker=dict(color=ACCENT, size=15, symbol="star",
                        line=dict(color=PAPER, width=1.0)),
            text=["<b><i>q</i>*</b>"], textposition="top center",
            textfont=dict(size=14, color=INK),
            customdata=[[q_star[0], q_star[1], q_star[2], d_star]],
            hovertemplate=_bary_hovertemplate("q*  (projection of p onto Q)", "D(p&#8741;q*)"),
            showlegend=False,
        ),
        row=1, col=1,
    )

    # ------------------------------------------------------------------ #
    #  (5) Per-frame layer: the connector, then the moving q and m markers.
    #  Built at the start frame (nearest q*); frames overwrite their x/y.
    # ------------------------------------------------------------------ #
    def _frame_state(s: float) -> dict:
        q = q_of_s(s)
        m = tilted_measure(q, f_star, r, gamma)
        d_pq = kl_divergence(p, q)
        d_pm = kl_divergence(p, m)
        xq = barycentric_to_cartesian(q)
        xm = barycentric_to_cartesian(m)
        return dict(q=q, m=m, d_pq=d_pq, d_pm=d_pm, xq=xq, xm=xm)

    st0 = _frame_state(s_grid[start_index])

    # Connector first, so the moving markers sit on top of it.
    fig.add_trace(
        go.Scatter(
            x=[st0["xq"][0], st0["xm"][0]], y=[st0["xq"][1], st0["xm"][1]],
            mode="lines", line=dict(color=with_alpha(INK, 0.5), width=1.0, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ),
        row=1, col=1,
    )
    idx_connector = len(fig.data) - 1

    fig.add_trace(
        go.Scatter(
            x=[st0["xq"][0]], y=[st0["xq"][1]], mode="markers+text",
            marker=dict(color=_MOVING, size=11, symbol="circle",
                        line=dict(color=PAPER, width=1.5)),
            text=["<i>q</i>"], textposition="bottom center",
            textfont=dict(size=13, color=INK),
            customdata=[[st0["q"][0], st0["q"][1], st0["q"][2], st0["d_pq"]]],
            hovertemplate=_bary_hovertemplate("q  (on Q)", "D(p&#8741;q)"),
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
            textfont=dict(size=13, color=INK),
            customdata=[[st0["m"][0], st0["m"][1], st0["m"][2], st0["d_pm"]]],
            hovertemplate=_bary_hovertemplate("m(q, w*)  (on M_w*)", "D(p&#8741;m)"),
            showlegend=False,
        ),
        row=1, col=1,
    )
    idx_m = len(fig.data) - 1

    # ------------------------------------------------------------------ #
    #  Vertex labels, just outside the triangle
    # ------------------------------------------------------------------ #
    vlabels = [
        (np.array([1.0, 0.0, 0.0]), f"&#948;<sub>1</sub> (&#947; = {_fmt_gamma(gamma[0])})", "top right", 0.0, -0.055),
        (np.array([0.0, 1.0, 0.0]), f"&#948;<sub>2</sub> (&#947; = {_fmt_gamma(gamma[1])})", "top left", 0.0, -0.055),
        (np.array([0.0, 0.0, 1.0]), f"&#948;<sub>3</sub> (&#947; = {_fmt_gamma(gamma[2])})", "top center", 0.06, 0.0),
    ]
    for vertex, text, pos, dy, dyy in vlabels:
        xy = barycentric_to_cartesian(vertex)
        fig.add_trace(
            go.Scatter(
                x=[xy[0]], y=[xy[1] + dy + dyy], mode="text",
                text=[text], textposition=pos,
                textfont=dict(size=12.5, color=LABEL),
                cliponaxis=False, hoverinfo="skip", showlegend=False,
            ),
            row=1, col=1,
        )

    # ------------------------------------------------------------------ #
    #  RIGHT PANEL -- the stacked decomposition bar (nats)
    # ------------------------------------------------------------------ #
    bar_x = ["D(p&#8741;q)"]
    # Lower block: the edge, D(p||q*). Identical in every frame.
    fig.add_trace(
        go.Bar(
            x=bar_x, y=[d_star], name="edge",
            marker=dict(color=_EDGE_COLOR, line=dict(width=0)),
            hovertemplate="edge  D(p&#8741;q*) = %{y:.4f} nats<extra></extra>",
            showlegend=False,
        ),
        row=1, col=2,
    )
    idx_edge = len(fig.data) - 1
    # Upper block: the unspanned remainder, D(p||m(q, w*)). Grows off q*.
    fig.add_trace(
        go.Bar(
            x=bar_x, y=[st0["d_pm"]], name="unspanned",
            marker=dict(color=_UNSPANNED_COLOR, line=dict(width=0)),
            hovertemplate="unspanned  D(p&#8741;m(q,w*)) = %{y:.4f} nats<extra></extra>",
            showlegend=False,
        ),
        row=1, col=2,
    )
    idx_unspanned = len(fig.data) - 1

    # Block labels, as text riding to the right of the bar at stable heights.
    fig.add_trace(
        go.Scatter(
            x=[1.0], y=[d_star / 2.0], mode="text", text=["edge"],
            textposition="middle right", textfont=dict(size=12, color=INK),
            xaxis="x2", yaxis="y2", cliponaxis=False,
            hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[1.0], y=[d_star + (cap - d_star) / 2.0], mode="text",
            text=["unspanned"], textposition="middle right",
            textfont=dict(size=12, color=LABEL),
            xaxis="x2", yaxis="y2", cliponaxis=False,
            hoverinfo="skip", showlegend=False,
        )
    )

    # ------------------------------------------------------------------ #
    #  Frames -- one per s, explicitly named "s000".."s0NN"
    # ------------------------------------------------------------------ #
    def _readout(state: dict) -> str:
        return (
            "<b>growth-rate decomposition</b><br>"
            f"D(p&#8741;q)&#9;&#9;= {state['d_pq']:.4f}<br>"
            f"D(p&#8741;q*)&#9;&#9;= {d_star:.4f}<br>"
            f"D(p&#8741;m(q, w*))&#9;= {state['d_pm']:.4f}<br>"
            f"W(w*)&#9;&#9;&#9;= {w_star_nats:.4f} nats "
            f"( = {w_star_bits:.4f} bits )"
        )

    def _readout_annotation(state: dict) -> dict:
        return dict(
            xref="x domain", yref="y domain", x=0.02, y=0.99,
            xanchor="left", yanchor="top", align="left",
            text=_readout(state), showarrow=False,
            font=dict(size=11.5, color=INK), bgcolor=_SCRIM,
            bordercolor=with_alpha(LABEL, 0.35), borderwidth=1, borderpad=5,
        )

    frame_names = [f"s{i:03d}" for i in range(n_frames)]
    frames = []
    for name, s in zip(frame_names, s_grid):
        state = _frame_state(s)
        frame_data = [
            go.Scatter(  # connector
                x=[state["xq"][0], state["xm"][0]],
                y=[state["xq"][1], state["xm"][1]],
            ),
            go.Scatter(  # moving q
                x=[state["xq"][0]], y=[state["xq"][1]],
                customdata=[[state["q"][0], state["q"][1], state["q"][2], state["d_pq"]]],
            ),
            go.Scatter(  # moving m
                x=[state["xm"][0]], y=[state["xm"][1]],
                customdata=[[state["m"][0], state["m"][1], state["m"][2], state["d_pm"]]],
            ),
            go.Bar(y=[state["d_pm"]]),  # upper (unspanned) block
        ]
        frames.append(
            go.Frame(
                name=name,
                data=frame_data,
                traces=[idx_connector, idx_q, idx_m, idx_unspanned],
                layout=go.Layout(annotations=[_readout_annotation(state)]),
            )
        )
    fig.frames = frames

    # ------------------------------------------------------------------ #
    #  Slider
    # ------------------------------------------------------------------ #
    # Every step keeps its s label (Plotly auto-thins which appear on the rail,
    # and the currentvalue readout mirrors the active step's label live).
    slider_steps = []
    for name, s in zip(frame_names, s_grid):
        slider_steps.append(
            dict(
                method="animate",
                label=f"{s:.2f}",
                args=[[name], dict(mode="immediate",
                                   frame=dict(duration=0, redraw=True),
                                   transition=dict(duration=0))],
            )
        )
    slider = dict(
        active=start_index,
        x=0.0, xanchor="left", y=-0.04, yanchor="top", len=0.72,
        pad=dict(t=10, b=10),
        currentvalue=dict(prefix="q at s = ", font=dict(size=12, color=LABEL)),
        tickcolor=with_alpha(LABEL, 0.5),
        font=dict(size=10, color=LABEL),
        steps=slider_steps,
    )

    # ------------------------------------------------------------------ #
    #  Axes and layout
    # ------------------------------------------------------------------ #
    fig.update_xaxes(
        range=[-0.11, 1.11], showgrid=False, zeroline=False,
        showticklabels=False, visible=False, row=1, col=1,
    )
    fig.update_yaxes(
        range=[-0.16, 1.0], scaleanchor="x", scaleratio=1.0,
        showgrid=False, zeroline=False, showticklabels=False, visible=False,
        row=1, col=1,
    )
    # Right panel: a single category, fixed y so blocks resize, not the axis.
    fig.update_xaxes(
        showgrid=False, zeroline=False, showticklabels=False,
        range=[-0.6, 2.4], row=1, col=2,
    )
    fig.update_yaxes(
        range=[0.0, cap * 1.06], title_text="nats per period",
        title_font=dict(size=13, color=LABEL), tickfont=dict(color=LABEL),
        gridcolor=with_alpha(LABEL, 0.15), zeroline=True,
        zerolinecolor=with_alpha(LABEL, 0.4), row=1, col=2,
    )

    fig.update_layout(
        barmode="stack",
        autosize=True, height=520,
        margin=dict(t=24, r=16, b=64, l=16),
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        hovermode="closest", hoverlabel=dict(namelength=-1),
        showlegend=False,
        sliders=[slider],
        annotations=[_readout_annotation(st0)],
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


if __name__ == "__main__":
    _run_checks()
