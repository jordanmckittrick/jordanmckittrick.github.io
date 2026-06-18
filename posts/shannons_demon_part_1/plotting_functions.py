"""Figure builders for the Shannon's-demon post.

All colour comes from the brand module (``blogkit.brand_plotly``), which also
registers the default Plotly template, so nothing here hard-codes a hex value:

    HERO       periwinkle  -- the quantity you keep (geometric / growth / median)
    SECONDARY  lime        -- its Jensen-overstating sibling (arithmetic / ceiling)
                             and "fraction above break-even"
    ACCENT     orange      -- optima and the arithmetic mean ("look here")
    INK/LABEL/GRID         -- neutrals for axes, guides, and the data cloud

The two Monte-Carlo figures (wealth, empirical growth) share a common skeleton
-- faint spaghetti, a percentile band, and a lower "fraction of paths" panel --
so that structure lives in the small private helpers at the top.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy.optimize as opt

from coin_flip_with_riskless_asset_model import CoinFlipWithRisklessAssetModel

from blogkit.brand_plotly import HERO, SECONDARY, ACCENT, INK, LABEL, with_alpha

GOLDEN_RATIO = (1 + np.sqrt(5)) / 2
_LN2 = np.log(2.0)


# --------------------------------------------------------------------------- #
#  Shared Monte-Carlo helpers
# --------------------------------------------------------------------------- #
def _add_spaghetti(
    fig: go.Figure,
    paths: pd.DataFrame,
    row: int,
    col: int,
    *,
    color: str = LABEL,
    alpha: float = 0.06,
    max_paths: int = 300,
    seed: int = 0,
) -> int:
    """Draw the raw simulation paths as a faint cloud.

    Caps the number of drawn lines at ``max_paths`` (a uniform random subset,
    reproducible via ``seed``) so the figure stays light no matter how many
    paths were simulated. Returns the number of paths actually drawn.
    """
    cols = list(paths.columns)
    if len(cols) > max_paths:
        rng = np.random.default_rng(seed)
        cols = list(rng.choice(cols, size=max_paths, replace=False))
    line = dict(color=with_alpha(color, alpha), width=0.6)
    for c in cols:
        fig.add_trace(
            go.Scatter(x=paths.index, y=paths[c], mode="lines", line=line,
                       hoverinfo="skip", showlegend=False),
            row=row, col=col,
        )
    return len(cols)


def _add_percentile_band(
    fig: go.Figure,
    summary: pd.DataFrame,
    row: int,
    col: int,
    *,
    color: str = HERO,
    alpha: float = 0.13,
    lower: str = "CI Lower",
    upper: str = "CI Upper",
) -> None:
    """Shade the band between two summary columns (default the 95% interval).

    Implemented as an invisible upper boundary followed by a ``tonexty`` fill,
    so only the band shows -- no boundary lines, no hover clutter.
    """
    fig.add_trace(
        go.Scatter(x=summary.index, y=summary[upper], line=dict(width=0),
                   showlegend=False, hoverinfo="skip"),
        row=row, col=col,
    )
    fig.add_trace(
        go.Scatter(x=summary.index, y=summary[lower], fill="tonexty",
                   fillcolor=with_alpha(color, alpha), line=dict(width=0),
                   showlegend=False, hoverinfo="skip"),
        row=row, col=col,
    )


def _add_fraction_panel(
    fig: go.Figure,
    summary: pd.DataFrame,
    row: int,
    col: int,
    *,
    frac_col: str = "Fraction Above",
    hover_label: str = "Above break-even",
    color: str = SECONDARY,
) -> None:
    """Lower panel: the fraction of paths above break-even, with a 50% guide.

    Only one series is drawn because "fraction below" is its complement; the
    50% dotted line is the reference a coin-flip story keeps returning to.
    """
    fig.add_trace(
        go.Scatter(x=summary.index, y=summary[frac_col], mode="lines",
                   line=dict(color=color, width=1.8),
                   hovertemplate=f"<b>{hover_label}:</b> %{{y:.1%}}<extra></extra>",
                   showlegend=False),
        row=row, col=col,
    )
    fig.add_hline(y=0.5, line_width=1.0, line_dash="dot",
                  line_color=with_alpha(LABEL, 0.7), row=row, col=col)
    fig.update_yaxes(range=[0, 1], tickformat=".0%",
                     title_text="Fraction of paths", row=row, col=col)


def _apply_spikes(fig: go.Figure) -> None:
    """Vertical cursor spike that spans both panels (reads with x-unified hover)."""
    fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor",
                     spikedash="dot", spikethickness=1,
                     spikecolor=with_alpha(LABEL, 0.6))


# --------------------------------------------------------------------------- #
#  Wealth over time
# --------------------------------------------------------------------------- #
def create_wealth_plot(
    simulations: pd.DataFrame,
    summary: pd.DataFrame,
    title: str,
    *,
    max_paths: int = 300,
    seed: int = 0,
) -> go.Figure:
    """Log-wealth fan chart over time, with the median/mean gap made visible.

    Parameters
    ----------
    simulations
        One column per simulated path, indexed by period; values are wealth.
    summary
        Per-period reduction across paths (e.g. the output of
        ``summarize_across_paths`` at threshold 1.0): must carry ``Mean``,
        ``Median``, ``CI Lower``, ``CI Upper`` and ``Fraction Above``.
    title
        Figure title; the drawn path count is appended automatically.

    The median (periwinkle) is the typical outcome; the mean (orange, dashed)
    is dragged upward by a few lucky paths -- the gap between them, on a log
    axis, is the volatility-drag story in one picture.
    """
    n_total = simulations.shape[1]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[2, 1],
        vertical_spacing=0.09,
        subplot_titles=("Wealth", "Fraction of paths above break-even"),
    )

    # ---- Top: raw paths, percentile band, then median & mean on top ----
    _add_spaghetti(fig, simulations, 1, 1, max_paths=max_paths, seed=seed)
    _add_percentile_band(fig, summary, 1, 1)

    fig.add_trace(
        go.Scatter(x=summary.index, y=summary["Median"], name="Median",
                   line=dict(color=HERO, width=2.5),
                   hovertemplate="<b>Median:</b> %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=summary.index, y=summary["Mean"], name="Mean",
                   line=dict(color=ACCENT, width=2, dash="dash"),
                   hovertemplate="<b>Mean:</b> %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_hline(y=1.0, line_width=1.2, line_dash="dash",
                  line_color=with_alpha(INK, 0.55),
                  annotation_text="break-even = 1",
                  annotation_position="bottom right", row=1, col=1)

    # ---- Bottom: fraction of paths above break-even ----
    _add_fraction_panel(fig, summary, 2, 1)

    # ---- Layout ----
    fig.update_yaxes(type="log", title_text="Wealth (log scale)",
                     hoverformat=".3f", row=1, col=1)
    fig.update_xaxes(title_text="Period", row=2, col=1)
    fig.update_layout(
        title=dict(text=f"{title}  ({n_total:,} paths)", x=0.5, xanchor="center"),
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=int(520 * GOLDEN_RATIO), height=560,
        legend=dict(orientation="h", y=-0.14),
    )
    _apply_spikes(fig)
    return fig


# --------------------------------------------------------------------------- #
#  Empirical growth rate over time
# --------------------------------------------------------------------------- #
def create_empirical_growth_rates_plot(
    simulations: pd.DataFrame,
    summary: pd.DataFrame,
    weights_vector: np.ndarray,
    coin_flip_model: CoinFlipWithRisklessAssetModel,
    title: str,
    *,
    max_paths: int = 300,
    seed: int = 0,
) -> go.Figure:
    """Empirical growth rate per path converging on the theoretical rate.

    Same skeleton as the wealth plot (spaghetti + percentile band + fraction
    panel). The horizontal dashed line is the asymptotic growth rate
    ``g(weights)``; it is drawn lime when positive (the demon wins) and orange
    when negative (over-betting), so the sign reads at a glance.
    """
    asymptotic_avg = float(coin_flip_model.growth_rate(weights_vector))
    winning = asymptotic_avg > 0
    rate_color = SECONDARY if winning else ACCENT
    pos_rate = "top right" if winning else "bottom right"
    pos_be = "bottom right" if winning else "top right"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[2, 1],
        vertical_spacing=0.09,
        subplot_titles=("Empirical growth rate", "Fraction of paths above break-even"),
    )

    # ---- Top: raw paths, percentile band, reference lines ----
    n_total = simulations.shape[1]
    _add_spaghetti(fig, simulations, 1, 1, max_paths=max_paths, seed=seed)
    _add_percentile_band(fig, summary, 1, 1)

    fig.add_hline(y=asymptotic_avg, line_width=1.5, line_dash="dash",
                  line_color=rate_color,
                  annotation_text=f"asymptotic growth = {asymptotic_avg:.3f}",
                  annotation_position=pos_rate, row=1, col=1)
    fig.add_hline(y=0.0, line_width=1.2, line_dash="dash",
                  line_color=with_alpha(INK, 0.55),
                  annotation_text="break-even = 0",
                  annotation_position=pos_be, row=1, col=1)

    # ---- Bottom: fraction of paths above break-even (here, growth > 0) ----
    _add_fraction_panel(fig, summary, 2, 1)

    # ---- Layout ----
    fig.update_yaxes(title_text="Empirical growth rate", hoverformat=".3f",
                     row=1, col=1)
    fig.update_xaxes(title_text="Period", row=2, col=1)
    fig.update_layout(
        title=dict(text=f"{title}  ({n_total:,} paths)", x=0.5, xanchor="center"),
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=int(520 * GOLDEN_RATIO), height=560,
    )
    _apply_spikes(fig)
    return fig


# --------------------------------------------------------------------------- #
#  Arithmetic vs geometric, and the drag
# --------------------------------------------------------------------------- #
_DRAG_FILL = "rgba(235, 236, 245, 1.0)"
_DRAG_LABEL = "#555a61"
_GUIDE = "#aab0b7"
_CALLOUT_BG = "rgba(255, 255, 255, 0.95)"   # opaque so it never veils a curve
_CALLOUT_BORDER = "rgba(120, 120, 120, 0.4)"
_ARROW_STANDOFF = 8


def _interior_growth_rate_zeros(
    f: np.ndarray, growth_rate: np.ndarray, edge_tol: float = 1e-3
) -> list[float]:
    """Interior f where the growth rate crosses zero (strict sign change).

    Crossings within ``edge_tol`` of either endpoint are dropped as the trivial
    pure-play zeros; only genuine interior (over-betting) zeros are returned, so
    the canonical fair coin yields none.
    """
    lo, hi = float(f.min()), float(f.max())
    margin = edge_tol * (hi - lo)
    zeros = []
    for i in np.where(growth_rate[:-1] * growth_rate[1:] < 0.0)[0]:
        f0, f1, g0, g1 = f[i], f[i + 1], growth_rate[i], growth_rate[i + 1]
        fz = float(f0 - g0 * (f1 - f0) / (g1 - g0))
        if lo + margin < fz < hi - margin:
            zeros.append(fz)
    return zeros


def _direct_label(fig, x, y, text, color, row, col):
    """Tiny coloured tag at a curve's right end -- replaces a legend entry."""
    fig.add_annotation(x=x, y=y, text=text, xanchor="left", xshift=7,
                       showarrow=False, font=dict(size=12, color=color),
                       row=row, col=col)


