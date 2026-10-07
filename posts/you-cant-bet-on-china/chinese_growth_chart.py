"""GDP per capita, China vs. the United States, for the "You Can't Bet on China" post.

One log-axis time series built from the World Bank's World Development
Indicators series ``NY.GDP.PCAP.CD`` (GDP per capita, current US$). The folder
``gdp_per_capita_current_USD`` beside this module is the World Bank's bulk
download, unpacked: the indicator CSV for every country plus two metadata CSVs.
Only the indicator CSV is read.

All colour comes from the brand module (``blogkit.brand_plotly``), which also
registers the default Plotly template, so nothing here hard-codes a hex value:

    HERO       periwinkle  -- China, the protagonist of the post
    SECONDARY  lime        -- the United States, the yardstick it is measured against
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from blogkit.brand_plotly import HERO, SECONDARY, LABEL, with_alpha

GOLDEN_RATIO = (1 + np.sqrt(5)) / 2

_DATA_DIR = Path(__file__).with_name("gdp_per_capita_current_USD")
# The World Bank stamps each download with a version suffix (..._v2_464091.csv),
# so match on the indicator code rather than pinning the full file name.
_DATA_GLOB = "API_NY.GDP.PCAP.CD_*.csv"

# World Bank country code -> the name the series is drawn under.
_COUNTRIES = {"CHN": "China", "USA": "United States"}
_COLORS = {"China": HERO, "United States": SECONDARY}
_WIDTHS = {"China": 2.5, "United States": 2.0}


def load_gdp_per_capita(data_dir: str | Path = _DATA_DIR) -> pd.DataFrame:
    """GDP per capita (current US$) for China and the United States, by year.

    Parameters
    ----------
    data_dir
        The unpacked World Bank bulk download for ``NY.GDP.PCAP.CD``.

    Returns
    -------
    pd.DataFrame
        Indexed by year (int), with columns ``China`` and ``United States``.
        Years in which either country has no observation are dropped.
    """
    (path,) = Path(data_dir).glob(_DATA_GLOB)
    # Four preamble lines (source, last-updated date, blanks) precede the header.
    raw = pd.read_csv(path, skiprows=4)

    wide = raw.set_index("Country Code").loc[list(_COUNTRIES)]
    # Keep only the year columns: this drops the descriptive columns and the
    # empty "Unnamed" column that the file's trailing commas produce.
    years = [c for c in wide.columns if c.isdigit()]
    df = wide[years].T.rename(columns=_COUNTRIES).astype(float).dropna()
    df.index = df.index.astype(int)
    df.index.name = "Year"
    df.columns.name = None
    return df


def create_gdp_per_capita_plot(df: pd.DataFrame) -> go.Figure:
    """GDP per capita over time for China and the United States, on a log axis.

    A single log-y panel, on which a constant growth rate reads as a straight
    line and the gap between the two lines is the ratio of the two countries'
    incomes. Each line is labelled directly at its right-hand end rather than
    in a legend.

    Parameters
    ----------
    df
        Indexed by year, with columns ``China`` and ``United States`` (e.g.
        the output of ``load_gdp_per_capita``).

    Returns
    -------
    go.Figure
        The assembled single-panel figure.
    """
    fig = go.Figure()
    years = df.index

    # The United States first, so that China -- the protagonist -- is drawn on top.
    for country in ("United States", "China"):
        fig.add_trace(
            go.Scatter(x=years, y=df[country], name=country,
                       line=dict(color=_COLORS[country], width=_WIDTHS[country]),
                       showlegend=False,
                       hovertemplate=f"<b>{country}:</b> $%{{y:,.0f}}<extra></extra>"),
        )
        # Direct label at the end of the line, in the right margin.
        fig.add_trace(
            go.Scatter(x=[years[-1]], y=[df[country].iloc[-1]],
                       mode="text", text=[f" {country}"], textposition="middle right",
                       textfont=dict(size=13, color=_COLORS[country]),
                       cliponaxis=False, hoverinfo="skip", showlegend=False),
        )

    # The y-range hugs the data (a tenth of a decade of padding either side)
    # rather than running out to whole decades, which would leave the bottom
    # of the panel empty. A log axis takes its range in log10 units.
    y_lo = np.log10(df.min().min()) - 0.1
    y_hi = np.log10(df.max().max()) + 0.1
    # One labelled tick per decade, written out as dollar amounts: the default
    # log-axis ticks would add bare "2" and "5" labels between the decades.
    tickvals = 10.0 ** np.arange(np.ceil(y_lo), np.floor(y_hi) + 1)
    fig.update_yaxes(type="log", title_text="GDP per capita (current US$)",
                     tickvals=tickvals, ticktext=[f"${v:,.0f}" for v in tickvals],
                     range=[y_lo, y_hi], automargin=True)
    fig.update_xaxes(range=[years[0], years[-1]], dtick=10,
                     showspikes=True, spikemode="across", spikesnap="cursor",
                     spikedash="dot", spikethickness=1,
                     spikecolor=with_alpha(LABEL, 0.6))
    fig.update_layout(
        hovermode="x unified", hoverlabel=dict(namelength=-1),
        width=int(520 * GOLDEN_RATIO), height=460,
        margin=dict(t=30, r=110, b=40),
        showlegend=False,
    )
    return fig
