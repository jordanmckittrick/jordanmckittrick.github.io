"""Figure builders for the Shannon's-demon post.

All colour comes from the brand module (``blogkit.brand_plotly``), which also
registers the default Plotly template, so nothing here hard-codes a hex value:

    HERO       periwinkle  -- the quantity you keep (geometric / growth / median),
                             its 95% band, and the fraction above break-even
    SECONDARY  lime        -- its Jensen-overstating sibling (arithmetic mean /
                             ceiling), shown only in contrast to periwinkle
    ACCENT     orange      -- optima and "look here" marks (never a whole series)
    INK/LABEL/GRID         -- neutrals for axes, guides, and the data cloud

The two Monte-Carlo figures (wealth, growth-rate convergence) share a skeleton
-- faint spaghetti under a percentile band, across stacked panels on a common
period axis -- so that structure lives in the small private helpers at the top.
The wealth figure alone adds a lower "fraction of paths above break-even" panel.
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

# Part-opaque white, for a label that has to sit on top of the spaghetti cloud:
# enough to lift the text off the lines, sheer enough to still read as one of
# them underneath.
_LABEL_SCRIM = "rgba(255, 255, 255, 0.72)"


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
    identify: bool = False,
    hovertemplate: str | None = None,
) -> int:
    """Draw the raw simulation paths as a faint cloud.

    Caps the number of drawn lines at ``max_paths`` (a uniform random subset,
    reproducible via ``seed``) so the figure stays light no matter how many
    paths were simulated. Returns the number of paths actually drawn.

    ``identify`` stamps each trace with ``meta.path``, the path's column label
    in ``paths``, and makes the trace hoverable. Two panels drawn from the same
    columns with the same ``seed`` draw the same subset in the same order, so
    the label is a key that pairs a path across panels -- which is what lets the
    linked-hover script in the post light up both at once. Off by default: it
    only earns its keep where that pairing means something.

    It also pins an explicit ``uid``. Plotly renders each trace into a ``<g>``
    classed ``trace<uid>``, so pinning it here is what lets that script find a
    path's SVG directly instead of assuming the DOM is in trace order.

    ``hovertemplate`` overrides the readout, and is ignored unless ``identify``.
    """
    cols = list(paths.columns)
    if len(cols) > max_paths:
        rng = np.random.default_rng(seed)
        cols = list(rng.choice(cols, size=max_paths, replace=False))
    line = dict(color=with_alpha(color, alpha), width=0.6)
    for c in cols:
        hover = (
            dict(meta=dict(path=int(c)), uid=f"p{int(c)}r{row}",
                 hovertemplate=hovertemplate or "%{y:.3f}<extra></extra>")
            if identify else dict(hoverinfo="skip")
        )
        fig.add_trace(
            go.Scatter(x=paths.index, y=paths[c], mode="lines", line=line,
                       showlegend=False, **hover),
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
    title: str = "",
    *,
    max_paths: int = 300,
    seed: int = 0,
) -> go.Figure:
    """Log-wealth fan chart over time, with the median/mean gap made visible.

    Two stacked panels sharing a period axis. Top: the individual wealth paths
    as a faint cloud (subsampled by ``_add_spaghetti``), the empirical 95%
    band, and the median (periwinkle) and mean (lime) on top; wealth is a
    multiple of starting wealth, so the dashed guide at 1.0 marks break-even
    and the y-axis is logarithmic. Bottom: the fraction of paths above
    break-even at each period.

    Both series are solid: dashes are reserved for reference lines (break-even,
    asymptotes), never for data, and each curve is labelled in place anyway.

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
        Optional heading for the top subplot; omitted when empty. Each panel is
        labelled by its y-axis regardless, so a rendered figure carrying its own
        caption can leave this blank.
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
        subplot_titles=(title, "") if title else None,
    )

    # ---- Top: raw paths, percentile band, then median & mean on top ----
    _add_spaghetti(fig, simulations, 1, 1, max_paths=max_paths, seed=seed)
    _add_percentile_band(fig, summary, 1, 1)

    fig.add_trace(
        go.Scatter(x=summary.index, y=summary["Median"], name="empirical median",
                   line=dict(color=HERO, width=2.5), showlegend=False,
                   hovertemplate="<b>empirical median:</b> %{y:.3e}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=summary.index, y=summary["Mean"], name="empirical mean",
                   line=dict(color=SECONDARY, width=2), showlegend=False,
                   hovertemplate="<b>empirical mean:</b> %{y:.3e}<extra></extra>"),
        row=1, col=1,
    )
    # Float each label above its own line at 80% of the horizon. Plotly has no
    # automatic "avoid the curve" placement, so we lift the anchor by a fixed
    # fraction of the visible decade-range -- a roughly constant pixel gap, so
    # the line never cuts through the text whatever the y-range -- and let "top
    # right" run the text up and to the right. A text trace uses raw data
    # values, which sit correctly on the log axis.
    i_label = int(round(0.8 * (len(summary) - 1)))
    x_label = summary.index[i_label]
    span = np.log10(summary["CI Upper"].max()) - np.log10(summary["CI Lower"].min())
    lift = 10.0 ** (0.08 * span)
    for label, col_name, color in (("empirical median", "Median", HERO),
                                   ("empirical mean", "Mean", SECONDARY)):
        fig.add_trace(
            go.Scatter(x=[x_label], y=[summary[col_name].iloc[i_label] * lift],
                       mode="text", text=[f"<b>{label}</b>"], textposition="top right",
                       textfont=dict(size=13, color=color),
                       cliponaxis=False, hoverinfo="skip", showlegend=False),
            row=1, col=1,
        )
    # Dashed guide at break-even (wealth = 1), no label: the line plus the 10^0
    # tick already say "break-even", so the text was redundant ink.
    fig.add_hline(y=1.0, line_width=1.2, line_dash="dash",
                  line_color=with_alpha(INK, 0.55), row=1, col=1)

    # ---- Bottom: fraction of paths above break-even ----
    _add_fraction_panel(fig, summary, 2, 1)
    fig.update_yaxes(title_text="Fraction above break-even", row=2, col=1)

    # ---- Layout ----
    # exponentformat="power" + showexponent="all" force every tick into
    # scientific notation (10^n); the evenly-spaced powers of ten also make the
    # log scaling self-evident. Each panel is named by its y-axis title rather
    # than a subplot heading, so the figure reads under its own caption without
    # repeating it; automargin keeps the wider 10^n tick labels from being
    # clipped.
    fig.update_yaxes(type="log", title_text="Wealth",
                     exponentformat="power", showexponent="all", automargin=True,
                     hoverformat=".3e", row=1, col=1)
    fig.update_xaxes(title_text="Period", row=2, col=1)
    fig.update_layout(
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=int(520 * GOLDEN_RATIO), height=560,
        # No figure-level title; the top margin just clears an optional subplot
        # heading. The series labels now sit inside the plot, so only a small
        # right margin is needed for the last x-tick.
        margin=dict(t=54, r=40),
        showlegend=False,
    )
    _apply_spikes(fig)
    return fig


