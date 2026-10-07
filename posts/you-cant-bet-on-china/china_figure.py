"""The animated two-panel China figure for the "You Can't Bet on China" post.

Two stacked panels on one time axis, under a strip of dated events. Every
quantity is China's divided by America's -- the United States is the numeraire
-- and every change is a log ratio, in nats.

* Top, "Economy": China's economy caught up with America's. Real GDP per
  capita, China / US, re-based to zero in 1978,

      g(t) = ln(CHN_t / USA_t) - ln(CHN_1978 / USA_1978),

  one point per year, dated July 1 (GDP is a flow over the year).

* Bottom, "Stocks": what an investor could actually buy. MSCI China / MSCI USA
  (net, USD), re-based to zero on December 31, 1998,

      s(t) = ln(C_t / U_t) - ln(C_0 / U_0),

  one point per month-end, against the SAME economy series re-based to that
  date, ``e(t) = g(t) - g(Dec 31, 1998)`` with ``g`` interpolated linearly to the
  month-ends. The area between the two is tinted periwinkle where the stocks
  are ahead of the economy and grey where they are behind. Before December 1998
  there is nothing to draw, and the panel says why.

The two panels share one vertical scale: a nat is the same number of pixels in
both, so each panel's height is proportional to its y-range and slopes can be
compared across them. The y-ranges are fixed (zooming is horizontal only), which
is what keeps that true.

The stock window ends on the last month-end the GDP data also cover
(:func:`common_cutoff`); later stock data stay in the derived file but are not
drawn. The two arrowed annotations are dated from the data
(:func:`last_fall_below`), not typed in.

Data. This module reads ONLY ``china_vs_us_log_ratios.csv``, the committed file
of log ratios written by ``prepare_china_figure_data.py``. It holds the GDP
ratio for every entity in the World Bank file, un-re-based, so peer-country
lines can be added to the top panel later (``build_china_figure(peers=...)``
already draws them). The MSCI index levels are licensed: the raw files are
git-ignored, and no level may reach the figure, its hover text or anything else
that is published.

Animation. The default state is the finished chart. A play button and a native
range input (not Plotly's slider, whose handle sticks in a drag state) move a
playhead from ``START_YEAR`` to the cutoff. The browser draws each frame itself:
``requestAnimationFrame`` works out the revealed part of every line, linearly
interpolated to the playhead, the fills between them and the x-range -- which
GROWS with the playhead -- and one ``Plotly.update`` writes it all into traces
that always exist. (``Plotly.animate`` re-appends SVG trace groups, so a trace
left out of a frame changes its stacking order; nothing here is ever added,
removed or reordered.) The pace is not constant: it slows near events and runs
through the empty stretches (:func:`pace_profile`).

Text. Positions that depend on the rendered size of text -- which row each
event label sits in, where the two arrowed annotations go -- are worked out in
the browser from measured text, for the width the figure actually has. If the
event labels cannot all be placed without touching, they are hidden (lines and
hover remain); if the arrowed annotations cannot, they become numbered markers
with a key beneath the plot. Each panel's title and subtitle are HTML over the
plot, with a halo of page colour that erases whatever runs behind the letters;
the notes in the bottom panel sit on a patch of page colour. Either way a
dashed event line passes behind the text rather than through it.

Hover. Plotly's own hover is off. A small HTML box reports the actual data
points at the cursor's date, panel by panel, from strings formatted here in
Python, so an interpolated animation point can never produce a label.

Colour follows ``_brand.yml``: lime for the economy, periwinkle for the stocks,
ink for events and annotations. The plot background is transparent and the ink
is re-read from the page, so the figure follows the site's dark mode.

Run the checks with ``uv run python china_figure.py``; the browser-side audit
(equal scale, text collisions at rest and mid-playback, hover) runs when the
page URL carries ``?china-audit``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Importing the brand module registers "plotly_white+blog" as the default
# template (font, ink, gridlines) and gives us the semantic palette.
from blogkit.brand_plotly import HERO, SECONDARY, INK, LABEL, GRID, PAPER, with_alpha

# --------------------------------------------------------------------------- #
#  Knobs
# --------------------------------------------------------------------------- #
START_YEAR = 1960        # first GDP year drawn; playback starts here
SHOW_MULTIPLE = False    # hover: append "(x e^x)" after each nat value, e.g. "+1.53 nats (x4.6)"

# ---- Playback pacing (tune these; _run_checks asserts the total is 20-35 s) ----
SECONDS_PER_YEAR_FAST = 0.25   # through stretches with nothing to mark
SECONDS_PER_YEAR_SLOW = 0.75   # near an event
SLOW_WITHIN_YEARS = 1.0        # "near": about this far either side of an event
MIN_WINDOW_YEARS = 8.0         # the x-axis never shows less than this during playback
WINDOW_MARGIN = 0.02           # room right of the playhead, as a fraction of the window

# The anchors. The stock anchor is fixed by the derived file (see
# prepare_china_figure_data.py); load_derived() verifies it.
GDP_ANCHOR_YEAR = 1978
STOCK_ANCHOR = pd.Timestamp("1998-12-31")
# What the caption says the common cutoff is. The cutoff itself is computed
# (common_cutoff); _run_checks compares the two, so a data refresh that moves it
# fails loudly instead of leaving the caption wrong.
EXPECTED_CUTOFF = pd.Timestamp("2025-06-30")

_HERE = Path(__file__).parent
_DATA_PATH = _HERE / "china_vs_us_log_ratios.csv"
_DECIMALS = 6            # precision of the derived file, kept for every plotted number

# Colour by meaning (semantics from _brand.yml; palette from brand_plotly):
_GDP_COLOR = SECONDARY                    # lime: the economy
_STOCK_COLOR = HERO                       # periwinkle: the stocks
_INK = INK                                # events, annotations, the zero line
_FILL_AHEAD = with_alpha(HERO, 0.22)      # stocks ahead of the economy
_FILL_BEHIND = with_alpha(INK, 0.10)      # stocks behind: the shortfall
_FAMINE_FILL = with_alpha(INK, 0.06)
_PEER_COLOR = with_alpha(LABEL, 0.45)

_EVENT_LINE_OPACITY = 0.4
_EVENT_LABEL_ALPHA = 0.9
_FADE_YEARS = 1.0        # anything timed fades in over this much playhead travel
_PACE_STEPS_PER_YEAR = 10

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# For the caption: the credit both licences ask for.
SOURCE_LINE = ("Sources: World Bank, World Development Indicators (CC BY 4.0), "
               "GDP per capita in constant 2015 US$; MSCI, MSCI China and MSCI USA "
               "net total return indexes in US dollars.")


# --------------------------------------------------------------------------- #
#  Events
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Event:
    """A dated event: a dashed ink line through both panels, labelled in the strip.

    ``tier`` 1 events are drawn. Tier 2 events are stored for phase 2 and pass
    through the same builder (``tiers=(1, 2)``); each entry that reaches the
    browser carries its tier, so a zoom-dependent rule is a change to
    ``alphaAt`` in the script, not to the structure. ``narration_text`` and
    ``image`` are carried for phase 2's narration pauses and are unused here.
    """
    date: str                          # ISO date at which the line is drawn
    label: str                         # short label for the strip
    description: str                   # one sentence for the hover box
    tier: int
    narration_text: str | None = None  # phase 2
    image: str | None = None           # phase 2


EVENTS = [
    # ---- Tier 1: drawn ----
    Event("1966-05-16", "Cultural Revolution",
          "16 May 1966: the Politburo's “May 16 Notification” launches the Cultural Revolution.", 1),
    Event("1972-02-21", "Nixon in Beijing",
          "21 February 1972: Richard Nixon arrives in Beijing, the first visit to the People's Republic "
          "by an American president.", 1),
    Event("1976-09-09", "Mao dies", "9 September 1976: Mao Zedong dies.", 1),
    Event("1978-12-18", "Deng's reforms",
          "18–22 December 1978: the Third Plenum of the 11th Central Committee, the conventional "
          "start of Deng Xiaoping's “reform and opening up”.", 1),
    # UNSURE of the day: I have 22 September - 12 October 1980 for Friedman's first visit.
    Event("1980-09-22", "Friedman visits",
          "September 1980: Milton Friedman visits China for the first time, on a lecture tour.", 1),
    Event("1989-06-04", "Tiananmen",
          "4 June 1989: the army clears the Tiananmen Square protests by force.", 1),
    Event("1990-12-19", "Shanghai exchange opens",
          "19 December 1990: the Shanghai Stock Exchange begins trading.", 1),
    Event("1992-01-18", "Southern Tour",
          "18 January – 21 February 1992: Deng Xiaoping tours the south, and economic reform regains its momentum.", 1),
    Event("2001-12-11", "Joins WTO",
          "11 December 2001: China becomes a member of the World Trade Organization.", 1),
    Event("2014-11-17", "Stock Connect",
          "17 November 2014: Stock Connect opens, letting investors in Hong Kong buy Shanghai-listed "
          "A-shares and mainland investors buy Hong Kong shares.", 1),

    # ---- Tier 2: stored, not drawn this round ----
    Event("1971-10-25", "UN seat",
          "25 October 1971: the UN General Assembly seats the People's Republic as China's representative.", 2),
    Event("1979-01-01", "US–China normalisation",
          "1 January 1979: the United States and the People's Republic establish full diplomatic relations.", 2),
    Event("1980-08-26", "Special economic zones",
          "26 August 1980: the first special economic zones, Shenzhen among them, are formally established.", 2),
    # UNSURE of the day: 21 February 1992 for the first B-share listing in
    # Shanghai (Shanghai Vacuum Electron Devices). February 1992 is solid.
    Event("1992-02-21", "First B-shares",
          "February 1992: the first B-shares, a class of share open to foreign investors, list in Shanghai.", 2),
    Event("1993-07-15", "First H-share",
          "15 July 1993: Tsingtao Brewery lists in Hong Kong, the first mainland company to issue H-shares.", 2),
    Event("1997-07-01", "Hong Kong handover",
          "1 July 1997: sovereignty over Hong Kong passes from Britain to China.", 2),
    # UNSURE which date is meant: the QFII rules were issued in early November
    # 2002 and took effect on 1 December 2002; the first QFII trade was in July
    # 2003. This uses the effective date.
    Event("2002-12-01", "QFII",
          "1 December 2002: the Qualified Foreign Institutional Investor scheme takes effect, "
          "admitting approved foreign institutions to the A-share market.", 2),
    # A choice: the Shanghai Composite's peak. The fall began the next trading
    # day; the other candidate is "Black Monday", 24 August 2015.
    Event("2015-06-12", "Market crash",
          "12 June 2015: the Shanghai Composite peaks; it loses about a third of its value within a month.", 2),
    Event("2018-06-01", "MSCI adds A-shares",
          "1 June 2018: MSCI begins adding mainland A-shares to its China and Emerging Markets indexes.", 2),
    # A choice: there is no single date. This is the cybersecurity review of
    # Didi, two days after its New York listing; others are the halted Ant IPO
    # (3 November 2020), Alibaba's fine (10 April 2021) and the tutoring ban
    # (24 July 2021).
    Event("2021-07-02", "Tech crackdown",
          "July 2021: regulators open a cybersecurity review of Didi days after its New York listing, "
          "the widest point of the crackdown on China's technology companies.", 2),
]


# --------------------------------------------------------------------------- #
#  Data and the quantities derived from it
# --------------------------------------------------------------------------- #
def load_derived(path: str | Path = _DATA_PATH) -> tuple[pd.DataFrame, pd.Series]:
    """The derived file, as the GDP ratios of every entity and the stock ratio.

    Returns
    -------
    (gdp, s)
        ``gdp``: ``ln(X_t / USA_t)`` by date (July 1 of each year) and entity
        code, NOT re-based (see :func:`rebased`). ``s``: the stock log ratio at
        each month-end, zero on ``STOCK_ANCHOR``; every month in the file,
        including those after the plotted window.
    """
    df = pd.read_csv(path, comment="#", parse_dates=["date"])
    gdp = df[df["series"] == "gdp"].pivot(index="date", columns="entity", values="log_ratio")
    gdp.columns.name = None
    s = df[(df["series"] == "stocks") & (df["entity"] == "CHN")].set_index("date")["log_ratio"]
    s.name = "s"
    assert s.index[0] == STOCK_ANCHOR and s.iloc[0] == 0.0, "stock series is not anchored at STOCK_ANCHOR"
    return gdp, s


def rebased(gdp: pd.DataFrame, entity: str = "CHN", year: int = GDP_ANCHOR_YEAR) -> pd.Series:
    """One entity's GDP ratio as the change since ``year``: ``g`` for China."""
    x = gdp[entity].dropna()
    at_anchor = x[x.index.year == year]
    if at_anchor.empty:
        raise ValueError(f"{entity} has no GDP observation in {year} to anchor on")
    out = (x - at_anchor.item()).round(_DECIMALS) + 0.0   # "+ 0.0" turns -0.0 into 0.0
    out.name = entity
    return out


def _days(when) -> np.ndarray:
    """Dates as days since the epoch, for interpolating linearly in time."""
    return np.asarray(pd.DatetimeIndex(np.atleast_1d(when)).as_unit("s").asi8) / 86_400


def g_at(g: pd.Series, when) -> np.ndarray:
    """``g`` interpolated linearly in time to arbitrary dates."""
    return np.interp(_days(when), _days(g.index), g.to_numpy())


def common_cutoff(g: pd.Series, s: pd.Series) -> pd.Timestamp:
    """The last month-end that both datasets cover: where the stock window ends."""
    return s.index[s.index <= g.index[-1]][-1]


def economy_since_anchor(g: pd.Series, month_ends: pd.DatetimeIndex) -> pd.Series:
    """``e(t) = g(t) - g(STOCK_ANCHOR)`` at the month-ends: the economy, re-anchored.

    The same series as the top panel's, moved down so that it starts from zero
    where the stock line does. ``g`` is annual, so the values between its July
    points are straight-line interpolations.
    """
    e = np.round(g_at(g, month_ends) - g_at(g, STOCK_ANCHOR)[0], _DECIMALS) + 0.0
    return pd.Series(e, index=month_ends, name="e")


