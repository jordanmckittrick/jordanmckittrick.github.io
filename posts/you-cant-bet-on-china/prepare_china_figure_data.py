"""Local prep step for ``china_figure.py``: raw downloads in, derived log ratios out.

Run by hand whenever a raw file is refreshed or swapped for another::

    uv run python prepare_china_figure_data.py
    uv run python prepare_china_figure_data.py --china msci_china_gross.csv --usa msci_usa_gross.csv --variant gross

It reads the raw downloads sitting beside this script (or the MSCI files named
on the command line) and writes ``china_vs_us_log_ratios.csv``, the only data
file the figure module reads. Nothing else needs to change when the source
files do: the derived file says of itself which return variant it holds and
where its stock series starts, and the figure takes both from there. The split
exists for licensing:

* the MSCI index levels are licensed and must never be published, so the raw
  ``msci_*`` files are git-ignored and stay on this machine;
* the derived file holds only a ratio of the two indexes, re-based to zero at
  its first month, from which neither index level can be recovered. That file
  is committed, so the site renders on a machine that has no raw data at all.

The series it writes:

    gdp     ln(X_t / USA_t) for EVERY entity X in the World Bank file (countries
            and the Bank's regional and income-group aggregates alike), GDP per
            capita in constant 2015 US$ (WDI, NY.GDP.PCAP.KD). One point per
            year, dated July 1 because GDP is a flow over the year. Deliberately
            NOT re-based: the figure subtracts the 1978 value itself, so the
            same file can anchor any country at any year (the peer-country
            lines planned for the top panel need exactly that).

    gdp_level  ln(USA_t): America's own GDP per capita, same units, so that any
            entity's own level (and so its own growth, which the figure's
            narration quotes) can be had by adding it back to a ratio.

    stocks  s(t) = ln(C_t / U_t) - ln(C_0 / U_0)
            MSCI China and MSCI USA, total return in USD, month-end levels;
            C_0 and U_0 are the levels at the first month-end the two files
            share. The figure re-bases the series at whatever anchor it is
            given (a log ratio re-bases by subtraction).

    usa_return  ln(U_trough / U_anchor): MSCI USA's own return from a possible
            stock anchor to the month at which the ratio above bottoms. The
            narration says how far each market had fallen by then, and the
            ratio alone cannot say that. One number per anchor, and only for
            the few anchors the figure may be given: the file's first month
            and each December after it, up to the bottom. That is all of
            either index, taken alone, that the derived file holds.

Return variants. An MSCI total return index comes net or gross of withholding
tax. Both files must be of the SAME variant, the one asked for with
``--variant``: each file says which it is in its preamble, and the script stops
if either disagrees. Variants are never mixed and one file is never spliced
onto another: a longer history means a longer download of both indexes in one
variant.
"""

from __future__ import annotations

import argparse
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
VARIANTS = ("net", "gross")

# Deliberately not named msci_*: that pattern is git-ignored, and this file is
# the one that has to be committed.
DERIVED_PATH = _HERE / "china_vs_us_log_ratios.csv"

_DECIMALS = 6


