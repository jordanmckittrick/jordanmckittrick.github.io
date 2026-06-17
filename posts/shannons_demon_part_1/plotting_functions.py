
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import scipy.optimize as opt

from coin_flip_with_riskless_asset_model import CoinFlipWithRisklessAssetModel

from blogkit.brand_plotly import HERO, SECONDARY, ACCENT

GOLDEN_RATIO = (1 + np.sqrt(5))/2




def create_wealth_plot(wealth_over_time: pd.DataFrame, summary_info: pd.DataFrame, title: str) -> go.Figure:
    '''
    Creates a log plot of the wealth over time for each simulation in the inputted DataFrame. It also shows
    the mean wealth, median wealth, and 95% confidence interval for the wealth over time. The lower plots
    shows the fraction of paths that are above 1.0 (positive return) and the fraction of paths that are 
    below 1.0 (negative return) over time.
    '''
    path_cols = wealth_over_time.columns

    num_simulations = wealth_over_time.shape[1]


    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True,
        row_heights=[2, 1], 
        vertical_spacing=0.1
        )


    # Update figure layout
    fig.update_layout(
        title=f"{title} ({num_simulations} simulations)",
        yaxis_title="Wealth",
        xaxis2_title="Period",
        yaxis2_title="Fraction of Paths",
        height=500,
        width=500*GOLDEN_RATIO,
        yaxis=dict(type='log')
    )    


    ##### UPPER PLOT: MC SIMULATIONS OF WEALTH OVER TIME #####

    # Spaghetti plot of the MC simulations
    for c in path_cols:
        fig.add_trace(
            go.Scatter(
                x=wealth_over_time.index,
                y=wealth_over_time[c],
                mode='lines',
                line=dict(color="rgba(41,128,185,0.15)", width=0.6),
                hoverinfo='skip', 
                showlegend=False), 
            row=1, 
            col=1,
            )


    # Add 95% confidence interval as two separate traces, one for the upper bound and one for the lower bound
    fig.add_trace(
        go.Scatter(
            x=wealth_over_time.index, 
            y=wealth_over_time['CI Upper'], 
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Upper CI:</b> %{y:.3f}"       
                "<extra></extra>"             
                ),
            showlegend=False,
            name="CI Upper",
            ),
        row=1, 
        col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=wealth_over_time.index,
            y=wealth_over_time['CI Lower'],
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Lower CI:</b> %{y:.3f}"
                "<extra></extra>"
                ),            
            showlegend=False,
            name="CI Lower",
            ), 
        row=1, 
        col=1,
        )


    # Add the mean wealth over time:
    fig.add_trace(
        go.Scatter(
            x=wealth_over_time.index,
            y=wealth_over_time['Mean'],
            mode='lines',
            line=dict(color="orange", width=1.5),
            hovertemplate=(
                "<b>Mean:</b> %{y:.3f}"
                "<extra></extra>"
                ),
            showlegend=False,
            name="Mean",
            ), 
        row=1, 
        col=1,
        )



    ##### LOWER PLOT: FRACTION OF PATHS ABOVE AND BELOW 1.0 #####

    fig.add_trace(
        go.Scatter(
            x=wealth_over_time.index,
            y=wealth_over_time['Fraction Above'],
            mode='lines',
            line=dict(color="rgba(26, 150, 65, 0.50)", width=1.2),
            hovertemplate=(
                "<b>Positive:</b> %{y:.1%}"
                "<extra></extra>"
                ),
            showlegend=False,
            ),
        row=2,
        col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=wealth_over_time.index,
            y=wealth_over_time['Fraction Below'],
            mode='lines',
            line=dict(color="rgba(215, 48, 39, 0.50)", width=1.2),
            hovertemplate=(
                "<b>Negative:</b> %{y:.1%}"
                "<extra></extra>"   
                ),            
            showlegend=False,
            ), 
        row=2, 
        col=1,
        )



    ##### UPDATE LAYOUT #####

    fig.update_layout(
        hovermode="x unified",
        )

    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikedash="dot",
        spikethickness=1,
        spikecolor="rgba(80,80,80,0.6)",
    )

    fig.update_yaxes(
        range=[0, 1],
        tickformat='.0%', 
        row=2, 
        col=1,
        )

    return fig 












