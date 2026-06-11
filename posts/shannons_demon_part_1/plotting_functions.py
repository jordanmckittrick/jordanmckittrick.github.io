
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import scipy.optimize as opt

from posts.shannons_demon_part_1.coin_flip_with_riskless_asset_model import CoinFlipWithRisklessAssetModel



GOLDEN_RATIO = (1 + np.sqrt(5))/2



def create_wealth_over_time_plot(df_running_wealth_over_time: pd.DataFrame, title: str) -> go.Figure:
    '''
    Creates a log plot of the wealth over time for each simulation in the inputted DataFrame. It also shows
    the mean wealth, median wealth, and 95% confidence interval for the wealth over time. The lower plots
    shows the fraction of paths that are above 1.0 (positive return) and the fraction of paths that are 
    below 1.0 (negative return) over time.
    '''
    path_cols = [c for c in df_running_wealth_over_time.columns if type(c) is int]


    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True,
        row_heights=[2, 1], 
        vertical_spacing=0.1
        )


    # Update figure layout
    fig.update_layout(
        template="plotly_white",
        title=f"{title} (N = {len(path_cols)})",
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
                x=df_running_wealth_over_time.index, 
                y=df_running_wealth_over_time[c], 
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
            x=df_running_wealth_over_time.index, 
            y=df_running_wealth_over_time['95% CI Upper'], 
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Upper CI:</b> %{y:.3f}"       
                "<extra></extra>"             
                ),
            showlegend=False,
            name="95% CI Upper",
            ),
        row=1, 
        col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=df_running_wealth_over_time.index,
            y=df_running_wealth_over_time['95% CI Lower'],
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Lower CI:</b> %{y:.3f}"
                "<extra></extra>"
                ),            
            showlegend=False,
            name="95% CI Lower",
            ), 
        row=1, 
        col=1,
        )


    # Add the mean wealth over time:
    fig.add_trace(
        go.Scatter(
            x=df_running_wealth_over_time.index,
            y=df_running_wealth_over_time['Mean'],
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
            x=df_running_wealth_over_time.index,
            y=df_running_wealth_over_time['Fraction Above'],
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
            x=df_running_wealth_over_time.index,
            y=df_running_wealth_over_time['Fraction Below'],
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












def create_empirical_growth_rates_plot(df_augmented: pd.DataFrame, weights_vector: np.ndarray, params: CoinFlipWithRisklessAssetModel, title: str) -> go.Figure:
    
    asymptotic_avg = params.return_expected_log_portfolio_gross_return(weights_vector)
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
        template="plotly_white",
        title=f"{title} (N = {len(path_cols)})",
        yaxis_title="Empirical Growth Rate",
        xaxis2_title="Period",
        yaxis2_title="Fraction of Paths",
        height=500,
        width=500*golden_ratio,
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
            y=df_augmented['95% CI Upper'], 
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Upper CI:</b> %{y:.3f}"       
                "<extra></extra>"             
                ),
            showlegend=False,
            name="95% CI Upper",
            ),
        row=1, 
        col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=df_augmented.index,
            y=df_augmented['95% CI Lower'],
            mode='lines',
            line=dict(color="blue", width=0.6),
            hovertemplate=(
                "<b>Lower CI:</b> %{y:.3f}"
                "<extra></extra>"
                ),            
            showlegend=False,
            name="95% CI Lower",
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














def generate_arithmetic_vs_geometric_plot(df: pd.DataFrame, opt_result_for_CRP: opt.OptimizeResult) -> go.Figure:

    optimal_allocation = opt_result_for_CRP.x
    optimal_growth_rate = -opt_result_for_CRP.fun

    coords_for_star = (optimal_allocation, np.exp(optimal_growth_rate))

    fig = px.line(
        df,
        x="f",
        y=["Arithmetic Gross Return", "Geometric Gross Return"],
        markers=False,
        labels={
            "value": "",
            "variable": "",
            "f": "Fraction Invested in Risky Asset"
        },
        title="Arithmetic vs Geometric Gross Returns"
    )

    # Break-even line at 1.0 gross return
    fig.add_hline(
        y=1.0, 
        line_width=2.0,
        line_dash="dash",
        line_color="black",
        annotation_text="Break-even: 1.0",
        annotation_position="top right" # Puts text cleanly above the line on the right side
    )


    name_map = {
        "Arithmetic Gross Return": "Arithmetic",
        "Geometric Gross Return": "Geometric",
    }

    fig.for_each_trace(
        lambda trace: trace.update(name=name_map[trace.name])
    )


    # Put a star at the optimal fraction and its corresponding geometric gross return
    fig.add_trace(
        go.Scatter(
            x=[coords_for_star[0]], 
            y=[coords_for_star[1]], 
            mode='markers',
            marker=dict(color="red", size=12, symbol="star"),
            hoverinfo='skip',
            showlegend=False,
            zorder=5, # Puts the star on top of the lines
            # name="Optimal Fraction",
        )
    )

    fig.add_annotation(
        x=coords_for_star[0], y=coords_for_star[1], text=f"f* = {coords_for_star[0]:.3f},  geo = {coords_for_star[1]:.4f}",
        showarrow=True, arrowhead=3, standoff=8, ax=80, ay=-30,
        font=dict(size=12), bgcolor='rgba(255,255,255,0.6)')


    # Put an X at the zero of the growth rate function
    # fig.add_trace(
    #     go.Scatter(
    #         x=[opt_result_for_zeros.x[1]], 
    #         y=[np.exp(-opt_result_for_zeros.fun)], 
    #         mode='markers',
    #         marker=dict(color="blue", size=12, symbol="x"),
    #         hoverinfo='skip',
    #         showlegend=False,
    #         # name="Zero of Growth Rate",
    #      )
    # )   

    # fig.add_annotation(
    #     x=opt_result_for_zeros.x[1], y=np.exp(-opt_result_for_zeros.fun), text=f"Zero of Growth Rate: f = {opt_result_for_zeros.x[1]:.3f}",
    #     showarrow=True, arrowhead=3, standoff=8, ax=-80, ay=-30,
    #     font=dict(size=12), bgcolor='rgba(255,255,255,0.6)')


    fig.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    fig.update_layout(width=800, height=500)

    return fig