# --------------------------------------------------------------------------- #
#  Empirical growth rate: risky asset against optimal CRP
# --------------------------------------------------------------------------- #
def _band_ylim(
    summary: pd.DataFrame,
    from_period: int,
    *,
    pad: float = 0.08,
) -> list[float]:
    """A y-range framing the 95% band from ``from_period`` onward.

    The running growth rate is a running mean, so its spread falls like
    1/sqrt(n): the band at n = 1 is over twenty times the width of the band at
    n = 500. Left to autoscale, the axis fits the opening flips and squeezes
    the entire convergence -- the point of the panel -- into a few percent of
    the height. So the range is set from the band *after* the early blow-up and
    the opening periods are allowed to run off; the funnel narrowing into frame
    reads as the tail of a wider funnel, which is exactly what it is.
    """
    tail = summary.loc[summary.index >= from_period]
    lo, hi = float(tail["CI Lower"].min()), float(tail["CI Upper"].max())
    margin = pad * (hi - lo)
    return [lo - margin, hi + margin]


def _add_growth_convergence_panel(
    fig: go.Figure,
    simulations: pd.DataFrame,
    summary: pd.DataFrame,
    asymptote: float,
    row: int,
    col: int,
    *,
    max_paths: int,
    seed: int,
    hovertemplate: str,
) -> None:
    """One convergence panel: spaghetti, 95% band, asymptote, break-even.

    The asymptote is the figure's punchline, so it is drawn heavy -- it has to
    carry over a cloud of 300 paths and still read as the thing they are all
    converging to. Break-even is drawn first, and lighter: it is a reference the
    eye should find without competing with periwinkle where the two run close
    together (they nearly touch in the optimal-CRP panel, whose asymptote is
    only 0.018 bits).
    """
    _add_spaghetti(fig, simulations, row, col, max_paths=max_paths, seed=seed,
                   identify=True, hovertemplate=hovertemplate)
    _add_percentile_band(fig, summary, row, col)
    fig.add_hline(y=0.0, line_width=1.2, line_dash="dash",
                  line_color=with_alpha(INK, 0.55), row=row, col=col)
    fig.add_hline(y=asymptote, line_width=3.0, line_dash="dash",
                  line_color=HERO, row=row, col=col)