def create_empirical_growth_rates_plot(df_augmented: pd.DataFrame, weights_vector: np.ndarray, coin_flip_model: CoinFlipWithRisklessAssetModel, title: str) -> go.Figure:
    
    asymptotic_avg = coin_flip_model.growth_rate(weights_vector)
    path_cols = [c for c in df_augmented.columns if type(c) is int]

    if asymptotic_avg > 0:
        position_lta = "top right"
        position_be = "bottom right"
        color_lta = "rgb(26, 150, 65)"
    else:
        position_lta = "bottom right"
        position_be = "top right"
        color_lta = "rgb(215, 48, 39)"


    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True,
        row_heights=[2, 1], 
        vertical_spacing=0.1
        )


    # Update figure layout
    fig.update_layout(
        title=f"{title} (N = {len(path_cols)})",
        yaxis_title="Empirical Growth Rate",
        xaxis2_title="Period",
        yaxis2_title="Fraction of Paths",
        height=500,
        width=500*GOLDEN_RATIO,
    )    


    # Spaghetti plot of the MC simulations
    for c in path_cols:
        fig.add_trace(
            go.Scatter(
                x=df_augmented.index, 
                y=df_augmented[c], 
                mode='lines',
                line=dict(color="rgba(41,128,185,0.05)", width=0.6),
                hoverinfo='skip', 
                showlegend=False), 
            row=1, 
            col=1,
            )


    # Add 95% confidence interval as two separate traces, one for the upper bound and one for the lower bound
    fig.add_trace(
        go.Scatter(
            x=df_augmented.index, 
            y=df_augmented['CI Upper'], 
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Upper CI:</b> %{y:.3f}"       
                "<extra></extra>"             
                ),
            showlegend=False,
            name="CI Upper",
            ),
        row=1, 
        col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=df_augmented.index,
            y=df_augmented['CI Lower'],
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Lower CI:</b> %{y:.3f}"
                "<extra></extra>"
                ),            
            showlegend=False,
            name="CI Lower",
            ), 
        row=1, 
        col=1,
        )


    # Asymptotic growth rate
    fig.add_hline(
        y=asymptotic_avg, 
        line_width=1.5,
        line_dash="dash",
        line_color=color_lta,
        annotation_text=f"Asymptotic Avg: {asymptotic_avg:.3f}",
        annotation_position=position_lta,
        row=1,
        col=1,
    )


    # Break-even line at 0.0
    fig.add_hline(
        y=0.0,
        line_width=1.5,
        line_dash="dash",
        line_color="rgb(40, 40, 40)",
        annotation_text="Break-even: 0.0",
        annotation_position=position_be,
        row=1,
        col=1,
    )



    ### LOWER PLOT ###

    # Plot of the fraction that are positive and the fraction that are negative, as two separate traces
    fig.add_trace(
        go.Scatter(
            x=df_augmented.index,
            y=df_augmented['Fraction Above'],
            mode='lines',
            line=dict(color="rgba(26, 150, 65, 0.50)", width=1.2),
            hovertemplate=(
                "<b>Positive:</b> %{y:.1%}"
                "<extra></extra>"
                ),
            showlegend=False,
            ),
        row=2,
        col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=df_augmented.index,
            y=df_augmented['Fraction Below'],
            mode='lines',
            line=dict(color="rgba(215, 48, 39, 0.50)", width=1.2),
            hovertemplate=(
                "<b>Negative:</b> %{y:.1%}"
                "<extra></extra>"   
                ),            
            showlegend=False,
            ), 
        row=2, 
        col=1,
        )


    fig.update_layout(
        hovermode="x unified",
        )

    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikedash="dot",
        spikethickness=1,
        spikecolor="rgba(80,80,80,0.6)",
    )

    fig.update_yaxes(
        range=[0, 1],
        tickformat='.0%', 
        row=2, 
        col=1,
        )


    return fig 


















_LN2 = np.log(2.0)

# Hero = the quantity you keep (geometric / growth); secondary = its
# Jensen-overstating sibling (arithmetic / ceiling). Both solid: within a
# panel they are also separated by position (arithmetic always above
# geometric, ceiling above growth), so colour alone disambiguates.
_DRAG_FILL = "rgba(235, 236, 245, 1.0)"
_DRAG_LABEL = "#555a61"
_GUIDE = "#aab0b7"

_ARROW_STANDOFF = 8               # uniform gap between every arrowhead and its point