def last_fall_below(a: pd.Series, b) -> pd.Timestamp:
    """The date on which ``a`` falls below ``b`` and never recovers within the window.

    That is, the first date of the final unbroken stretch in which ``a < b``.
    ``b`` is a series on the same dates, or a number.
    """
    below = np.asarray(a < b)
    assert below[-1], "a is not below b at the end of the window"
    assert not below.all(), "a is below b throughout: it never falls below"
    last_above = len(below) - 1 - int(np.argmax(~below[::-1]))
    return a.index[last_above + 1]


def fill_polygons(t: np.ndarray, s: np.ndarray, e: np.ndarray) -> dict[str, list[tuple[np.ndarray, ...]]]:
    """The area between ``s`` and ``e``, split into runs of one sign.

    Walks the shared grid ``t``; wherever ``s - e`` changes sign, the exact
    crossing (linear between the two grid points) ends one run and starts the
    next. Returns ``{"ahead": [...], "behind": [...]}``, each a list of runs
    ``(t, s, e)``: ahead where ``s > e``, behind where ``s < e``. The browser
    script has the same walk (``fills``) for the animated frames; the audit
    checks the two agree.
    """
    runs: dict[str, list] = {"ahead": [], "behind": []}
    cur = [(t[0], s[0], e[0])]

    def flush():
        total = sum(p[1] - p[2] for p in cur)
        if len(cur) > 1 and total != 0:
            runs["ahead" if total > 0 else "behind"].append(tuple(np.array(c) for c in zip(*cur)))

    for i in range(1, len(t)):
        d0, d1 = s[i - 1] - e[i - 1], s[i] - e[i]
        if d0 * d1 < 0:
            f = d0 / (d0 - d1)
            tc, yc = t[i - 1] + f * (t[i] - t[i - 1]), s[i - 1] + f * (s[i] - s[i - 1])
            cur.append((tc, yc, yc))
            flush()
            cur = [(tc, yc, yc)]
        elif d0 == 0 and len(cur) > 1:          # touches exactly on a grid point
            flush()
            cur = [(t[i - 1], s[i - 1], e[i - 1])]
        cur.append((t[i], s[i], e[i]))
    flush()
    return runs


def pace_profile(moments: list[pd.Timestamp], start: pd.Timestamp, end: pd.Timestamp) -> np.ndarray:
    """Seconds of playback per year of data, on a uniform grid from start to end.

    ``SECONDS_PER_YEAR_SLOW`` within half of ``SLOW_WITHIN_YEARS`` of any of the
    ``moments``, easing to ``SECONDS_PER_YEAR_FAST`` by one and a half times it.
    The grid has ``_PACE_STEPS_PER_YEAR`` steps a year; the script integrates it
    to map playback time to playhead date and back.
    """
    n = round((end - start).days / 365.25 * _PACE_STEPS_PER_YEAR)
    years = (_days(start)[0] + (_days(end)[0] - _days(start)[0]) * np.arange(n + 1) / n) / 365.25
    at = _days(pd.DatetimeIndex(moments)) / 365.25
    nearest = np.abs(years[:, None] - at[None, :]).min(axis=1)
    w = np.clip(1.5 - nearest / SLOW_WITHIN_YEARS, 0.0, 1.0)
    w = w * w * (3 - 2 * w)                                        # smoothstep
    return SECONDS_PER_YEAR_FAST + (SECONDS_PER_YEAR_SLOW - SECONDS_PER_YEAR_FAST) * w