def create_growth_rate_convergence_plot(
    simulations_risky: pd.DataFrame,
    summary_risky: pd.DataFrame,
    weights_risky: np.ndarray,
    simulations_optimal: pd.DataFrame,
    summary_optimal: pd.DataFrame,
    weights_optimal: np.ndarray,
    coin_flip_model: CoinFlipWithRisklessAssetModel,
    *,
    max_paths: int = 300,
    seed: int = 0,
    from_period: int | None = None,
    y_range_risky: tuple[float, float] | None = None,
    y_range_optimal: tuple[float, float] | None = None,
) -> go.Figure:
    """The law of large numbers doing its work, on a lemon and on the demon.

    Two stacked panels sharing a period axis, each showing the same thing for a
    different portfolio: the per-path empirical growth rate ``W_n`` as a faint
    cloud, its empirical 95% band, and the theoretical asymptote ``W(w)`` the
    paths are converging to (periwinkle, dashed -- a reference line, hence the
    dash). Top is the risky asset alone; bottom is the growth-optimal CRP.

    The panels carry independent y-ranges, which is forced rather than chosen:
    the two asymptotes are -0.161 and +0.018 bits, so a range wide enough for
    the risky asset would put the optimal CRP's asymptote a couple of percent of
    the panel height off break-even, fusing it with the break-even line. The
    cost of independent ranges is that the reader cannot compare *levels* across
    panels by eye -- which is why break-even (neutral, dashed) is drawn in both.
    It is the shared landmark that survives the rescaling, and the whole story
    is where each periwinkle line falls relative to it: below in the top panel
    (the lemon, almost surely ruinous), above in the bottom (the demon, almost
    surely exponential). Without it the two panels would read as the same
    picture twice.

    There is no legend and no subplot headings. Both panels measure the same
    quantity in the same units, so the units are said once, in the figure title,
    and each y-axis is left to name only its portfolio; the asymptote is the one
    other mark, labelled in place with its value.

    Each path is tagged with ``meta.path`` and the figure with
    ``layout.meta.figure``, which together are the handles the post's linked-hover
    script needs (see :func:`_add_spaghetti`). The pairing they expose is real
    and is the reason the figure is drawn this way round: both panels are
    simulated from one tensor of coin flips, so path *i* in each is the same run
    of luck under a different allocation. Plotly cannot light up both at once on
    its own -- there is no cross-subplot linked highlighting -- so the figure
    only lays the handles out, and the script in the post does the work.

    Parameters
    ----------
    simulations_risky, simulations_optimal
        Wide frames of per-path running growth rates -- one column per path,
        indexed by period, in nats/period (an ensemble's
        ``running_growth_rate``, transposed).
    summary_risky, summary_optimal
        The matching per-period cross-path reductions, e.g.
        ``summarize_across_paths(ensemble.running_growth_rate, threshold=0.0)``.
        Only ``CI Lower``/``CI Upper`` are read -- the empirical 2.5/97.5
        percentiles, an asymmetric band rather than a parametric interval.
    weights_risky, weights_optimal
        The CRP weights ``[1 - f, f]`` each ensemble was simulated under; each
        panel's asymptote is ``coin_flip_model.growth_rate(weights)``.
    coin_flip_model
        Model supplying the theoretical growth rate for each asymptote.
    max_paths, seed
        Forwarded to ``_add_spaghetti`` (see :func:`create_wealth_plot`).
    from_period
        The period from which each y-range is fitted (see :func:`_band_ylim`);
        defaults to 5% of the horizon, which clears the early blow-up on both
        panels. Ignored for a panel given an explicit range.
    y_range_risky, y_range_optimal
        Explicit ``(low, high)`` overrides, in bits/period.

    Returns
    -------
    go.Figure
        The assembled two-panel figure.
    """
    # Everything arrives in nats; convert at the display boundary. Copy the
    # summaries so the caller's frames are untouched.
    asymptote_risky = float(coin_flip_model.growth_rate(weights_risky)) / _LN2
    asymptote_optimal = float(coin_flip_model.growth_rate(weights_optimal)) / _LN2
    simulations_risky = simulations_risky / _LN2
    simulations_optimal = simulations_optimal / _LN2
    summary_risky = summary_risky.copy()
    summary_optimal = summary_optimal.copy()
    summary_risky[["CI Lower", "CI Upper"]] /= _LN2
    summary_optimal[["CI Lower", "CI Upper"]] /= _LN2

    if from_period is None:
        from_period = max(10, int(round(0.05 * len(summary_risky))))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08)

    # The readouts carry only what the reader cannot already see. Which panel is
    # which, the y-axis answers; what the units are, the title answers; and the
    # two boxes always surface together at the same period, so the period is said
    # once, in the upper one. What is left is a bare number. That also keeps the
    # box narrow, which is not incidental -- it sits directly on the cloud it is
    # reporting, so every word in it hides a path.
    _add_growth_convergence_panel(
        fig, simulations_risky, summary_risky, asymptote_risky, 1, 1,
        max_paths=max_paths, seed=seed,
        hovertemplate="Period: %{x}<br>%{y:.3f}<extra></extra>",
    )
    _add_growth_convergence_panel(
        fig, simulations_optimal, summary_optimal, asymptote_optimal, 2, 1,
        max_paths=max_paths, seed=seed,
        hovertemplate="%{y:.3f}<extra></extra>",
    )

    # Each asymptote is labelled on the side away from break-even, so the tag
    # never lands in the gap between the two lines -- a gap only 0.018 bits wide
    # in the lower panel. The label rides over the spaghetti at the right-hand
    # end, so it needs a scrim to stay legible against the cloud.
    for row, asymptote in ((1, asymptote_risky), (2, asymptote_optimal)):
        fig.add_annotation(
            xref=f"x{row if row > 1 else ''} domain", x=0.99,
            yref=f"y{row if row > 1 else ''}", y=asymptote,
            text=f"asymptotic growth = {asymptote:.3f} bits / period",
            xanchor="right", yanchor="top" if asymptote < 0 else "bottom",
            yshift=-4 if asymptote < 0 else 4,
            showarrow=False, font=dict(size=12, color=HERO),
            bgcolor=_LABEL_SCRIM, borderpad=2,
        )

    # Both panels are the same quantity in the same units, so the units are
    # hoisted into the figure title and each y-axis is left to name only its
    # portfolio. That is what buys the larger type: the labels are now two words
    # rather than a sentence, so they can be read at a glance without running the
    # height of the panel and colliding across the boundary.
    for row, panel, y_range in ((1, "Risky Asset", y_range_risky),
                                (2, "Optimal Portfolio", y_range_optimal)):
        summary = summary_risky if row == 1 else summary_optimal
        fig.update_yaxes(
            title=dict(text=panel, font=dict(size=16), standoff=10),
            range=list(y_range) if y_range else _band_ylim(summary, from_period),
            automargin=True, hoverformat=".3f", row=row, col=1,
        )
    fig.update_xaxes(title_text="Period", row=2, col=1)
    fig.update_layout(
        title=dict(text="Growth rate (bits / period)", x=0.5, xanchor="center",
                   font=dict(size=18, color=INK)),
        # "closest", not "x unified": every path is its own trace, so a unified
        # hover would try to list all 300 of them at once. The linked-hover
        # script keys off layout.meta to find this figure among the page's other
        # Plotly divs without depending on a generated element id.
        hovermode="closest", hoverlabel=dict(namelength=-1),
        # The script reads its highlight style from here rather than repeating
        # the palette in JavaScript, where it would quietly drift out of step
        # with the brand module. It restores the faint style by remembering each
        # trace's own, so only the lit style has to be passed across.
        meta=dict(figure="growth-convergence", hero=HERO, litWidth=2.0),
        width=int(520 * GOLDEN_RATIO), height=700,
        margin=dict(t=70, r=40),
        showlegend=False,
    )
    # No _apply_spikes here, unlike the other figures. Plotly's spikedistance
    # defaults to no cutoff while hoverdistance stops at 20px, so on a cloud this
    # sparse the spike spends most of its time drawn to a path the cursor is
    # nowhere near -- appearing precisely when there is no readout to anchor it.
    # It also does not survive the script's Fx.hover echo, so it goes missing in
    # the one case it could have helped. Wrong in both directions; dropped.
    return fig


