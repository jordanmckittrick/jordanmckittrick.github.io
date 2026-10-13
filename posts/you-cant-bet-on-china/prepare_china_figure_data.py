"""Local prep step for ``china_figure.py``: raw downloads in, derived log ratios out.

Run by hand whenever a raw file is refreshed (``uv run python
prepare_china_figure_data.py``). It reads the three raw downloads sitting beside
this script and writes ``china_vs_us_log_ratios.csv``, the only data file the
figure module reads. The split exists for licensing:

* the MSCI index levels are licensed and must never be published, so the raw
  ``msci_*`` files are git-ignored and stay on this machine;
* the derived file holds only a ratio of the two indexes, re-based to zero at
  its anchor date, from which neither index level can be recovered. That file
  is committed, so the site renders on a machine that has no raw data at all.

The two series it writes:

    gdp     ln(X_t / USA_t) for EVERY entity X in the World Bank file (countries
            and the Bank's regional and income-group aggregates alike), GDP per
            capita in constant 2015 US$ (WDI, NY.GDP.PCAP.KD). One point per
            year, dated July 1 because GDP is a flow over the year. Deliberately
            NOT re-based: the figure subtracts the 1978 value itself, so the
            same file can anchor any country at any year (the peer-country
            lines planned for the top panel need exactly that).

    stocks  s(t) = ln(C_t / U_t) - ln(C_0 / U_0)
            MSCI China and MSCI USA, net total return in USD, month-end levels;
            C_0 and U_0 are the levels on the anchor date, December 31, 1998.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).parent

_GDP_DIR = _HERE / "gdp_per_capita_2015_usd"
# The World Bank stamps each download with a version suffix (..._v2_445765.csv),
# so match on the indicator code rather than pinning the full file name.
_GDP_GLOB = "API_NY.GDP.PCAP.KD_*.csv"
_MSCI_CHINA = _HERE / "msci_china_index_monthly.csv"
_MSCI_USA = _HERE / "msci_usa_index_monthly.csv"

# Deliberately not named msci_*: that pattern is git-ignored, and this file is
# the one that has to be committed.
DERIVED_PATH = _HERE / "china_vs_us_log_ratios.csv"

STOCK_ANCHOR = pd.Timestamp("1998-12-31")

_DECIMALS = 6


def gdp_log_ratios() -> tuple[pd.DataFrame, str]:
    """``ln(X_t / USA_t)`` by year (rows) and entity code (columns).

    Also returns the World Bank's "last updated" date for the file. Entities
    with no data at all are dropped, as is the USA column (identically zero).
    """
    (path,) = _GDP_DIR.glob(_GDP_GLOB)
    with open(path, encoding="utf-8-sig") as f:
        preamble = [next(f) for _ in range(4)]
    updated = preamble[2].split(",")[1].strip().strip('"')
    # Four preamble lines (source, last-updated date, blanks) precede the header.
    raw = pd.read_csv(path, skiprows=4)

    wide = raw.set_index("Country Code")
    assert set(wide["Indicator Code"]) == {"NY.GDP.PCAP.KD"}, "not the constant-2015-US$ series"
    # Keep only the year columns: this drops the descriptive columns and the
    # empty "Unnamed" column that the file's trailing commas produce.
    years = [c for c in wide.columns if c.isdigit()]
    levels = wide[years].T.astype(float)
    levels.index = levels.index.astype(int)
    assert not levels[["CHN", "USA"]].isna().any().any(), "a missing GDP observation for China or the USA"

    ratios = np.log(levels.div(levels["USA"], axis=0))
    return ratios.drop(columns="USA").dropna(axis=1, how="all"), updated


def _msci_levels(path: Path) -> pd.Series:
    """Month-end index levels from an MSCI export, indexed by date."""
    with open(path, encoding="utf-8-sig") as f:
        preamble = [next(f) for _ in range(5)]
    assert preamble[2].startswith("Index Level:,Net"), f"{path.name} is not a Net index"
    assert preamble[3].startswith("Currency:,USD"), f"{path.name} is not in USD"
    # Five preamble lines precede the header. Of the five columns, only the date
    # and the level are data: two are empty and the last is MSCI's disclaimer.
    raw = pd.read_csv(path, skiprows=5, usecols=[0, 1], header=0,
                      names=["date", "level"], parse_dates=["date"])
    levels = raw.set_index("date")["level"].astype(float)
    assert levels.index.is_monotonic_increasing and levels.index.is_unique, path.name
    assert (levels > 0).all() and not levels.isna().any(), path.name
    months = levels.index.to_period("M").astype("int64")
    assert (np.diff(months) == 1).all(), f"{path.name} skips or repeats a month"
    return levels


def stock_log_ratio() -> pd.Series:
    """``s(t)`` at each month-end, zero on the anchor date."""
    china, usa = _msci_levels(_MSCI_CHINA), _msci_levels(_MSCI_USA)
    assert china.index.equals(usa.index), "the two MSCI files cover different dates"
    assert china.index[0] == STOCK_ANCHOR, "the MSCI files do not start on the anchor date"
    ratio = np.log(china / usa)
    return ratio - ratio[STOCK_ANCHOR]


def main() -> None:
    gdp, gdp_updated = gdp_log_ratios()
    s = stock_log_ratio()

    long = (gdp.rename_axis(index="year", columns="entity").stack().rename("log_ratio")
            .dropna().reset_index())                    # one row per observation, gaps left out
    rows = pd.concat([
        pd.DataFrame({"series": "gdp", "entity": long["entity"],
                      "date": long["year"].astype(str) + "-07-01",
                      "log_ratio": long["log_ratio"]}).sort_values(["entity", "date"]),
        pd.DataFrame({"series": "stocks", "entity": "CHN",
                      "date": s.index.strftime("%Y-%m-%d"),
                      "log_ratio": s.to_numpy()}),
    ])
    # "+ 0.0" turns the anchor's -0.0 into 0.0, so it prints without a sign.
    rows["log_ratio"] = rows["log_ratio"].round(_DECIMALS) + 0.0

    header = f"""\
# Derived data for china_figure.py. Written by prepare_china_figure_data.py; do not edit by hand.
#
# gdp:    ln(X_t / USA_t), GDP per capita in constant 2015 US$, for every entity X in the World Bank file
#         (ISO3 country codes, plus the Bank's own codes for its regional and income-group aggregates).
#         One point per year, dated July 1. NOT re-based: subtract an entity's value in the anchor year.
#         Source: World Bank, World Development Indicators, NY.GDP.PCAP.KD (CC BY 4.0), last updated {gdp_updated}.
# stocks: s(t) = ln(C_t / U_t) - ln(C_0 / U_0), MSCI China (C) and MSCI USA (U), net total return in USD.
#         Month-end. Zero on {STOCK_ANCHOR:%Y-%m-%d}.
#         Source: MSCI. Only this re-based log ratio is stored; the index levels are licensed and are not redistributed.
"""
    with open(DERIVED_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        rows.to_csv(f, index=False, float_format=f"%.{_DECIMALS}f")

    print(f"wrote {DERIVED_PATH.name}: {gdp.shape[1]} GDP entities ({gdp.index[0]}-{gdp.index[-1]}, "
          f"{int(gdp.notna().sum().sum())} points), "
          f"{len(s)} stock points ({s.index[0]:%Y-%m-%d} to {s.index[-1]:%Y-%m-%d}).")


if __name__ == "__main__":
    main()