def playback_seconds(profile: np.ndarray, start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Total playback time implied by a pace profile (trapezoid rule, as in the script)."""
    step_years = (end - start).days / 365.25 / (len(profile) - 1)
    return float(np.sum((profile[1:] + profile[:-1]) / 2) * step_years)


def _nats(x: float, show_multiple: bool) -> str:
    """A change in nats for the hover box: ``+2.71 nats``, with a true minus sign."""
    shown = round(float(x), 2) + 0.0                # "+ 0.0" turns -0.0 into 0.0
    text = f"{'+' if shown >= 0 else '−'}{abs(shown):.2f} nats"
    if show_multiple:
        m = float(np.exp(x))
        # Two significant figures across the range the data covers.
        text += f" (×{m:.0f})" if round(m, 1) >= 10 else f" (×{m:.1f})" if m >= 1 else f" (×{m:.2f})"
    return text


def _iso(when) -> str:
    return pd.Timestamp(when).strftime("%Y-%m-%d")


def _month(when) -> str:
    return f"{_MONTHS[when.month - 1]} {when.year}"


def _signed(v: int, unit: str = "") -> str:
    """An axis label: +2, 0, −1 (true minus), with the unit on the tick that carries it."""
    return ("0" if v == 0 else f"{'+' if v > 0 else '−'}{abs(v)}") + unit


# --------------------------------------------------------------------------- #
#  Layout
# --------------------------------------------------------------------------- #
# Two layouts, switched by the measured column width (fit() in the script): the
# 920 px body column and a phone. Each fixes ``px_per_nat``, the one vertical
# scale both panels share; panel heights follow from the y-ranges.
#
# ``head`` sizes the in-panel title and subtitle (HTML, see _MARKUP);
# ``labels`` gives every annotation role its size, text and visibility;
# ``strip.fonts`` and ``arrow_fonts`` are the sizes tried, largest first, for
# the event labels and for the two arrowed annotations.
# On a phone the two notes in the empty part of the bottom panel merge into
# one, and the optional "China ahead" / "US ahead" hints are dropped.
_NARROW_BELOW_PX = 560
_REF_WIDTH = 920         # Quarto grid body-width
_SUB_TOP = f"Real GDP per capita, China ÷ US, change since {GDP_ANCHOR_YEAR}"
_SUB_BOTTOM = "MSCI China ÷ MSCI USA (net, USD), change since Dec 1998"
_ARROW_TEXT = dict(
    arrow_economy="Stocks fall behind the economy, and stay behind",
    arrow_parity="US stocks pull ahead, and stay ahead",
)
# Ways to break each arrowed annotation over lines, fewest lines first; the
# script takes the first that fits beside the data.
_ARROW_WRAPS = dict(
    arrow_economy=["Stocks fall behind<br>the economy,<br>and stay behind",
                   "Stocks fall<br>behind the<br>economy, and<br>stay behind"],
    arrow_parity=["US stocks pull ahead,<br>and stay ahead",
                  "US stocks<br>pull ahead, and<br>stay ahead",
                  "US stocks<br>pull ahead,<br>and stay<br>ahead"],
)
_LAYOUTS = dict(
    wide=dict(
        margin=dict(l=54, r=34, t=44, b=26), margin_t_bare=12, px_per_nat=90, gap=18, font=12.5,
        gdp_width=2.5, stock_width=1.8, economy_width=1.7, modebar=True,
        strip=dict(fonts=[11.5, 10.5, 9.5], row=20), arrow_fonts=[11.5, 10.5, 9.5], mark_frac=0.46, head=dict(title=15, sub=11.5),
        labels=dict(
            famine=dict(size=10.5),
            note_none=dict(size=11, text="No Chinese<br>stock exchange"),
            note_open=dict(size=10.5, text="Exchanges<br>open; index<br>data begin<br>Dec 1998"),
            note_both=dict(show=False),
            zero=dict(size=11), zero_up=dict(size=10), zero_down=dict(size=10),
        )),
    narrow=dict(
        margin=dict(l=46, r=10, t=40, b=24), margin_t_bare=10, px_per_nat=70, gap=16, font=11,
        gdp_width=2.2, stock_width=1.4, economy_width=1.4, modebar=False,
        strip=dict(fonts=[10, 9], row=18), arrow_fonts=[10, 9], mark_frac=0.5, head=dict(title=13.5, sub=10),
        labels=dict(
            famine=dict(size=9.5),
            note_none=dict(show=False), note_open=dict(show=False),
            note_both=dict(size=9.5, text="No Chinese stock exchange<br>until Dec 1990; index data<br>begin Dec 1998"),
            zero=dict(size=10), zero_up=dict(show=False), zero_down=dict(show=False),
        )),
)
# How each annotation role is coloured -- "ink" is re-read from the page for
# dark mode, ``alpha`` makes the faint ones faint -- and whether it sits on
# a patch of page colour that masks the event lines behind it. (The faintness
# is in the text colour, not the annotation's opacity, so the patch stays
# opaque.)
_STYLES = dict(
    famine=dict(color="ink", alpha=0.6),
    note_none=dict(color="ink", alpha=0.55, mask=True), note_open=dict(color="ink", alpha=0.55, mask=True),
    note_both=dict(color="ink", alpha=0.55, mask=True),
    zero=dict(color="ink", alpha=0.85, mask=True),
    zero_up=dict(color="ink", alpha=0.5, mask=True), zero_down=dict(color="ink", alpha=0.5, mask=True),
    arrow_economy=dict(color="ink", alpha=0.9, arrow=True), arrow_parity=dict(color="ink", alpha=0.9, arrow=True),
)


def _text_color(name: str) -> str:
    style = _STYLES[name]
    return with_alpha(_INK, style["alpha"]) if "alpha" in style else _INK


def _geometry(layout: dict, top_span: float, bottom_span: float, top_margin: float | None = None) -> dict:
    """Figure height and the two y-domains that give both panels one scale.

    Each panel is ``px_per_nat`` times its y-span tall, with ``gap`` pixels
    between them; the domains are those heights as fractions of the plot area.
    The script's ``geometry`` is the same arithmetic.
    """
    ppn, gap, m = layout["px_per_nat"], layout["gap"], layout["margin"]
    top_h, bottom_h = ppn * top_span, ppn * bottom_span
    plot_h = top_h + gap + bottom_h
    t = m["t"] if top_margin is None else top_margin
    return dict(height=round(plot_h + t + m["b"]), plot_h=plot_h,
                top=[1 - top_h / plot_h, 1.0], bottom=[0.0, bottom_h / plot_h])


def _widest_gap(lo: pd.Timestamp, hi: pd.Timestamp, lines: list[pd.Timestamp]) -> pd.Timestamp:
    """The middle of the widest stretch of [lo, hi] that no event line crosses."""
    edges = [lo] + sorted(d for d in lines if lo < d < hi) + [hi]
    a, b = max(zip(edges, edges[1:]), key=lambda ab: ab[1] - ab[0])
    return a + (b - a) / 2


# --------------------------------------------------------------------------- #
#  The figure
# --------------------------------------------------------------------------- #
def build_china_figure(
    start_year: int = START_YEAR,
    show_multiple: bool = SHOW_MULTIPLE,
    tiers: tuple[int, ...] = (1,),
    peers: tuple[str, ...] = (),
) -> go.Figure:
    """Assemble the figure in its default state: the completed chart.

    Traces, top panel then bottom, each always present and only ever restyled
    (``layout.meta.trace`` names their positions): any peer-country lines, the
    economy line and its playback head; the two fills, the re-anchored economy
    line, the stock line and its head, and the numbered markers used when the
    arrowed annotations become a key.

    Everything else is a layout shape or annotation, so that it follows the
    data under zoom and during playback: the famine band, the zero line, one
    dashed line and one strip label per event, the notes in the bottom panel,
    and the two arrowed annotations. ``layout.meta.items`` lists every one with
    the date from which it is shown. (The panels' titles are not in the figure
    at all: they are HTML, added by :func:`china_figure_html`.)

    Parameters
    ----------
    start_year
        First GDP year drawn. Must precede the stock anchor.
    show_multiple
        Append the multiple ``e^x`` to each nat value in the hover box.
    tiers
        Which event tiers to draw. This round draws tier 1 only.
    peers
        Entity codes to draw as grey lines in the top panel, each re-based to
        ``GDP_ANCHOR_YEAR`` like China's. Empty this round.

    Returns
    -------
    go.Figure
        Built at the wide layout; the script re-fits it to the column.
    """
    gdp, s_all = load_derived()
    g_full = rebased(gdp, "CHN")
    g = g_full[g_full.index.year >= start_year]
    assert g.index[0] < STOCK_ANCHOR and len(g) >= 2, "start_year must precede the stock anchor"
    cutoff = common_cutoff(g, s_all)
    s = s_all[:cutoff]
    e = economy_since_anchor(g_full, s.index)
    fell_behind_economy = last_fall_below(s, e)
    fell_behind_parity = last_fall_below(s, 0.0)

    # Plain lists, not arrays: plotly.py would base64-encode arrays, and the
    # figure JSON should stay readable (and auditable for stray index levels).
    gdp_x, gdp_y = [_iso(d) for d in g.index], [float(v) for v in g]
    month_x = [_iso(d) for d in s.index]
    stock_y, economy_y = [float(v) for v in s], [float(v) for v in e]

    first = pd.Timestamp(year=start_year, month=1, day=1)
    x_range = [_iso(first), _iso(first + (cutoff - first) * (1 + WINDOW_MARGIN))]
    y_top = [round(min(gdp_y) - 0.15, 2), round(max(gdp_y) + 0.15, 2)]
    # A little more room under the stock line than above the economy line: the
    # two arrowed annotations stand there, up to four lines deep.
    y_bottom = [round(min(stock_y + economy_y) - 0.3, 2), round(max(stock_y + economy_y) + 0.2, 2)]

    wide = _LAYOUTS["wide"]
    geo = _geometry(wide, y_top[1] - y_top[0], y_bottom[1] - y_bottom[0])
    quiet = dict(hoverinfo="skip", showlegend=False)             # Plotly never labels a point
    top, bottom = dict(xaxis="x", yaxis="y"), dict(xaxis="x", yaxis="y2")

    # ---- Traces ----
    fig = go.Figure()
    for code in peers:
        peer = rebased(gdp, code)
        peer = peer[peer.index.year >= start_year]
        fig.add_trace(go.Scatter(x=[_iso(d) for d in peer.index], y=[float(v) for v in peer],
                                 mode="lines", name=f"peer {code}",
                                 line=dict(color=_PEER_COLOR, width=1.2), **top, **quiet))
    fig.add_trace(go.Scatter(x=gdp_x, y=gdp_y, mode="lines", name="gdp",
                             line=dict(color=_GDP_COLOR, width=wide["gdp_width"]), **top, **quiet))
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="gdp_head", cliponaxis=False,
                             marker=dict(size=9, color=_GDP_COLOR, line=dict(color=PAPER, width=1.5)),
                             **top, **quiet))

    t_ms = np.asarray(pd.DatetimeIndex(s.index).as_unit("ms").asi8, dtype=float)
    runs = fill_polygons(t_ms, np.array(stock_y), np.array(economy_y))
    for side, color in (("behind", _FILL_BEHIND), ("ahead", _FILL_AHEAD)):
        xs, ys = [], []
        for run_t, run_s, run_e in runs[side]:
            stamps = [pd.Timestamp(float(v), unit="ms").strftime("%Y-%m-%d %H:%M:%S") for v in run_t]
            xs += stamps + stamps[::-1] + [None]
            ys += [float(v) for v in run_s] + [float(v) for v in run_e[::-1]] + [None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=f"fill_{side}", fill="toself", fillcolor=color,
                                 line=dict(width=0), **bottom, **quiet))
    fig.add_trace(go.Scatter(x=month_x, y=economy_y, mode="lines", name="economy",
                             line=dict(color=_GDP_COLOR, width=wide["economy_width"]), **bottom, **quiet))
    fig.add_trace(go.Scatter(x=month_x, y=stock_y, mode="lines", name="stock",
                             line=dict(color=_STOCK_COLOR, width=wide["stock_width"]), **bottom, **quiet))
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="stock_head", cliponaxis=False,
                             marker=dict(size=9, color=_STOCK_COLOR, line=dict(color=PAPER, width=1.5)),
                             **bottom, **quiet))
    # Numbered markers: empty unless the arrowed annotations fall back to a key.
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers+text", name="markers", text=["1", "2"],
                             textposition="middle center", textfont=dict(size=9, color=PAPER),
                             marker=dict(size=14, color=_INK, line=dict(color=PAPER, width=1)),
                             cliponaxis=False, **bottom, **quiet))
    names = [t.name for t in fig.data]
    trace = {n: names.index(n) for n in ("gdp", "gdp_head", "fill_behind", "fill_ahead", "economy",
                                         "stock", "stock_head", "markers")}
    trace["peers"] = [i for i, n in enumerate(names) if n.startswith("peer ")]

    # ---- Shapes and annotations, registered as they are added ----
    shapes, annotations, items, role, shape_role = [], [], [], {}, {}

    def shape(name: str | None, date=None, opacity: float = 1.0, **kw) -> int:
        shapes.append(dict(opacity=opacity, **kw))
        items.append(dict(kind="shape", index=len(shapes) - 1, date=date, opacity=opacity))
        if name:
            shape_role[name] = len(shapes) - 1
        return len(shapes) - 1

    def note(name: str | None, date=None, **kw) -> int:
        kw.setdefault("showarrow", False)
        annotations.append(kw)
        items.append(dict(kind="annotation", index=len(annotations) - 1, date=date, opacity=1.0))
        if name:
            role[name] = len(annotations) - 1
        return len(annotations) - 1

    labels = wide["labels"]

    def font(name: str) -> dict:
        return dict(size=labels[name]["size"], color=_text_color(name))

    # Top panel: the famine band.
    famine_end = pd.Timestamp(year=start_year + 2, month=12, day=31)
    shape("famine", type="rect", xref="x", yref="y domain", x0=x_range[0], x1=_iso(famine_end),
          y0=0, y1=1, fillcolor=_FAMINE_FILL, line=dict(width=0), layer="below")
    note("famine", xref="x", yref="y domain", x=_iso(first + (famine_end - first) / 2), y=0.42,
         text="Famine", textangle=-90, font=font("famine"))
    # Bottom panel before the index data begin: no lines, only a note saying why.
    drawn = [ev for ev in EVENTS if ev.tier in tiers and x_range[0] <= ev.date <= _iso(cutoff)]
    lines = [pd.Timestamp(ev.date) for ev in drawn]
    opened = pd.Timestamp("1990-12-19")                     # the Shanghai exchange
    # Each has a home date -- the middle of the widest stretch of its period
    # that no event line crosses -- where it sits on the finished chart. During
    # playback the script holds it back inside the growing window until its
    # home comes into view, so the panel is never left empty without a reason.
    faint = dict(xref="x", yref="y2", align="center", bgcolor=PAPER, borderpad=2)
    both = _LAYOUTS["narrow"]["labels"]["note_both"]
    homes = dict(note_none=_iso(_widest_gap(first, opened, lines)),
                 note_open=_iso(_widest_gap(opened, STOCK_ANCHOR, lines)),
                 note_both=_iso(first + (STOCK_ANCHOR - first) * 0.47))
    note("note_none", x=homes["note_none"], y=0.55,
         text=labels["note_none"]["text"], font=font("note_none"), **faint)
    note("note_open", date=_iso(opened), x=homes["note_open"], y=0.85,
         text=labels["note_open"]["text"], font=font("note_open"), **faint)
    note("note_both", visible=False, x=homes["note_both"], y=0.5, text=both["text"],
         font=dict(size=both["size"], color=_text_color("note_both")), **faint)

    # The zero line -- parity between Chinese and US stocks -- from where the
    # index data begin, labelled at its start.
    anchor = _iso(STOCK_ANCHOR)
    shape("zero_line", date=anchor, type="line", xref="x", yref="y2", x0=anchor, x1=x_range[1], y0=0, y1=0,
          line=dict(color=_INK, width=1.2), layer="below")
    at_zero = dict(xref="x", yref="y2", x=anchor, y=0, xanchor="right", xshift=-6, bgcolor=PAPER, borderpad=1)
    note("zero", date=anchor, yanchor="middle", text="China = US", font=font("zero"), **at_zero)
    note("zero_up", date=anchor, yanchor="bottom", yshift=11, text="China ahead", font=font("zero_up"), **at_zero)
    note("zero_down", date=anchor, yanchor="top", yshift=-11, text="US ahead", font=font("zero_down"), **at_zero)

    # The two arrowed annotations, dated from the data. The script decides
    # where each text box goes (ax, ay and the line breaks) for the real width.
    arrows = []
    for name, when in (("arrow_economy", fell_behind_economy), ("arrow_parity", fell_behind_parity)):
        note(name, date=_iso(when), xref="x", yref="y2", x=_iso(when), y=float(s[when]),
             text=_ARROW_WRAPS[name][0], showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1,
             arrowcolor=_text_color(name), standoff=3, ax=-70, ay=70, align="center",
             font=dict(size=wide["arrow_fonts"][0], color=_text_color(name)))
        arrows.append(dict(role=name, date=_iso(when), month=_month(when), text=_ARROW_TEXT[name]))

    # Events: a dashed line through both panels and a label in the strip above.
    # The script assigns each label a row and a side from its measured width.
    events = []
    for i, ev in enumerate(drawn):
        row = i % 2
        line = shape(None, date=ev.date, opacity=_EVENT_LINE_OPACITY, type="line", xref="x", yref="paper",
                     x0=ev.date, x1=ev.date, y0=0, y1=1 + (2 + row * wide["strip"]["row"]) / geo["plot_h"],
                     line=dict(color=_INK, width=1, dash="dash"), layer="below")
        label = note(None, date=ev.date, xref="x", yref="y domain", x=ev.date, y=1,
                     yanchor="bottom", yshift=3 + row * wide["strip"]["row"], text=ev.label,
                     font=dict(size=wide["strip"]["fonts"][0], color=with_alpha(_INK, _EVENT_LABEL_ALPHA)))
        events.append(dict(date=ev.date, tier=ev.tier, label=ev.label, description=ev.description,
                           narration_text=ev.narration_text, image=ev.image, shape=line, annotation=label))

    # ---- Axes: one y-axis per panel, no titles, no tick marks ----
    def y_axis(domain, y_range):
        ticks = list(range(int(np.ceil(y_range[0])), int(np.floor(y_range[1])) + 1))
        halves = np.arange(np.ceil(y_range[0] - 0.5) + 0.5, y_range[1], 1.0)
        unit = " nat" if ticks[-1] == 1 else " nats"
        return dict(domain=domain, range=y_range, fixedrange=True, anchor="x", automargin=False,
                    tickvals=ticks, ticktext=[_signed(v, unit if v == ticks[-1] else "") for v in ticks],
                    ticks="", tickfont=dict(color=LABEL), gridcolor=GRID, zeroline=False,
                    minor=dict(tickvals=[float(h) for h in halves], showgrid=True, ticks="",
                               gridcolor=with_alpha(LABEL, 0.07)))

    moments = lines + [STOCK_ANCHOR, fell_behind_economy, fell_behind_parity]
    start, end = g.index[1], cutoff
    fig.update_layout(
        # No width: the graph div fills its container until fit() sizes it.
        autosize=True, height=geo["height"], margin=wide["margin"], font=dict(size=wide["font"]),
        # Transparent, so the page shows through in light and dark mode alike.
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hovermode=False, dragmode="zoom", showlegend=False, modebar=dict(orientation="v"),
        xaxis=dict(type="date", range=x_range, minallowed=x_range[0], maxallowed=x_range[1], anchor="y2",
                   showgrid=False, showline=True, linecolor=with_alpha(LABEL, 0.5), ticks="",
                   tickfont=dict(color=LABEL), automargin=False,
                   tickformatstops=[dict(dtickrange=[None, "M11"], value="%b %Y"),
                                    dict(dtickrange=["M12", None], value="%Y")]),
        yaxis=y_axis(geo["top"], y_top),
        yaxis2=y_axis(geo["bottom"], y_bottom),
        shapes=shapes, annotations=annotations,
        meta=dict(
            trace=trace, ann=role, shape=shape_role, items=items, styles=_STYLES, events=events,
            event_label_alpha=_EVENT_LABEL_ALPHA, arrows=arrows, arrow_wraps=_ARROW_WRAPS, anchor=anchor,
            note_homes=homes,
            hover=dict(
                gdp=[f"Economy ({d.year}): {_nats(v, show_multiple)}" for d, v in g.items()],
                stock=[f"Stocks ({_month(d)}): {_nats(v, show_multiple)}" for d, v in s.items()],
                economy=[f"Economy ({_month(d)}): {_nats(v, show_multiple)}" for d, v in e.items()],
            ),
            # Playback opens on the first segment (two GDP points), not a lone point.
            play=dict(start=_iso(start), end=_iso(end), fade_years=_FADE_YEARS,
                      min_window_years=MIN_WINDOW_YEARS, margin=WINDOW_MARGIN,
                      seconds_per_year=[round(float(v), 4) for v in pace_profile(moments, start, end)]),
            view=dict(x=x_range, y=y_top, y2=y_bottom),
            layouts=_LAYOUTS, narrow_below=_NARROW_BELOW_PX,
            light=dict(ink=_INK, label=LABEL, grid=GRID, minor=with_alpha(LABEL, 0.07), paper=PAPER,
                       behind=_FILL_BEHIND, famine=_FAMINE_FILL, axis=with_alpha(LABEL, 0.5)),
        ),
    )
    return fig


# --------------------------------------------------------------------------- #
#  The embeddable HTML: figure, overlays, controls, and the script
# --------------------------------------------------------------------------- #
_DIV_ID = "china-figure"

_MARKUP = """<div class="china-fig-wrap">
<div class="china-year-mark" aria-hidden="true"></div>
__FIG__
<div class="china-head china-head-top">
  <div class="china-head-title">Economy</div>
  <div class="china-head-sub">__SUB_TOP__</div>
</div>
<div class="china-head china-head-bottom">
  <div class="china-head-title">Stocks</div>
  <div class="china-head-sub">__SUB_BOTTOM__</div>
</div>
<div class="china-overlay" aria-hidden="true">
  <div class="china-guide"></div>
  <div class="china-dot china-dot-gdp"></div>
  <div class="china-dot china-dot-economy"></div>
  <div class="china-dot china-dot-stock"></div>
  <div class="china-tip"></div>
</div>
</div>
<div class="china-key" hidden></div>
<div class="china-controls">
  <button type="button" class="china-play" aria-label="Play the animation" title="Play">
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <path class="china-ico-play" d="M4.5 2.4v11.2L13.4 8z"/>
      <path class="china-ico-pause" d="M3.6 2.6h3v10.8h-3zM9.4 2.6h3v10.8h-3z"/>
    </svg>
  </button>
  <div class="china-scrub-wrap">
    <input type="range" class="china-scrub" min="0" max="2000" step="1" value="2000"
      aria-label="Move through time">
  </div>
  <output class="china-year"></output>
</div>
"""

_STYLE = """<style>
/* The figure lives in a position:relative wrapper whose width fit() sets. The
   overlay is a SIBLING of the graph div (Plotly owns that div's children) and
   lets every click and drag through to the plot. */
.china-fig-wrap { position: relative; margin: 0 auto; }
.china-fig-wrap .js-plotly-plot { position: relative; z-index: 1; }
.china-fig-wrap.is-narrow .modebar-container { display: none !important; }
/* The year watermark sits BEHIND the plot, whose background is transparent, so
   the data draws over it. Page colour at low opacity: faint in either theme. */
.china-year-mark { position: absolute; left: 0; top: 0; z-index: 0; display: none; pointer-events: none;
  transform: translate(-50%, -50%); line-height: 1; font-weight: 700; letter-spacing: .02em;
  font-variant-numeric: tabular-nums lining-nums; color: var(--bs-body-color, #1f2328); opacity: .075; }
/* Each panel's title and subtitle, top-left. The halo (text-shadow in the page
   colour, all round) erases the event lines and gridlines behind the letters,
   the cartographic treatment, so the text never looks crossed. */
.china-head { position: absolute; left: 0; top: 0; z-index: 2; pointer-events: none; text-align: left;
  line-height: 1.3; --halo: var(--bs-body-bg, #fff);
  text-shadow: -1.5px 0 var(--halo), 1.5px 0 var(--halo), 0 -1.5px var(--halo), 0 1.5px var(--halo),
    -1.1px -1.1px var(--halo), 1.1px -1.1px var(--halo), -1.1px 1.1px var(--halo), 1.1px 1.1px var(--halo); }
.china-head-title { font-weight: 700; }
.china-head-top .china-head-title { color: __GDP__; }
.china-head-bottom .china-head-title { color: __STOCK__; }
.china-head-sub { color: var(--china-label, #5b5f66); }
.china-overlay { position: absolute; inset: 0; z-index: 3; pointer-events: none; overflow: hidden; }
.china-guide { position: absolute; left: 0; top: 0; width: 1px; display: none;
  background: var(--bs-body-color, #1f2328); opacity: .28; }
.china-dot { position: absolute; left: -4.5px; top: -4.5px; width: 9px; height: 9px; display: none;
  box-sizing: border-box; border-radius: 50%; border: 1.5px solid var(--bs-body-bg, #fff); }
.china-dot-gdp, .china-dot-economy { background: __GDP__; }
.china-dot-stock { background: __STOCK__; }
/* Page colours throughout, so the box follows the site's dark mode. */
.china-tip { position: absolute; left: 0; top: 0; display: none; max-width: 260px;
  padding: 6px 9px; border-radius: 4px; font-size: 13px; line-height: 1.45; text-align: left;
  color: var(--bs-body-color, #1f2328); background: var(--bs-body-bg, #fff);
  border: 1px solid var(--bs-border-color, #cfd3d8); box-shadow: 0 2px 8px rgba(0, 0, 0, .14); }
.china-tip-row { white-space: nowrap; }
.china-tip-key { display: inline-block; width: 9px; height: 9px; margin-right: 6px; border-radius: 50%; }
.china-tip-gdp .china-tip-key, .china-tip-economy .china-tip-key { background: __GDP__; }
.china-tip-stock .china-tip-key { background: __STOCK__; }
.china-tip-event { margin-bottom: 4px; padding-bottom: 4px; font-size: 12px; line-height: 1.35;
  border-bottom: 1px solid var(--bs-border-color, #cfd3d8); }
.china-tip-event:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: 0; }
/* The key: where the two arrowed annotations go when there is no room for
   them beside the data (a phone). Numbered to match the markers on the line. */
.china-key { box-sizing: border-box; margin: .1rem auto .35rem; padding: 0 8px; font-size: 12px; line-height: 1.35;
  text-align: left; color: var(--bs-body-color, #1f2328); }
.china-key[hidden] { display: none; }
.china-key-row { display: flex; align-items: baseline; gap: 7px; margin: 3px 0; }
.china-key-n { flex: none; width: 15px; height: 15px; border-radius: 50%; font-size: 9.5px; line-height: 15px;
  text-align: center; background: var(--bs-body-color, #1f2328); color: var(--bs-body-bg, #fff); }
/* Controls. */
.china-controls { --thumb-d: 12.5px; display: flex; align-items: center; gap: 14px; margin: .15rem auto 1.3rem;
  box-sizing: border-box; padding: 0 6px; }
.china-play { flex: none; width: 28px; height: 28px; padding: 0;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
  border-radius: 50%; border: 1px solid var(--bs-border-color, #cfd3d8);
  background: transparent; color: var(--bs-body-color, #1f2328); }
.china-play:hover { border-color: var(--bs-body-color, #1f2328); }
.china-play:focus-visible, .china-scrub:focus-visible { outline: 2px solid __STOCK__; outline-offset: 2px; }
.china-play svg { fill: currentColor; }
.china-play .china-ico-pause, .china-play.is-playing .china-ico-play { display: none; }
.china-play.is-playing .china-ico-pause { display: inline; }
.china-year { flex: none; min-width: 2.4em; font-size: 13px; line-height: 1;
  font-variant-numeric: tabular-nums; color: var(--bs-body-color, #1f2328); }
.china-scrub-wrap { position: relative; flex: 1 1 auto; height: 28px; line-height: 0; margin: 0 6px; }
.china-scrub-wrap::before, .china-scrub-wrap::after { content: ""; position: absolute; left: 0; top: 50%;
  height: 3px; border-radius: 2px; transform: translateY(-50%); }
.china-scrub-wrap::before { width: 100%; background: var(--bs-border-color, #cfd3d8); }
.china-scrub-wrap::after { width: var(--china-p, 100%); background: var(--bs-body-color, #1f2328); opacity: .5; }
/* A range thumb's centre travels from d/2 to W - d/2. The input overhangs the
   track by d/2 on each side, so the centre runs the track's full width. */
.china-scrub { -webkit-appearance: none; appearance: none; position: absolute; z-index: 1;
  left: calc(var(--thumb-d) / -2); top: 50%; width: calc(100% + var(--thumb-d)); height: 28px;
  transform: translateY(-50%); margin: 0; background: transparent; outline: none; cursor: pointer; }
.china-scrub::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; box-sizing: border-box;
  width: var(--thumb-d); height: var(--thumb-d); border-radius: 50%;
  background: var(--bs-body-color, #1f2328); border: 1.5px solid var(--bs-body-bg, #fff); }
.china-scrub::-moz-range-thumb { box-sizing: border-box; width: var(--thumb-d); height: var(--thumb-d);
  border-radius: 50%; background: var(--bs-body-color, #1f2328); border: 1.5px solid var(--bs-body-bg, #fff); }
.china-scrub::-moz-range-track { background: transparent; }
</style>
"""

# Plain string, not an f-string: the only substitution is the div id.
_SCRIPT = r"""<script>
(function () {
  var gd = document.getElementById("__DIV__");
  if (!gd) return;
  var wrap = gd.closest(".china-fig-wrap"), scope = wrap.parentNode;
  function $(sel) { return scope.querySelector(sel); }
  var controls = $(".china-controls"), playBtn = $(".china-play"), scrub = $(".china-scrub");
  var scrubWrap = $(".china-scrub-wrap"), yearOut = $(".china-year"), keyBox = $(".china-key");
  var mark = $(".china-year-mark"), guide = $(".china-guide"), tip = $(".china-tip");
  var heads = [$(".china-head-top"), $(".china-head-bottom")];
  var dotEl = {gdp: $(".china-dot-gdp"), stock: $(".china-dot-stock"), economy: $(".china-dot-economy")};
  var DAY = 86400000, YEAR = 31557600000;          // ms
  var PL, M, TR, AN, G, S, PEERS, EV, ITEMS, ARROWS, TAU, NP, TOTAL, T0, T1, TA, X0, X1, FONT;
  var L = null, GEO = null, P = null, lastW = 0, stripOn = true, keyMode = false, enabled = {};
  var playhead = 0, playing = false, raf = 0, busy = false, pending = null;
  var syncing = false, dragging = false, down = null, themeKey = "";

  // Plotly reads a date string as wall-clock time with no zone, i.e. as UTC ms.
  function toMs(d) {
    d = String(d);
    if (d.length > 10) return Date.parse(d.replace(" ", "T") + "Z");
    var p = d.split("-");
    return Date.UTC(+p[0], p[1] - 1, +p[2]);
  }
  function iso(ms) { return new Date(ms).toISOString().replace("T", " ").slice(0, 23); }
  function last(a) { return a[a.length - 1]; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  // Number of entries of the sorted array t that are <= T.
  function upper(t, T) {
    var lo = 0, hi = t.length;
    while (lo < hi) { var mid = (lo + hi) >> 1; if (t[mid] <= T) lo = mid + 1; else hi = mid; }
    return lo;
  }
  // Linear interpolation of the series (t, y) at T; null outside it.
  function at(t, y, T) {
    var n = upper(t, T);
    if (n === 0 || T > last(t)) return null;
    if (n === t.length) return y[n - 1];
    return y[n - 1] + (T - t[n - 1]) / (t[n] - t[n - 1]) * (y[n] - y[n - 1]);
  }

  // ---- The revealed part of the lines at playhead T -------------------------------
  // Every actual point up to T, then one point AT T, interpolated linearly. That
  // last point is for display only: it goes into line traces (hoverinfo "skip")
  // and never into the hover data.
  function reveal(D, T) {
    var n = upper(D.t, T), x = D.x.slice(0, n), y = D.y.slice(0, n);
    if (n > 0 && n < D.t.length && T > D.t[n - 1]) { x.push(iso(T)); y.push(at(D.t, D.y, T)); }
    return {x: x, y: y};
  }
  // The stock line and the re-anchored economy line share one grid of month-ends.
  function revealPair(T) {
    var n = upper(S.t, T), p = {t: S.t.slice(0, n), x: S.x.slice(0, n), s: S.s.slice(0, n), e: S.e.slice(0, n)};
    if (n > 0 && n < S.t.length && T > S.t[n - 1]) {
      p.t.push(T); p.x.push(iso(T)); p.s.push(at(S.t, S.s, T)); p.e.push(at(S.t, S.e, T));
    }
    return p;
  }
  // The area between them, split into runs of one sign at the exact crossings.
  // The same walk as fill_polygons() in the Python module.
  function fills(p) {
    var out = {ahead: {x: [], y: []}, behind: {x: [], y: []}}, n = p.t.length;
    if (n < 2) return out;
    var run = [[p.t[0], p.s[0], p.e[0]]];
    function flush() {
      var sum = 0, k;
      for (k = 0; k < run.length; k++) sum += run[k][1] - run[k][2];
      if (run.length < 2 || sum === 0) return;
      var o = sum > 0 ? out.ahead : out.behind;
      for (k = 0; k < run.length; k++) { o.x.push(iso(run[k][0])); o.y.push(run[k][1]); }
      for (k = run.length - 1; k >= 0; k--) { o.x.push(iso(run[k][0])); o.y.push(run[k][2]); }
      o.x.push(null); o.y.push(null);
    }
    for (var i = 1; i < n; i++) {
      var d0 = p.s[i - 1] - p.e[i - 1], d1 = p.s[i] - p.e[i];
      if (d0 * d1 < 0) {
        var f = d0 / (d0 - d1), tc = p.t[i - 1] + f * (p.t[i] - p.t[i - 1]);
        var yc = p.s[i - 1] + f * (p.s[i] - p.s[i - 1]);
        run.push([tc, yc, yc]); flush(); run = [[tc, yc, yc]];
      } else if (d0 === 0 && run.length > 1) {
        flush(); run = [[p.t[i - 1], p.s[i - 1], p.e[i - 1]]];
      }
      run.push([p.t[i], p.s[i], p.e[i]]);
    }
    flush();
    return out;
  }

  // ---- Pacing: playback seconds <-> playhead date ---------------------------------
  function tauOf(T) {
    var u = clamp((T - T0) / (T1 - T0), 0, 1) * NP, i = Math.min(NP - 1, Math.floor(u));
    return TAU[i] + (u - i) * (TAU[i + 1] - TAU[i]);
  }
  function timeOf(tau) {
    if (tau <= 0) return T0;
    if (tau >= TOTAL) return T1;
    var j = upper(TAU, tau) - 1;
    return T0 + (j + (tau - TAU[j]) / (TAU[j + 1] - TAU[j])) / NP * (T1 - T0);
  }
  // The growing x-axis: from the start to a little past the playhead, never
  // narrower than the minimum window.
  function windowEnd(T) {
    return Math.max(X0 + M.play.min_window_years * YEAR, X0 + (T - X0) * (1 + M.play.margin));
  }

  // ---- Everything timed fades in as a pure function of the playhead ---------------
  // Phase 2 hook: a zoom-dependent rule for tier-2 events belongs here.
  function alphaAt(t, T) {
    if (t === null || T >= T1) return 1;
    return clamp((T - t) / (M.play.fade_years * YEAR), 0, 1);
  }
  function itemsPatch(T, force) {
    var patch = {};
    ITEMS.forEach(function (it) {
      var on = it.kind === "shape" || enabled[it.index] !== false;
      var a = on ? alphaAt(it.t, T) : 0;
      if (!force && Math.abs(a - it.alpha) < 1e-3) return;
      it.alpha = a;
      var key = (it.kind === "shape" ? "shapes[" : "annotations[") + it.index + "]";
      patch[key + ".visible"] = a > 0;
      patch[key + ".opacity"] = a * it.opacity;
    });
    return patch;
  }
  // The notes in the empty part of the bottom panel: at home on the finished
  // chart; during playback held back inside the growing window until home is in view.
  function notesPatch(T) {
    var patch = {}, end = T >= T1 ? X1 : windowEnd(T), scale = GEO.plotW / (end - X0);
    Object.keys(M.note_homes).forEach(function (role) {
      var spec = L.labels[role], home = toMs(M.note_homes[role]);
      if (spec.show === false) return;
      var half = textSize(spec.text, spec.size).w / 2 + 12;
      patch["annotations[" + AN[role] + "].x"] = iso(T >= T1 ? home : Math.min(home, end - half / scale));
    });
    return patch;
  }
  function markersAt(T) {
    var shown = keyMode ? ARROWS.filter(function (a) { return a.t <= T; }) : [];
    return {x: shown.map(function (a) { return a.date; }), y: shown.map(function (a) { return a.y; })};
  }

  // ---- Draw the chart as of playhead T: one Plotly.update, all traces --------------
  function render(T) {
    T = clamp(T, T0, T1);
    if (busy) { pending = T; return; }
    playhead = T;
    var done = T >= T1, data = {x: [], y: []}, idx = [];
    function put(i, x, y) { idx.push(i); data.x.push(x); data.y.push(y); }
    var g = reveal(G, T), p = revealPair(T), f = fills(p), mk = markersAt(T), live = !done;
    PEERS.forEach(function (D) { var r = reveal(D, T); put(D.trace, r.x, r.y); });
    put(TR.gdp, g.x, g.y);
    put(TR.gdp_head, live ? [last(g.x)] : [], live ? [last(g.y)] : []);
    put(TR.fill_behind, f.behind.x, f.behind.y);
    put(TR.fill_ahead, f.ahead.x, f.ahead.y);
    put(TR.economy, p.x, p.e);
    put(TR.stock, p.x, p.s);
    put(TR.stock_head, live && p.x.length ? [last(p.x)] : [], live && p.x.length ? [last(p.s)] : []);
    put(TR.markers, mk.x, mk.y);
    var layout = itemsPatch(T, false), where = notesPatch(T);
    for (var key in where) layout[key] = where[key];
    // The x-range follows the playhead, which also undoes any zoom.
    layout["xaxis.range"] = [M.view.x[0], done ? M.view.x[1] : iso(windowEnd(T))];
    syncControls();
    hideTip();
    busy = true;
    function freed() { busy = false; if (pending !== null) { var q = pending; pending = null; render(q); } }
    Promise.resolve(PL.update(gd, data, layout, idx)).then(freed, freed);
  }
  function syncControls() {
    var f = tauOf(playhead) / TOTAL, year = new Date(playhead).getUTCFullYear(), done = playhead >= T1;
    scrub.value = Math.round(f * scrub.max);
    scrubWrap.style.setProperty("--china-p", (100 * f).toFixed(2) + "%");
    yearOut.textContent = year;
    mark.textContent = year;
    mark.style.display = done ? "none" : "block";      // the watermark is for playback only
    Array.prototype.forEach.call(keyBox.children, function (row, i) {
      row.style.opacity = alphaAt(ARROWS[i].t, playhead);
    });
  }

  // ---- Playback -------------------------------------------------------------------
  function reducedMotion() { return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }
  function setPlaying(on) {
    playing = on;
    playBtn.classList.toggle("is-playing", on);
    playBtn.title = on ? "Pause" : "Play";
    playBtn.setAttribute("aria-label", on ? "Pause the animation" : "Play the animation");
  }
  function pause() { if (playing) { setPlaying(false); cancelAnimationFrame(raf); } }
  function play() {
    if (reducedMotion()) { render(T1); return; }   // reduced motion: straight to the finished chart
    var tau = playhead >= T1 ? 0 : tauOf(playhead), prev = null;
    setPlaying(true);
    render(timeOf(tau));
    function step(now) {
      if (!playing) return;
      // Advance by wall-clock time, capped so a backgrounded tab resumes, not jumps.
      if (prev !== null) tau += Math.min(now - prev, 100) / 1000;
      prev = now;
      if (tau >= TOTAL) { setPlaying(false); render(T1); return; }
      if (!busy) render(timeOf(tau));
      raf = requestAnimationFrame(step);
    }
    raf = requestAnimationFrame(step);
  }

  // ---- The x-axis after a zoom, pan, autoscale or reset ---------------------------
  // The y-axes are fixed (that is what keeps one vertical scale), so only x can
  // change. An autoranged axis would re-range on every animation frame without
  // telling us, so autorange is frozen into the explicit full view.
  function syncAxes() {
    if (syncing || !gd._fullLayout.xaxis.autorange) return;
    syncing = true;
    function freed() { syncing = false; }
    Promise.resolve(PL.relayout(gd, {"xaxis.range": M.view.x.slice()})).then(freed, freed);
  }

  // ---- Measured text ---------------------------------------------------------------
  var ctx = document.createElement("canvas").getContext("2d");
  function textSize(html, px, bold) {
    ctx.font = (bold ? "bold " : "") + px + "px " + FONT;
    var lines = String(html).replace(/<\/?b>/g, "").split("<br>"), w = 0;
    lines.forEach(function (ln) { w = Math.max(w, ctx.measureText(ln).width); });
    return {w: w, h: lines.length * px * 1.3};       // 1.3 is Plotly's line spacing
  }

  // ---- The event strip: a row and a side for every label ---------------------------
  // Each label goes in the lower or the upper row, centred on its line or to
  // one side of it. No two labels in a row may come within 8 px, and no label
  // may sit across another event's line where that line reaches it (a line
  // climbs to its own label's row). Taken in date order, all that matters about
  // the labels already placed is how far right each row extends and where the
  // last line into the upper row is, so the search is over those three numbers,
  // remembering the dead ends. It is done at the scale of the FINISHED chart:
  // playback and zooming only ever spread the lines further apart, so what fits
  // there fits throughout. Returns null if nothing fits (a narrow screen).
  function placeStrip(plotW, font) {
    var scale = plotW / (X1 - X0);
    var lo = -L.margin.l + 2, hi = plotW + L.margin.r - 2;
    var it = EV.map(function (e) { return {x: (e.t - X0) * scale, w: textSize(e.label, font).w + 4}; });
    var sides = ["center", "left", "right"], chosen = [], dead = {};
    function span(i, side) {
      var x = it[i].x, w = it[i].w;
      return side === "center" ? [x - w / 2, x + w / 2] : side === "left" ? [x + 3, x + 3 + w] : [x - 3 - w, x - 3];
    }
    function go(i, right0, right1, upperX) {
      if (i === it.length) return true;
      var key = i + "|" + right0.toFixed(1) + "|" + right1.toFixed(1) + "|" + upperX.toFixed(1);
      if (dead[key]) return false;
      var x = it[i].x, prevX = i ? it[i - 1].x : -1e9;
      for (var row = 0; row < 2; row++) for (var k = 0; k < 3; k++) {
        var s = span(i, sides[k]);
        if (s[0] < lo || s[1] > hi) continue;
        if (s[0] < (row ? right1 : right0) + 8) continue;           // too close to the label before it
        if (s[0] - 3 < (row ? upperX : prevX)) continue;            // an earlier line runs into this label
        if (x < right0 + 3 || (row && x < right1 + 3)) continue;    // this line runs into an earlier label
        chosen[i] = {row: row, side: sides[k]};
        if (go(i + 1, row ? right0 : Math.max(right0, s[1]), row ? Math.max(right1, s[1]) : right1, row ? x : upperX))
          return true;
      }
      dead[key] = true;
      return false;
    }
    return go(0, -1e9, -1e9, -1e9) ? chosen : null;
  }

  // ---- The two arrowed annotations: a box under the zero line, clear of the data ---
  // Each text box hangs just below the zero line, as near beneath its arrow tip
  // as it can get without touching the stock or economy line (or the tint
  // between them), an event line, the other box or the panel's edge. All at
  // the scale of the finished chart, for the reason given above. Returns null
  // if either cannot be placed at this font size.
  function placeArrows(font) {
    var scale = GEO.plotW / (X1 - X0), ppn = GEO.ppn, zeroY = M.view.y2[1] * ppn, c = 5;
    var top = zeroY + 10, left = (TA - X0) * scale + 6, right = GEO.plotW - 3, placed = [];
    function clear(a, b, H) {
      if (a < left || b > right || top + H > GEO.botH - 3) return false;
      var i, x;
      for (i = 0; i < EV.length; i++) { x = (EV[i].t - X0) * scale; if (x > a - c && x < b + c) return false; }
      for (i = 0; i < placed.length; i++) if (a < placed[i].b + 8 && placed[i].a < b + 8) return false;
      for (x = a - c; x <= b + c; x += 2) {
        var T = X0 + x / scale, s = at(S.t, S.s, T), e = at(S.t, S.e, T);
        if (s !== null && zeroY - Math.min(s, e) * ppn > top - c) return false;
      }
      return true;
    }
    for (var n = 0; n < ARROWS.length; n++) {
      var A = ARROWS[n], tipX = (A.t - X0) * scale, tipY = zeroY - A.y * ppn, found = null;
      var wraps = M.arrow_wraps[A.role];
      for (var k = 0; k < wraps.length && !found; k++) {
        var sz = textSize(wraps[k], font), W = sz.w + 6, H = sz.h + 4;
        for (var step = 0; step <= 120 && !found; step++) for (var sign = -1; sign <= 1 && !found; sign += 2) {
          var cx = tipX + sign * step * 3;
          if (clear(cx - W / 2, cx + W / 2, H))
            found = {a: cx - W / 2, b: cx + W / 2, text: wraps[k], ax: cx - tipX, ay: top + H / 2 - tipY};
        }
      }
      if (!found) return null;
      placed.push(found);
    }
    return placed;
  }

  // ---- Fit: fill the column, size the panels to one scale, place the text ----------
  function host() { return gd.closest(".cell-output-display") || scope; }
  // The same arithmetic as _geometry() in the Python module.
  function geometry(topMargin) {
    var spanT = M.view.y[1] - M.view.y[0], spanB = M.view.y2[1] - M.view.y2[0];
    var topH = L.px_per_nat * spanT, botH = L.px_per_nat * spanB, plotH = topH + L.gap + botH;
    var height = Math.round(plotH + topMargin + L.margin.b), k = (height - topMargin - L.margin.b) / plotH;
    return {t: topMargin, height: height, plotH: plotH * k, topH: topH * k, botH: botH * k, ppn: L.px_per_nat * k,
            top: [1 - topH / plotH, 1], bottom: [0, botH / plotH]};
  }
  function fit(force) {
    var w = Math.floor(host().clientWidth || gd.offsetWidth);
    if (!w) return setTimeout(fit, 30);
    if (w === lastW && force !== true) return;
    lastW = w;
    L = M.layouts[w < M.narrow_below ? "narrow" : "wide"];
    var plotW = w - L.margin.l - L.margin.r, strip = null, stripFont = 0;
    L.strip.fonts.forEach(function (f) { if (!strip) { strip = placeStrip(plotW, f); stripFont = f; } });
    stripOn = !!strip;
    GEO = geometry(stripOn ? L.margin.t : L.margin_t_bare);
    GEO.plotW = plotW;
    var patch = {width: w, height: GEO.height, autosize: false, "font.size": L.font,
      margin: {l: L.margin.l, r: L.margin.r, t: GEO.t, b: L.margin.b},
      "yaxis.domain": GEO.top, "yaxis2.domain": GEO.bottom};
    function set(i, props) { for (var key in props) patch["annotations[" + i + "]." + key] = props[key]; }

    // Per-layout text: sizes, wording, and which notes are shown at all.
    Object.keys(L.labels).forEach(function (role) {
      var spec = L.labels[role], i = AN[role];
      enabled[i] = spec.show !== false;
      if (spec.size) set(i, {"font.size": spec.size});
      if (spec.text) set(i, {text: spec.text});
    });
    // The strip: labels in their rows, and each line drawn up to its own label.
    EV.forEach(function (e, j) {
      var q = strip ? strip[j] : null;
      e.row = q ? q.row : 0;
      enabled[e.annotation] = stripOn;
      if (q) set(e.annotation, {"font.size": stripFont, yshift: 3 + e.row * L.strip.row,
        xanchor: q.side, xshift: q.side === "left" ? 3 : q.side === "right" ? -3 : 0});
      patch["shapes[" + e.shape + "].y1"] = 1 + (stripOn ? 2 + e.row * L.strip.row : 0) / GEO.plotH;
    });

    // The arrowed annotations: beside the data if they fit at some font size
    // (both at the same one), otherwise numbered markers and a key.
    var boxes = null, arrowFont = 0;
    L.arrow_fonts.forEach(function (f) { if (!boxes) { boxes = placeArrows(f); arrowFont = f; } });
    keyMode = !boxes;
    ARROWS.forEach(function (A, n) {
      enabled[AN[A.role]] = !keyMode;
      if (boxes) set(AN[A.role], {text: boxes[n].text, ax: boxes[n].ax, ay: boxes[n].ay,
        "font.size": arrowFont, xanchor: "center", yanchor: "middle"});
    });
    keyBox.hidden = !keyMode;

    wrap.style.width = controls.style.width = keyBox.style.width = w + "px";
    wrap.classList.toggle("is-narrow", !L.modebar);
    // Plotly resizes its SVG but leaves the graph div's inline size alone.
    gd.style.width = w + "px";
    gd.style.height = GEO.height + "px";
    heads.forEach(function (h, k) {
      h.style.transform = "translate(" + (L.margin.l + 8) + "px," + (GEO.t + (k ? GEO.topH + L.gap : 0) + 4) + "px)";
      // Wrapped short of the data: the top panel's line climbs to the top right,
      // and the bottom panel's lines begin at the stock anchor.
      h.style.maxWidth = Math.round(k ? (TA - X0) / (X1 - X0) * plotW - 20 : plotW * 0.6) + "px";
      h.querySelector(".china-head-title").style.fontSize = L.head.title + "px";
      h.querySelector(".china-head-sub").style.fontSize = L.head.sub + "px";
    });
    mark.style.left = (L.margin.l + plotW / 2) + "px";
    mark.style.top = (GEO.t + GEO.topH * 0.52) + "px";
    mark.style.fontSize = Math.round(Math.min(GEO.topH * L.mark_frac, plotW * 0.3)) + "px";
    hideTip();
    var extra = itemsPatch(playhead, true), where = notesPatch(playhead), mk = markersAt(playhead), key;
    for (key in extra) patch[key] = extra[key];
    for (key in where) patch[key] = where[key];
    PL.update(gd, {"line.width": [L.gdp_width, L.economy_width, L.stock_width]}, patch,
      [TR.gdp, TR.economy, TR.stock]).then(function () {
        return PL.restyle(gd, {x: [mk.x], y: [mk.y]}, [TR.markers]);
      });
    syncControls();
  }

  // ---- Theme: brand colours in light mode, the page's own ink in dark mode ---------
  function rgb(str) {
    var m = /rgba?\(([^)]+)\)/.exec(str || "");
    if (m) {
      var p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
      return {c: [p[0], p[1], p[2]], a: p.length > 3 ? p[3] : 1};
    }
    m = /^#([0-9a-f]{6})$/i.exec(str || "");
    return m ? {c: [0, 2, 4].map(function (i) { return parseInt(m[1].substr(i, 2), 16); }), a: 1} : null;
  }
  function mix(a, b, t) {
    return "rgb(" + [0, 1, 2].map(function (i) { return Math.round(a[i] + (b[i] - a[i]) * t); }).join(",") + ")";
  }
  function tint(c, a) { return "rgba(" + c.join(",") + "," + a + ")"; }
  function shade(color, a) { return a === undefined ? color : tint(rgb(color).c, a); }
  function palette() {
    var cs = getComputedStyle(document.body), ink = rgb(cs.color), paper = rgb(cs.backgroundColor);
    var darkClass = document.body.classList.contains("quarto-dark");
    if (!paper || paper.a === 0) paper = {c: darkClass ? [34, 34, 34] : [255, 255, 255]};
    if (!ink) ink = {c: darkClass ? [255, 255, 255] : [31, 35, 40]};
    var lum = (0.2126 * paper.c[0] + 0.7152 * paper.c[1] + 0.0722 * paper.c[2]) / 255;
    if (!(darkClass || lum < 0.4)) return M.light;
    return {ink: mix(ink.c, paper.c, 0), paper: mix(paper.c, ink.c, 0), label: mix(ink.c, paper.c, 0.3),
            grid: mix(ink.c, paper.c, 0.86), minor: tint(ink.c, 0.06), axis: mix(ink.c, paper.c, 0.6),
            behind: tint(ink.c, 0.14), famine: tint(ink.c, 0.09)};
  }
  function applyTheme() {
    P = palette();
    var key = JSON.stringify(P);
    if (key === themeKey) return;
    themeKey = key;
    heads.forEach(function (h) { h.style.setProperty("--china-label", P.label); });
    var layout = {"font.color": P.ink, "xaxis.tickfont.color": P.label, "xaxis.linecolor": P.axis,
      "yaxis.tickfont.color": P.label, "yaxis2.tickfont.color": P.label,
      "yaxis.gridcolor": P.grid, "yaxis2.gridcolor": P.grid,
      "yaxis.minor.gridcolor": P.minor, "yaxis2.minor.gridcolor": P.minor,
      "modebar.bgcolor": "rgba(0,0,0,0)", "modebar.color": P.label, "modebar.activecolor": P.ink};
    layout["shapes[" + M.shape.famine + "].fillcolor"] = P.famine;
    layout["shapes[" + M.shape.zero_line + "].line.color"] = P.ink;
    Object.keys(M.styles).forEach(function (role) {
      var st = M.styles[role], a = "annotations[" + AN[role] + "].";
      layout[a + "font.color"] = shade(P.ink, st.alpha);
      if (st.mask) layout[a + "bgcolor"] = P.paper;
      if (st.arrow) layout[a + "arrowcolor"] = shade(P.ink, st.alpha);
    });
    EV.forEach(function (e) {
      layout["shapes[" + e.shape + "].line.color"] = P.ink;
      layout["annotations[" + e.annotation + "].font.color"] = shade(P.ink, M.event_label_alpha);
    });
    // One restyle per attribute group: a null in a per-trace list would unset it.
    PL.relayout(gd, layout);
    PL.restyle(gd, {fillcolor: P.behind}, [TR.fill_behind]);
    PL.restyle(gd, {"marker.line.color": P.paper}, [TR.gdp_head, TR.stock_head, TR.markers]);
    PL.restyle(gd, {"marker.color": P.ink, "textfont.color": P.paper}, [TR.markers]);
  }

  // ---- Hover: actual data points only, at the cursor's date, panel by panel --------
  // The nearest ACTUAL point to date T that has been revealed (<= playhead) and
  // lies within tol of T; -1 if there is none. Half a sampling period either
  // side: a GDP point answers for its calendar year, a month-end for the two
  // weeks around it.
  function nearest(t, T, tol) {
    var n = upper(t, T), best = -1, bd = Infinity;
    [n - 1, n].forEach(function (i) {
      if (i < 0 || i >= t.length || t[i] > playhead) return;
      var d = Math.abs(t[i] - T);
      if (d < bd) { bd = d; best = i; }
    });
    return bd <= tol ? best : -1;
  }
  function probe(T, inTop, inBottom) {
    return {gdp: inTop ? nearest(G.t, T, YEAR / 2) : -1, month: inBottom ? nearest(S.t, T, 16 * DAY) : -1};
  }
  function eventNear(px, cx, cy, xa) {
    for (var i = 0; i < EV.length; i++) {
      var e = EV[i];
      if (alphaAt(e.t, playhead) < 0.5) continue;
      if (Math.abs(xa.l2p(e.t) - px) <= 4) return e;
      if (!stripOn) continue;
      var el = gd.querySelector('.annotation[data-index="' + e.annotation + '"]');
      var r = el && el.getBoundingClientRect();
      if (r && cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom) return e;
    }
    return null;
  }
  function hideTip() {
    tip.style.display = guide.style.display = "none";
    for (var k in dotEl) dotEl[k].style.display = "none";
  }
  function tipRow(cls, text) {
    var d = document.createElement("div");
    d.className = cls;
    if (cls.indexOf("china-tip-row") === 0) { var k = document.createElement("span"); k.className = "china-tip-key"; d.appendChild(k); }
    d.appendChild(document.createTextNode(text));
    return d;
  }
  function showTip(cx, cy) {
    var fl = gd._fullLayout, xa = fl.xaxis, ya = fl.yaxis, y2 = fl.yaxis2, r = gd.getBoundingClientRect();
    var px = cx - r.left - xa._offset, py = cy - r.top;
    var topEdge = ya._offset - GEO.t, bottomEdge = y2._offset + y2._length;
    if (px < 0 || px > xa._length || py < topEdge || py > bottomEdge) return hideTip();
    var inTop = py >= ya._offset && py <= ya._offset + ya._length, inBottom = py >= y2._offset;
    var hit = probe(xa.p2l(px), inTop, inBottom), ev = eventNear(px, cx, cy, xa);
    if (hit.gdp < 0 && hit.month < 0 && !ev) return hideTip();
    tip.replaceChildren();
    if (ev) tip.appendChild(tipRow("china-tip-event", ev.description));
    if (hit.gdp >= 0) tip.appendChild(tipRow("china-tip-row china-tip-gdp", G.hover[hit.gdp]));
    if (hit.month >= 0) {
      tip.appendChild(tipRow("china-tip-row china-tip-stock", S.hoverS[hit.month]));
      tip.appendChild(tipRow("china-tip-row china-tip-economy", S.hoverE[hit.month]));
    }
    var w = wrap.getBoundingClientRect(), ox = r.left - w.left, oy = r.top - w.top;
    function dot(el, ax, t, v) {
      var x = v === null ? -1 : xa.l2p(t), y = v === null ? -1 : ax.l2p(v);
      if (v === null || x < 0 || x > xa._length || y < 0 || y > ax._length) { el.style.display = "none"; return; }
      el.style.display = "block";
      el.style.transform = "translate(" + (ox + xa._offset + x) + "px," + (oy + ax._offset + y) + "px)";
    }
    dot(dotEl.gdp, ya, G.t[hit.gdp], hit.gdp < 0 ? null : G.y[hit.gdp]);
    dot(dotEl.stock, y2, S.t[hit.month], hit.month < 0 ? null : S.s[hit.month]);
    dot(dotEl.economy, y2, S.t[hit.month], hit.month < 0 ? null : S.e[hit.month]);
    guide.style.display = "block";
    guide.style.height = (bottomEdge - ya._offset) + "px";
    guide.style.transform = "translate(" + (ox + xa._offset + px) + "px," + (oy + ya._offset) + "px)";
    tip.style.display = "block";
    var tw = tip.offsetWidth, th = tip.offsetHeight, x0 = cx - w.left, y0 = cy - w.top;
    var left = x0 + 14 + tw > w.width - 4 ? x0 - 14 - tw : x0 + 14;
    var top = y0 - th - 12 < 4 ? y0 + 16 : y0 - th - 12;
    tip.style.transform = "translate(" + Math.max(4, left) + "px," + Math.max(4, top) + "px)";
  }

  // ---- Audit (?china-audit): one scale, no text on anything, hover ------------------
  function runAudit() {
    var out = {width: lastW, layout: lastW < M.narrow_below ? "narrow" : "wide",
               dark: document.body.classList.contains("quarto-dark"), hidden: document.hidden,
               strip: stripOn ? "labels in rows " + EV.map(function (e) { return e.row; }).join("") : "labels hidden",
               arrows: keyMode ? "key" : "in plot", fails: [], frames: {}};
    // Let n frames pass. A hidden page gets no animation frames and its timers
    // are throttled to one a second, so there a wait is a message-channel turn;
    // the timer covers a page that is hidden part-way through a wait.
    function turn(ok) {
      var done = false;
      function fin() { if (!done) { done = true; ok(); } }
      if (document.hidden) {
        var ch = new MessageChannel();
        ch.port1.onmessage = fin;
        ch.port2.postMessage(0);
      } else {
        requestAnimationFrame(fin);
        setTimeout(fin, 100);
      }
    }
    function frames(n) { return new Promise(function (ok) { (function f(k) { k ? turn(function () { f(k - 1); }) : ok(); })(n); }); }
    function fail(msg) { if (out.fails.indexOf(msg) < 0) out.fails.push(msg); }
    function pxPerNat() {
      var fl = gd._fullLayout, a = fl.yaxis, b = fl.yaxis2;
      return [a._length / (a.range[1] - a.range[0]), b._length / (b.range[1] - b.range[0])];
    }
    var roleOf = {};
    Object.keys(AN).forEach(function (r) { roleOf[AN[r]] = r; });
    EV.forEach(function (e) { roleOf[e.annotation] = "event: " + e.label; });

    // Every visible text box against every other, the event lines, and the data.
    function collisions(tag) {
      var fl = gd._fullLayout, xa = fl.xaxis, ya = fl.yaxis, y2 = fl.yaxis2, r = gd.getBoundingClientRect();
      var X = function (t) { return r.left + xa._offset + xa.l2p(t); };
      var panels = [{ax: ya, top: r.top + ya._offset}, {ax: y2, top: r.top + y2._offset}];
      var boxes = [], minText = 1e9, minData = 1e9, minLine = 1e9;
      Array.prototype.forEach.call(gd.querySelectorAll(".annotation"), function (el) {
        var i = +el.getAttribute("data-index"), tg = el.querySelector(".annotation-text-g"), a = fl.annotations[i];
        if (!tg || !a || a.visible === false || a.opacity < 0.05) return;
        var b = tg.getBoundingClientRect(), role = roleOf[i] || ("#" + i), st = M.styles[role] || {};
        if (!b.width) return;
        boxes.push({i: i, role: role, mask: !!st.mask, l: b.left, r: b.right, t: b.top, b: b.bottom});
      });
      heads.forEach(function (h, k) {
        var b = h.getBoundingClientRect();
        boxes.push({i: -1 - k, role: k ? "head: Stocks" : "head: Economy", mask: true, l: b.left, r: b.right, t: b.top, b: b.bottom});
      });
      boxes.forEach(function (a, n) {
        if (a.l < r.left - 1 || a.r > r.right + 1 || a.t < r.top - 1 || a.b > r.bottom + 1)
          fail(tag + ": text outside the figure: " + a.role);
        boxes.forEach(function (c, m) {
          if (m <= n) return;
          var gap = Math.max(c.l - a.r, a.l - c.r, c.t - a.b, a.t - c.b);
          minText = Math.min(minText, gap);
          if (gap < 1) fail(tag + ": text on text: " + a.role + " / " + c.role);
        });
        // Event lines: a masked box hides the line behind it; anything else must stand clear.
        EV.forEach(function (e) {
          if (a.mask || e.annotation === a.i || alphaAt(e.t, playhead) <= 0) return;
          var x = X(e.t), lineTop = r.top + ya._offset - (stripOn ? 2 + e.row * L.strip.row : 0);
          if (a.b <= lineTop + 0.5) return;               // the line stops below this label
          var gap = Math.max(a.l - x, x - a.r);
          minLine = Math.min(minLine, gap);
          if (gap < 1) fail(tag + ": text on an event line: " + a.role + " / " + e.label);
        });
        // Data: the lines of whichever panel the box is in, and the tint between s and e.
        // (Not the panel titles under a reader's own zoom: they are fixed to the
        // panel's corner, so a zoom can bring data up beneath them. The halo is for that.)
        panels.forEach(function (pn, k) {
          if (a.b < pn.top || a.t > pn.top + pn.ax._length || (tag === "zoomed" && a.i < 0)) return;
          for (var x = Math.floor(a.l) - 2; x <= Math.ceil(a.r) + 2; x++) {
            var T = xa.p2l(x - r.left - xa._offset);
            if (T > playhead) continue;
            var vals = k === 0 ? [at(G.t, G.y, T)] : [at(S.t, S.s, T), at(S.t, S.e, T)];
            if (vals[0] === null) continue;
            var ys = vals.map(function (v) { return pn.top + pn.ax.l2p(v); });
            var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
            var gap = Math.max(a.t - hi, lo - a.b);
            minData = Math.min(minData, gap);
            if (gap < 3) fail(tag + ": text on the data: " + a.role);
          }
        });
      });
      var ppn = pxPerNat();
      if (Math.abs(ppn[0] - ppn[1]) > 0.02) fail(tag + ": panels have different scales: " + ppn.join(" vs ") + " px per nat");
      return {texts: boxes.length, minGapText: +minText.toFixed(1), minGapData: +minData.toFixed(1),
              minGapEventLine: +minLine.toFixed(1), pxPerNat: +ppn[0].toFixed(3),
              xEnd: String(xa.range[1]).slice(0, 10)};
    }

    var fill0 = [gd.data[TR.fill_behind].y.slice(), gd.data[TR.fill_ahead].y.slice()];
    return frames(3).then(function () {
      out.frames.complete = collisions("complete");
      // The script's fill walk reproduces the module's at the end of the data.
      var f = fills(revealPair(T1));
      [f.behind.y, f.ahead.y].forEach(function (y, k) {
        var same = y.length === fill0[k].length && y.every(function (v, i) {
          return v === fill0[k][i] || Math.abs(v - fill0[k][i]) < 1e-9; });
        if (!same) fail("the script's fill differs from the module's (" + (k ? "ahead" : "behind") + ")");
      });
      // A horizontal zoom and an autoscale leave the scale alone.
      return PL.relayout(gd, {"xaxis.range": ["2005-01-01", "2012-01-01"]});
    }).then(function () { return frames(3); }).then(function () {
      out.frames.zoomed = collisions("zoomed");
      return PL.relayout(gd, {"xaxis.autorange": true});
    }).then(function () { return frames(3); }).then(function () {
      var fl = gd._fullLayout;
      if (fl.xaxis.autorange) fail("the x-axis is still autoranged after autoscale");
      if (String(fl.xaxis.range[0]).slice(0, 10) !== M.view.x[0]) fail("autoscale did not return to the full view");
      if (!fl.yaxis.fixedrange || !fl.yaxis2.fixedrange) fail("a y-axis can be zoomed");
      // Playback frames.
      var years = [1961.6, 1963, 1975, 1985, 1995, 2005, 2011.2, 2023], chain = Promise.resolve();
      years.forEach(function (y) {
        chain = chain.then(function () {
          busy = false; pending = null;
          render(Date.UTC(Math.floor(y), 0, 1) + (y % 1) * YEAR);
          return frames(3);
        }).then(function () {
          var c = collisions("playback " + y), xa = gd._fullLayout.xaxis;
          c.windowYears = +((xa.r2l(xa.range[1]) - xa.r2l(xa.range[0])) / YEAR).toFixed(2);
          c.watermark = mark.style.display !== "none" ? mark.textContent : null;
          out.frames["playback " + y] = c;
          if (c.windowYears < M.play.min_window_years - 0.01) fail("window narrower than the minimum at " + y);
          if (c.watermark !== String(Math.floor(y))) fail("watermark does not show the year at " + y);
        });
      });
      return chain;
    }).then(function () {
      // Hover at an interpolated playhead: nothing from Plotly, only actual points from us.
      var k = Math.floor(G.t.length * 0.7), Tm = G.t[k] + 0.37 * (G.t[k + 1] - G.t[k]);
      busy = false; pending = null;
      render(Tm);
      return frames(3).then(function () {
        var fl = gd._fullLayout, xa = fl.xaxis, r = gd.getBoundingClientRect(), drag = gd.querySelector(".nsewdrag") || gd;
        var hx = r.left + xa._offset + xa.l2p(Tm) - 2, known = G.hover.concat(S.hoverS, S.hoverE);
        out.hover = {playhead: iso(Tm).slice(0, 10), interpolated: G.t.indexOf(Tm) < 0 && S.t.indexOf(Tm) < 0, rows: {}};
        [["top", fl.yaxis], ["bottom", fl.yaxis2]].forEach(function (pn) {
          var hy = r.top + pn[1]._offset + pn[1]._length / 2;
          ["mousemove", "pointermove"].forEach(function (type) {
            var Ctor = type === "pointermove" && window.PointerEvent ? PointerEvent : MouseEvent;
            drag.dispatchEvent(new Ctor(type, {clientX: hx, clientY: hy, bubbles: true, pointerType: "mouse"}));
          });
          var rows = Array.prototype.map.call(tip.querySelectorAll(".china-tip-row"), function (d) { return d.textContent; });
          out.hover.rows[pn[0]] = rows;
          if (!rows.length) fail("no hover box in the " + pn[0] + " panel at the playhead");
          rows.forEach(function (t) { if (known.indexOf(t) < 0) fail("hover row is not an actual data point: " + t); });
        });
        if (out.hover.rows.top.length !== 1) fail("the top panel should report the economy alone");
        if (out.hover.rows.bottom.length !== 2) fail("the bottom panel should report the stocks and the economy");
        var h = probe(Tm, true, true);
        if (G.t[h.gdp] > Tm || S.t[h.month] > Tm) fail("hover reports a point the playhead has not reached");
        out.hover.plotlyLabels = gd.querySelectorAll(".hoverlayer .hovertext, .hoverlayer .legend").length;
        if (out.hover.plotlyLabels) fail("Plotly drew a hover label");
        hideTip();
        // Stacking order survives mid-animation draws: within each panel, SVG groups in trace order.
        var want = gd._fullData.map(function (d) { return "trace" + d.uid; });
        out.traceOrder = Array.prototype.map.call(gd.querySelectorAll(".scatterlayer"), function (layer) {
          return Array.prototype.map.call(layer.querySelectorAll(".trace"), function (t) {
            return want.indexOf(Array.prototype.filter.call(t.classList, function (c) { return c.length > 5 && c.indexOf("trace") === 0; })[0]); });
        });
        out.traceOrder.forEach(function (order) {
          if (order.some(function (v, j, a) { return v < 0 || (j && v <= a[j - 1]); }))
            fail("SVG trace groups are out of order: " + order.join(","));
        });
        // Cost of one draw call (the synchronous part of a frame).
        var n = 60, i = 0, worst = 0, total = 0;
        function one() {
          if (i >= n) return Promise.resolve();
          busy = false; pending = null;
          var t0 = performance.now();
          render(T0 + (T1 - T0) * (i++ / n));
          var dt = performance.now() - t0;
          worst = Math.max(worst, dt); total += dt;
          return frames(1).then(one);
        }
        return one().then(function () {
          out.drawMs = {mean: +(total / n).toFixed(1), worst: +worst.toFixed(1)};
          busy = false; pending = null;
          render(T1);
          return frames(3);
        });
      });
    }).then(function () {
      var fl = gd._fullLayout, r = gd.getBoundingClientRect(), hr = host().getBoundingClientRect(), spill = 0;
      [gd, controls, keyBox].forEach(function (el) {
        var b = el.getBoundingClientRect();
        if (b.width) spill = Math.max(spill, hr.left - b.left, b.right - hr.right);
      });
      out.fit = {column: host().clientWidth, figure: +r.width.toFixed(1), height: fl.height,
                 panels: [Math.round(fl.yaxis._length), Math.round(fl.yaxis2._length)], spill: +spill.toFixed(1)};
      if (Math.abs(r.width - host().clientWidth) > 1.5 || spill > 1.5) fail("the figure does not fit its column");
      if (mark.style.display !== "none") fail("the year watermark is showing on the finished chart");
      if (String(fl.xaxis.range[1]).slice(0, 10) !== M.view.x[1]) fail("the finished chart does not show the full range");
      out.playSeconds = +TOTAL.toFixed(1);
      out.pass = out.fails.length === 0;
      window.__CHINA_AUDIT__ = out;
      console.log("CHINA-AUDIT " + JSON.stringify(out));
      return out;
    });
  }

  // ---- Boot -----------------------------------------------------------------------
  function boot() {
    if (!window.Plotly || !gd._fullLayout || !gd.layout || !gd.layout.meta) return setTimeout(boot, 30);
    // Hold on to the Plotly that drew this figure. Every figure on the page
    // loads its own copy of plotly.js, each replacing window.Plotly, and a copy
    // that has not drawn anything yet cannot measure annotation text.
    PL = window.Plotly;
    M = gd.layout.meta; TR = M.trace; AN = M.ann;
    FONT = gd._fullLayout.font.family;
    function series(i) { var x = gd.data[i].x.slice(); return {trace: i, x: x, t: x.map(toMs), y: gd.data[i].y.slice()}; }
    G = series(TR.gdp); G.hover = M.hover.gdp;
    S = series(TR.stock);
    S.s = S.y; S.e = gd.data[TR.economy].y.slice(); S.hoverS = M.hover.stock; S.hoverE = M.hover.economy;
    PEERS = TR.peers.map(series);
    EV = M.events.map(function (e) {
      return {t: toMs(e.date), tier: e.tier, label: e.label, description: e.description,
              shape: e.shape, annotation: e.annotation, row: 0};
    });
    ITEMS = M.items.map(function (it) {
      return {kind: it.kind, index: it.index, opacity: it.opacity, t: it.date ? toMs(it.date) : null, alpha: -1};
    });
    ARROWS = M.arrows.map(function (a) {
      var t = toMs(a.date);
      return {role: a.role, date: a.date, t: t, y: S.s[S.t.indexOf(t)], month: a.month, text: a.text};
    });
    T0 = toMs(M.play.start); T1 = toMs(M.play.end); TA = toMs(M.anchor);
    X0 = toMs(M.view.x[0]); X1 = toMs(M.view.x[1]);
    // Integrate the pace profile (seconds per year on a uniform grid) into playback time.
    var spy = M.play.seconds_per_year, stepYears = (T1 - T0) / YEAR / (spy.length - 1);
    TAU = [0];
    for (var i = 1; i < spy.length; i++) TAU.push(TAU[i - 1] + (spy[i] + spy[i - 1]) / 2 * stepYears);
    NP = TAU.length - 1; TOTAL = TAU[NP];
    ARROWS.forEach(function (a, n) {
      var row = document.createElement("div"), num = document.createElement("span");
      row.className = "china-key-row"; num.className = "china-key-n"; num.textContent = n + 1;
      row.appendChild(num);
      row.appendChild(document.createTextNode(a.month + ". " + a.text + "."));
      keyBox.appendChild(row);
    });
    playhead = T1;

    playBtn.addEventListener("click", function () { if (playing) pause(); else play(); });
    scrub.addEventListener("input", function () { pause(); render(timeOf(scrub.value / scrub.max * TOTAL)); });
    gd.on("plotly_relayout", function () { hideTip(); syncAxes(); });

    gd.addEventListener("pointermove", function (e) {
      if (e.pointerType === "touch" || dragging) return;
      showTip(e.clientX, e.clientY);
    });
    gd.addEventListener("pointerleave", hideTip);
    gd.addEventListener("pointerdown", function (e) {
      down = {x: e.clientX, y: e.clientY};
      if (e.pointerType !== "touch") { dragging = true; hideTip(); }
      if (e.target.closest && e.target.closest(".draglayer")) pause();
    });
    window.addEventListener("pointerup", function (e) {
      dragging = false;
      if (e.pointerType === "touch") {                 // a tap reports; a drag or a tap elsewhere clears
        var tap = down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 8 && gd.contains(e.target);
        if (tap) showTip(e.clientX, e.clientY); else hideTip();
      }
      down = null;
    });

    applyTheme();
    new MutationObserver(function () { requestAnimationFrame(applyTheme); setTimeout(applyTheme, 250); })
      .observe(document.body, {attributes: true, attributeFilter: ["class"]});
    if (window.ResizeObserver) new ResizeObserver(function () { fit(); }).observe(host());
    window.addEventListener("resize", function () { fit(); });
    fit();
    // Text was measured with whatever font was ready; measure again when the real one is.
    var fontsReady = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    fontsReady.then(function () { fit(true); });
    // The audit waits for that second fit, so it measures the settled figure.
    if (location.search.indexOf("china-audit") >= 0) fontsReady.then(function () { setTimeout(runAudit, 900); });
  }
  boot();
})();
</script>
"""


def china_figure_html(fig: go.Figure) -> str:
    """The figure, its overlays, the playback controls, and the script.

    Returns one HTML string for a Quarto cell to render (via ``IPython.HTML``):
    the Plotly figure div (plotly.js from the same CDN as the simplex figure,
    scroll-zoom off so the page still scrolls), the year watermark behind it,
    each panel's title and subtitle and the hover overlay in front of it, the
    key used when the arrowed annotations do not fit, a
    play button and a native ``<input type="range">`` scrubber, and the script
    that fits the figure to its column, places the text, draws the animation,
    follows the site's light/dark theme and shows the hover box. Everything the
    script needs comes from the figure itself (the traces and ``layout.meta``).
    """
    import plotly.io as pio

    fig_html = pio.to_html(
        fig, include_plotlyjs="cdn", full_html=False, div_id=_DIV_ID, auto_play=False,
        config={"displaylogo": False, "scrollZoom": False,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"]})
    style = _STYLE.replace("__GDP__", _GDP_COLOR).replace("__STOCK__", _STOCK_COLOR)
    markup = _MARKUP.replace("__SUB_TOP__", _SUB_TOP).replace("__SUB_BOTTOM__", _SUB_BOTTOM)
    return markup.replace("__FIG__", fig_html) + style + _SCRIPT.replace("__DIV__", _DIV_ID)


# --------------------------------------------------------------------------- #
#  Assertions and the numbers for the caption (run: uv run python china_figure.py)
# --------------------------------------------------------------------------- #
_NUMBER = re.compile(r"(?<![\w.])\d+\.\d+")       # decimal literals; a bare integer is not a level


def _raw_msci_levels() -> np.ndarray | None:
    """Every month-end level in the raw MSCI files, sorted; None if they are absent."""
    paths = [_HERE / "msci_china_index_monthly.csv", _HERE / "msci_usa_index_monthly.csv"]
    if not all(p.exists() for p in paths):
        return None
    return np.sort(np.concatenate([
        pd.read_csv(p, skiprows=5, usecols=[1], header=0, names=["level"])["level"].to_numpy(float)
        for p in paths]))


def _decimals_in(text: str) -> np.ndarray:
    return np.unique([float(m) for m in _NUMBER.findall(text)])


def _run_checks() -> None:
    def close(a, b, tol=1e-12, msg=""):
        assert abs(a - b) <= tol, f"{msg}: {a} != {b} (tol {tol})"

    gdp, s_all = load_derived()
    g = rebased(gdp, "CHN")
    cutoff = common_cutoff(g, s_all)
    s = s_all[:cutoff]
    e = economy_since_anchor(g, s.index)
    fig = build_china_figure()
    meta = dict(fig.layout.meta)
    tr = meta["trace"]
    gdp_tr, stock, economy = fig.data[tr["gdp"]], fig.data[tr["stock"]], fig.data[tr["economy"]]

    # (1) The anchors.
    assert g[g.index.year == GDP_ANCHOR_YEAR].item() == 0.0, "g(1978) != 0"
    assert s[STOCK_ANCHOR] == 0.0, "s(Dec 1998) != 0"
    assert e[STOCK_ANCHOR] == 0.0, "e(Dec 1998) != 0"
    assert stock.x[0] == economy.x[0] == _iso(STOCK_ANCHOR) and stock.y[0] == economy.y[0] == 0.0
    g98, g99 = g[g.index.year == 1998].item(), g[g.index.year == 1999].item()
    by_hand = g98 + (g99 - g98) * 183 / 365        # Jul 1 -> Dec 31, 1998 is 183 of 365 days
    for d, v in list(e.items())[::37]:
        close(v, g_at(g, d)[0] - by_hand, 2e-6, f"e({d:%Y-%m}) is not g re-anchored at Dec 1998")
    assert gdp_tr.yaxis in (None, "y") and stock.yaxis == economy.yaxis == "y2", "a line is in the wrong panel"

    # (2) One vertical scale: nats per pixel is the same in both panels, in both layouts.
    top_span = fig.layout.yaxis.range[1] - fig.layout.yaxis.range[0]
    bottom_span = fig.layout.yaxis2.range[1] - fig.layout.yaxis2.range[0]
    dom_top, dom_bottom = fig.layout.yaxis.domain, fig.layout.yaxis2.domain
    close((dom_top[1] - dom_top[0]) / top_span, (dom_bottom[1] - dom_bottom[0]) / bottom_span, 1e-12,
          "the two panels have different scales as built")
    for name, layout in _LAYOUTS.items():
        for t in (layout["margin"]["t"], layout["margin_t_bare"]):
            geo = _geometry(layout, top_span, bottom_span, t)
            plot_px = geo["height"] - t - layout["margin"]["b"]
            ppn = [(d[1] - d[0]) * plot_px / span for d, span in ((geo["top"], top_span), (geo["bottom"], bottom_span))]
            close(ppn[0], ppn[1], 1e-9, f"{name}: the panels have different scales")
            close(ppn[0], layout["px_per_nat"], 0.2, f"{name}: the scale is not px_per_nat")
    assert fig.layout.yaxis.fixedrange and fig.layout.yaxis2.fixedrange, "a y-zoom would break the shared scale"
    assert dom_top[0] > dom_bottom[1], "the panels overlap"

    # (3) The window: the bottom panel ends at the common cutoff, and nothing later is in the figure.
    assert cutoff == EXPECTED_CUTOFF, f"the common cutoff moved to {cutoff:%Y-%m-%d}: update the caption"
    assert stock.x[-1] == economy.x[-1] == _iso(EXPECTED_CUTOFF), "the bottom panel does not end at the cutoff"
    assert len(stock.x) == len(economy.x) == len(s) and list(stock.x) == list(economy.x)
    assert s_all.index[-1] > cutoff, "expected later stock data in the derived file (dropped from the plot)"
    latest = max(x for t in fig.data if t.yaxis == "y2" for x in t.x if x)
    assert latest[:10] <= _iso(cutoff), f"the bottom panel holds data after the cutoff: {latest}"

    # (4) The fill: periwinkle exactly where s > e, grey exactly where s < e.
    covered = {}
    for name, sign, color in (("fill_ahead", 1, _FILL_AHEAD), ("fill_behind", -1, _FILL_BEHIND)):
        t = fig.data[tr[name]]
        assert t.fillcolor == color and t.fill == "toself" and t.yaxis == "y2"
        xs, ys, start = list(t.x), list(t.y), 0
        while start < len(xs):
            stop = xs.index(None, start)
            half = (stop - start) // 2
            run_x, run_s, run_e = xs[start:start + half], ys[start:start + half], ys[start + half:stop][::-1]
            assert run_x == xs[start + half:stop][::-1], "a fill polygon does not return along the same dates"
            diff = np.array(run_s) - np.array(run_e)
            assert (sign * diff >= -1e-12).all() and (sign * diff).max() > 0, f"{name} covers the wrong sign"
            for x in run_x:
                covered[x[:10]] = sign
            start = stop + 1
    for d, ds in (s - e).items():
        if ds != 0:
            assert covered.get(_iso(d)) == np.sign(ds), f"the fill at {d:%Y-%m} does not match the sign of s - e"

    # (5) The two annotation dates come from the data.
    def by_scanning(a, b):                         # an independent route to the same date
        date = None
        for d in a.index[::-1]:
            if not a[d] < (b[d] if isinstance(b, pd.Series) else b):
                break
            date = d
        return date
    behind_economy, behind_parity = last_fall_below(s, e), last_fall_below(s, 0.0)
    assert behind_economy == by_scanning(s, e) and behind_parity == by_scanning(s, 0.0)
    for name, when in (("arrow_economy", behind_economy), ("arrow_parity", behind_parity)):
        a = fig.layout.annotations[meta["ann"][name]]
        assert a.x == _iso(when) and a.y == s[when] and a.showarrow, f"{name} does not point at its date"
    assert [a["date"] for a in meta["arrows"]] == [_iso(behind_economy), _iso(behind_parity)]
    expected = {"economy": "2010-12", "parity": "2022-07"}
    computed = {"economy": f"{behind_economy:%Y-%m}", "parity": f"{behind_parity:%Y-%m}"}

    # (6) Hover: Plotly labels nothing, and our box can only report actual points.
    assert fig.layout.hovermode is False, "Plotly hover must be off"
    assert all(t.hoverinfo == "skip" for t in fig.data), "a trace can still produce a Plotly hover label"
    assert not fig.frames, "no Plotly frames: interpolated points exist only inside the browser's draw call"
    hover = meta["hover"]
    assert len(hover["gdp"]) == len(gdp_tr.x) and len(hover["stock"]) == len(hover["economy"]) == len(stock.x)
    read = lambda text: float(text.split(": ")[1].split(" nats")[0].replace("−", "-"))
    for text, x, v in zip(hover["gdp"], gdp_tr.x, gdp_tr.y):
        assert text.startswith(f"Economy ({x[:4]})"), "GDP hover names the wrong year"
        close(read(text), round(v, 2), 1e-9, "GDP hover is not g(t)")
    for d, ts, te in zip(s.index, hover["stock"], hover["economy"]):
        assert ts.startswith(f"Stocks ({_month(d)})") and te.startswith(f"Economy ({_month(d)})")
        close(read(ts), round(s[d], 2), 1e-9, "stock hover is not s(t)")
        close(read(te), round(e[d], 2), 1e-9, "economy hover is not e(t)")
    assert _nats(2.709, False) == "+2.71 nats" and _nats(-0.118, False) == "−0.12 nats"
    assert _nats(1.53, True) == "+1.53 nats (×4.6)" and _nats(-0.118, True) == "−0.12 nats (×0.89)"
    assert _nats(-0.004, False) == "+0.00 nats", "a rounded zero must not print as minus zero"

    # (7) Axes and labels: no titles, no tick marks, signed labels, the unit once per panel.
    for axis in (fig.layout.yaxis, fig.layout.yaxis2):
        assert axis.ticks == "" and not axis.title.text and axis.side in (None, "left")
        text = list(axis.ticktext)
        assert sum("nat" in t for t in text) == 1 and "nat" in text[-1], "the unit belongs on the top tick alone"
        assert all(t == "0" or t[0] in "+−" for t in text) and not any("-" in t for t in text)
    assert fig.layout.xaxis.ticks == "" and not fig.layout.showlegend
    page = china_figure_html(fig)
    for word, subtitle in (("Economy", _SUB_TOP), ("Stocks", _SUB_BOTTOM)):
        assert f'<div class="china-head-title">{word}</div>' in page and subtitle in page, f"no in-panel label: {word}"
    assert sum(k.startswith("yaxis") for k in fig.layout.to_plotly_json()) == 2, "exactly one y-axis per panel"

    # (8) Events: every stored event is inside the plotted range; tier 1 is drawn; phase-2 fields exist.
    x0, x1 = fig.layout.xaxis.range
    for ev in EVENTS:
        assert x0 <= ev.date <= x1, f"event outside the plotted range: {ev.label} ({ev.date})"
        assert ev.narration_text is None and ev.image is None, "narration fields are unused this round"
        assert ev.description.endswith(".") and ". " not in ev.description, f"one sentence, please: {ev.label}"
    tier1 = [ev for ev in EVENTS if ev.tier == 1]
    assert [ev["label"] for ev in meta["events"]] == [ev.label for ev in tier1], "tier 1 is not what is drawn"
    for ev in meta["events"]:
        line = fig.layout.shapes[ev["shape"]]
        assert line.x0 == ev["date"] == fig.layout.annotations[ev["annotation"]].x
        assert line.yref == "paper" and line.y0 == 0 and line.y1 >= 1, "an event line must run through both panels"
        assert "narration_text" in ev and "image" in ev
    both = build_china_figure(tiers=(1, 2))
    assert len(both.layout.meta["events"]) == len(EVENTS), "tier 2 does not pass through the same builder"

    # (9) Pacing: slower near events, 20-35 s in all.
    profile = np.array(meta["play"]["seconds_per_year"])
    start, end = pd.Timestamp(meta["play"]["start"]), pd.Timestamp(meta["play"]["end"])
    total = playback_seconds(profile, start, end)
    assert 20 <= total <= 35, f"playback takes {total:.1f} s; tune the pacing constants"
    close(profile.max(), SECONDS_PER_YEAR_SLOW, 1e-4)
    close(profile.min(), SECONDS_PER_YEAR_FAST, 1e-4)

    # (10) The top panel takes peer countries without restructuring.
    peers = build_china_figure(peers=("KOR", "JPN"))
    ptr = peers.layout.meta["trace"]
    assert len(ptr["peers"]) == 2 and all(peers.data[i].yaxis in (None, "y") for i in ptr["peers"])
    assert max(ptr["peers"]) < ptr["gdp"] and len(peers.data) == len(fig.data) + 2
    assert all(peers.data[ptr[k]].name == k for k in tr if k != "peers"), "a peer line shifted a named trace"
    assert gdp.shape[1] > 200, "the derived file should keep every World Bank entity"

    # (11) Licensing: no MSCI index level in the figure, the page HTML or the derived file.
    html = china_figure_html(fig)
    derived = _DATA_PATH.read_text(encoding="utf-8")
    published = {"figure JSON": fig.to_json(), "page HTML": html, "derived file": derived}
    assert '"bdata"' not in published["figure JSON"], "an array was binary-encoded; the JSON must stay readable"
    for name in ("figure JSON", "derived file"):
        # Log ratios are a few nats at most. Any decimal as large as an index
        # level (the smallest is above 50) would be a leak whatever its value.
        big = [v for v in _decimals_in(published[name]) if v >= 20]
        assert not big, f"{name} holds decimals too large to be log ratios: {big[:5]}"
    levels = _raw_msci_levels()
    if levels is None:
        print("  licensing: raw MSCI files not present, so the level-by-level comparison was skipped.")
    else:
        for name, text in published.items():
            found = _decimals_in(text)
            idx = np.clip(np.searchsorted(levels, found), 1, len(levels) - 1)
            gap = np.minimum(np.abs(levels[idx] - found), np.abs(levels[idx - 1] - found))
            # 0.006 also catches a level rounded to two decimals.
            leaked = found[gap <= 0.006]
            assert not len(leaked), f"{name} contains MSCI index levels: {leaked[:5]}"
        print(f"  licensing: none of the {len(levels)} raw MSCI levels appears in the figure JSON, "
              f"the page HTML or the derived file.")

    ppn = _LAYOUTS["wide"]["px_per_nat"]
    print(f"  anchors: g({GDP_ANCHOR_YEAR}) = 0, s(Dec 1998) = 0, e(Dec 1998) = 0.")
    print(f"  scale: {ppn} px per nat in both panels (top {top_span:.2f} nats, bottom {bottom_span:.2f} nats); "
          f"y-axes fixed.")
    print(f"  window: stocks {s.index[0]:%Y-%m-%d} to {cutoff:%Y-%m-%d} ({len(s)} month-ends); "
          f"{len(s_all) - len(s)} later months in the derived file are not drawn.")
    months = s - e
    print(f"  fill: {int((months > 0).sum())} months ahead of the economy, {int((months < 0).sum())} behind; "
          f"colour matches the sign throughout.")
    for key, label in (("economy", "stocks fall behind the economy for good"),
                       ("parity", "stocks fall behind US stocks for good")):
        flag = "as expected" if computed[key] == expected[key] else f"NOT the expected {expected[key]}"
        print(f"  annotation: {label} in {computed[key]} ({flag}).")
    print(f"  hover: {len(hover['gdp'])} GDP + {len(hover['stock'])} stock + {len(hover['economy'])} economy "
          f"strings, one per actual point; Plotly hover off; no frames.")
    print(f"  events: {len(tier1)} drawn (tier 1), {len(EVENTS) - len(tier1)} stored (tier 2), "
          f"all inside [{x0}, {x1}].")
    print(f"  pacing: {total:.1f} s of playback ({SECONDS_PER_YEAR_FAST}-{SECONDS_PER_YEAR_SLOW} s per year).")
    print(f"  derived file: {gdp.shape[1]} GDP entities; page HTML {len(html) / 1024:.0f} KB.")

    end_g, end_e, end_s = g.iloc[-1], e.iloc[-1], s.iloc[-1]
    print("\n  For the caption (changes in nats, multiple in brackets):")
    print(f"  economy, {GDP_ANCHOR_YEAR} to {g.index[-1].year}:        {end_g:+.3f} (×{np.exp(end_g):.1f})")
    print(f"  economy, Dec 1998 to {_month(cutoff)}: {end_e:+.3f} (×{np.exp(end_e):.2f})")
    print(f"  stocks,  Dec 1998 to {_month(cutoff)}: {end_s:+.3f} (×{np.exp(end_s):.2f})")
    print(f"  shortfall at {_month(cutoff)}:         {end_e - end_s:+.3f} (×{np.exp(end_e - end_s):.2f})")
    side = np.sign(months.to_numpy())
    flips = months.index[1:][side[1:] != side[:-1]]
    print("  stocks vs the economy change sides in: " + ", ".join(f"{t:%b %Y}" for t in flips))
    zside = np.sign(s.to_numpy())
    zflips = s.index[1:][zside[1:] != zside[:-1]]
    print("  stocks vs US stocks change sides in:   " + ", ".join(f"{t:%b %Y}" for t in zflips[-4:])
          + " (the last four)")


if __name__ == "__main__":
    _run_checks()