# --------------------------------------------------------------------------- #
#  Probability of not losing money over time
# --------------------------------------------------------------------------- #
def create_no_loss_probability_plot(
    df: pd.DataFrame,
    title: str = "",
) -> go.Figure:
    """P(no loss) over time: the exact tail probability and its Chernoff bound.

    A single log-y panel. The exact probability ``P(S_n >= 1)`` (periwinkle) is
    the true quantity; the Chernoff large-deviation bound ``e^{-n D_KL}`` (lime)
    is its upper bound, shown in contrast -- the same periwinkle/lime
    "true vs. bound" pairing as the ceiling in the arithmetic-vs-geometric
    figure, drawn solid there and here alike. Both decay exponentially, so the
    y-axis is logarithmic; on it, exponential decay reads as a straight line.

    Parameters
    ----------
    df
        Indexed by period, with columns ``Exact`` and ``Chernoff bound`` (e.g.
        the output of ``generate_no_loss_probability_data``).
    title
        Optional panel title; omitted when empty.

    Returns
    -------
    go.Figure
        The assembled single-panel figure.
    """
    fig = make_subplots(rows=1, cols=1,
                        subplot_titles=(title,) if title else None)
    n = df.index

    fig.add_trace(
        go.Scatter(x=n, y=df["Chernoff bound"], name="Chernoff bound",
                   line=dict(color=SECONDARY, width=2), showlegend=False,
                   hovertemplate="<b>Chernoff bound:</b> %{y:.3e}<extra></extra>"),
    )
    fig.add_trace(
        go.Scatter(x=n, y=df["Exact"], name="exact probability",
                   line=dict(color=HERO, width=2.5), showlegend=False,
                   hovertemplate="<b>exact probability:</b> %{y:.3e}<extra></extra>"),
    )

    # Direct labels floated above each line at 80% of the horizon -- the same
    # lifted text-trace approach as create_wealth_plot, so the line never cuts
    # through the text on the log axis. Not bold: unlike the wealth chart, whose
    # labels sit over the spaghetti cloud, these sit on clean white, so the
    # weight would be gratuitous.
    i_label = int(round(0.8 * (len(df) - 1)))
    x_label = n[i_label]
    span = np.log10(df["Chernoff bound"].max()) - np.log10(df["Exact"].min())
    lift = 10.0 ** (0.08 * span)
    for label, col_name, color in (("exact probability", "Exact", HERO),
                                   ("Chernoff bound", "Chernoff bound", SECONDARY)):
        fig.add_trace(
            go.Scatter(x=[x_label], y=[df[col_name].iloc[i_label] * lift],
                       mode="text", text=[label], textposition="top right",
                       textfont=dict(size=13, color=color),
                       cliponaxis=False, hoverinfo="skip", showlegend=False),
        )

    # dtick=1 pins one label per decade. Left to itself, Plotly adds intermediate
    # ticks at 2x10^n and 5x10^n on a short (~3-decade) log axis, and
    # exponentformat="power" then prints those as a bare "2" and "5" alongside
    # the 10^n decade labels -- unreadable without knowing the convention.
    fig.update_yaxes(type="log", title_text="Probability of not losing money",
                     exponentformat="power", showexponent="all", automargin=True,
                     dtick=1, hoverformat=".3e")
    fig.update_xaxes(title_text="Period")
    fig.update_layout(
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=int(520 * GOLDEN_RATIO), height=460,
        margin=dict(t=54, r=40),
        showlegend=False,
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


def _direct_label(fig, x, y, text, color, row, col, *, above: bool, xshift: int = 0):
    """Tiny coloured tag riding on a curve -- replaces a legend entry.

    Sits inside the plotting area, centred on ``x`` and pushed clear of the line
    by a fixed pixel offset (not a data offset, so it holds whatever the y-range
    or scale). Lime rides above its curve and periwinkle below, which keeps each
    tag on the side where the two series are pulling apart. ``xshift`` nudges a
    tag along the axis when a steep curve would otherwise close on its far end.
    """
    fig.add_annotation(x=x, y=y, text=text, xanchor="center",
                       yanchor="bottom" if above else "top",
                       yshift=6 if above else -6, xshift=xshift,
                       showarrow=False, font=dict(size=12, color=color),
                       row=row, col=col)


def create_arithmetic_vs_geometric_plot(
    df: pd.DataFrame,
    opt_result_for_CRP: opt.OptimizeResult,
) -> go.Figure:
    """Two-panel arithmetic-vs-geometric figure with the compounding drag.

    Top: gross returns (levels). Bottom: the same two quantities in log space
    (growth rate, bits/period), the shaded band being the drag
    ``log E[Y] - E[log Y]`` (leading term the volatility drag sigma^2/2, but
    carrying every higher cumulant too).

    Curves are labelled directly, riding on the lines themselves rather than via
    a legend: the bottom panel repeats the top panel's two colours (periwinkle =
    the quantity you keep, lime = its Jensen-overstating sibling), so a single
    shared legend would show each colour twice and read as ambiguous. The figure
    draws neither a title nor subplot headings: each panel's y-axis names it, and
    a rendered figure carries its caption instead.
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

    # Curves are tagged here rather than at f = 1: the two series have separated
    # cleanly by this point, and the tags stay inside the plotting area. Anchored
    # at f = 0.82 so the longest tag ("arithmetic mean"), centred on this x, still
    # clears the right edge.
    at_label = int(np.argmin(np.abs(f - 0.82)))
    label_x = f[at_label]

    # No subplot titles: each panel's y-axis already names it ("Gross return per
    # period", "Growth rate (bits / period)"), so headings would just repeat it.
    # The "bottom is the log of the top" note lives in the figure caption instead.
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
    )

    # ---- Top: gross returns (levels) ----
    fig.add_trace(
        go.Scatter(x=f, y=arithmetic, line=dict(color=SECONDARY, width=2),
                   name="arithmetic mean", showlegend=False,
                   hovertemplate="<b>arithmetic mean:</b> %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=f, y=geometric, line=dict(color=HERO, width=3),
                   name="geometric mean", showlegend=False,
                   hovertemplate="<b>geometric mean:</b> %{y:.3f}<extra></extra>"),
        row=1, col=1,
    )
    # Both curves climb/fall left-to-right through their tags, closing on the
    # trailing edge, so nudge each a character left to keep clear of the line.
    _direct_label(fig, label_x, arithmetic[at_label], "arithmetic mean", SECONDARY, 1, 1, above=True, xshift=-7)
    _direct_label(fig, label_x, geometric[at_label], "geometric mean", HERO, 1, 1, above=False, xshift=-7)

    fig.add_hline(y=1.0, line_width=1.5, line_dash="dash", line_color="black",
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
                   name="ceiling", showlegend=False,
                   hovertemplate="<b>ceiling:</b> %{y:.3f}<extra></extra>"),
        row=2, col=1,
    )
    fig.add_trace(  # visible growth line, on top of the fill
        go.Scatter(x=f, y=growth_bits, line=dict(color=HERO, width=3),
                   name="growth rate", showlegend=False,
                   hovertemplate="<b>growth rate:</b> %{y:.3f}<extra></extra>"),
        row=2, col=1,
    )
    _direct_label(fig, label_x, ceiling_bits[at_label], "ceiling", SECONDARY, 2, 1, above=True)
    # The growth curve steepens as it falls, so it closes on the tag's trailing
    # edge; nudge the tag a character to the left to keep clear of the line.
    _direct_label(fig, label_x, growth_bits[at_label], "growth rate", HERO, 2, 1,
                  above=False, xshift=-7)

    fig.add_hline(y=0.0, line_width=1.5, line_dash="dash", line_color="black",
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
        # No figure-level title: it collided with the top subplot heading, and
        # the heading is the more useful of the two. The top margin now only has
        # to clear that heading, and the labels ride on the curves rather than
        # off the right edge, so the wide right margin is gone too.
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=820, height=700, margin=dict(t=40, r=40),
        showlegend=False,
    )
    return fig