def _interior_growth_rate_zeros(
    f: np.ndarray, growth_rate: np.ndarray, edge_tol: float = 1e-3
) -> list[float]:
    """Interior f where the growth rate crosses zero (strict sign change).

    Crossings within ``edge_tol`` of either endpoint are dropped as the
    trivial pure-play zeros; only genuine interior (over-betting) zeros are
    returned, so the canonical fair coin yields none.
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


def create_arithmetic_vs_geometric_plot(
    df: pd.DataFrame,
    opt_result_for_CRP: opt.OptimizeResult,
    subtitle: str | None = None,
) -> go.Figure:
    """Two-panel arithmetic-vs-geometric figure with the compounding drag.

    Top: gross returns (levels). Bottom: the same two quantities in log
    space (growth rate, bits/period), with the shaded band the drag,
    log E[Y] - E[log Y] (whose leading term is the volatility drag
    sigma^2/2, but which carries every higher cumulant too).
    """
    f = df.index.to_numpy()
    f_star = float(opt_result_for_CRP.x)
    growth_star_nats = -float(opt_result_for_CRP.fun)
    geometric_star = float(np.exp(growth_star_nats))
    growth_star_bits = growth_star_nats / _LN2

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
        go.Scatter(x=f, y=df["Arithmetic Gross Return"], name="Arithmetic Return",
                   line=dict(color=SECONDARY, width=2)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=f, y=df["Geometric Gross Return"], name="Geometric Return",
                   line=dict(color=HERO, width=3)),
        row=1, col=1,
    )
    fig.add_hline(y=1.0, line_width=1.5, line_dash="dash", line_color="black",
                  annotation_text="break-even = 1", annotation_position="bottom right",
                  row=1, col=1)
    fig.add_trace(
        go.Scatter(x=[f_star], y=[geometric_star], mode="markers",
                   marker=dict(color=ACCENT, size=13, symbol="star"),
                   hoverinfo="skip", showlegend=False, zorder=5),
        row=1, col=1,
    )
    fig.add_annotation(
        x=f_star, y=geometric_star,
        text=f"f* = {f_star:.3f},  geo = {geometric_star:.3f}",
        showarrow=True, arrowhead=3, standoff=_ARROW_STANDOFF, ax=80, ay=-30,
        font=dict(size=12), bgcolor="rgba(255,255,255,0.75)", row=1, col=1,
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
        go.Scatter(x=f, y=ceiling_bits, name="Ceiling",
                   line=dict(color=SECONDARY, width=2)),
        row=2, col=1,
    )
    fig.add_trace(  # visible growth line, on top of the fill
        go.Scatter(x=f, y=growth_bits, name="Growth Rate",
                   line=dict(color=HERO, width=3)),
        row=2, col=1,
    )
    fig.add_hline(y=0.0, line_width=1.5, line_dash="dash", line_color="black",
                  annotation_text="break-even = 0", annotation_position="bottom right",
                  row=2, col=1)
    fig.add_trace(
        go.Scatter(x=[f_star], y=[growth_star_bits], mode="markers",
                   marker=dict(color=ACCENT, size=13, symbol="star"),
                   hoverinfo="skip", showlegend=False, zorder=5),
        row=2, col=1,
    )
    fig.add_annotation(
        x=f_star, y=growth_star_bits,
        text=f"max growth = {growth_star_bits:.3f} bits at f* = {f_star:.3f}",
        showarrow=True, arrowhead=3, standoff=_ARROW_STANDOFF, ax=85, ay=-28,
        font=dict(size=12), bgcolor="rgba(255,255,255,0.75)", row=2, col=1,
    )
    label_i = int(0.85 * (len(f) - 1))
    fig.add_annotation(
        x=f[label_i], y=0.5 * ceiling_bits[label_i],
        text="drag", showarrow=False, font=dict(size=12, color=_DRAG_LABEL),
        row=2, col=1,
    )
    # Interior growth-rate zeros: labelled BELOW the break-even line (mirror of
    # the optimum's label), with the same arrow standoff for a uniform look.
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
                           bgcolor="rgba(255,255,255,0.75)", row=2, col=1)

    # f* guide BELOW the traces so the star/dot always sit on top of it.
    fig.add_vline(x=f_star, line_width=1.0, line_dash="dash", line_color=_GUIDE,
                  layer="below", row="all", col=1)

    fig.update_yaxes(title_text="Gross return per period", hoverformat=".3f", row=1, col=1)
    fig.update_yaxes(title_text="Growth rate (bits / period)", hoverformat=".3f", row=2, col=1)
    fig.update_xaxes(title_text="Fraction f invested in the risky asset",
                     hoverformat=".3f", row=2, col=1)
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        hovermode="x unified",
        hoverlabel=dict(namelength=-1),
        width=820, height=700, legend=dict(orientation="h", y=-0.12),
    )
    return fig