def create_arithmetic_vs_geometric_plot(
    df: pd.DataFrame,
    opt_result_for_CRP: opt.OptimizeResult,
    subtitle: str | None = None,
) -> go.Figure:
    """Two-panel arithmetic-vs-geometric figure with the compounding drag.

    Top: gross returns (levels). Bottom: the same two quantities in log space
    (growth rate, bits/period), the shaded band being the drag
    ``log E[Y] - E[log Y]`` (leading term the volatility drag sigma^2/2, but
    carrying every higher cumulant too).

    Curves are labelled directly at their right ends rather than via a legend:
    the bottom panel repeats the top panel's two colours (periwinkle = the
    quantity you keep, lime = its Jensen-overstating sibling), so a single
    shared legend would show each colour twice and read as ambiguous.
    """
    f = df.index.to_numpy()
    f_star = float(opt_result_for_CRP.x)
    growth_star_nats = -float(opt_result_for_CRP.fun)
    geometric_star = float(np.exp(growth_star_nats))
    growth_star_bits = growth_star_nats / _LN2

    arithmetic = df["Arithmetic Gross Return"].to_numpy()
    geometric = df["Geometric Gross Return"].to_numpy()
    growth_bits = df["Growth Rate"].to_numpy() / _LN2
    ceiling_bits = df["Growth Rate Ceiling"].to_numpy() / _LN2
    zeros = _interior_growth_rate_zeros(f, df["Growth Rate"].to_numpy())

    title = "Arithmetic vs Geometric Return, and the Drag"
    if subtitle:
        title = f"{title}<br><sub>{subtitle}</sub>"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
        subplot_titles=("Gross return", "Growth rate \u2014 the log of the curves above"),
    )

    # ---- Top: gross returns (levels) ----
    fig.add_trace(
        go.Scatter(x=f, y=arithmetic, line=dict(color=SECONDARY, width=2),
                   name="Arithmetic", showlegend=False,
                   hovertemplate="<b>Arithmetic:</b> %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=f, y=geometric, line=dict(color=HERO, width=3),
                   name="Geometric", showlegend=False,
                   hovertemplate="<b>Geometric:</b> %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    _direct_label(fig, f[-1], arithmetic[-1], "Arithmetic", SECONDARY, 1, 1)
    _direct_label(fig, f[-1], geometric[-1], "Geometric", HERO, 1, 1)

    fig.add_hline(y=1.0, line_width=1.5, line_dash="dash", line_color="black",
                  annotation_text="break-even = 1", annotation_position="bottom right",
                  row=1, col=1)
    fig.add_trace(
        go.Scatter(x=[f_star], y=[geometric_star], mode="markers",
                   marker=dict(color=ACCENT, size=13, symbol="star"),
                   hoverinfo="skip", showlegend=False, zorder=5),
        row=1, col=1,
    )
    # label sent DOWN-right into open space below the curves (clear of the lime line)
    fig.add_annotation(
        x=f_star, y=geometric_star,
        text=f"f* = {f_star:.3f},  geo = {geometric_star:.3f}",
        showarrow=True, arrowhead=3, standoff=_ARROW_STANDOFF, ax=70, ay=34,
        font=dict(size=12), bgcolor=_CALLOUT_BG,
        bordercolor=_CALLOUT_BORDER, borderwidth=1, row=1, col=1,
    )

    # ---- Bottom: log space. Opaque fill first (beneath), crisp lines on top ----
    fig.add_trace(  # invisible upper boundary for the fill
        go.Scatter(x=f, y=ceiling_bits, line=dict(width=0),
                   showlegend=False, hoverinfo="skip"),
        row=2, col=1,
    )
    fig.add_trace(  # fill between growth and the ceiling boundary = the drag band
        go.Scatter(x=f, y=growth_bits, fill="tonexty", fillcolor=_DRAG_FILL,
                   line=dict(width=0), showlegend=False, hoverinfo="skip"),
        row=2, col=1,
    )
    fig.add_trace(  # visible ceiling line, on top of the fill
        go.Scatter(x=f, y=ceiling_bits, line=dict(color=SECONDARY, width=2),
                   name="Ceiling", showlegend=False,
                   hovertemplate="<b>Ceiling:</b> %{y:.3f}<extra></extra>"),
        row=2, col=1,
    )
    fig.add_trace(  # visible growth line, on top of the fill
        go.Scatter(x=f, y=growth_bits, line=dict(color=HERO, width=3),
                   name="Growth rate", showlegend=False,
                   hovertemplate="<b>Growth rate:</b> %{y:.3f}<extra></extra>"),
        row=2, col=1,
    )
    _direct_label(fig, f[-1], ceiling_bits[-1], "Ceiling", SECONDARY, 2, 1)
    _direct_label(fig, f[-1], growth_bits[-1], "Growth rate", HERO, 2, 1)

    fig.add_hline(y=0.0, line_width=1.5, line_dash="dash", line_color="black",
                  annotation_text="break-even = 0", annotation_position="bottom right",
                  row=2, col=1)
    fig.add_trace(
        go.Scatter(x=[f_star], y=[growth_star_bits], mode="markers",
                   marker=dict(color=ACCENT, size=13, symbol="star"),
                   hoverinfo="skip", showlegend=False, zorder=5),
        row=2, col=1,
    )
    # label sent DOWN-right into open space below the growth line (clear of both lines)
    fig.add_annotation(
        x=f_star, y=growth_star_bits,
        text=f"max growth = {growth_star_bits:.3f} bits at f* = {f_star:.3f}",
        showarrow=True, arrowhead=3, standoff=_ARROW_STANDOFF, ax=80, ay=32,
        font=dict(size=12), bgcolor=_CALLOUT_BG,
        bordercolor=_CALLOUT_BORDER, borderwidth=1, row=2, col=1,
    )
    label_i = int(0.55 * (len(f) - 1))     # "drag" tag where the band is mid-width
    fig.add_annotation(
        x=f[label_i], y=0.5 * (ceiling_bits[label_i] + growth_bits[label_i]),
        text="drag", showarrow=False, font=dict(size=12, color=_DRAG_LABEL),
        row=2, col=1,
    )
    # Interior growth-rate zeros: labelled BELOW the break-even line.
    for fz in zeros:
        fig.add_trace(
            go.Scatter(x=[fz], y=[0.0], mode="markers",
                       marker=dict(color="black", size=11, symbol="x"),
                       hoverinfo="skip", showlegend=False, zorder=5),
            row=2, col=1,
        )
        fig.add_annotation(x=fz, y=0.0, text=f"growth = 0 at f = {fz:.3f}",
                           showarrow=True, arrowhead=3, standoff=_ARROW_STANDOFF,
                           ax=0, ay=28, font=dict(size=11),
                           bgcolor=_CALLOUT_BG, bordercolor=_CALLOUT_BORDER,
                           borderwidth=1, row=2, col=1)

    # f* guide BELOW the traces so the stars always sit on top of it.
    fig.add_vline(x=f_star, line_width=1.0, line_dash="dash", line_color=_GUIDE,
                  layer="below", row="all", col=1)

    fig.update_yaxes(title_text="Gross return per period", hoverformat=".3f", row=1, col=1)
    fig.update_yaxes(title_text="Growth rate (bits / period)", hoverformat=".3f", row=2, col=1)
    fig.update_xaxes(title_text="Fraction f invested in the risky asset",
                     hoverformat=".3f", row=2, col=1)
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=820, height=700, margin=dict(r=120),   # room for right-end labels
        showlegend=False,
    )
    return fig