def gdp_log_ratios() -> tuple[pd.DataFrame, pd.Series, str]:
    """``ln(X_t / USA_t)`` by year (rows) and entity code (columns), and ``ln(USA_t)`` by year.

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
    return ratios.drop(columns="USA").dropna(axis=1, how="all"), np.log(levels["USA"]), updated


def _msci_cells(path: Path) -> pd.DataFrame:
    """The first two columns of an MSCI export, every row, as text: a CSV, or an Excel file."""
    if path.suffix.lower() in (".xls", ".xlsx"):
        try:
            cells = pd.read_excel(path, header=None, usecols=[0, 1], dtype=object)
        except ImportError as error:
            raise SystemExit(f"{path.name}: reading Excel needs a package that is not installed ({error}). "
                             f"Install it, or save the sheet as CSV and pass that instead.") from None
    else:
        # Of the five columns, only the first two are data: two are empty and the last is MSCI's disclaimer.
        cells = pd.read_csv(path, header=None, usecols=[0, 1], dtype=str, skip_blank_lines=False,
                            encoding="utf-8-sig")
    cells.columns = ["a", "b"]
    return cells


def _msci_levels(path: Path, variant: str) -> pd.Series:
    """Month-end index levels from an MSCI export, indexed by date.

    The export's preamble says what it holds ("Index Level:", "Currency:"): it
    must be the ``variant`` asked for, in US dollars. The rows under the "Date"
    header are the data, up to the first row that is not a date.
    """
    cells = _msci_cells(path)
    key = cells["a"].astype(str).str.strip().str.rstrip(":").str.lower()
    said = {name: str(cells["b"][key == name].iloc[0]).strip() for name in ("index level", "currency")
            if (key == name).any()}
    assert "index level" in said, f"{path.name} does not say whether it is a net or a gross index"
    assert said["index level"].lower() == variant, (
        f"{path.name} is a {said['index level']} index, not {variant}: both files must be the same "
        f"return variant, and variants are never spliced")
    assert said.get("currency", "").upper() == "USD", f"{path.name} is not in USD"
    assert (key == "date").any(), f"{path.name} has no Date header"
    rows = cells.iloc[int(np.flatnonzero(key == "date")[0]) + 1:]
    dates = pd.to_datetime(rows["a"], errors="coerce")
    stop = int(np.argmax(dates.isna().to_numpy())) if dates.isna().any() else len(rows)
    levels = pd.Series(rows["b"].iloc[:stop].astype(float).to_numpy(), index=pd.DatetimeIndex(dates.iloc[:stop]),
                       name="level")
    assert len(levels) > 12, f"{path.name}: no monthly data found"
    assert levels.index.is_monotonic_increasing and levels.index.is_unique, path.name
    assert (levels > 0).all() and not levels.isna().any(), path.name
    months = levels.index.to_period("M").astype("int64")
    assert (np.diff(months) == 1).all(), f"{path.name} skips or repeats a month"
    return levels


def stock_log_ratio(china_path: Path = _MSCI_CHINA, usa_path: Path = _MSCI_USA,
                    variant: str = "net") -> tuple[pd.Series, pd.DataFrame]:
    """``s(t)`` at each month-end the two files share, zero at the first of them; and MSCI USA's returns to the bottom.

    The second is one row per possible anchor (the first month, and each
    December before the ratio's early bottom): the anchor, the month of the
    bottom (the ratio's low before its peak, as the figure finds it), and
    ``ln(U_bottom / U_anchor)``.
    """
    china, usa = _msci_levels(china_path, variant), _msci_levels(usa_path, variant)
    start, end = max(china.index[0], usa.index[0]), min(china.index[-1], usa.index[-1])
    china, usa = china[start:end], usa[start:end]
    assert len(china) > 12 and china.index.equals(usa.index), "the two MSCI files do not share their month-ends"
    ratio = np.log(china / usa)
    bottom = ratio[:ratio.idxmax()].idxmin()
    anchors = [d for n, d in enumerate(ratio.index) if (n == 0 or d.month == 12) and d < bottom]
    to_bottom = pd.DataFrame({"anchor": anchors, "bottom": bottom,
                              "log_return": [float(np.log(usa[bottom] / usa[a])) for a in anchors]})
    return ratio - ratio.iloc[0], to_bottom


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the derived file that china_figure.py reads.")
    parser.add_argument("--china", type=Path, default=_MSCI_CHINA, help="the MSCI China export (CSV or Excel)")
    parser.add_argument("--usa", type=Path, default=_MSCI_USA, help="the MSCI USA export, in the same variant")
    parser.add_argument("--variant", choices=VARIANTS, default="net",
                        help="the return variant BOTH files hold (checked against what each file says)")
    parser.add_argument("--out", type=Path, default=DERIVED_PATH, help="where to write the derived file")
    args = parser.parse_args(argv)

    gdp, usa_gdp, gdp_updated = gdp_log_ratios()
    s, to_bottom = stock_log_ratio(args.china, args.usa, args.variant)

    long = (gdp.rename_axis(index="year", columns="entity").stack().rename("log_ratio")
            .dropna().reset_index())                    # one row per observation, gaps left out
    rows = pd.concat([
        pd.DataFrame({"series": "gdp", "entity": long["entity"],
                      "date": long["year"].astype(str) + "-07-01",
                      "log_ratio": long["log_ratio"]}).sort_values(["entity", "date"]),
        pd.DataFrame({"series": "gdp_level", "entity": "USA",
                      "date": usa_gdp.index.astype(str) + "-07-01",
                      "log_ratio": usa_gdp.to_numpy()}),
        pd.DataFrame({"series": "stocks", "entity": "CHN",
                      "date": s.index.strftime("%Y-%m-%d"),
                      "log_ratio": s.to_numpy()}),
        # The "entity" of one of these rows is the anchor it starts from; its date is the bottom.
        pd.DataFrame({"series": "usa_return", "entity": to_bottom["anchor"].dt.strftime("%Y-%m-%d"),
                      "date": to_bottom["bottom"].dt.strftime("%Y-%m-%d"),
                      "log_ratio": to_bottom["log_return"]}),
    ])
    # "+ 0.0" turns the first month's -0.0 into 0.0, so it prints without a sign.
    rows["log_ratio"] = rows["log_ratio"].round(_DECIMALS) + 0.0

    # The two "key: value" lines are read back by china_figure.derived_info().
    header = f"""\
# Derived data for china_figure.py. Written by prepare_china_figure_data.py; do not edit by hand.
#
# gdp:    ln(X_t / USA_t), GDP per capita in constant 2015 US$, for every entity X in the World Bank file
#         (ISO3 country codes, plus the Bank's own codes for its regional and income-group aggregates).
#         One point per year, dated July 1. NOT re-based: subtract an entity's value in the anchor year.
#         Source: World Bank, World Development Indicators, NY.GDP.PCAP.KD (CC BY 4.0), last updated {gdp_updated}.
# gdp_level: ln(USA_t), the same series for the United States itself: add it to a ratio for that entity's own level.
# stocks: s(t) = ln(C_t / U_t) - ln(C_0 / U_0), MSCI China (C) and MSCI USA (U), {args.variant} total return in USD.
#         Month-end. Zero at its first month; the figure re-bases it at its own anchor.
#         Source: MSCI. Only this re-based log ratio is stored; the index levels are licensed and are not redistributed.
# usa_return: ln(U_bottom / U_anchor), MSCI USA's own return from a possible anchor (in the entity column) to the
#         month the ratio bottoms (the date): {len(to_bottom)} numbers, for the narration. No level, and no series.
# stocks_variant: {args.variant}
# stocks_start: {s.index[0]:%Y-%m-%d}
"""
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        rows.to_csv(f, index=False, float_format=f"%.{_DECIMALS}f")

    print(f"wrote {args.out.name}: {gdp.shape[1]} GDP entities ({gdp.index[0]}-{gdp.index[-1]}, "
          f"{int(gdp.notna().sum().sum())} points), "
          f"{len(usa_gdp)} US GDP levels, "
          f"{len(s)} stock points ({s.index[0]:%Y-%m-%d} to {s.index[-1]:%Y-%m-%d}, {args.variant}), "
          f"{len(to_bottom)} MSCI USA returns to the bottom of {to_bottom['bottom'].iloc[0]:%b %Y}.")


if __name__ == "__main__":
    main()
