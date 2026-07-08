"""Figure builders for the Shannon's-demon post.

All colour comes from the brand module (``blogkit.brand_plotly``), which also
registers the default Plotly template, so nothing here hard-codes a hex value:

    HERO       periwinkle  -- the quantity you keep (geometric / growth / median),
                             its 95% band, and the fraction above break-even
    SECONDARY  lime        -- its Jensen-overstating sibling (arithmetic mean /
                             ceiling), shown only in contrast to periwinkle
    ACCENT     orange      -- optima and "look here" marks (never a whole series)
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
    color: str = HERO,
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
                     title_text="", row=row, col=col)


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

    Two stacked panels sharing a period axis. Top: the individual wealth paths
    as a faint cloud (subsampled by ``_add_spaghetti``), the empirical 95%
    band, and the median (periwinkle) and mean (lime, dashed) on top; wealth is
    a multiple of starting wealth, so the dashed guide at 1.0 marks break-even
    and the y-axis is logarithmic. Bottom: the fraction of paths above
    break-even at each period.

    On the log axis the mean sits above the median because a few high paths pull
    the average up; that gap is the volatility drag. The colours make the point:
    periwinkle (median, band, fraction) is the honest, typical outcome; lime
    (mean) is its Jensen-overstating sibling, deliberately not the neutral or
    "look here" hue -- the reader should not mistake it for the baseline.

    Parameters
    ----------
    simulations
        Wide frame of wealth paths: one column per path, indexed by period,
        values being wealth as a multiple of the start (e.g. an ensemble's
        ``running_wealth_ratio``, where 1.0 is break-even).
    summary
        Per-period cross-path reduction on the same index -- e.g.
        ``EnsembleOfReturnsPaths.summarize_across_paths(..., threshold=1.0)``.
        Must carry ``Mean``, ``Median``, ``CI Lower``, ``CI Upper`` and
        ``Fraction Above``; the 1.0 threshold is what makes "Fraction Above"
        read as "above break-even". ``CI Lower``/``CI Upper`` are the empirical
        2.5/97.5 percentiles -- an asymmetric band, not a parametric interval.
    title
        Text for the top subplot title (e.g. "Wealth over time"). No separate
        figure-level title is drawn.
    max_paths, seed
        Forwarded to ``_add_spaghetti``: the cap on how many raw paths are
        drawn, and the RNG seed for the reproducible subsample above that cap.

    Returns
    -------
    go.Figure
        The assembled two-panel figure.
    """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[2, 1],
        vertical_spacing=0.09,
        subplot_titles=(title, "Fraction of paths above break-even"),
    )

    # ---- Top: raw paths, percentile band, then median & mean on top ----
    _add_spaghetti(fig, simulations, 1, 1, max_paths=max_paths, seed=seed)
    _add_percentile_band(fig, summary, 1, 1)

    fig.add_trace(
        go.Scatter(x=summary.index, y=summary["Median"], name="Median",
                   line=dict(color=HERO, width=2.5), showlegend=False,
                   hovertemplate="<b>Median:</b> %{y:.3e}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=summary.index, y=summary["Mean"], name="Mean",
                   line=dict(color=SECONDARY, width=2, dash="dash"), showlegend=False,
                   hovertemplate="<b>Mean:</b> %{y:.3e}<extra></extra>"),
        row=1, col=1,
    )
    # Label the two lines directly at their right ends instead of via a legend
    # (consistent with the other figures in this module). A text trace carries
    # raw data values, so it lands correctly on the log y-axis -- unlike a layout
    # annotation, which would need the log10 of the value.
    x_end = summary.index[-1]
    for label, col_name, color in (("Median", "Median", HERO), ("Mean", "Mean", SECONDARY)):
        fig.add_trace(
            go.Scatter(x=[x_end], y=[summary[col_name].iloc[-1]], mode="text",
                       text=[label], textposition="middle right",
                       textfont=dict(size=12, color=color),
                       cliponaxis=False, hoverinfo="skip", showlegend=False),
            row=1, col=1,
        )
    fig.add_hline(y=1.0, line_width=1.2, line_dash="dash",
                  line_color=with_alpha(INK, 0.55),
                  annotation_text="break-even = 1",
                  annotation_position="bottom right", annotation_yshift=-8,
                  row=1, col=1)

    # ---- Bottom: fraction of paths above break-even ----
    _add_fraction_panel(fig, summary, 2, 1)

    # ---- Layout ----
    # exponentformat="power" + showexponent="all" force every tick into
    # scientific notation (10^n); the evenly-spaced powers of ten also make the
    # log scaling self-evident. The "Wealth over time" subplot title labels the
    # panel, so the y-axis carries no (redundant) title of its own; automargin
    # keeps the wider 10^n tick labels from being clipped.
    fig.update_yaxes(type="log", title_text="",
                     exponentformat="power", showexponent="all", automargin=True,
                     hoverformat=".3e", row=1, col=1)
    fig.update_xaxes(title_text="Period", row=2, col=1)
    fig.update_layout(
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=int(520 * GOLDEN_RATIO), height=560,
        # No figure-level title (the subplot titles label each panel); the top
        # margin just clears the top subplot title, and the right margin leaves
        # room for the direct end-of-line labels.
        margin=dict(t=54, r=74),
        showlegend=False,
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
    """Per-path empirical growth rate converging on the theoretical rate.

    The same two-panel layout as :func:`create_wealth_plot`, without the
    central lines: the per-path running growth rates as a faint cloud, the
    empirical 95% band, and two horizontal references (the theoretical
    asymptote and break-even). The lower panel tracks the fraction of paths
    above break-even -- here, growth > 0.

    The empirical series and the asymptotic reference
    ``coin_flip_model.growth_rate(weights_vector) = E[log Y]`` are natural-log
    growth rates (nats/period) as supplied; both are converted to bits (log
    base 2) for display, to match the rest of the post. The asymptote line is
    drawn lime when positive and orange when negative, and its label and the
    break-even label swap top/bottom with the sign so neither overlaps the
    curves.

    Parameters
    ----------
    simulations
        Wide frame of per-path growth rates: one column per path, indexed by
        period (e.g. an ensemble's ``running_growth_rate``), in nats/period.
    summary
        Per-period cross-path reduction on the same index -- e.g.
        ``summarize_across_paths(..., threshold=0.0)``. Must carry
        ``CI Lower``, ``CI Upper`` and ``Fraction Above`` (``Mean``/``Median``
        are not drawn here); the 0.0 threshold is what makes "Fraction Above"
        read as "growth above break-even".
    weights_vector
        The CRP weights ``[1 - f, f]`` whose theoretical growth rate is drawn
        as the asymptote -- should match the weights the paths were simulated
        under.
    coin_flip_model
        Model supplying ``growth_rate(weights_vector) = E[log Y]`` for the
        asymptote (and its sign, which sets the colour and label placement).
    title
        Figure title; the total path count is appended automatically.
    max_paths, seed
        Forwarded to ``_add_spaghetti`` (see :func:`create_wealth_plot`).

    Returns
    -------
    go.Figure
        The assembled two-panel figure.
    """
    # The model and the summary arrive in nats (natural log); convert the
    # growth-rate quantities to bits (log base 2) for display, to match the
    # rest of the post. Work on a copy so the caller's summary is untouched;
    # the dimensionless "Fraction Above" column is left as-is.
    asymptotic_avg = float(coin_flip_model.growth_rate(weights_vector)) / _LN2
    simulations = simulations / _LN2
    summary = summary.copy()
    summary[["CI Lower", "CI Upper"]] /= _LN2

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
                  annotation_text=f"asymptotic growth = {asymptotic_avg:.3f} bits",
                  annotation_position=pos_rate, row=1, col=1)
    fig.add_hline(y=0.0, line_width=1.2, line_dash="dash",
                  line_color=with_alpha(INK, 0.55),
                  annotation_text="break-even = 0",
                  annotation_position=pos_be, row=1, col=1)

    # ---- Bottom: fraction of paths above break-even (here, growth > 0) ----
    _add_fraction_panel(fig, summary, 2, 1)

    # ---- Layout ----
    fig.update_yaxes(title_text="Empirical growth rate (bits / period)", hoverformat=".3f",
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
    # label sent UP-left into open space ABOVE break-even (clear of the "growth = 0" tags below)
    fig.add_annotation(
        x=f_star, y=growth_star_bits,
        text=f"max growth = {growth_star_bits:.3f} bits at f* = {f_star:.3f}",
        showarrow=True, arrowhead=3, standoff=_ARROW_STANDOFF, ax=-70, ay=-56,
        font=dict(size=12), bgcolor=_CALLOUT_BG,
        bordercolor=_CALLOUT_BORDER, borderwidth=1, row=2, col=1,
    )
    label_i = int(np.argmin(np.abs(f - 0.8)))   # "drag" tag out near f=0.8, in the bulk of the band
    fig.add_annotation(
        x=f[label_i], y=0.5 * ceiling_bits[label_i],   # halfway between break-even (0) and the ceiling
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