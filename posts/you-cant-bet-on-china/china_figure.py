"""The animated two-panel China figure for the "You Can't Bet on China" post.

Two stacked panels on one time axis, under the title "China ÷ United States".
Every quantity is China's divided by America's -- the United States is the
numeraire -- and every change is a log ratio in BITS: one bit is one doubling
of China relative to the US.

* Top, "Economy": China's economy caught up with America's. Real GDP per
  capita, China / US, re-based to zero in 1978,

      g(t) = log2(CHN_t / USA_t) - log2(CHN_1978 / USA_1978),

  one point per year, dated July 1 (GDP is a flow over the year).

* Bottom, "Stocks": what an investor could actually buy. MSCI China / MSCI USA
  (net, USD), re-based to zero on December 31, 1998,

      s(t) = log2(C_t / U_t) - log2(C_0 / U_0),

  one point per month-end, against the SAME economy series re-based to that
  date, ``e(t) = g(t) - g(Dec 31, 1998)`` with ``g`` interpolated linearly to the
  month-ends. The area between the two is tinted periwinkle where the stocks
  outpace the economy and grey where they lag it.

The two panels share one vertical scale: a bit is the same number of pixels in
both, so each panel's height is proportional to its y-range and slopes can be
compared across them. The y-ranges are fixed (zooming is horizontal only), which
is what keeps that true.

Colour. Lime (the economy) and periwinkle (the stocks) are reserved for data.
Historical context is NAVY, the brand's neutral-but-coloured hue: the leaders,
the eras, and the shading for the years before the index data. Events and
annotations are ink.

Context, kept apart by kind and by panel:

* LEADERS are one continuous row of segments above the Economy panel, in two
  alternating navy tints.
* ERAS are thin navy bars in the row beneath them (the famine, the Cultural
  Revolution, and so on).
* EVENTS are points in time, in one of three tiers that are set in the data. A
  labelled marker is a short label in the strip above its own panel and a
  dashed ink line through THAT panel only. A tick is a short navy mark at the
  top of its panel, with hover text and no label. A note has no mark at all: it
  is a dated line in the hover text of the event or era it is attached to.
* ACCESS BANDS are shading inside the Stocks panel for the years before the
  index data begin: hatched while there was no exchange at all, then a plain
  tint while there were exchanges a foreigner could barely use. They are the
  thesis: nothing to buy, then little you were allowed to buy, then the data.

The stock window ends on the last month-end the GDP data also cover
(:func:`common_cutoff`); later stock data stay in the derived file but are not
drawn. The four arrowed annotations are placed from the data, not typed in: the
early trough and the peak of ``s``, and the exact points at which the stock line
crosses below the economy line, and below zero, for the last time
(:func:`final_crossing`).

Data. This module reads ONLY ``china_vs_us_log_ratios.csv``, the committed file
of log ratios written by ``prepare_china_figure_data.py``. The file holds
natural logs; they are converted to bits as they are loaded. It carries the GDP
ratio for every entity in the World Bank file, un-re-based, so peer-country
lines can be added to the top panel later (``build_china_figure(peers=...)``
already draws them). The MSCI index levels are licensed: the raw files are
git-ignored, and no level may reach the figure, its hover text or anything else
that is published.

Animation. The default state is the finished chart. A play button, a 1x / 2x
speed toggle and a native range input (not Plotly's slider, whose handle sticks
in a drag state) move a playhead from the first data point to the cutoff; the
scrubber's position is the date, linearly. The browser draws each frame itself:
``requestAnimationFrame`` works out the revealed part of every line, linearly
interpolated to the playhead, the fills between them, how far each bar and band
has grown, and the x-range -- which GROWS with the playhead -- and one
``Plotly.update`` writes it all into traces, shapes and annotations that always
exist. (``Plotly.animate`` re-appends SVG trace groups, so a trace left out of a
frame changes its stacking order; nothing here is ever added, removed or
reordered.) The pace follows the story: slower once the index data begin, and a
little slower still near events (:func:`pace_profile`).

Text. No label has a background box. Wherever text sits over a line, a band or
a fill it carries a halo instead -- its own outline in whatever colour is behind
it (a CSS ``text-shadow``, as in ``simplex_figure.py``) -- so a line passes
behind the letters without a patch being cut out of it. Whatever depends on the
rendered size of text is worked out in the browser from measured text, for the
width the figure actually has: which row each event label sits in, which leader
and era labels fit, where the arrowed annotations and the labels by the fills
go. An era's or a leader's label is left-aligned at the start of its bar and
stays there while the bar grows beneath it; it never re-centres or changes
sides. Each strip has a height budget. At the full column, if a strip cannot
hold everything without a collision, things are dropped in a fixed order (see
``Era.drop_first`` and ``Event``); on narrower screens labels are hidden instead
and the lines, bars and hover remain.

Hover. Plotly's own hover is off. A small HTML box reports the actual data
points at the cursor's date, panel by panel, from strings formatted here in
Python, so an interpolated animation point can never produce a label; it also
describes whatever event, era, leader or band the cursor is on.

The plot background is transparent and the ink and the navy are re-read from the
page, so the figure follows the site's dark mode (with a lighter navy there).

Run the checks with ``uv run python china_figure.py``; the browser-side audit
(one scale, strip heights, text collisions at rest and mid-playback, arrow tips,
labels that stay put, hover) runs when the page URL carries ``?china-audit``.
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
from blogkit.brand_plotly import HERO, SECONDARY, HERMES, INK, LABEL, GRID, PAPER, with_alpha

# --------------------------------------------------------------------------- #
#  Knobs
# --------------------------------------------------------------------------- #
TITLE = "China ÷ United States"
START_YEAR = 1960        # first GDP year drawn; playback starts here
SHOW_MULTIPLE = False    # hover: append "(x 2^x)" after each value, e.g. "+2.24 bits (x4.7)"

# ---- Playback pacing (tune these; _run_checks asserts 65-75 s in all at 1x) ----
SECONDS_PER_YEAR_BEFORE = 0.8    # the base pace until the index data begin
SECONDS_PER_YEAR_AFTER = 1.3     # and from then on
SLOWDOWN_NEAR_EVENTS = 1.3       # near an event or an era boundary the pace is multiplied by this ...
EASE_YEARS = 1.5                 # ... eased in and out over this long either side; the base pace
                                 # changes over the same span either side of the stock anchor
SPEEDS = (1, 2)                  # what the speed toggle steps through
MIN_WINDOW_YEARS = 5.0           # the x-axis never shows less than this during playback
WINDOW_MARGIN = 0.02             # room right of the playhead, as a fraction of the window

# ---- Space at the full column (hard limits) ----
TITLE_ROW_MAX_PX = 28
TOP_STRIP_MAX_PX = 96            # leaders + eras + event labels
BOTTOM_STRIP_MAX_PX = 52

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
_DECIMALS = 6            # precision kept for every plotted number
_LN2 = float(np.log(2.0))

# Colour by meaning (semantics from _brand.yml; palette from brand_plotly):
_GDP_COLOR = SECONDARY                    # lime: the economy
_STOCK_COLOR = HERO                       # periwinkle: the stocks
_INK = INK                                # events, annotations, the zero lines
_CONTEXT = HERMES                         # navy: historical context (leaders, eras, access bands, hatch)
_CONTEXT_DARK = "#a3b4e6"                 # the same hue, lightened, for a dark page
_PEER_COLOR = with_alpha(LABEL, 0.45)
# How strong each tint is, by theme. "ahead" is periwinkle (stocks outpacing the
# economy) and "behind" ink (the shortfall); the rest are navy: the hatched band
# (its tint and its hatch lines), the plain band and the darker stretch at its
# start, the era bars, the ticks, and the two tints the leaders alternate between.
_ALPHA = dict(
    light=dict(ahead=0.5, behind=0.06, band_none=0.05, hatch=0.17, band_limited=0.035, band_early=0.045,
               era=0.6, tick=0.85, leader=[0.13, 0.25]),
    dark=dict(ahead=0.55, behind=0.10, band_none=0.07, hatch=0.24, band_limited=0.05, band_early=0.06,
              era=0.7, tick=0.9, leader=[0.2, 0.36]),
)
# How strong each kind of text is: ink for events, hints, annotations and the
# grey fill's label; navy for the context labels.
_TEXT_ALPHA = dict(event=0.9, hint=0.6, arrow=0.9, fill=0.66, era=0.95, leader=0.95, band=0.8)
_EVENT_LINE_OPACITY = 0.4
_FADE_YEARS = 0.5        # anything timed fades in over this much playhead travel
_PACE_STEPS_PER_YEAR = 10
# A text halo: the text's own outline, in the colour behind it, as eight
# offset copies (a CSS text-shadow). The same recipe as simplex_figure.py.
_HALO_OFFSETS = ("-1.5px 0", "1.5px 0", "0 -1.5px", "0 1.5px",
                 "-1.1px -1.1px", "1.1px -1.1px", "-1.1px 1.1px", "1.1px 1.1px")

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# For the caption: the credit both licences ask for.
SOURCE_LINE = ("Sources: World Bank, World Development Indicators (CC BY 4.0), "
               "GDP per capita in constant 2015 US$; MSCI, MSCI China and MSCI USA "
               "net total return indexes in US dollars.")


# --------------------------------------------------------------------------- #
#  Events, leaders, eras and access bands
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Note:
    """A dated line in the hover text of the event or era it is attached to. No mark of its own.

    ``date`` (ISO) puts the notes of one parent in order; ``when`` is how the
    date reads in the hover box ("Jul 1977", "1966–67"); ``text`` is the line.
    """
    date: str
    when: str
    text: str


@dataclass(frozen=True)
class Event:
    """A point in time, shown according to its ``tier``.

    * ``"label"``: a labelled marker -- a short label in its panel's strip and a
      dashed ink line through that panel.
    * ``"tick"``: worth keeping, but not worth a label -- a short navy mark at
      the top of its panel and hover text. It takes no room in the strip.
    * ``"stored"``: not drawn. Kept for phase 2, and drawn as a labelled marker
      if the builder is asked for it (``tiers=("label", "tick", "stored")``).

    What earns a marker. Economy strip: an event that plausibly changed China's
    growth path. Stocks strip: an event that changed, for the plotted series
    (MSCI China ÷ MSCI USA, in US dollars), foreign access to Chinese stocks,
    what MSCI China is made of, the translation into US dollars, or a large
    market shock. Everything else is a ``Note`` on a parent, or nothing.

    ``panel`` is ``"economy"`` (top) or ``"stocks"`` (bottom). WITHIN A PANEL,
    THE ORDER OF THE LABELLED EVENTS IS THE ORDER IN WHICH THEY ARE KEPT, NOT
    THEIR ORDER IN TIME: if a strip cannot hold them all at the full column,
    they are dropped from the end of the list. Labels are in sentence case.
    ``short`` is a label to fall back on where the full one does not fit.
    Events with the same ``group`` share one label, "<group>: <label> ·
    <label>", and keep a line and hover text each; they must be adjacent in the
    list, in date order. ``notes`` appear as dated lines under the event's own
    hover text. Every acronym is spelled out in the hover text it appears in.
    ``narration_text`` and ``image`` are carried for phase 2's narration pauses
    and are unused.
    """
    date: str                          # ISO date at which the mark is drawn
    label: str                         # short label for the strip (a tick's is its name only)
    description: str                   # the hover text
    tier: str                          # "label" | "tick" | "stored"
    panel: str                         # "economy" | "stocks"
    short: str | None = None           # a shorter label, if the full one does not fit
    group: str | None = None           # events that share one label
    notes: tuple[Note, ...] = ()       # dated lines in this event's hover text
    narration_text: str | None = None  # phase 2
    image: str | None = None           # phase 2


EVENTS = [
    # ---- Economy, labelled: drawn above and through the top panel. Kept in
    #      this order; dropped from the end (Property crisis first). ----
    Event("1972-02-21", "Nixon in Beijing",
          "21 February 1972: Richard Nixon arrives in Beijing, the first visit to the People's Republic "
          "by an American president.", "label", "economy"),
    Event("1978-12-18", "Deng's reforms",
          "18–22 December 1978: the Third Plenum of the 11th Central Committee, the conventional "
          "start of Deng Xiaoping's “reform and opening up”.", "label", "economy",
          notes=(
              # The Third Plenum of the 10th Central Committee, 16-21 July 1977.
              Note("1977-07-21", "Jul 1977", "Deng rehabilitated."),
              # UNSURE of the wording, which is as given to me: the exams were
              # suspended in 1966 and were last HELD in 1965.
              Note("1977-12-10", "Dec 1977",
                   "national university entrance exams (gaokao) held for the first time since 1966."),
              Note("1979-01-01", "1 Jan 1979", "US and China establish diplomatic relations."),
          )),
    Event("1989-06-04", "Tiananmen",
          "4 June 1989: the army clears the Tiananmen Square protests by force.", "label", "economy"),
    Event("1992-01-18", "Southern Tour",
          "18 January – 21 February 1992: Deng Xiaoping tours the south, and economic reform regains "
          "its momentum.", "label", "economy"),
    Event("2001-12-11", "Joins WTO",
          "11 December 2001: China becomes a member of the World Trade Organization.", "label", "economy"),
    # UNSURE of one name in the text, which is as given to me. On 26 August 1980
    # the National People's Congress Standing Committee approved the regulations
    # for the zones in Guangdong: Shenzhen, Zhuhai and Shantou. Xiamen's zone, in
    # Fujian, was approved by the State Council in October 1980.
    Event("1980-08-26", "Special economic zones",
          "Aug 1980: Shenzhen, Zhuhai, Shantou and Xiamen designated special economic zones (SEZs) — "
          "enclaves with lower taxes and looser rules for foreign investment and export production.",
          "label", "economy", short="SEZs"),
    # UNSURE: two dates, one line. The IMF's board recognised the People's
    # Republic as China's representative on 17 April 1980 and the World Bank's
    # followed on 15 May 1980 (both days are from memory); the line is drawn at
    # the first.
    Event("1980-04-17", "Joins World Bank, IMF",
          "April–May 1980: the People's Republic takes China's seat at the International Monetary Fund "
          "and then at the World Bank.", "label", "economy"),
    Event("2008-11-09", "Chinese stimulus",
          "9 November 2008: China announces a four-trillion-yuan stimulus programme.", "label", "economy"),
    Event("1997-07-01", "Hong Kong handover",
          "1 July 1997: sovereignty over Hong Kong passes from Britain to China.", "label", "economy"),
    Event("1994-01-01", "Currency unification",
          "1 January 1994: China merges its official and swap-market exchange rates into one, "
          "devaluing the official yuan by about a third.", "label", "economy"),
    # UNSURE of the day, and of the label: 9 December 2021 is when Fitch declared
    # Evergrande in "restricted default"; it had been missing payments since
    # September, and "property crisis" names something that has no single date.
    Event("2021-12-09", "Property crisis",
          "9 December 2021: the developer Evergrande is declared in default on its dollar bonds, "
          "the emblem of a wider property crisis.", "label", "economy",
          # The meeting of regulators and developers was on 20 August 2020.
          notes=(Note("2020-08-20", "Aug 2020", "“three red lines” debt limits imposed on property developers."),)),

    # ---- Economy, tick ----
    # UNSURE of the day: I have 22 September - 12 October 1980 for Friedman's first visit.
    Event("1980-09-22", "Friedman visits",
          "September 1980: Milton Friedman visits China for the first time, on a lecture tour.", "tick", "economy"),

    # ---- Stocks, labelled: drawn above and through the bottom panel. Dropped
    #      from the end (Shenzhen exchange opens first). ----
    # UNSURE of the day: 21 February 1992 for the first B-share listing in
    # Shanghai (Shanghai Vacuum Electron Devices). February 1992 is solid.
    Event("1992-02-21", "First B-shares",
          "February 1992: the first B-shares, a class of share open to foreign investors, list in Shanghai.",
          "label", "stocks"),
    # UNSURE which date is meant: the QFII rules were issued in early November
    # 2002 and took effect on 1 December 2002; the first QFII trade was in July
    # 2003. This uses the effective date.
    Event("2002-12-01", "QFII",
          "1 December 2002: the Qualified Foreign Institutional Investor (QFII) scheme takes effect, "
          "admitting approved foreign institutions to the A-share market.", "label", "stocks",
          notes=(
              Note("2011-12-16", "Dec 2011",
                   "RQFII (Renminbi QFII) lets licensed investors use renminbi raised offshore."),
              Note("2019-09-10", "Sep 2019", "QFII and RQFII quota limits abolished."),
          )),
    Event("2008-09-15", "Financial crisis",
          "15 September 2008: Lehman Brothers files for bankruptcy and the global financial crisis "
          "enters its most acute phase.", "label", "stocks"),
    Event("2014-11-17", "Stock Connect",
          "November 2014: Stock Connect, a trading link through which investors in Hong Kong can buy "
          "mainland-listed A-shares and mainland investors Hong Kong shares.", "label", "stocks",
          notes=(
              Note("2014-11-17", "17 Nov 2014", "Shanghai–Hong Kong link opens."),
              Note("2016-12-05", "5 Dec 2016", "Shenzhen–Hong Kong link opens."),
          )),
    # A choice: the Shanghai Composite's peak. The fall began the next trading
    # day; the other candidate is "Black Monday", 24 August 2015.
    Event("2015-06-12", "Crash",
          "12 June 2015: the Shanghai Composite peaks; it loses about a third of its value within a month.",
          "label", "stocks",
          notes=(Note("2015-08-11", "11 Aug 2015", "renminbi devalued."),)),
    # These two share one label: five weeks apart, they stand about a pixel apart.
    Event("2018-06-01", "A-shares join MSCI",
          "Jun 2018: MSCI begins including mainland-listed A-shares, at 2.5% of their free-float market cap, "
          "raised in steps to 20% by Nov 2019. This changes what the index measures.",
          "label", "stocks", group="2018"),
    Event("2018-07-06", "US tariffs",
          "6 July 2018: the first American tariffs of the trade war take effect, on 34 billion dollars "
          "of Chinese goods, and China answers in kind.", "label", "stocks", group="2018"),
    # Re-dated from the Didi review (2 July 2021) to the start of the crackdown.
    # The Ant listing had been due on 5 November 2020.
    Event("2020-11-03", "Chinese tech crackdown",
          "3 Nov 2020: Ant Group's initial public offering (IPO) suspended days before listing. "
          "Widens through 2021: Didi probe (Jul), private-tutoring ban (Jul).", "label", "stocks"),
    # UNSURE of the day: 24 September 2024 for the central bank's announcement
    # (the Politburo followed two days later). September 2024 is solid. The
    # text says whose package it was, to tell it from the 2008 stimulus above.
    Event("2024-09-24", "Chinese stimulus",
          "24 September 2024: the People's Bank of China, the central bank, announces a market-support "
          "package of rate cuts and funding for share purchases.", "label", "stocks"),
    Event("1993-07-15", "First H-shares",
          "15 July 1993: Tsingtao Brewery lists in Hong Kong, the first mainland company to issue H-shares.",
          "label", "stocks"),
    # UNSURE which date is meant: the Shenzhen exchange began trading on a trial
    # basis on 1 December 1990 and opened formally on 3 July 1991 (the day is
    # from memory). This uses the formal opening, as asked.
    Event("1991-07-03", "Shenzhen exchange opens",
          "3 July 1991: the Shenzhen Stock Exchange opens formally, after trial trading from December 1990.",
          "label", "stocks"),

    # ---- Stocks, ticks ----
    Event("2005-07-21", "Renminbi de-pegged",
          "21 Jul 2005: renminbi's fixed peg to the US dollar ends; managed appreciation follows. "
          "The economy panel is unaffected (constant 2015 US dollars fix the exchange rate); MSCI China was "
          "then mostly Hong Kong-listed and priced in Hong Kong dollars, which are pegged to the US dollar, "
          "so the effect on this line runs mainly through earnings.", "tick", "stocks"),
    # China Construction Bank listed on 27 October 2005 and Bank of China on 1 June 2006.
    Event("2006-10-27", "ICBC IPO",
          "Big-bank listings in Hong Kong reshape MSCI China: China Construction Bank (Oct 2005), "
          "Bank of China (Jun 2006), Industrial and Commercial Bank of China (ICBC, 27 Oct 2006 — then the "
          "largest IPO, or initial public offering, ever).", "tick", "stocks"),
    # Effective at the close of 30 November 2015; the second half on 31 May 2016.
    Event("2015-11-30", "Chinese ADRs join MSCI",
          "Nov 2015: MSCI China begins including US-listed Chinese companies (American depositary receipts, "
          "ADRs) — Alibaba, Baidu, JD.com, NetEase and others. Half weight in Nov 2015, full weight in "
          "May 2016. This changes what the index measures.", "tick", "stocks"),

    # ---- Stored: not drawn ----
    Event("1971-10-25", "UN seat",
          "25 October 1971: the United Nations General Assembly seats the People's Republic as China's "
          "representative.", "stored", "economy"),
    # A date only: this text must not say it caused anything.
    Event("2022-11-30", "ChatGPT launches", "30 November 2022: OpenAI releases ChatGPT.", "stored", "stocks"),
]
# Capitalised words that may follow the first word of a label written in
# sentence case: proper nouns and initialisms. _run_checks holds labels to it.
_PROPER = {"Beijing", "World", "Bank", "IMF", "WTO", "Tour", "Hong", "Kong", "B-shares", "H-shares", "A-shares",
           "Connect", "US", "Revolution", "UN", "MSCI", "Dec", "Chinese", "IPO", "ADRs", "SEZs"}
# All-capitals words that are names in their own right and need no spelling out
# in hover text. Every other one must be spelled out where it appears.
_NAMES = {"US", "MSCI", "COVID", "JD"}        # JD: the company JD.com


@dataclass(frozen=True)
class Leader:
    """A paramount leader: one segment of the continuous row above the eras.

    ``end`` None means "still in office when the plot ends". The label goes
    inside the segment, left-aligned, if the segment is long enough to hold it;
    a segment too short for its name has hover text only.
    """
    start: str
    end: str | None
    label: str
    description: str


# The convention the dates follow, shown under each leader's own hover text.
LEADER_NOTE = ("“Paramount leader” dates are conventional. Deng kept decisive influence until about 1992; "
               "later dates follow the Party general-secretaryship.")
# UNSURE: every boundary here is a convention rather than a fact. Mao died on
# 9 September 1976 and Hua became chairman on 7 October (the four weeks between
# are left blank). Hua's end and Deng's start are both put at the close of the
# Third Plenum, 22 December 1978, though Hua kept his titles until 1980-81.
# From Jiang on, the dates are those of the general-secretaryship.
LEADERS = [
    Leader("1949-10-01", "1976-09-09", "Mao", "Mao Zedong: 1 October 1949 – 9 September 1976."),
    Leader("1976-10-07", "1978-12-22", "Hua", "Hua Guofeng: October 1976 – December 1978."),
    Leader("1978-12-22", "1989-06-24", "Deng", "Deng Xiaoping: December 1978 – June 1989."),
    Leader("1989-06-24", "2002-11-15", "Jiang", "Jiang Zemin: June 1989 – November 2002."),
    Leader("2002-11-15", "2012-11-15", "Hu", "Hu Jintao: November 2002 – November 2012."),
    Leader("2012-11-15", None, "Xi", "Xi Jinping: from November 2012."),
]


@dataclass(frozen=True)
class Era:
    """A stretch of time: a thin bar in the row above the Economy panel's event labels.

    Eras share one row, so they may not overlap. A bar that began before the
    plot does is cut off at the left edge and gets a small left-pointing marker
    there. The label sits just above the bar, left-aligned at its start (or at
    the plot's left edge), and never moves. ``drop_first`` marks the eras given
    up first if the row cannot hold every label. ``notes`` appear as dated
    lines under the era's own hover text.
    """
    start: str
    end: str
    label: str
    description: str
    drop_first: bool = False
    notes: tuple[Note, ...] = ()


ERAS = [
    # The calendar years the famine is conventionally given. Drawn 1959-61,
    # though the plot starts in 1960.
    Era("1959-01-01", "1961-12-31", "Famine", "1959–61: the famine that followed the Great Leap Forward."),
    Era("1966-05-16", "1976-10-06", "Cultural Revolution",
        "16 May 1966 – 6 October 1976: the Cultural Revolution, from the “May 16 Notification” "
        "to the arrest of the Gang of Four.",
        notes=(
            Note("1966-10-01", "1966–67",
                 "Deng purged as the “number two capitalist roader”; sent to work in a Jiangxi tractor factory, "
                 "Oct 1969."),
            # The Twelfth Plenum of the 8th Central Committee, 13-31 October 1968.
            Note("1968-10-31", "Oct 1968", "Liu Shaoqi expelled from the Party."),
            # Mao's directive, in People's Daily on 22 December 1968. The figure
            # is an estimate; others run from about 16 to 18 million.
            Note("1968-12-22", "Dec 1968",
                 "“Down to the countryside” directive; about 17 million urban youths sent down by 1980."),
            Note("1971-09-13", "13 Sep 1971", "Lin Biao dies in a plane crash in Mongolia."),
            # Removed from all his posts on 7 April 1976. He had been restored in 1973.
            Note("1976-04-07", "Apr 1976", "Deng purged a second time."),
        )),
    # UNSURE, INTERPRETIVE: there is no agreed start or end. The start is the
    # Third Plenum of the 13th Central Committee (26-30 September 1988), which
    # launched the austerity programme; the end is put at the close of 1991,
    # just before the Southern Tour.
    Era("1988-09-26", "1991-12-31", "Retrenchment",
        "About September 1988 – 1991: an austerity programme to curb inflation slows growth and stalls reform.",
        drop_first=True),
    # UNSURE, INTERPRETIVE: whole calendar years, from the first year of WTO
    # membership to the last year before the global financial crisis.
    Era("2002-01-01", "2007-12-31", "WTO export boom",
        "About 2002–07: exports surge in the years after China joins the World Trade Organization (WTO).",
        drop_first=True),
    # UNSURE of both days: 23 January 2020 is the lockdown of Wuhan and
    # 7 December 2022 the "ten new measures" that ended most controls.
    Era("2020-01-23", "2022-12-07", "Zero-COVID",
        "January 2020 – December 2022: from the lockdown of Wuhan to the lifting of most zero-COVID controls."),
]


@dataclass(frozen=True)
class Band:
    """A period of market access: shading inside the Stocks panel, before the data.

    ``start`` None means "from the start of the plot". ``kind`` "none" is the
    hatched band (no exchange at all), "limited" the plain one. ``wraps`` are
    the ways to break the label over lines, widest first; the script uses the
    first that fits the part of the band that is in view, centred there. A band
    may have a first stretch, up to ``early_end``, shaded a touch darker with
    its own hover text and no label. NO TEXT HERE MAY SAY THAT CAPITAL CONTROLS
    CAUSED THE GAP IN THE DATA (the index simply begins when it begins), OR CALL
    B-SHARES RED TAPE.
    """
    start: str | None
    end: str
    kind: str                # "none" | "limited"
    wraps: tuple[str, ...]
    description: str
    y: float                 # label height, as a fraction of the panel from its bottom
    early_end: str | None = None
    early_description: str | None = None


_EXCHANGE_OPENS = "1990-12-19"          # the Shanghai Stock Exchange begins trading
BANDS = [
    Band(None, _EXCHANGE_OPENS, "none",
         ("No stock exchange", "No stock<br>exchange"),
         "Until the Shanghai Stock Exchange opened on 19 December 1990, mainland China had no stock exchange.",
         y=0.56),
    Band(_EXCHANGE_OPENS, "1998-12-31", "limited",
         ("Exchanges open, mostly closed to foreigners", "Exchanges open,<br>mostly closed to foreigners",
          "Exchanges open,<br>mostly closed<br>to foreigners", "Exchanges<br>open, mostly<br>closed to<br>foreigners"),
         "From Feb 1992, a small B-share market for foreign investors; from Jul 1993, H-shares listed in "
         "Hong Kong. A-shares stayed closed to foreigners until QFII (the Qualified Foreign Institutional "
         "Investor scheme: licensed institutions with quotas, from 2002–03).",
         y=0.76,
         # Ends where the "First B-shares" event stands.
         early_end="1992-02-21",
         early_description="Dec 1990 – Feb 1992: A-shares only, closed to foreigners."),
]


# --------------------------------------------------------------------------- #
#  Data and the quantities derived from it
# --------------------------------------------------------------------------- #
def load_derived(path: str | Path = _DATA_PATH) -> tuple[pd.DataFrame, pd.Series]:
    """The derived file, in bits: the GDP ratios of every entity and the stock ratio.

    The file stores natural logs; dividing by ``ln 2`` makes them bits.

    Returns
    -------
    (gdp, s)
        ``gdp``: ``log2(X_t / USA_t)`` by date (July 1 of each year) and entity
        code, NOT re-based (see :func:`rebased`). ``s``: the stock log ratio at
        each month-end, zero on ``STOCK_ANCHOR``; every month in the file,
        including those after the plotted window.
    """
    df = pd.read_csv(path, comment="#", parse_dates=["date"])
    gdp = df[df["series"] == "gdp"].pivot(index="date", columns="entity", values="log_ratio") / _LN2
    gdp.columns.name = None
    s = df[(df["series"] == "stocks") & (df["entity"] == "CHN")].set_index("date")["log_ratio"] / _LN2
    s = s.round(_DECIMALS) + 0.0
    s.name = "s"
    assert s.index[0] == STOCK_ANCHOR and s.iloc[0] == 0.0, "stock series is not anchored at STOCK_ANCHOR"
    return gdp, s


def rebased(gdp: pd.DataFrame, entity: str = "CHN", year: int = GDP_ANCHOR_YEAR) -> pd.Series:
    """One entity's GDP ratio as the change since ``year``, in bits: ``g`` for China."""
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

    The base pace is ``SECONDS_PER_YEAR_BEFORE`` until the index data begin and
    ``SECONDS_PER_YEAR_AFTER`` from then on, changing smoothly over
    ``EASE_YEARS`` either side of ``STOCK_ANCHOR``. Near any of the ``moments``
    (events and era boundaries) it is multiplied by up to
    ``SLOWDOWN_NEAR_EVENTS``, eased in and out over the same span, so the speed
    never changes abruptly. The grid has ``_PACE_STEPS_PER_YEAR`` steps a year;
    the script integrates it to map playback time to playhead date and back.
    """
    n = round((end - start).days / 365.25 * _PACE_STEPS_PER_YEAR)
    years = (_days(start)[0] + (_days(end)[0] - _days(start)[0]) * np.arange(n + 1) / n) / 365.25
    step = np.clip((years - (_days(STOCK_ANCHOR)[0] / 365.25 - EASE_YEARS)) / (2 * EASE_YEARS), 0.0, 1.0)
    step = step * step * (3 - 2 * step)                              # smoothstep
    base = SECONDS_PER_YEAR_BEFORE + (SECONDS_PER_YEAR_AFTER - SECONDS_PER_YEAR_BEFORE) * step
    at = _days(pd.DatetimeIndex(moments)) / 365.25
    nearest = np.abs(years[:, None] - at[None, :]).min(axis=1)
    bump = 0.5 * (1 + np.cos(np.pi * np.clip(nearest / EASE_YEARS, 0.0, 1.0)))
    return base * (1 + (SLOWDOWN_NEAR_EVENTS - 1) * bump)


def playback_seconds(profile: np.ndarray, start: pd.Timestamp, end: pd.Timestamp,
                     since: pd.Timestamp | None = None) -> float:
    """Playback time implied by a pace profile (trapezoid rule, as in the script).

    The whole of it, or with ``since`` only the part from that date on.
    """
    years = (end - start).days / 365.25
    steps = (profile[1:] + profile[:-1]) / 2 * (years / (len(profile) - 1))
    if since is None:
        return float(steps.sum())
    first = (since - start).days / 365.25 / years * (len(profile) - 1)
    whole = int(np.ceil(first))
    return float(steps[whole:].sum() + (whole - first) * steps[whole - 1])


def _bits(x: float, show_multiple: bool) -> str:
    """A change in bits for the hover box: ``+2.24 bits``, with a true minus sign."""
    shown = round(float(x), 2) + 0.0                # "+ 0.0" turns -0.0 into 0.0
    text = f"{'+' if shown >= 0 else '−'}{abs(shown):.2f} bits"
    if show_multiple:
        m = float(2.0 ** x)
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


def _rgb(color: str) -> np.ndarray:
    """``#rrggbb`` or ``rgb(...)`` / ``rgba(...)`` as three numbers."""
    if color.startswith("#"):
        return np.array([int(color[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    return np.array([float(v) for v in color[color.index("(") + 1:color.index(")")].split(",")[:3]])


def _flat(color: str, alpha: float, paper: str) -> str:
    """What ``color`` at ``alpha`` looks like on ``paper``, as one opaque colour."""
    c = np.round(_rgb(paper) + (_rgb(color) - _rgb(paper)) * alpha).astype(int)
    return "rgb({},{},{})".format(*c)


def _lab(color: str) -> np.ndarray:
    """An sRGB colour in CIE L*a*b* (D65), for measuring how different two colours look."""
    c = _rgb(color) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ c
    f = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(f > 0.008856, np.cbrt(f), 7.787 * f + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def color_difference(a: str, b: str) -> float:
    """CIE76 delta-E between two opaque colours: about 2 is just noticeable, 10 is obvious."""
    return float(np.linalg.norm(_lab(a) - _lab(b)))


def final_crossing(a: pd.Series, b) -> tuple[pd.Timestamp, float]:
    """The exact point at which ``a`` crosses below ``b`` for the last time.

    The lines are drawn straight between month-ends, so the crossing lies
    between the last month-end with ``a >= b`` and the next (which is
    :func:`last_fall_below`), found by linear interpolation. Returns the moment
    and the level there: a point ON the drawn lines, though not a data point.
    ``b`` is a series on the same dates, or a number.
    """
    i = a.index.get_loc(last_fall_below(a, b))
    gap = a - b
    d0, d1 = float(gap.iloc[i - 1]), float(gap.iloc[i])
    f = d0 / (d0 - d1)
    when = a.index[i - 1] + (a.index[i] - a.index[i - 1]) * f
    return when, round(float(a.iloc[i - 1] + f * (a.iloc[i] - a.iloc[i - 1])), _DECIMALS) + 0.0


def _halo(color: str) -> str:
    """The CSS text-shadow that outlines text in ``color``: its halo."""
    return ", ".join(f"{offset} {color}" for offset in _HALO_OFFSETS)


def _times(x: float) -> str:
    """A multiple for an annotation: x3.2, x0.58 (two significant figures)."""
    return f"{x:.1f}" if x >= 1 else f"{x:.2f}"


# --------------------------------------------------------------------------- #
#  Layout
# --------------------------------------------------------------------------- #
# Two layouts, switched by the measured column width (fit() in the script): the
# 920 px body column and a phone. Each fixes ``px_per_bit``, the one vertical
# scale both panels share; panel heights follow from the y-ranges.
#
# ``strip`` sizes the strips. From the Economy panel upward the top strip is:
# rows of event labels, the era bars with their labels just above them, and the
# leaders' segments. The bottom strip is rows of event labels only. ``plans``
# are the ways a strip's event labels may be laid out (rows, the pitch of a
# row, the font sizes to try); the script prefers a larger font, then fewer
# rows. ``bare_gap`` is the space between the panels when the bottom strip's
# labels are hidden. ``tick`` sizes a tick mark: how far it reaches above and
# below the top edge of its panel, and how thick it is; it sits in the few
# pixels between the panel and the first row of labels, so it costs no height.
# ``drop_from`` is the column width from which a strip that
# cannot hold everything DROPS items in order rather than hiding its labels
# (None: never).
_NARROW_BELOW_PX = 560
_LAYOUTS = dict(
    wide=dict(
        margin=dict(l=54, r=34, b=26), px_per_bit=58, font=12.5, drop_from=900, modebar=True,
        gdp_width=2.5, stock_width=1.8, economy_width=1.7, head=15, title=15.5, title_row=26, anchor=10.5,
        tick=dict(up=3, down=7, width=2),
        strip=dict(
            plans=dict(top=[dict(rows=2, pitch=16, fonts=[11.5, 10.5, 10]), dict(rows=3, pitch=16, fonts=[11.5, 10.5, 10])],
                       bottom=[dict(rows=2, pitch=16, fonts=[11.5, 10.5, 10]), dict(rows=3, pitch=15, fonts=[10.5, 10])]),
            era_font=10.5, era_bar=6, era_label=14, leader=16, leader_font=10.5, bare_gap=14),
        arrow_fonts=[11.5, 10.5, 9.5], band_font=11, fill_font=10.5, hint_font=10, mark_frac=0.4),
    narrow=dict(
        margin=dict(l=46, r=10, b=24), px_per_bit=46, font=11, drop_from=None, modebar=False,
        gdp_width=2.2, stock_width=1.4, economy_width=1.4, head=13.5, title=14, title_row=24, anchor=9,
        tick=dict(up=3, down=6, width=2),
        strip=dict(
            plans=dict(top=[dict(rows=2, pitch=15, fonts=[10, 9.5])], bottom=[dict(rows=2, pitch=15, fonts=[10, 9.5])]),
            era_font=9.5, era_bar=6, era_label=13, leader=14, leader_font=9.5, bare_gap=12),
        arrow_fonts=[10, 9], band_font=9.5, fill_font=9.5, hint_font=9, mark_frac=0.45),
)
# The four arrowed annotations, in date order: how each may be broken over
# lines (fewest lines first; the script takes the first that fits clear of the
# data) and where its text goes. "above": over the arrow tip, which is the
# highest point of the stock line. "under": below both lines across its own
# width and at least ``gap`` px under the tip -- which, for a tip above the zero
# line, means hung just under that line.
_ARROWS = dict(
    arrow_trough=dict(mode="under", wraps=[
        "{trough} trough: Chinese stocks<br>×{trough_x} US stocks since Dec 1998",
        "{trough} trough:<br>Chinese stocks ×{trough_x}<br>US stocks since Dec 1998"]),
    arrow_peak=dict(mode="above", wraps=[
        "{peak} peak: Chinese stocks<br>×{peak_x} US stocks since Dec 1998",
        "{peak} peak:<br>Chinese stocks ×{peak_x}<br>US stocks since Dec 1998",
        "{peak} peak:<br>Chinese stocks<br>×{peak_x} US stocks<br>since Dec 1998"]),
    arrow_economy=dict(mode="under", wraps=[
        "Stocks fall behind the economy,<br>and stay behind",
        "Stocks fall behind<br>the economy,<br>and stay behind",
        "Stocks fall<br>behind the<br>economy, and<br>stay behind"]),
    arrow_parity=dict(mode="under", wraps=[
        "US stocks pull ahead,<br>and stay ahead",
        "US stocks<br>pull ahead, and<br>stay ahead",
        "US stocks<br>pull ahead,<br>and stay<br>ahead"]),
)
# The two labels by the fills. "lag" goes inside the grey, where it is deepest
# between these dates. "outpace" cannot go inside the periwinkle, which is too
# thin to hold it: it goes in clear space as near as possible to the periwinkle
# between these dates, in periwinkle type.
_FILL_LABELS = dict(
    fill_ahead=dict(kind="ahead", wraps=["Stocks outpace<br>the economy", "Stocks<br>outpace the<br>economy"],
                    start="2006-01-01", end="2011-06-30"),
    fill_behind=dict(kind="behind", wraps=["Stocks lag<br>the economy", "Stocks<br>lag the<br>economy"],
                     start="2015-06-30", end="2022-06-30"),
)
# The small labels either side of each panel's zero line. In the bottom panel
# they stand left of the anchor. In the top panel the anchor is mid-series, so
# "China ahead" would be wrong for the years before it: the labels there say
# what a move away from the 1978 level means instead, and stand right of the
# anchor, as near it as the line itself leaves room.
_HINTS = dict(zero_up="China ahead", zero_down="US ahead",
              gap_up=f"Gap narrower than in {GDP_ANCHOR_YEAR}", gap_down=f"Gap wider than in {GDP_ANCHOR_YEAR}")


def _strip_heights(layout: dict, top: tuple[int, int] | None = None, bottom: tuple[int, int] | None = None) -> dict:
    """Pixel offsets inside the two strips, for ``(rows, pitch)`` of event labels in each.

    ``top`` and ``bottom`` default to the layout's roomiest plans; ``(0, 0)``
    means the labels are hidden. Returns, in px above the Economy panel: where
    the era bars start (``era``), the baseline of their labels (``era_label``),
    where the leaders' segments start and end (``leader``, ``top``, the latter
    being the top strip's height); and ``bottom``, the bottom strip's height
    (the gap between the panels). The script's ``geometry`` is the same
    arithmetic.
    """
    st = layout["strip"]
    rows, pitch = top if top is not None else (st["plans"]["top"][-1]["rows"], st["plans"]["top"][-1]["pitch"])
    b_rows, b_pitch = (bottom if bottom is not None
                       else (st["plans"]["bottom"][-1]["rows"], st["plans"]["bottom"][-1]["pitch"]))
    era = 3 + rows * pitch + 3 if rows else 3
    era_label = era + st["era_bar"] + 2
    leader = era_label + st["era_label"] + 2
    return dict(era=era, era_label=era_label, leader=leader, top=leader + st["leader"],
                bottom=3 + b_rows * b_pitch + 3 if b_rows else st["bare_gap"])


def _geometry(layout: dict, top_span: float, bottom_span: float, strips: dict) -> dict:
    """Figure height and the two y-domains that give both panels one scale.

    Each panel is ``px_per_bit`` times its y-span tall, with the bottom strip
    between them and the title row and the top strip above; the domains are
    those heights as fractions of the plot area.
    """
    ppb, m = layout["px_per_bit"], layout["margin"]
    top_h, bottom_h = ppb * top_span, ppb * bottom_span
    plot_h = top_h + strips["bottom"] + bottom_h
    t = layout["title_row"] + strips["top"] + 2
    return dict(height=round(plot_h + t + m["b"]), t=t, plot_h=plot_h, top_h=top_h, bottom_h=bottom_h,
                top=[1 - top_h / plot_h, 1.0], bottom=[0.0, bottom_h / plot_h])


# --------------------------------------------------------------------------- #
#  The figure
# --------------------------------------------------------------------------- #
def build_china_figure(
    start_year: int = START_YEAR,
    show_multiple: bool = SHOW_MULTIPLE,
    tiers: tuple[str, ...] = ("label", "tick"),
    peers: tuple[str, ...] = (),
) -> go.Figure:
    """Assemble the figure in its default state: the completed chart.

    Traces, top panel then bottom, each always present and only ever restyled
    (``layout.meta.trace`` names their positions): any peer-country lines, the
    economy line, its anchor marker and its playback head; the hatched band,
    the two fills, the re-anchored economy line, the stock line, the anchor
    marker, the head, and the numbered markers used when the arrowed
    annotations become a key.

    Everything else is a layout shape or annotation, so that it follows the
    data under zoom and during playback: the plain access band and its darker
    first stretch, the band labels, the two zero lines and the labels either
    side of them, the leaders' segments and the era bars with their labels, one
    dashed line per labelled event with a label of its own or one shared with its
    group, one short mark per tick, the arrowed annotations and the labels by
    the fills. ``layout.meta`` lists them all, with the dates from which
    each is shown. No annotation has a background: each carries a halo
    (``font.shadow``) in the colour behind it. (The title and the panels' names
    are not in the figure at all: they are HTML, added by
    :func:`china_figure_html`.)

    Parameters
    ----------
    start_year
        First GDP year drawn. Must precede the stock anchor.
    show_multiple
        Append the multiple ``2^x`` to each value in the hover box.
    tiers
        Which event tiers to draw: labelled markers and ticks. A "stored" event,
        if asked for, is drawn as a labelled marker.
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
    # The four annotated points. The trough is the low before the peak; the two
    # crossings are exact points on the drawn lines, between month-ends.
    peak = s.idxmax()
    trough = s[:peak].idxmin()
    behind_economy = final_crossing(s, e)
    behind_parity = final_crossing(s, 0.0)

    # Plain lists, not arrays: plotly.py would base64-encode arrays, and the
    # figure JSON should stay readable (and auditable for stray index levels).
    gdp_x, gdp_y = [_iso(d) for d in g.index], [float(v) for v in g]
    month_x = [_iso(d) for d in s.index]
    stock_y, economy_y = [float(v) for v in s], [float(v) for v in e]

    first = pd.Timestamp(year=start_year, month=1, day=1)
    x_range = [_iso(first), _iso(first + (cutoff - first) * (1 + WINDOW_MARGIN))]
    # Headroom over the top panel's line keeps its top gridline clear of the
    # panel's name. In the bottom panel the room over the stock line's peak
    # holds that peak's annotation, and the room under the line the other three.
    y_top = [round(min(gdp_y) - 0.2, 2), round(max(gdp_y) + 0.45, 2)]
    y_bottom = [round(min(stock_y + economy_y) - 0.85, 2), round(max(stock_y + economy_y) + 0.42, 2)]

    wide, light = _LAYOUTS["wide"], _ALPHA["light"]
    st = wide["strip"]
    strips = _strip_heights(wide)
    geo = _geometry(wide, y_top[1] - y_top[0], y_bottom[1] - y_bottom[0], strips)
    pitch = {"economy": st["plans"]["top"][-1]["pitch"], "stocks": st["plans"]["bottom"][-1]["pitch"]}
    quiet = dict(hoverinfo="skip", showlegend=False)             # Plotly never labels a point
    top, bottom = dict(xaxis="x", yaxis="y"), dict(xaxis="x", yaxis="y2")

    def ink(kind: str) -> str:
        return with_alpha(_INK, _TEXT_ALPHA[kind])

    def navy(kind: str) -> str:
        return with_alpha(_CONTEXT, _TEXT_ALPHA[kind])

    def on(alpha: float, color: str = _CONTEXT) -> str:          # a tint, as the opaque colour it makes on the page
        return _flat(color, alpha, PAPER)

    def frac(when) -> float:                                     # position along the full x-range, 0..1
        span = _days(x_range[1])[0] - _days(x_range[0])[0]
        return float((_days(when)[0] - _days(x_range[0])[0]) / span)

    def stamp(when) -> str:                                      # a moment between month-ends
        return pd.Timestamp(when).strftime("%Y-%m-%d %H:%M:%S")

    def dated(notes) -> list[dict]:                              # a parent's notes, in date order
        return [dict(date=n.date, when=n.when, text=n.text) for n in sorted(notes, key=lambda n: n.date)]

    # ---- Traces ----
    fig = go.Figure()
    ring = dict(color=PAPER, width=1.5)
    for code in peers:
        peer = rebased(gdp, code)
        peer = peer[peer.index.year >= start_year]
        fig.add_trace(go.Scatter(x=[_iso(d) for d in peer.index], y=[float(v) for v in peer],
                                 mode="lines", name=f"peer {code}",
                                 line=dict(color=_PEER_COLOR, width=1.2), **top, **quiet))
    fig.add_trace(go.Scatter(x=gdp_x, y=gdp_y, mode="lines", name="gdp",
                             line=dict(color=_GDP_COLOR, width=wide["gdp_width"]), **top, **quiet))
    gdp_anchor = _iso(g[g.index.year == GDP_ANCHOR_YEAR].index[0])
    fig.add_trace(go.Scatter(x=[gdp_anchor], y=[0.0], mode="markers", name="anchor_top",
                             marker=dict(size=wide["anchor"], color=PAPER, line=dict(color=_GDP_COLOR, width=2)),
                             **top, **quiet))
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="gdp_head", cliponaxis=False,
                             marker=dict(size=9, color=_GDP_COLOR, line=ring), **top, **quiet))

    # The hatched band is a trace, not a shape: only a trace's fill can carry a
    # pattern. It is first in the bottom panel, so everything else draws over it.
    hatched = next(band for band in BANDS if band.kind == "none")
    fig.add_trace(go.Scatter(
        x=[x_range[0], hatched.end, hatched.end, x_range[0]], y=[y_bottom[0], y_bottom[0], y_bottom[1], y_bottom[1]],
        mode="none", name="band_none", fill="toself",
        fillpattern=dict(shape="/", size=8, solidity=0.1, fillmode="replace",
                         bgcolor=with_alpha(_CONTEXT, light["band_none"]), fgcolor=with_alpha(_CONTEXT, light["hatch"])),
        **bottom, **quiet))
    t_ms = np.asarray(pd.DatetimeIndex(s.index).as_unit("ms").asi8, dtype=float)
    runs = fill_polygons(t_ms, np.array(stock_y), np.array(economy_y))
    for side, color in (("behind", with_alpha(_INK, light["behind"])),
                        ("ahead", with_alpha(_STOCK_COLOR, light["ahead"]))):
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
    anchor = _iso(STOCK_ANCHOR)
    fig.add_trace(go.Scatter(x=[anchor], y=[0.0], mode="markers", name="anchor_bottom",
                             marker=dict(size=wide["anchor"], color=PAPER, line=dict(color=_INK, width=2)),
                             **bottom, **quiet))
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="stock_head", cliponaxis=False,
                             marker=dict(size=9, color=_STOCK_COLOR, line=ring), **bottom, **quiet))
    # Numbered markers: empty unless the arrowed annotations fall back to a key.
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers+text", name="markers", text=["1", "2", "3", "4"],
                             textposition="middle center", textfont=dict(size=9, color=PAPER),
                             marker=dict(size=14, color=_INK, line=dict(color=PAPER, width=1)),
                             cliponaxis=False, **bottom, **quiet))
    names = [t.name for t in fig.data]
    trace = {n: names.index(n) for n in ("gdp", "anchor_top", "gdp_head", "band_none", "fill_behind", "fill_ahead",
                                         "economy", "stock", "anchor_bottom", "stock_head", "markers")}
    trace["peers"] = [i for i, n in enumerate(names) if n.startswith("peer ")]

    # ---- Shapes and annotations, registered as they are added ----
    shapes, annotations, role = [], [], {}

    def shape(**kw) -> int:
        shapes.append(kw)
        return len(shapes) - 1

    def note(name: str | None = None, *, size: float, color: str, behind: str = PAPER, **kw) -> int:
        """A label with no box: its halo is the colour ``behind`` it."""
        kw.setdefault("showarrow", False)
        annotations.append(dict(font=dict(size=size, color=color, shadow=_halo(behind)), borderpad=0, **kw))
        if name:
            role[name] = len(annotations) - 1
        return len(annotations) - 1

    # Access bands: the years before the data. The hatched one is the trace
    # above; the plain one is a rectangle, with a second over its first stretch.
    bands = []
    for band in BANDS:
        start = x_range[0] if band.start is None else band.start
        none = band.kind == "none"
        entry = dict(start=band.start, end=band.end, kind=band.kind, wraps=list(band.wraps),
                     description=band.description, trace=trace["band_none"] if none else None, shape=None, early=None)
        if not none:
            entry["shape"] = shape(type="rect", xref="x", yref="y2 domain", x0=start, x1=band.end, y0=0, y1=1,
                                   fillcolor=with_alpha(_CONTEXT, light["band_limited"]), line=dict(width=0), layer="below")
        if band.early_end:
            entry["early"] = dict(
                end=band.early_end, description=band.early_description,
                shape=shape(type="rect", xref="x", yref="y2 domain", x0=start, x1=band.early_end, y0=0, y1=1,
                            fillcolor=with_alpha(_CONTEXT, light["band_early"]), line=dict(width=0), layer="below"))
        tint = light["band_none" if none else "band_limited"]
        entry["annotation"] = note(xref="x domain", yref="y2 domain", x=(frac(start) + frac(band.end)) / 2, y=band.y,
                                   xanchor="center", yanchor="middle", align="center", text=band.wraps[-2],
                                   size=wide["band_font"], color=navy("band"), behind=on(tint))
        bands.append(entry)

    # The zero lines: ink, a little heavier than the gridlines, above them and
    # below the data. The top one spans the plot; the bottom one starts where
    # the index data do. Either side of each, small labels say which way is which.
    # (In data coordinates: plotly.js cannot put a domain-referenced shape "between".)
    line = dict(color=_INK, width=1.2)
    zero = dict(top=shape(type="line", xref="x", yref="y", x0=x_range[0], x1=x_range[1], y0=0, y1=0, line=line,
                          layer="between"),
                bottom=shape(type="line", xref="x", yref="y2", x0=anchor, x1=x_range[1], y0=0, y1=0, line=line,
                             layer="between"))
    hint = dict(size=wide["hint_font"], color=ink("hint"))
    left_of = dict(xref="x", yref="y2", x=anchor, y=0, xanchor="right", xshift=-10, behind=on(light["band_limited"]))
    note("zero_up", yanchor="bottom", yshift=3, text=_HINTS["zero_up"], **hint, **left_of)
    note("zero_down", yanchor="top", yshift=-3, text=_HINTS["zero_down"], **hint, **left_of)
    right_of = dict(xref="x", yref="y", x=f"{GDP_ANCHOR_YEAR + 5}-01-01", y=0, xanchor="left")   # the script sets x
    note("gap_up", yanchor="bottom", yshift=3, text=_HINTS["gap_up"], **hint, **right_of)
    note("gap_down", yanchor="top", yshift=-3, text=_HINTS["gap_down"], **hint, **right_of)

    # The arrowed annotations. Each arrow ends ON its point (no standoff). The
    # script decides where each text goes (ax, ay and the line breaks).
    words = dict(trough=_month(trough), trough_x=_times(2.0 ** s[trough]),
                 peak=_month(peak), peak_x=_times(2.0 ** s[peak]))
    points = dict(arrow_trough=(trough, float(s[trough])), arrow_peak=(peak, float(s[peak])),
                  arrow_economy=behind_economy, arrow_parity=behind_parity)
    arrows = []
    for name, (when, level) in points.items():
        wraps = [w.format(**words) for w in _ARROWS[name]["wraps"]]
        text = wraps[0].replace("<br>", " ")
        note(name, xref="x", yref="y2", x=stamp(when), y=level, text=wraps[1], showarrow=True,
             arrowhead=2, arrowsize=1, arrowwidth=1, arrowcolor=ink("arrow"), standoff=0, ax=-70, ay=60,
             align="center", size=wide["arrow_fonts"][0], color=ink("arrow"))
        # The same words for the key under a narrow plot, led by the month (and still in sentence case).
        first = text.split()[0]
        key = text if text.startswith(_month(when)) else (
            f"{_month(when)}: {text if first in _PROPER else text[0].lower() + text[1:]}")
        arrows.append(dict(role=name, date=stamp(when), y=level, month=_month(when), mode=_ARROWS[name]["mode"],
                           wraps=wraps, text=text, key=key))

    # The labels by the fills; placed by the script.
    fills = []
    for name, spec in _FILL_LABELS.items():
        behind = spec["kind"] == "behind"
        note(name, xref="x", yref="y2", x=spec["start"], y=1.0, text=spec["wraps"][0], align="center",
             xanchor="center", yanchor="middle", visible=False, size=wide["fill_font"],
             color=ink("fill") if behind else _STOCK_COLOR, behind=on(light["behind"], _INK) if behind else PAPER)
        fills.append(dict(role=name, **spec))

    # Leaders: one continuous row of segments in two alternating tints, a
    # left-pointing marker where a segment began before the plot does, and a
    # label inside the segment, left-aligned at its start.
    def above(px: float) -> float:                       # a height above the Economy panel, as a y-domain value
        return 1 + px / geo["top_h"]

    leaders = []
    for n, who in enumerate(LEADERS):
        end = who.end or x_range[1]
        tint = light["leader"][n % 2]
        middle = strips["leader"] + st["leader"] // 2
        leaders.append(dict(
            start=who.start, end=who.end, label=who.label, description=who.description, tint=n % 2,
            shape=shape(type="rect", xref="x", yref="y domain", x0=who.start, x1=end,
                        y0=above(strips["leader"]), y1=above(strips["top"]),
                        fillcolor=with_alpha(_CONTEXT, tint), line=dict(width=0), layer="below"),
            tip=shape(type="path", xref="x domain", yref="y domain", xsizemode="pixel", ysizemode="pixel",
                      xanchor=0, yanchor=above(middle), path="M-3,-5L-10,0L-3,5Z",
                      fillcolor=with_alpha(_CONTEXT, light["era"]), line=dict(width=0), visible=who.start < x_range[0]),
            annotation=note(xref="x", yref="y domain", x=max(who.start, x_range[0]), y=1, xanchor="left", xshift=5,
                            yanchor="middle", yshift=middle, text=who.label,
                            size=st["leader_font"], color=navy("leader"), behind=on(tint))))

    # Eras: a thin bar, the same marker where one began before the plot does,
    # and a label just above the bar, left-aligned at its start.
    eras = []
    for era in ERAS:
        middle = strips["era"] + st["era_bar"] / 2
        eras.append(dict(
            start=era.start, end=era.end, label=era.label, description=era.description, drop_first=era.drop_first,
            notes=dated(era.notes),
            bar=shape(type="rect", xref="x", yref="y domain", x0=era.start, x1=era.end,
                      y0=above(strips["era"]), y1=above(strips["era"] + st["era_bar"]),
                      fillcolor=with_alpha(_CONTEXT, light["era"]), line=dict(width=0), layer="below"),
            tip=shape(type="path", xref="x domain", yref="y domain", xsizemode="pixel", ysizemode="pixel",
                      xanchor=0, yanchor=above(middle), path="M-3,-4L-9,0L-3,4Z",
                      fillcolor=with_alpha(_CONTEXT, light["era"]), line=dict(width=0), visible=era.start < x_range[0]),
            annotation=note(xref="x", yref="y domain", x=max(era.start, x_range[0]), y=1, xanchor="left",
                            yanchor="bottom", yshift=strips["era_label"], text=era.label,
                            size=st["era_font"], color=navy("era"))))

    # Events, by tier. A labelled marker is a dashed line through the event's
    # own panel and a label in the strip above it; events in one group share a
    # label, which the first of them carries, and keep a line each. A tick is a
    # short solid navy mark across the top edge of its panel and nothing else.
    # The script assigns each label a row and a place along its line.
    drawn = [ev for ev in EVENTS if ev.tier in tiers and x_range[0] <= ev.date <= _iso(cutoff)]
    events = []
    for panel, domain, height in (("economy", "y domain", geo["top_h"]), ("stocks", "y2 domain", geo["bottom_h"])):
        mine = [ev for ev in drawn if ev.panel == panel]
        labelled = [ev for ev in mine if ev.tier != "tick"]
        lead_of, rows = {}, 0                    # group -> (index of the event that carries its label, its row)
        for ev in mine:
            entry = dict(date=ev.date, tier=ev.tier, panel=ev.panel, label=ev.label, description=ev.description,
                         notes=dated(ev.notes), text=None, short=None, lead=None, annotation=None,
                         narration_text=ev.narration_text, image=ev.image)
            if ev.tier == "tick":
                mark = wide["tick"]
                entry["shape"] = shape(type="line", xref="x", yref=domain, x0=ev.date, x1=ev.date,
                                       y0=1 - mark["down"] / height, y1=1 + mark["up"] / height,
                                       line=dict(color=with_alpha(_CONTEXT, light["tick"]), width=mark["width"]),
                                       layer="below")
                events.append(entry)
                continue
            if ev.group in lead_of:              # shares the label that an earlier event carries
                entry["lead"], row = lead_of[ev.group]
            else:
                row, rows = rows % 2, rows + 1
                members = [m for m in labelled if ev.group and m.group == ev.group] or [ev]
                entry["text"] = f"{ev.group}: " + " · ".join(m.label for m in members) if ev.group else ev.label
                entry["short"] = ev.short
                entry["annotation"] = note(xref="x", yref=domain, x=ev.date, y=1, yanchor="bottom",
                                           yshift=3 + row * pitch[panel], text=entry["text"],
                                           size=st["plans"]["top"][-1]["fonts"][0], color=ink("event"))
                if ev.group:
                    lead_of[ev.group] = (len(events), row)
            entry["shape"] = shape(type="line", xref="x", yref=domain, x0=ev.date, x1=ev.date, y0=0,
                                   y1=1 + (2 + row * pitch[panel]) / height, opacity=_EVENT_LINE_OPACITY,
                                   line=dict(color=_INK, width=1, dash="dash"), layer="below")
            events.append(entry)

    # ---- Axes: one y-axis per panel, no titles, no tick marks ----
    def y_axis(domain, y_range):
        ticks = list(range(int(np.ceil(y_range[0])), int(np.floor(y_range[1])) + 1))
        unit = " bit" if abs(ticks[-1]) == 1 else " bits"
        return dict(domain=domain, range=y_range, fixedrange=True, anchor="x", automargin=False,
                    tickvals=ticks, ticktext=[_signed(v, unit if v == ticks[-1] else "") for v in ticks],
                    ticks="", tickfont=dict(color=LABEL), gridcolor=GRID, zeroline=False)

    edges = [pd.Timestamp(d) for era in ERAS for d in (era.start, era.end)]
    edges += [pd.Timestamp(d) for band in BANDS for d in (band.end, band.early_end) if d]
    start, end = g.index[0], cutoff
    # The pace eases near labelled events and era boundaries; a tick does not slow it.
    marked = [pd.Timestamp(ev.date) for ev in drawn if ev.tier != "tick"]
    moments = [t for t in marked + edges if start <= t <= end]
    fig.update_layout(
        # No width: the graph div fills its container until fit() sizes it.
        autosize=True, height=geo["height"], font=dict(size=wide["font"]),
        margin=dict(l=wide["margin"]["l"], r=wide["margin"]["r"], t=geo["t"], b=wide["margin"]["b"]),
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
            trace=trace, ann=role, zero=zero, events=events, eras=eras, leaders=leaders, leader_note=LEADER_NOTE,
            bands=bands, arrows=arrows, fills=fills, anchor=anchor,
            anchors=[dict(trace="anchor_top", panel="economy", date=gdp_anchor, text=f"{GDP_ANCHOR_YEAR} = 0"),
                     dict(trace="anchor_bottom", panel="stocks", date=anchor, text="Dec 1998 = 0")],
            hover=dict(
                gdp=[f"Economy ({d.year}): {_bits(v, show_multiple)}" for d, v in g.items()],
                stock=[f"Stocks ({_month(d)}): {_bits(v, show_multiple)}" for d, v in s.items()],
                economy=[f"Economy ({_month(d)}): {_bits(v, show_multiple)}" for d, v in e.items()],
            ),
            # Playback opens on a single dot: the first data point.
            play=dict(start=_iso(start), end=_iso(end), fade_years=_FADE_YEARS, speeds=list(SPEEDS),
                      min_window_years=MIN_WINDOW_YEARS, margin=WINDOW_MARGIN,
                      seconds_per_year=[round(float(v), 4) for v in pace_profile(moments, start, end)]),
            view=dict(x=x_range, y=y_top, y2=y_bottom),
            layouts=_LAYOUTS, narrow_below=_NARROW_BELOW_PX,
            budget=dict(title=TITLE_ROW_MAX_PX, top=TOP_STRIP_MAX_PX, bottom=BOTTOM_STRIP_MAX_PX),
            alpha=_ALPHA, text_alpha=_TEXT_ALPHA, event_line_opacity=_EVENT_LINE_OPACITY, halo=list(_HALO_OFFSETS),
            colors=dict(gdp=_GDP_COLOR, stock=_STOCK_COLOR, context=_CONTEXT, context_dark=_CONTEXT_DARK),
            light=dict(ink=_INK, label=LABEL, grid=GRID, paper=PAPER, axis=with_alpha(LABEL, 0.5)),
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
<div class="china-title">__TITLE__</div>
<div class="china-head china-head-top">Economy</div>
<div class="china-head china-head-bottom">Stocks</div>
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
  <button type="button" class="china-speed" title="Playback speed">1×</button>
  <div class="china-scrub-wrap">
    <input type="range" class="china-scrub" min="0" max="4000" step="1" value="4000"
      aria-label="Move through time">
  </div>
  <span class="china-end" title="The end of the timeline"></span>
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
/* The title, top-left above the strips. */
.china-title { position: absolute; left: 0; top: 0; z-index: 2; pointer-events: none; white-space: nowrap;
  line-height: 1.3; font-weight: 700; color: var(--bs-body-color, #1f2328); }
/* Each panel's name, top-left: the bold word in the series colour. No box
   behind it: a halo in whatever colour IS behind it (the page for the top one,
   the access band for the bottom one), so nothing reads as crossing it. */
.china-head { position: absolute; left: 0; top: 0; z-index: 2; pointer-events: none; text-align: left;
  line-height: 1.3; font-weight: 700; --halo: var(--bs-body-bg, #fff);
  text-shadow: -1.5px 0 var(--halo), 1.5px 0 var(--halo), 0 -1.5px var(--halo), 0 1.5px var(--halo),
    -1.1px -1.1px var(--halo), 1.1px -1.1px var(--halo), -1.1px 1.1px var(--halo), 1.1px 1.1px var(--halo); }
.china-head-top { color: __GDP__; }
.china-head-bottom { color: __STOCK__; --halo: var(--china-band, var(--bs-body-bg, #fff)); }
.china-overlay { position: absolute; inset: 0; z-index: 3; pointer-events: none; overflow: hidden; }
.china-guide { position: absolute; left: 0; top: 0; width: 1px; display: none;
  background: var(--bs-body-color, #1f2328); opacity: .28; }
.china-dot { position: absolute; left: -4.5px; top: -4.5px; width: 9px; height: 9px; display: none;
  box-sizing: border-box; border-radius: 50%; border: 1.5px solid var(--bs-body-bg, #fff); }
.china-dot-gdp, .china-dot-economy { background: __GDP__; }
.china-dot-stock { background: __STOCK__; }
/* Page colours throughout, so the box follows the site's dark mode. */
.china-tip { position: absolute; left: 0; top: 0; display: none; max-width: 310px;
  padding: 6px 9px; border-radius: 4px; font-size: 13px; line-height: 1.45; text-align: left;
  color: var(--bs-body-color, #1f2328); background: var(--bs-body-bg, #fff);
  border: 1px solid var(--bs-border-color, #cfd3d8); box-shadow: 0 2px 8px rgba(0, 0, 0, .14); }
.china-tip-row { white-space: nowrap; }
.china-tip-key { display: inline-block; width: 9px; height: 9px; margin-right: 6px; border-radius: 50%; }
.china-tip-gdp .china-tip-key, .china-tip-economy .china-tip-key { background: __GDP__; }
.china-tip-stock .china-tip-key { background: __STOCK__; }
.china-tip-note { font-size: 12px; line-height: 1.35; }
.china-tip-note + .china-tip-note { margin-top: 4px; }
/* A note: a dated line under the text of the event or era it belongs to. */
.china-tip-note.china-tip-sub { margin-top: 2px; padding-left: 10px; opacity: .85; }
.china-tip-note + .china-tip-row { margin-top: 4px; padding-top: 4px; border-top: 1px solid var(--bs-border-color, #cfd3d8); }
/* The key: where direct labels go when there is no room for them beside the
   data (a phone). The numbers match the markers on the stock line. */
.china-key { box-sizing: border-box; margin: .1rem auto .35rem; padding: 0 8px; font-size: 12px; line-height: 1.35;
  text-align: left; color: var(--bs-body-color, #1f2328); }
.china-key[hidden], .china-key-row[hidden] { display: none; }
.china-key-row { display: flex; align-items: baseline; gap: 7px; margin: 3px 0; }
.china-key-n { flex: none; width: 15px; height: 15px; border-radius: 50%; font-size: 9.5px; line-height: 15px;
  text-align: center; background: var(--bs-body-color, #1f2328); color: var(--bs-body-bg, #fff); }
.china-key-line { flex: none; width: 15px; height: 0; border-top: 1.5px solid var(--bs-body-color, #1f2328);
  transform: translateY(-3px); }
/* Controls. */
.china-controls { --thumb-d: 12.5px; display: flex; align-items: center; gap: 12px; margin: .15rem auto 1.3rem;
  box-sizing: border-box; padding: 0 6px; }
.china-play { flex: none; width: 28px; height: 28px; padding: 0;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
  border-radius: 50%; border: 1px solid var(--bs-border-color, #cfd3d8);
  background: transparent; color: var(--bs-body-color, #1f2328); }
.china-play:hover, .china-speed:hover { border-color: var(--bs-body-color, #1f2328); }
.china-play:focus-visible, .china-speed:focus-visible, .china-scrub:focus-visible { outline: 2px solid __STOCK__; outline-offset: 2px; }
.china-play svg { fill: currentColor; }
.china-play .china-ico-pause, .china-play.is-playing .china-ico-play { display: none; }
.china-play.is-playing .china-ico-pause { display: inline; }
/* The speed toggle: small and quiet beside the play button. */
.china-speed { flex: none; min-width: 30px; height: 22px; margin-left: -4px; padding: 0 5px; cursor: pointer;
  border-radius: 11px; border: 1px solid var(--bs-border-color, #cfd3d8); background: transparent;
  font: inherit; font-size: 11.5px; line-height: 1; font-variant-numeric: tabular-nums lining-nums;
  color: var(--bs-body-color, #1f2328); opacity: .75; }
.china-speed.is-fast { opacity: 1; border-color: var(--bs-body-color, #1f2328); }
.china-end { flex: none; min-width: 2.4em; font-size: 13px; line-height: 1;
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
  var controls = $(".china-controls"), playBtn = $(".china-play"), speedBtn = $(".china-speed"), scrub = $(".china-scrub");
  var scrubWrap = $(".china-scrub-wrap"), endOut = $(".china-end"), keyBox = $(".china-key");
  var mark = $(".china-year-mark"), guide = $(".china-guide"), tip = $(".china-tip"), title = $(".china-title");
  var heads = [$(".china-head-top"), $(".china-head-bottom")];
  var dotEl = {gdp: $(".china-dot-gdp"), stock: $(".china-dot-stock"), economy: $(".china-dot-economy")};
  var DAY = 86400000, YEAR = 31557600000, HOUR = 3600000;          // ms
  // How long a label may wait for room after its line appears, in years: the tiers tried, in order.
  var WAITS = [0.5, 1, 2, Infinity];
  var PL, M, TR, AN, G, S, PEERS, EV, ERAS, LEADERS, BANDS, ARROWS, FILLS, ANCHORS, TAU, NP, TOTAL;
  var T0, T1, TA, TG, X0, X1, FADE, FONT;
  var L = null, GEO = null, P = null, FIT = null, lastW = 0, sent = {};
  var playhead = 0, playing = false, raf = 0, busy = false, pending = null, speed = 1;
  var syncing = false, dragging = false, down = null, themeKey = "", halo = "";

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
  // How far right of a date's position the figure extends `late` years after the
  // playhead reaches that date: the room a label there has without sticking out.
  function roomAt(t, plotW, late) {
    return plotW + L.margin.r - 2 - (t - X0) / (windowEnd(Math.min(t + (late || 0) * YEAR, T1)) - X0) * plotW;
  }
  // The playhead date from which a box reaching `off` px right of the date t's
  // position is inside the figure: t itself, or later if the window must grow first.
  function fitsFrom(t, off, plotW) {
    var room = plotW + L.margin.r - 2 - off;
    if (room <= 0) return T1;
    var need = (t - X0) * plotW / room;                           // the window that takes, in ms
    if (need <= M.play.min_window_years * YEAR) return t;
    return clamp(X0 + need / (1 + M.play.margin), t, T1);
  }
  // What is in view: the growing window while the playhead is short of the end,
  // otherwise whatever the reader has zoomed or panned to.
  function view() {
    if (playhead < T1) return [X0, windowEnd(playhead)];
    var xa = gd._fullLayout.xaxis;
    return [xa.r2l(xa.range[0]), xa.r2l(xa.range[1])];
  }

  // ---- Measured text ---------------------------------------------------------------
  var ctx = document.createElement("canvas").getContext("2d"), sizes = {};
  function textSize(html, px) {
    var key = px + "|" + html;
    if (sizes[key]) return sizes[key];
    ctx.font = px + "px " + FONT;
    var lines = String(html).split("<br>"), w = 0;
    lines.forEach(function (ln) { w = Math.max(w, ctx.measureText(ln).width); });
    return (sizes[key] = {w: w, h: lines.length * px * 1.3});       // 1.3 is Plotly's line spacing
  }

  // The playhead date from which a bar that starts at t0 (or at the plot's left
  // edge, if it began before the plot does) has grown to w px; null if never.
  function longFrom(t0, w, plotW) {
    var a = Math.max(t0, X0), lo = a, hi = T1;
    function len(T) { return (T - a) / (windowEnd(T) - X0) * plotW; }
    if (len(hi) < w) return null;
    for (var k = 0; k < 40; k++) { var mid = (lo + hi) / 2; if (len(mid) >= w) hi = mid; else lo = mid; }
    return hi;
  }

  // ---- A strip of event labels: a row and a place for every label ------------------
  // Each label goes in one of `rows` rows (0 nearest the plot): centred on its
  // line if it can be, otherwise slid along it or set to one side (SPOTS: how
  // far along the label its line stands). No two labels in a row may come
  // within 8 px, and no label may sit across another event's line where that
  // line reaches it (a line climbs to its own label's row). Taken in date
  // order, all that matters about the labels already placed is how far right
  // each row extends and where the last line to climb to each row is, so the
  // search is over those numbers, remembering the dead ends. It is done at the
  // scale of the FINISHED chart: playback and zooming only ever spread the
  // lines further apart, so what fits there fits throughout. `late` is how
  // many years a label may wait for room after its line appears (the playhead
  // is near the figure's right edge then). `says` is what each label reads.
  // Returns null if nothing fits.
  var SPOTS = [0.5, 1, 0.75, 0.625, 0.375, 0.25, 0.875, 0.125, 0];
  function reachOf(x, w, spot) {             // where a label starts and ends, for a line at x
    return spot === 1 ? [x - 3 - w, x - 3] : spot === 0 ? [x + 3, x + 3 + w] : [x - spot * w, x + (1 - spot) * w];
  }
  function placeStrip(evs, says, plotW, font, rows, late) {
    var scale = plotW / (X1 - X0), lo = -L.margin.l + 2, hi = plotW + L.margin.r - 2;
    var it = evs.map(function (e, i) {
      return {x: (e.t - X0) * scale, w: textSize(says[i], font).w + 4, room: late === Infinity ? Infinity : roomAt(e.t, plotW, late)};
    });
    var chosen = [], dead = {};
    function fx(v) { return v.toFixed(1); }
    function go(i, right, reach) {
      if (i === it.length) return true;
      var key = i + "|" + right.map(fx).join(",") + "|" + reach.map(fx).join(",");
      if (dead[key]) return false;
      var x = it[i].x, q;
      for (var row = 0; row < rows; row++) for (var k = 0; k < SPOTS.length; k++) {
        var s = reachOf(x, it[i].w, SPOTS[k]);
        var ok = s[0] >= lo && s[1] <= hi && s[1] - x <= it[i].room
          && s[0] >= right[row] + 8          // clear of the label before it in this row
          && s[0] - 3 >= reach[row];         // and of every earlier line that climbs this high
        for (q = 0; ok && q <= row; q++) ok = x >= right[q] + 3;   // its own line clears the labels below
        if (!ok) continue;
        var r2 = right.slice(), c2 = reach.slice();
        r2[row] = Math.max(r2[row], s[1]);
        for (q = 0; q <= row; q++) c2[q] = Math.max(c2[q], x);
        chosen[i] = {row: row, spot: SPOTS[k]};
        if (go(i + 1, r2, c2)) return true;
      }
      dead[key] = true;
      return false;
    }
    var start = [];
    for (var r = 0; r < rows; r++) start.push(-1e9);
    return go(0, start, start.slice()) ? chosen.slice(0, it.length) : null;
  }
  // Fit one panel's strip of event labels. Everything, with no label waiting
  // more than half a year for room, in the largest type and then the fewest
  // rows that work; failing that, waits of up to a year; only then the
  // smallest type, and after that longer waits. At each step the labels are
  // tried in full first, and then with their short forms where they have one.
  // Only events that carry a label take part: a tick has none, and an event
  // that shares its group's label follows the one that carries it. If nothing
  // works at the full column, events are given up from the end of their list
  // (which is in the order they are to be kept). On a narrower column the same
  // events lose only their labels, in the same order, and keep their lines and
  // hover text; on a phone every label is hidden and the rows are given back.
  function fitStrip(panel, plotW, w) {
    var all = EV.filter(function (e) { return e.panel === panel && e.annotation !== null; });
    var canDrop = L.drop_from !== null && w >= L.drop_from, canBare = L.drop_from !== null && !canDrop, combos = [];
    var forms = all.some(function (e) { return e.short; }) ? 2 : 1;
    L.strip.plans[panel === "economy" ? "top" : "bottom"].forEach(function (plan) {
      plan.fonts.forEach(function (f) { combos.push({rows: plan.rows, pitch: plan.pitch, font: f}); });
    });
    combos.sort(function (a, b) { return b.font - a.font || a.rows - b.rows; });
    // What to try, in order: [how long a label may wait, in which type and rows].
    var least = combos[combos.length - 1].font, tries = [];
    var main = combos.filter(function (c) { return c.font > least; }), small = combos.filter(function (c) { return c.font === least; });
    [[WAITS.slice(0, 2), main], [WAITS.slice(0, 2), small], [WAITS.slice(2), combos]].forEach(function (group) {
      group[0].forEach(function (wait) { group[1].forEach(function (c) { tries.push([wait, c]); }); });
    });
    for (var drop = 0; drop <= (canDrop || canBare ? all.length : 0); drop++) {
      var keep = all.slice(0, all.length - drop), byDate = keep.slice().sort(function (a, b) { return a.t - b.t; });
      for (var n = 0; n < tries.length; n++) for (var form = 0; form < forms; form++) {
        var says = byDate.map(function (e) { return form && e.short ? e.short : e.text; });
        var c = tries[n][1], placed = placeStrip(byDate, says, plotW, c.font, c.rows, tries[n][0]);
        if (placed) return {labels: true, events: byDate, says: says, placed: placed, font: c.font, rows: c.rows,
                            pitch: c.pitch, wait: tries[n][0], dropped: canDrop ? all.slice(all.length - drop) : [],
                            bare: canDrop ? [] : all.slice(all.length - drop)};
      }
    }
    return {labels: false, events: all, says: all.map(function (e) { return e.text; }), placed: null,
            font: combos[0].font, rows: 0, pitch: 0, wait: 0, dropped: [], bare: []};
  }

  // ---- The era row -------------------------------------------------------------------
  // Each era's label is left-aligned at its bar's start (or at the plot's left
  // edge), so two labels can meet when their bars start close together, and one
  // can run off the figure's right edge. Which labels a view can show: the
  // longer era keeps its label; the other has hover text only.
  function eraLabels(V0, V1, plotW, on) {
    var scale = plotW / (V1 - V0), hi = plotW + L.margin.r - 2, taken = [], out = [];
    ERAS.map(function (e, n) { return n; })
      .filter(function (n) { return on[n] && ERAS[n].t1 > V0 && ERAS[n].t0 < V1; })
      .sort(function (i, j) { return (ERAS[j].t1 - ERAS[j].t0) - (ERAS[i].t1 - ERAS[i].t0); })
      .forEach(function (n) {
        var a = Math.max((ERAS[n].t0 - V0) * scale, 0), b = a + ERAS[n].w;
        if (b > hi || taken.some(function (q) { return a < q[1] + 8 && q[0] < b + 8; })) return;
        taken.push([a, b]);
        out[n] = true;
      });
    return out;
  }
  // The row for the finished chart. If it cannot label every era, then at the
  // full column the eras marked to go first are given up, bars and all.
  function fitEras(plotW, w) {
    var canDrop = L.drop_from !== null && w >= L.drop_from;
    var on = ERAS.map(function () { return true; }), lab = eraLabels(X0, X1, plotW, on), dropped = [];
    if (canDrop && !on.every(function (o, n) { return lab[n]; })) {
      ERAS.forEach(function (e, n) { if (e.drop_first) { on[n] = false; dropped.push(e.label); } });
      lab = eraLabels(X0, X1, plotW, on);
    }
    return {on: on, labelled: lab, dropped: dropped};
  }

  // ---- The arrowed annotations: text clear of the data ------------------------------
  // "above": over the arrow tip, which is the highest point of the stock line.
  // "under": below both lines across its own width, and well under the tip;
  // never astride the zero line, so for a tip above that line the text hangs
  // just beneath it. Either way as near the tip as it can get, clear of the
  // other annotations and inside the panel, right of where the data begin. An
  // event's line may pass behind the text (it has a halo). The text sits at a
  // fixed pixel offset from its tip, and the chart is stretched while the
  // playhead is short of the end, so every position is checked at several
  // stages between its arrow's first appearance and the finished chart. Each
  // goes where it has least long to wait for room after its arrow appears,
  // then in the fewest lines. A text may reach left of where the data begin,
  // over the plain band, but never over the hatched band or an event's line
  // there. Returns null if any of them cannot be placed.
  function placeArrows(font) {
    var plotW = GEO.plotW, ppb = GEO.ppb, zeroY = M.view.y2[1] * ppb, c = 5, placed = [];
    var end = plotW / (X1 - X0), edge = 0, waits = [0].concat(WAITS);
    BANDS.forEach(function (bd) { if (bd.kind === "none") edge = Math.max(edge, (bd.t1 - X0) * end); });
    EV.forEach(function (e) { if (e.on && !e.tick && e.panel === "stocks" && e.t < TA) edge = Math.max(edge, (e.t - X0) * end); });
    function stages(t) {                   // px per ms from when the playhead reaches t to the finished chart
      var out = [];
      for (var k = 0; k < 5; k++) out.push(plotW / (windowEnd(t + (T1 - t) * k / 5) - X0));
      out.push(end);
      return out;
    }
    function reach(tip, sc, a, b) {        // how high and how low the two lines get across [a, b] px from the tip, in px
      var hi = Infinity, lo = -Infinity;
      for (var x = a; x <= b; x += 2) {
        var T = tip + x / sc, s = at(S.t, S.s, T), e = at(S.t, S.e, T);
        if (s === null) continue;
        hi = Math.min(hi, zeroY - Math.max(s, e) * ppb);
        lo = Math.max(lo, zeroY - Math.min(s, e) * ppb);
      }
      return {hi: hi, lo: lo};
    }
    function clear(q) {
      return placed.every(function (o) {
        if (q.top >= o.bottom + 6 || o.top >= q.bottom + 6) return true;
        return stages(Math.max(q.t, o.t)).every(function (sc) {
          var xq = (q.t - X0) * sc, xo = (o.t - X0) * sc;
          return xq + q.dx0 >= xo + o.dx1 + 8 || xo + o.dx0 >= xq + q.dx1 + 8;
        });
      });
    }
    for (var n = 0; n < ARROWS.length; n++) {
      var A = ARROWS[n], tipX = (A.t - X0) * end, tipY = zeroY - A.y * ppb, scs = stages(A.t), found = null;
      for (var w8 = 0; w8 < waits.length && !found; w8++) for (var k = 0; k < A.wraps.length && !found; k++) {
        var sz = textSize(A.wraps[k], font), W = sz.w + 8, H = sz.h + 6;
        var room = waits[w8] === Infinity ? Infinity : roomAt(A.t, plotW, waits[w8]);
        for (var step = 0; step <= 120 && !found; step++) for (var sign = -1; sign <= 1 && !found; sign += 2) {
          if (!step && sign > 0) continue;
          var dx0 = sign * step * 3 - W / 2, dx1 = dx0 + W, hi = Infinity, lo = -Infinity, top;
          if (tipX + dx0 < edge + 6 || tipX + dx1 > plotW - 3 || dx1 > room) continue;
          for (var j = 0; j < scs.length; j++) {
            var d = reach(A.t, scs[j], dx0 - c, dx1 + c);
            hi = Math.min(hi, d.hi); lo = Math.max(lo, d.lo);
          }
          if (A.mode === "above") {
            // As high as the panel allows (below any tick mark), up to 22 px clear of the tip, and never nearer than 10.
            top = Math.max(L.tick.down + 3, tipY - 22 - H);
            if (top + H > tipY - 10 || hi < top + H + c) continue;
          } else {
            top = Math.max(tipY + 16, lo + c + 1);
            if (top < zeroY + 7 && top + H > zeroY - 4) top = zeroY + 7;
            if (lo > top - c) continue;
          }
          if (top < 3 || top + H > GEO.botH - 3) continue;
          var q = {t: A.t, dx0: dx0, dx1: dx1, top: top, bottom: top + H};
          if (!clear(q)) continue;
          q.text = A.wraps[k]; q.ax = (dx0 + dx1) / 2; q.ay = top + H / 2 - tipY;
          q.a = tipX + dx0; q.b = tipX + dx1; q.tipX = tipX; q.tipY = tipY;    // on the finished chart
          q.show = fitsFrom(A.t, dx1, plotW); q.late = (q.show - A.t) / YEAR;
          found = q;
        }
      }
      if (!found) return null;
      placed.push(found);
    }
    return placed;
  }

  // The three lines on the finished chart, as px above their panel's zero line,
  // one value per pixel column (NaN where a line has no data).
  function columns(plotW) {
    var c = {g: [], s: [], e: []}, ms = (X1 - X0) / plotW;
    for (var x = 0; x <= Math.ceil(plotW); x++) {
      var T = X0 + x * ms, g = at(G.t, G.y, T), s = at(S.t, S.s, T), e = at(S.t, S.e, T);
      c.g.push(g === null ? NaN : g * GEO.ppb);
      c.s.push(s === null ? NaN : s * GEO.ppb);
      c.e.push(e === null ? NaN : e * GEO.ppb);
    }
    return c;
  }

  // ---- The two labels by the fills --------------------------------------------------
  // "behind": inside the grey, wherever between its two dates the grey is
  // deepest, with both lines clear of the text. "ahead": the periwinkle is too
  // thin to hold its label, so that goes in clear space as near as it can get
  // to the periwinkle between its two dates -- above both lines or below both
  // across its whole width, never between them. Both keep clear of the
  // annotations already placed, and prefer not to lie over an event's line.
  // Worked out on the finished chart: a label is pinned to a date at its
  // centre, so a stretched chart only moves things away from it. Returns the
  // box, or null.
  function placeFill(F, boxes, COL) {
    var plotW = GEO.plotW, scale = plotW / (X1 - X0), zeroY = M.view.y2[1] * GEO.ppb, c = 4, best = null;
    var from = Math.max(0, Math.ceil((TA - X0) * scale) + 6), to = Math.floor(plotW) - 3;
    var lines = EV.filter(function (e) { return e.on && !e.tick && e.panel === "stocks"; }).map(function (e) { return (e.t - X0) * scale; });
    function crossings(a, b) { return lines.filter(function (x) { return x > a - 3 && x < b + 3; }).length; }
    // Clear of the annotations already placed: of their text, and of the arrow from each text to its tip.
    function free(q) {
      return boxes.every(function (o) {
        if (!(q.a >= o.b + 6 || o.a >= q.b + 6 || q.top >= o.bottom + 4 || o.top >= q.bottom + 4)) return false;
        if (o.tipX === undefined) return true;
        for (var k = 0; k <= 24; k++) {                 // points along the arrow, from its tip to the middle of its text
          var x = o.tipX + ((o.a + o.b) / 2 - o.tipX) * k / 24, y = o.tipY + ((o.top + o.bottom) / 2 - o.tipY) * k / 24;
          if (x > q.a - 5 && x < q.b + 5 && y > q.top - 5 && y < q.bottom + 5) return false;
        }
        return true;
      });
    }
    var x0 = Math.max(from, Math.round((F.t0 - X0) * scale)), x1 = Math.min(to, Math.round((F.t1 - X0) * scale)), pts = [];
    if (F.kind === "ahead") for (var x = x0; x <= x1; x++) if (COL.s[x] > COL.e[x]) pts.push([x, zeroY - (COL.s[x] + COL.e[x]) / 2]);
    if (F.kind === "ahead" && !pts.length) return null;
    for (var k = 0; k < F.wraps.length && !best; k++) {
      var sz = textSize(F.wraps[k], L.fill_font), W = sz.w + 6, H = sz.h + 4;
      var a0 = F.kind === "ahead" ? Math.max(from, Math.floor(pts[0][0] - W - 50)) : x0;
      var a1 = F.kind === "ahead" ? Math.min(to, pts[pts.length - 1][0] + 50 + W) : x1;
      for (var a = a0; a + W <= a1; a += 2) {
        var b = a + W, up = Infinity, down = -Infinity, roof = -Infinity, floor = Infinity, ok = true;
        for (var xx = Math.max(0, Math.floor(a - c)); ok && xx <= Math.min(COL.s.length - 1, Math.ceil(b + c)); xx++) {
          var ys = zeroY - COL.s[xx], ye = zeroY - COL.e[xx];
          if (isNaN(ys)) { ok = false; break; }
          up = Math.min(up, ys, ye); down = Math.max(down, ys, ye);        // the highest and the lowest any line gets
          if (F.kind === "behind") {
            if (ys <= ye) ok = false;                                      // the stock line must be the lower one throughout
            roof = Math.max(roof, ye); floor = Math.min(floor, ys);        // under the economy line, over the stock line
          }
        }
        if (!ok) continue;
        var cross = crossings(a, b), tops = [], q;
        if (F.kind === "behind") {
          if (floor - roof < H + 2 * c) continue;
          q = {a: a, b: b, top: (roof + floor - H) / 2, bottom: (roof + floor + H) / 2, score: floor - roof - 30 * cross};
          if (free(q) && (!best || q.score > best.score)) { q.text = F.wraps[k]; q.t = X0 + b / scale; best = q; }
          continue;
        }
        for (var t1 = up - c - H; t1 >= L.tick.down + 3; t1 -= 2) tops.push(t1);      // above both lines
        for (var t2 = down + c; t2 + H <= GEO.botH - 4; t2 += 2) tops.push(t2);       // or below both
        tops.forEach(function (top) {
          if (top < zeroY + 3 && top + H > zeroY - 3) return;             // never astride the zero line
          var dist = Infinity, near = null;
          pts.forEach(function (p) {
            var dd = Math.hypot(Math.max(a - p[0], 0, p[0] - b), Math.max(top - p[1], 0, p[1] - top - H));
            if (dd < dist) { dist = dd; near = p; }
          });
          var cand = {a: a, b: b, top: top, bottom: top + H, score: -dist - 12 * cross};
          if (dist > 45 || (best && cand.score <= best.score) || !free(cand)) return;
          cand.text = F.wraps[k]; cand.t = X0 + Math.max(b, near[0]) / scale; best = cand;
        });
      }
    }
    if (!best) return null;
    best.w = best.b - best.a;
    best.at = X0 + (best.a + best.b) / 2 / scale;      // the date it is pinned to, at its centre
    best.x = iso(best.at);
    best.y = (zeroY - (best.top + best.bottom) / 2) / GEO.ppb;
    return best;                                       // best.t: shown once the playhead has drawn what it labels
  }

  // The top panel's two labels, either side of its zero line and right of the
  // 1978 anchor. The line itself runs just above zero for the first years after
  // the anchor, so the pair starts as near the anchor as the line leaves room
  // for the upper label, and not on an event's line.
  function placeHints(plotW, COL) {
    var f = L.hint_font, a = gd.layout.annotations, scale = plotW / (X1 - X0);
    var w = Math.max(textSize(a[AN.gap_up].text, f).w, textSize(a[AN.gap_down].text, f).w) + 4, h = textSize(a[AN.gap_up].text, f).h;
    var lines = EV.filter(function (e) { return e.on && !e.tick && e.panel === "economy"; }).map(function (e) { return (e.t - X0) * scale; });
    for (var x = Math.ceil((TG - X0) * scale) + 10; x + w <= plotW - 4; x++) {
      var ok = !lines.some(function (lx) { return lx > x - 5 && lx < x + 3; });
      for (var xx = x - 3; ok && xx <= x + w + 3; xx++) ok = COL.g[xx] >= 3 + h + 4;
      if (ok) return {t: X0 + x / scale, w: w, show: longFrom(X0 + x / scale, w + 8, plotW) || T1};
    }
    return null;
  }

  // ---- Everything in the layout that depends on the playhead and the window -------
  // A pure function of the playhead T and the visible window [V0, V1]: which
  // events, bars, bands and annotations are showing and how strongly, how far
  // each bar and band has grown, and where the band labels sit. Stateless, so
  // scrubbing, playing and zooming all agree. A leader's or an era's label is
  // pinned to the start of its bar (or to the plot's left edge when the bar
  // began before the view does) and does not move while the bar grows.
  // Phase 2 hook: a zoom-dependent rule for tier-2 events belongs in fade().
  function scene(T, V0, V1) {
    var p = {}, scale = GEO.plotW / (V1 - V0), done = T >= T1;
    var lo = -L.margin.l + 2, hi = GEO.plotW + L.margin.r - 2;
    function A(i, props) { for (var k in props) p["annotations[" + i + "]." + k] = props[k]; }
    function H(i, props) { for (var k in props) p["shapes[" + i + "]." + k] = props[k]; }
    // Whatever is timed fades in; what was already there when playback starts is simply there.
    function fade(t) { return done || t <= T0 ? 1 : clamp((T - t) / FADE, 0, 1); }
    function px(t) { return (t - V0) * scale; }

    // A label is shown only where its whole box is inside the figure: during
    // playback that can be a moment after its line appears, and under the
    // reader's own zoom a label at the edge of the view simply steps aside. A
    // line with no label (a phone) that would run through its panel's name
    // starts below the name instead.
    // A tick appears by the same rule as a labelled marker, and that is all there is to it.
    EV.forEach(function (e) {
      var a = e.on ? fade(e.t) : 0, x = px(e.t), k = e.panel === "economy" ? 0 : 1, head = GEO.head[k];
      if (e.tick) { H(e.shape, {visible: a > 0, opacity: a}); return; }
      var b = e.on && e.labelled && x + e.ext[0] >= lo - 0.5 && x + e.ext[1] <= hi + 0.5 ? fade(e.show) : 0;
      var top = e.labelled ? e.stem : (x > head.a - 4 && x < head.b + 4 ? -head.h : 0);
      H(e.shape, {visible: a > 0, opacity: a * M.event_line_opacity, y1: 1 + top / GEO.panelH[k]});
      if (e.annotation !== null) A(e.annotation, {visible: b > 0, opacity: b});
    });
    var az = fade(TA), roomZ = px(TA) - 10 - FIT.hints.bottomW >= 2;
    H(M.zero.bottom, {visible: az > 0, opacity: az});
    ["zero_up", "zero_down"].forEach(function (r) { A(AN[r], {visible: az > 0 && FIT.hints.bottom && roomZ, opacity: az}); });
    var ht = FIT.hints.top, ag = ht && px(ht.t) + ht.w <= GEO.plotW - 2 ? fade(ht.show) : 0;
    ["gap_up", "gap_down"].forEach(function (r) { A(AN[r], {visible: ag > 0, opacity: ag}); });
    ARROWS.forEach(function (a) {
      var q = a.box, x = px(a.t), f = 0;
      // Clear of the plot's edges, and of the panel's name if it is level with it.
      if (q && x + q.dx0 >= (q.top < 28 ? GEO.head[1].b + 6 : 2) && x + q.dx1 <= hi + 0.5) f = fade(q.show);
      A(AN[a.role], {visible: f > 0, opacity: f});
    });
    FILLS.forEach(function (f) {
      var q = f.box, x = q ? px(q.at) : 0, a = q && x - q.w / 2 >= 2 && x + q.w / 2 <= GEO.plotW - 2 ? fade(q.t) : 0;
      A(AN[f.role], {visible: a > 0, opacity: a});
    });

    // Bars grow with the playhead; Plotly cuts them off at the plot's edge, and
    // a bar that runs off the left edge gets its marker there.
    var eraText = done ? eraLabels(V0, V1, GEO.plotW, ERAS.map(function (e) { return e.on; })) : null;
    ERAS.forEach(function (e, n) {
      var start = Math.max(e.t0, V0), end = Math.min(e.t1, T, V1);
      e.cut = e.t0 < V0; e.a = px(start); e.b = px(end);
      e.live = e.on && e.b > e.a + 0.5;
      H(e.bar, {visible: e.live, x1: iso(Math.max(e.t0, Math.min(e.t1, T)))});
      H(e.tip, {visible: e.live && e.cut});
      var f = !e.live ? 0 : done ? (eraText[n] ? 1 : 0) : e.labelled ? fade(e.show) : 0;
      e.text = f > 0;
      A(e.annotation, f > 0 ? {visible: true, opacity: f, x: iso(Math.max(e.t0, V0 + HOUR))} : {visible: false});
    });
    // A leader's name shows once its segment is long enough to hold it.
    LEADERS.forEach(function (l) {
      var start = Math.max(l.t0, V0), end = Math.min(l.t1, T, V1);
      l.cut = l.t0 < V0; l.a = px(start); l.b = px(end);
      l.live = l.b > l.a + 0.5;
      H(l.shape, {visible: l.live, x1: iso(Math.max(l.t0, Math.min(l.t1, T, X1)))});
      H(l.tip, {visible: l.live && l.cut});
      var f = !l.live ? 0 : done ? (l.b - l.a >= l.w + 12 ? 1 : 0) : l.labelled ? fade(l.show) : 0;
      l.text = f > 0;
      A(l.annotation, f > 0 ? {visible: true, opacity: f, x: iso(Math.max(l.t0, V0 + HOUR))} : {visible: false});
    });

    // Access bands grow with the playhead too. (The hatched one is a trace:
    // render() grows it.) Each label is centred in the part of its band that is
    // in view, in the widest wording that fits there.
    BANDS.forEach(function (bd) {
      var from = Math.max(bd.t0, X0), start = Math.max(bd.t0, V0), end = Math.min(bd.t1, T, V1), a = px(start), b = px(end);
      var live = b > a + 0.5, text = null;
      if (bd.shape !== null) H(bd.shape, {visible: T > from, x1: iso(Math.max(from, Math.min(bd.t1, T)))});
      if (bd.early) H(bd.early.shape, {visible: T > from, x1: iso(Math.max(from, Math.min(bd.early.t1, T)))});
      if (live) for (var k = 0; k < bd.wraps.length && !text; k++)
        if (textSize(bd.wraps[k], L.band_font).w + 16 <= b - a) text = bd.wraps[k];
      bd.span = live ? [a, b] : null;
      A(bd.annotation, text ? {visible: true, text: text, x: (a + b) / 2 / GEO.plotW} : {visible: false});
    });
    return p;
  }
  // The bottom panel's name sits on an access band, or on the page once the
  // reader has zoomed past the bands; its halo takes the colour behind it.
  function syncHead() {
    var a = GEO.head[1].a, b = GEO.head[1].b, under = P.paper;
    BANDS.forEach(function (bd) {
      if (bd.span && bd.span[0] <= a && bd.span[1] >= b) under = bd.kind === "none" ? P.onNone : P.onLimited;
    });
    if (under !== halo) heads[1].style.setProperty("--china-band", halo = under);
  }
  // Send a layout patch, and optionally trace data with it: only what has
  // changed since it was last sent. (The x-range is always sent: the reader can
  // change it behind our back.)
  function send(layout, data, idx) {
    var out = {}, n = 0;
    for (var k in layout) {
      var v = JSON.stringify(layout[k]);
      if (k !== "xaxis.range" && sent[k] === v) continue;
      sent[k] = v; out[k] = layout[k]; n++;
    }
    if (data) return PL.update(gd, data, out, idx);
    return n ? PL.relayout(gd, out) : Promise.resolve();
  }
  function markersAt(T) {
    var shown = FIT && !FIT.arrows ? ARROWS.filter(function (a) { return a.t <= T; }) : [];
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
    BANDS.forEach(function (bd) {
      if (bd.trace === null) return;
      var x0 = iso(Math.max(bd.t0, X0)), x1 = iso(Math.max(Math.max(bd.t0, X0), Math.min(bd.t1, T)));
      put(bd.trace, [x0, x1, x1, x0], bd.y);
    });
    put(TR.fill_behind, f.behind.x, f.behind.y);
    put(TR.fill_ahead, f.ahead.x, f.ahead.y);
    put(TR.economy, p.x, p.e);
    put(TR.stock, p.x, p.s);
    put(TR.stock_head, live && p.x.length ? [last(p.x)] : [], live && p.x.length ? [last(p.s)] : []);
    put(TR.markers, mk.x, mk.y);
    ANCHORS.forEach(function (a) { put(TR[a.trace], T >= a.t ? [a.date] : [], T >= a.t ? [0] : []); });
    var end = done ? X1 : windowEnd(T), layout = scene(T, X0, end);
    // The x-range follows the playhead, which also undoes any zoom.
    layout["xaxis.range"] = [M.view.x[0], done ? M.view.x[1] : iso(end)];
    syncHead();
    syncControls();
    hideTip();
    busy = true;
    function freed() { busy = false; if (pending !== null) { var q = pending; pending = null; render(q); } }
    Promise.resolve(send(layout, data, idx)).then(freed, freed);
  }
  // Re-place whatever depends on the window, after a zoom or pan or a re-fit.
  function refresh() { var v = view(), p = scene(playhead, v[0], v[1]); syncHead(); return send(p); }
  function syncControls() {
    var f = (playhead - T0) / (T1 - T0), done = playhead >= T1;
    scrub.value = Math.round(f * scrub.max);          // the thumb's position IS the date, linearly
    scrubWrap.style.setProperty("--china-p", (100 * f).toFixed(2) + "%");
    mark.textContent = new Date(playhead).getUTCFullYear();
    mark.style.display = done ? "none" : "block";      // the watermark is for playback only
    Array.prototype.forEach.call(keyBox.querySelectorAll("[data-t]"), function (row) {
      row.style.opacity = done ? 1 : clamp((playhead - row.getAttribute("data-t")) / FADE, 0, 1);
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
      // Advance by wall-clock time (times the chosen speed), capped so a backgrounded tab resumes, not jumps.
      if (prev !== null) tau += Math.min(now - prev, 100) / 1000 * speed;
      prev = now;
      if (tau >= TOTAL) { setPlaying(false); render(T1); return; }
      if (!busy) render(timeOf(tau));
      raf = requestAnimationFrame(step);
    }
    raf = requestAnimationFrame(step);
  }
  // The speed toggle steps through the speeds on offer; it takes effect at once.
  function setSpeed(v) {
    speed = v;
    speedBtn.textContent = v + "×";
    speedBtn.classList.toggle("is-fast", v > 1);
    var next = M.play.speeds[(M.play.speeds.indexOf(v) + 1) % M.play.speeds.length];
    speedBtn.setAttribute("aria-label", "Playback speed: " + v + "×. Switch to " + next + "×.");
  }

  // ---- After the reader zooms, pans, autoscales or resets -------------------------
  // The y-axes are fixed (that is what keeps one vertical scale), so only x can
  // change. An autoranged axis would re-range on every animation frame without
  // telling us, so autorange is frozen into the explicit full view. Then
  // whatever depends on the window is re-placed.
  function onRelayout() {
    hideTip();
    if (syncing || !GEO) return;
    if (gd._fullLayout.xaxis.autorange) {
      syncing = true;
      var freed = function () { syncing = false; refresh(); };
      Promise.resolve(PL.relayout(gd, {"xaxis.range": M.view.x.slice()})).then(freed, freed);
    } else if (playhead >= T1) refresh();
  }

  // ---- Fit: fill the column, size the panels to one scale, place the text ----------
  function host() { return gd.closest(".cell-output-display") || scope; }
  // The same arithmetic as _strip_heights() and _geometry() in the Python module.
  function geometry(top, bottom) {
    var st = L.strip, spanT = M.view.y[1] - M.view.y[0], spanB = M.view.y2[1] - M.view.y2[0];
    var era = top.rows ? 3 + top.rows * top.pitch + 3 : 3, eraLabel = era + st.era_bar + 2;
    var leader = eraLabel + st.era_label + 2, topStrip = leader + st.leader;
    var gap = bottom.rows ? 3 + bottom.rows * bottom.pitch + 3 : st.bare_gap;
    var topH = L.px_per_bit * spanT, botH = L.px_per_bit * spanB, plotH = topH + gap + botH, t = L.title_row + topStrip + 2;
    var height = Math.round(plotH + t + L.margin.b), k = (height - t - L.margin.b) / plotH;
    return {t: t, height: height, plotH: plotH * k, topH: topH * k, botH: botH * k, gap: gap * k, ppb: L.px_per_bit * k,
            top: [1 - topH / plotH, 1], bottom: [0, botH / plotH], era: era, eraLabel: eraLabel, leader: leader,
            topStrip: topStrip, bottomStrip: gap};
  }
  function fit(force) {
    var w = Math.floor(host().clientWidth || gd.offsetWidth);
    if (!w) return setTimeout(fit, 30);
    if (w === lastW && force !== true) return;
    lastW = w;
    L = M.layouts[w < M.narrow_below ? "narrow" : "wide"];
    var st = L.strip, plotW = w - L.margin.l - L.margin.r, scale = plotW / (X1 - X0), ann = gd.layout.annotations;
    var patch = {};
    function A(i, props) { for (var k in props) patch["annotations[" + i + "]." + k] = props[k]; }
    function H(i, props) { for (var k in props) patch["shapes[" + i + "]." + k] = props[k]; }

    // The two strips: which events are drawn and labelled, in which rows.
    FIT = {top: fitStrip("economy", plotW, w), bottom: fitStrip("stocks", plotW, w)};
    EV.forEach(function (e) {
      e.on = false; e.labelled = false; e.row = 0; e.spot = 0.5; e.ext = [0, 0]; e.show = e.t; e.stem = 0; e.lift = 3;
    });
    [FIT.top, FIT.bottom].forEach(function (F) {
      F.events.forEach(function (e, j) {
        e.on = true; e.labelled = F.labels; e.font = F.font; e.say = F.says[j];
        if (!F.placed) return;
        e.row = F.placed[j].row; e.spot = F.placed[j].spot;
        e.stem = 2 + e.row * F.pitch; e.lift = 3 + e.row * F.pitch;      // where its line stops and its label stands, px above the panel
        // How far the label reaches either side of its line, and when it first fits in the figure.
        e.ext = reachOf(0, textSize(e.say, F.font).w + 2, e.spot);
        e.show = fitsFrom(e.t, e.ext[1], plotW);
      });
    });
    // An event whose label had to go keeps its line.
    FIT.top.bare.concat(FIT.bottom.bare).forEach(function (e) { e.on = true; e.labelled = false; });
    // A tick is always drawn. An event that shares a label goes wherever the one carrying it goes.
    EV.forEach(function (e) {
      if (e.tick) { e.on = true; return; }
      if (e.lead === null) return;
      var l = EV[e.lead];
      e.on = l.on; e.labelled = l.labelled; e.row = l.row; e.stem = l.stem;
    });
    // The eras and the leaders: which are drawn, which are labelled, and from when.
    ERAS.forEach(function (e) { e.w = textSize(e.label, st.era_font).w + 2; });
    FIT.eras = fitEras(plotW, w);
    ERAS.forEach(function (e, n) {
      e.on = FIT.eras.on[n]; e.labelled = !!FIT.eras.labelled[n];
      e.show = fitsFrom(Math.max(e.t0, X0), e.w, plotW);
    });
    LEADERS.forEach(function (l) {
      l.w = textSize(l.label, st.leader_font).w + 2;
      l.labelled = (Math.min(l.t1, T1) - Math.max(l.t0, X0)) * scale >= l.w + 12;
      l.show = l.labelled ? longFrom(l.t0, l.w + 12, plotW) : null;
    });

    GEO = geometry(FIT.top, FIT.bottom);
    GEO.plotW = plotW; GEO.panelH = [GEO.topH, GEO.botH];
    patch.width = w; patch.height = GEO.height; patch.autosize = false; patch["font.size"] = L.font;
    patch.margin = {l: L.margin.l, r: L.margin.r, t: GEO.t, b: L.margin.b};
    patch["yaxis.domain"] = GEO.top; patch["yaxis2.domain"] = GEO.bottom;
    function above(px) { return 1 + px / GEO.topH; }
    EV.forEach(function (e) {
      var panelH = GEO.panelH[e.panel === "economy" ? 0 : 1];
      if (e.tick) H(e.shape, {y0: 1 - L.tick.down / panelH, y1: 1 + L.tick.up / panelH, "line.width": L.tick.width});
      if (e.annotation === null) return;
      // Centred on its line, to one side of it, or slid along it by a share of its own width.
      A(e.annotation, {text: e.say, "font.size": e.font || st.plans.top[0].fonts[0], yshift: e.lift,
        xanchor: e.spot === 0.5 ? "center" : e.spot === 1 ? "right" : "left",
        xshift: e.spot === 0.5 ? 0 : e.spot === 1 ? -3 : e.spot === 0 ? 3 : Math.round(e.ext[0])});
    });
    ERAS.forEach(function (e) {
      H(e.bar, {y0: above(GEO.era), y1: above(GEO.era + st.era_bar)});
      H(e.tip, {yanchor: above(GEO.era + st.era_bar / 2)});
      A(e.annotation, {yshift: GEO.eraLabel, "font.size": st.era_font});
    });
    LEADERS.forEach(function (l) {
      H(l.shape, {y0: above(GEO.leader), y1: above(GEO.topStrip)});
      H(l.tip, {yanchor: above(GEO.leader + st.leader / 2)});
      A(l.annotation, {yshift: GEO.leader + st.leader / 2, "font.size": st.leader_font});
    });
    BANDS.forEach(function (bd) { A(bd.annotation, {"font.size": L.band_font}); });

    // The title and the panels' names (HTML): sized first, since what follows needs their extent.
    title.style.fontSize = L.title + "px";
    heads.forEach(function (h) { h.style.fontSize = L.head + "px"; });
    GEO.head = heads.map(function (h) { return {a: 4, b: 12 + h.offsetWidth, h: 4 + h.offsetHeight + 3}; });

    // The labels either side of the zero lines. Bottom panel: left of where the
    // line starts, on the plain band, if they fit inside that band; otherwise
    // a line in the key says it. Top panel: right of the anchor, where they fit.
    var COL = columns(plotW), into = BANDS.filter(function (bd) { return bd.t1 === TA; })[0];
    var room = into ? (TA - Math.max(into.t0, X0)) * scale - 16 : 0;
    var wb = Math.max(textSize(ann[AN.zero_up].text, L.hint_font).w, textSize(ann[AN.zero_down].text, L.hint_font).w) + 4;
    FIT.hints = {bottom: wb <= room, bottomW: wb, top: placeHints(plotW, COL)};
    ["zero_up", "zero_down", "gap_up", "gap_down"].forEach(function (r) { A(AN[r], {"font.size": L.hint_font}); });
    if (FIT.hints.top) ["gap_up", "gap_down"].forEach(function (r) { A(AN[r], {x: iso(FIT.hints.top.t)}); });

    // The arrowed annotations: beside the data if they all fit, in the largest
    // type that keeps every one of them within a year of its arrow (failing
    // that, whichever type waits least); otherwise numbered markers and a key.
    // Then the labels by the fills.
    var tries = L.arrow_fonts.map(function (f) { return {font: f, boxes: placeArrows(f)}; })
      .filter(function (t) { return t.boxes; });
    tries.forEach(function (t) { t.late = Math.max.apply(null, t.boxes.map(function (q) { return q.late; })); });
    var pick = tries.filter(function (t) { return t.late <= 1; })[0]
      || tries.slice().sort(function (a, b) { return a.late - b.late; })[0];
    FIT.arrows = pick ? pick.boxes : null; FIT.arrowFont = pick ? pick.font : null;
    ARROWS.forEach(function (a, n) {
      a.box = FIT.arrows ? FIT.arrows[n] : null;
      if (a.box) A(AN[a.role], {text: a.box.text, ax: a.box.ax, ay: a.box.ay,
        "font.size": FIT.arrowFont, xanchor: "center", yanchor: "middle"});
    });
    // (Where the annotations have become numbered markers, the labels keep clear of the markers.)
    var boxes = FIT.arrows ? FIT.arrows.slice() : ARROWS.map(function (a) {
      var mx = (a.t - X0) * scale, my = (M.view.y2[1] - a.y) * GEO.ppb;
      return {a: mx - 9, b: mx + 9, top: my - 9, bottom: my + 9};
    });
    FILLS.forEach(function (F) {
      F.box = placeFill(F, boxes, COL);
      if (!F.box) return;
      boxes.push(F.box);
      A(AN[F.role], {text: F.box.text, x: F.box.x, y: F.box.y, "font.size": L.fill_font});
    });

    // The key under the plot: whatever could not be labelled directly.
    var keyed = false;
    Array.prototype.forEach.call(keyBox.children, function (row) {
      row.hidden = row.hasAttribute("data-zero") ? FIT.hints.bottom : !!FIT.arrows;
      keyed = keyed || !row.hidden;
    });
    keyBox.hidden = !keyed;

    wrap.style.width = controls.style.width = keyBox.style.width = w + "px";
    wrap.classList.toggle("is-narrow", !L.modebar);
    // Plotly resizes its SVG but leaves the graph div's inline size alone.
    gd.style.width = w + "px";
    gd.style.height = GEO.height + "px";
    title.style.transform = "translate(" + L.margin.l + "px," + Math.max(0, (L.title_row - title.offsetHeight) / 2) + "px)";
    heads.forEach(function (h, k) {
      h.style.transform = "translate(" + (L.margin.l + 8) + "px," + (GEO.t + (k ? GEO.topH + GEO.gap : 0) + 4) + "px)";
    });
    mark.style.left = (L.margin.l + plotW / 2) + "px";
    mark.style.top = (GEO.t + GEO.topH * 0.52) + "px";
    mark.style.fontSize = Math.round(Math.min(GEO.topH * L.mark_frac, plotW * 0.3)) + "px";
    hideTip();
    var v = view(), where = scene(playhead, v[0], v[1]), mk = markersAt(playhead);
    syncHead();
    for (var key in where) patch[key] = where[key];
    send(patch, {"line.width": [L.gdp_width, L.economy_width, L.stock_width]}, [TR.gdp, TR.economy, TR.stock])
      .then(function () { return PL.restyle(gd, {"marker.size": L.anchor}, [TR.anchor_top, TR.anchor_bottom]); })
      .then(function () { return PL.restyle(gd, {x: [mk.x], y: [mk.y]}, [TR.markers]); });
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
  // A text halo: the text's own outline in the colour behind it (a CSS text-shadow).
  function haloOf(c) { return M.halo.map(function (offset) { return offset + " " + c; }).join(", "); }
  function palette() {
    var cs = getComputedStyle(document.body), ink = rgb(cs.color), paper = rgb(cs.backgroundColor);
    var darkClass = document.body.classList.contains("quarto-dark");
    if (!paper || paper.a === 0) paper = {c: darkClass ? [34, 34, 34] : [255, 255, 255]};
    if (!ink) ink = {c: darkClass ? [255, 255, 255] : [31, 35, 40]};
    var lum = (0.2126 * paper.c[0] + 0.7152 * paper.c[1] + 0.0722 * paper.c[2]) / 255;
    var dark = darkClass || lum < 0.4;
    var base = dark ? {ink: mix(ink.c, paper.c, 0), paper: mix(paper.c, ink.c, 0), label: mix(ink.c, paper.c, 0.3),
                       grid: mix(ink.c, paper.c, 0.86), axis: mix(ink.c, paper.c, 0.6)} : M.light;
    var al = M.alpha[dark ? "dark" : "light"], i = rgb(base.ink).c, pp = rgb(base.paper).c, st = rgb(M.colors.stock).c;
    // Historical context is navy; on a dark page, a lighter navy.
    var nv = rgb(dark ? M.colors.context_dark : M.colors.context).c;
    function on(c, a) { return mix(pp, c, a); }       // a tint of c at alpha a, flattened onto the page
    return {dark: dark, ink: base.ink, paper: base.paper, label: base.label, grid: base.grid, axis: base.axis,
            ahead: tint(st, al.ahead), behind: tint(i, al.behind), onBehind: on(i, al.behind),
            none: tint(nv, al.band_none), hatch: tint(nv, al.hatch), onNone: on(nv, al.band_none),
            limited: tint(nv, al.band_limited), early: tint(nv, al.band_early), onLimited: on(nv, al.band_limited),
            era: tint(nv, al.era), tick: tint(nv, al.tick), leader: al.leader.map(function (a) { return tint(nv, a); }),
            onLeader: al.leader.map(function (a) { return on(nv, a); }),
            text: function (kind) { return tint(i, M.text_alpha[kind]); },
            navy: function (kind) { return tint(nv, M.text_alpha[kind]); }};
  }
  function applyTheme() {
    var next = palette(), key = JSON.stringify(next);
    if (key === themeKey) return;
    themeKey = key; P = next;
    halo = "";
    var layout = {"font.color": P.ink, "xaxis.tickfont.color": P.label, "xaxis.linecolor": P.axis,
      "yaxis.tickfont.color": P.label, "yaxis2.tickfont.color": P.label,
      "yaxis.gridcolor": P.grid, "yaxis2.gridcolor": P.grid,
      "modebar.bgcolor": "rgba(0,0,0,0)", "modebar.color": P.label, "modebar.activecolor": P.ink};
    // Every label: its colour, and a halo in the colour behind it.
    function A(i, color, behind) {
      layout["annotations[" + i + "].font.color"] = color;
      layout["annotations[" + i + "].font.shadow"] = haloOf(behind);
    }
    function H(i, props) { for (var k in props) layout["shapes[" + i + "]." + k] = props[k]; }
    H(M.zero.top, {"line.color": P.ink});
    H(M.zero.bottom, {"line.color": P.ink});
    EV.forEach(function (e) {
      H(e.shape, {"line.color": e.tick ? P.tick : P.ink});
      if (e.annotation !== null) A(e.annotation, P.text("event"), P.paper);
    });
    ERAS.forEach(function (e) {
      H(e.bar, {fillcolor: P.era}); H(e.tip, {fillcolor: P.era});
      A(e.annotation, P.navy("era"), P.paper);
    });
    LEADERS.forEach(function (l) {
      H(l.shape, {fillcolor: P.leader[l.tint]}); H(l.tip, {fillcolor: P.era});
      A(l.annotation, P.navy("leader"), P.onLeader[l.tint]);
    });
    BANDS.forEach(function (bd) {
      if (bd.shape !== null) H(bd.shape, {fillcolor: P.limited});
      if (bd.early) H(bd.early.shape, {fillcolor: P.early});
      A(bd.annotation, P.navy("band"), bd.kind === "none" ? P.onNone : P.onLimited);
    });
    A(AN.zero_up, P.text("hint"), P.onLimited);
    A(AN.zero_down, P.text("hint"), P.onLimited);
    A(AN.gap_up, P.text("hint"), P.paper);
    A(AN.gap_down, P.text("hint"), P.paper);
    ARROWS.forEach(function (a) { A(AN[a.role], P.text("arrow"), P.paper); layout["annotations[" + AN[a.role] + "].arrowcolor"] = P.text("arrow"); });
    FILLS.forEach(function (f) {
      if (f.kind === "behind") A(AN[f.role], P.text("fill"), P.onBehind); else A(AN[f.role], M.colors.stock, P.paper);
    });
    // One restyle per attribute group: a null in a per-trace list would unset it.
    send(layout);
    PL.restyle(gd, {fillcolor: P.behind}, [TR.fill_behind]);
    PL.restyle(gd, {fillcolor: P.ahead}, [TR.fill_ahead]);
    PL.restyle(gd, {"fillpattern.bgcolor": P.none, "fillpattern.fgcolor": P.hatch}, [TR.band_none]);
    PL.restyle(gd, {"marker.line.color": P.paper}, [TR.gdp_head, TR.stock_head, TR.markers]);
    PL.restyle(gd, {"marker.color": P.ink, "textfont.color": P.paper}, [TR.markers]);
    PL.restyle(gd, {"marker.color": P.paper}, [TR.anchor_top, TR.anchor_bottom]);
    PL.restyle(gd, {"marker.line.color": P.ink}, [TR.anchor_bottom]);
    if (GEO) refresh();                                 // the bottom panel's name re-reads the colour behind it
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
  function inside(el, cx, cy) {
    var r = el && el.getBoundingClientRect();
    return !!r && cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom;
  }
  function label(i) { return gd.querySelector('.annotation[data-index="' + i + '"]'); }
  // What the cursor is on, besides data: an event (anywhere along its date
  // within its own panel -- a tick's target is as tall as a labelled marker's
  // -- or on its label), a leader's segment, an era (its bar or label), an
  // anchor marker, or an access band. An event or era with notes is followed
  // by them, as dated lines, in date order: those the playhead has reached.
  function describe(px, py, cx, cy, xa, ya, y2) {
    var out = [], st = L.strip, done = playhead >= T1, up = ya._offset - py;      // up: px above the Economy panel
    function shown(t) { return done || playhead - t >= FADE / 2; }
    function tell(parent) {
      out.push(parent.description);
      parent.notes.forEach(function (n) { if (done || n.t <= playhead) out.push({sub: true, text: n.when + ": " + n.text}); });
    }
    EV.forEach(function (e) {
      if (!e.on || !shown(e.t)) return;
      var ax = e.panel === "economy" ? ya : y2, top = ax._offset - (e.tick ? L.tick.up : e.labelled ? e.stem : 0);
      var onLine = Math.abs(xa.l2p(e.t) - px) <= 4 && py >= top - 2 && py <= ax._offset + ax._length;
      var lead = e.tick ? null : e.lead === null ? e : EV[e.lead];       // whose label this event stands under
      if (onLine || (lead && lead.labelled && inside(label(lead.annotation), cx, cy))) tell(e);
    });
    LEADERS.forEach(function (l) {
      if (l.live && px >= l.a && px <= l.b && up >= GEO.leader - 1 && up <= GEO.topStrip + 1) out.push(l.description, M.leader_note);
    });
    ERAS.forEach(function (e) {
      if (!e.live) return;
      var onBar = px >= e.a - 2 && px <= e.b + 2 && up >= GEO.era - 3 && up <= GEO.era + st.era_bar + 3;
      if (onBar || (e.text && inside(label(e.annotation), cx, cy))) tell(e);
    });
    ANCHORS.forEach(function (a) {
      var ax = a.panel === "economy" ? ya : y2;
      if (playhead >= a.t && Math.hypot(xa.l2p(a.t) - px, ax._offset + ax.l2p(0) - py) <= 8) out.push(a.text);
    });
    if (py >= y2._offset && py <= y2._offset + y2._length) BANDS.forEach(function (bd) {
      if (!bd.span || px < bd.span[0] || px > bd.span[1]) return;
      out.push(bd.early && xa.p2l(px) < bd.early.t1 ? bd.early.description : bd.description);
    });
    return out;
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
    var px = cx - r.left - xa._offset, py = cy - r.top, bottomEdge = y2._offset + y2._length;
    if (px < -L.margin.l || px > xa._length + L.margin.r || py < 0 || py > bottomEdge) return hideTip();
    var over = px >= 0 && px <= xa._length;
    var inTop = over && py >= ya._offset && py <= ya._offset + ya._length, inBottom = over && py >= y2._offset;
    var hit = probe(xa.p2l(px), inTop, inBottom), notes = describe(px, py, cx, cy, xa, ya, y2);
    if (hit.gdp < 0 && hit.month < 0 && !notes.length) return hideTip();
    tip.replaceChildren();
    // A plain string is a mark's own text; an object is one of its notes. (Told apart by type:
    // every string has a method called "sub".)
    notes.forEach(function (n) {
      tip.appendChild(typeof n === "string" ? tipRow("china-tip-note", n) : tipRow("china-tip-note china-tip-sub", n.text));
    });
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
    guide.style.display = over && py >= ya._offset ? "block" : "none";
    guide.style.height = (bottomEdge - ya._offset) + "px";
    guide.style.transform = "translate(" + (ox + xa._offset + px) + "px," + (oy + ya._offset) + "px)";
    tip.style.display = "block";
    var tw = tip.offsetWidth, th = tip.offsetHeight, x0 = cx - w.left, y0 = cy - w.top;
    var left = x0 + 14 + tw > w.width - 4 ? x0 - 14 - tw : x0 + 14;
    var top = y0 - th - 12 < 4 ? y0 + 16 : y0 - th - 12;
    tip.style.transform = "translate(" + Math.max(4, left) + "px," + Math.max(4, top) + "px)";
  }

  // ---- Audit (?china-audit): one scale, strip heights, no text on anything, hover ---
  function runAudit() {
    var full = L.drop_from !== null && lastW >= L.drop_from;
    var out = {width: lastW, layout: lastW < M.narrow_below ? "narrow" : "wide",
               dark: document.body.classList.contains("quarto-dark"), hidden: document.hidden, fails: [], frames: {}};
    function names(list) { return list.map(function (e) { return e.label; }); }
    out.top = {labels: FIT.top.labels, font: FIT.top.font, rows: FIT.top.rows, dropped: names(FIT.top.dropped), lineOnly: names(FIT.top.bare)};
    out.bottom = {labels: FIT.bottom.labels, font: FIT.bottom.font, rows: FIT.bottom.rows, dropped: names(FIT.bottom.dropped), lineOnly: names(FIT.bottom.bare)};
    out.eras = {dropped: FIT.eras.dropped, hoverOnly: names(ERAS.filter(function (e) { return e.on && !e.labelled; }))};
    out.leaders = {hoverOnly: names(LEADERS.filter(function (l) { return !l.labelled; }))};
    out.rows = EV.filter(function (e) { return e.on; }).map(function (e) {
      var how = e.tick ? "tick" : e.lead !== null ? "under the label of " + EV[e.lead].label
        : e.labelled ? "“" + e.say + "”, row " + e.row + ", at " + e.spot : "no label";
      return e.label + " [" + e.panel + ", " + how + (e.notes.length ? ", " + e.notes.length + " notes" : "") + "]"; });
    out.arrows = FIT.arrows ? "in plot at " + FIT.arrowFont + " px" : "key";
    // Labels that wait for room after their line, bar or arrow appears, and for how many years.
    out.late = EV.filter(function (e) { return e.on && e.labelled && e.annotation !== null && e.show > e.t; })
      .map(function (e) { return e.label + " +" + ((e.show - e.t) / YEAR).toFixed(1); })
      .concat(ERAS.filter(function (e) { return e.on && e.labelled && e.show > Math.max(e.t0, X0); })
        .map(function (e) { return e.label + " +" + ((e.show - Math.max(e.t0, X0)) / YEAR).toFixed(1); }))
      .concat(ARROWS.filter(function (a) { return a.box && a.box.show > a.t; })
        .map(function (a) { return a.role + " +" + ((a.box.show - a.t) / YEAR).toFixed(1); }));
    out.fillLabels = FILLS.map(function (f) { return f.role + (f.box ? " at " + f.box.x.slice(0, 7) : " hidden"); });
    out.hints = {bottom: FIT.hints.bottom ? "in plot" : "key", top: FIT.hints.top ? "from " + iso(FIT.hints.top.t).slice(0, 7) : "hidden"};
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
    function go(T) { busy = false; pending = null; render(T); return frames(3); }
    // What each label is. `over`: text inside a panel that may lie over a band,
    // a fill or an event's line, which is what its halo is for.
    var who = {};
    EV.forEach(function (e) {
      if (e.annotation !== null) who[e.annotation] = {name: "event: " + e.label, kind: "event", strip: e.panel};
    });
    ERAS.forEach(function (e) { who[e.annotation] = {name: "era: " + e.label, kind: "era", strip: "economy", bar: e, inset: 0}; });
    LEADERS.forEach(function (l) { who[l.annotation] = {name: "leader: " + l.label, kind: "leader", strip: "economy", bar: l, inset: 5}; });
    BANDS.forEach(function (bd) { who[bd.annotation] = {name: "band: " + bd.wraps[0], kind: "band", over: true}; });
    ["zero_up", "zero_down", "gap_up", "gap_down"].forEach(function (r) { who[AN[r]] = {name: r, kind: "hint", over: true}; });
    ARROWS.forEach(function (a) { who[AN[a.role]] = {name: a.role, kind: "arrow", over: true}; });
    FILLS.forEach(function (f) { who[AN[f.role]] = {name: f.role, kind: "fill", over: true, infill: f.kind === "behind"}; });

    // Every visible text box against every other, the bars, the event lines and
    // the data; that each bar's label is still at the bar's start; and how tall
    // the title row and the two strips actually are.
    function collisions(tag) {
      var fl = gd._fullLayout, xa = fl.xaxis, ya = fl.yaxis, y2 = fl.yaxis2, r = gd.getBoundingClientRect(), st = L.strip;
      var X = function (t) { return r.left + xa._offset + xa.l2p(t); }, left = r.left + xa._offset, zoomed = tag === "zoomed";
      var panels = [{ax: ya, top: r.top + ya._offset}, {ax: y2, top: r.top + y2._offset}];
      var boxes = [], bars = [], minText = 1e9, minData = 1e9, minLine = 1e9, crossed = 0;
      var topMost = panels[0].top, midMost = panels[1].top;
      Array.prototype.forEach.call(gd.querySelectorAll(".annotation"), function (el) {
        var i = +el.getAttribute("data-index"), tg = el.querySelector(".annotation-text-g"), a = fl.annotations[i];
        if (!tg || !a || a.visible === false || a.opacity < 0.05) return;
        var b = tg.getBoundingClientRect(), id = who[i] || {name: "#" + i, kind: "?"};
        if (!b.width) return;
        boxes.push({i: i, name: id.name, kind: id.kind, strip: id.strip, over: !!id.over, infill: !!id.infill, bar: id.bar,
                    inset: id.inset, l: b.left, r: b.right, t: b.top, b: b.bottom});
      });
      var tb = title.getBoundingClientRect();
      boxes.push({i: -9, name: "title", kind: "title", l: tb.left, r: tb.right, t: tb.top, b: tb.bottom});
      heads.forEach(function (h, k) {
        var b = h.getBoundingClientRect();
        boxes.push({i: -1 - k, name: k ? "name: Stocks" : "name: Economy", kind: "head", l: b.left, r: b.right, t: b.top, b: b.bottom});
      });
      ERAS.forEach(function (e) {
        if (e.live) bars.push({owner: e, name: "era bar: " + e.label, l: left + e.a - (e.cut ? 10 : 0), r: left + e.b,
                               t: panels[0].top - GEO.era - st.era_bar, b: panels[0].top - GEO.era});
      });
      LEADERS.forEach(function (l) {
        if (l.live) bars.push({owner: l, name: "leader: " + l.label, l: left + l.a - (l.cut ? 11 : 0), r: left + l.b,
                               t: panels[0].top - GEO.topStrip, b: panels[0].top - GEO.leader});
      });
      bars.forEach(function (b) { topMost = Math.min(topMost, b.t); });
      boxes.forEach(function (a, n) {
        if (a.strip === "economy") topMost = Math.min(topMost, a.t);
        if (a.strip === "stocks") {
          midMost = Math.min(midMost, a.t);
          if (a.t < panels[0].top + ya._length + 1) fail(tag + ": the bottom strip runs into the top panel: " + a.name);
        }
        if (a.l < r.left - 1 || a.r > r.right + 1 || a.t < r.top - 1 || a.b > r.bottom + 1)
          fail(tag + ": text outside the figure: " + a.name);
        boxes.forEach(function (c, m) {
          if (m <= n) return;
          var gap = Math.max(c.l - a.r, a.l - c.r, c.t - a.b, a.t - c.b);
          minText = Math.min(minText, gap);
          if (gap < 1) fail(tag + ": text on text: " + a.name + " / " + c.name);
        });
        // Bars: a leader's name sits inside its own segment; nothing else may touch a bar.
        bars.forEach(function (bar) {
          if (a.kind === "leader" && a.bar === bar.owner) {
            if (a.l < bar.l + 1 || a.r > bar.r - 1) fail(tag + ": a leader's name runs outside its segment: " + a.name);
            return;
          }
          if (Math.max(bar.l - a.r, a.l - bar.r, bar.t - a.b, a.t - bar.b) < 1) fail(tag + ": text on a bar: " + a.name + " / " + bar.name);
        });
        // A bar's label stays at the bar's start (or at the plot's left edge).
        if (a.bar && Math.abs(a.l - (left + a.bar.a + a.inset)) > 1.5)
          fail(tag + ": a label has left its bar's start: " + a.name + " by " + (a.l - left - a.bar.a - a.inset).toFixed(1) + " px");
        // Event lines. Haloed text inside a panel may lie over one (they are counted); everything
        // else must stand clear -- the panels' names too, except under a reader's own zoom.
        EV.forEach(function (e) {
          if (e.annotation === a.i || !e.on || (playhead < T1 && playhead <= e.t)) return;
          var pn = panels[e.panel === "economy" ? 0 : 1], x = X(e.t);
          var sh = gd.layout.shapes[e.shape];
          var lineTop = pn.top - (sh.y1 - 1) * pn.ax._length, lineBottom = pn.top + (1 - sh.y0) * pn.ax._length;
          if (a.b <= lineTop + 0.5 || a.t >= lineBottom) return;        // the line does not reach this box
          var gap = Math.max(a.l - x, x - a.r);
          // A tick is short and solid: no text may lie on one, halo or not.
          if (e.tick) { if (gap < 1 && !(zoomed && a.kind === "head")) fail(tag + ": text on a tick: " + a.name + " / " + e.label); return; }
          if (a.over) { if (gap < 0) crossed++; return; }
          if (a.kind === "head" && zoomed) return;
          minLine = Math.min(minLine, gap);
          if (gap < 1) fail(tag + ": text on an event line: " + a.name + " / " + e.label);
        });
        // Data: the lines of whichever panel the box is in. A label inside a fill must clear
        // both lines; anything else must clear the whole tinted area between them. (Not the
        // panels' names under a reader's own zoom: a zoom can bring data up beneath them.)
        panels.forEach(function (pn, k) {
          if (a.b < pn.top || a.t > pn.top + pn.ax._length || (zoomed && a.kind === "head")) return;
          for (var x = Math.floor(a.l) - 2; x <= Math.ceil(a.r) + 2; x++) {
            var T = xa.p2l(x - left);
            if (T > playhead) continue;
            var vals = k === 0 ? [at(G.t, G.y, T)] : [at(S.t, S.s, T), at(S.t, S.e, T)];
            if (vals[0] === null) continue;
            var ys = vals.map(function (v) { return pn.top + pn.ax.l2p(v); }), gap;
            if (a.infill) gap = Math.min.apply(null, ys.map(function (y) { return Math.max(a.t - y, y - a.b); }));
            else gap = Math.max(a.t - Math.max.apply(null, ys), Math.min.apply(null, ys) - a.b);
            minData = Math.min(minData, gap);
            if (gap < 2.5) fail(tag + ": text on the data: " + a.name);
          }
        });
      });
      if (tb.bottom > topMost - 0.5) fail(tag + ": the title runs into the top strip");
      var ppb = [ya._length / (ya.range[1] - ya.range[0]), y2._length / (y2.range[1] - y2.range[0])];
      if (Math.abs(ppb[0] - ppb[1]) > 0.02) fail(tag + ": panels have different scales: " + ppb.join(" vs ") + " px per bit");
      return {texts: boxes.length, minGapText: +minText.toFixed(1), minGapData: +minData.toFixed(1),
              minGapEventLine: +minLine.toFixed(1), overEventLines: crossed, pxPerBit: +ppb[0].toFixed(3),
              xEnd: String(xa.range[1]).slice(0, 10), titleRowPx: +(tb.bottom - r.top).toFixed(1),
              topStripPx: +(panels[0].top - topMost).toFixed(1), bottomStripPx: +(panels[1].top - midMost).toFixed(1)};
    }

    var fill0 = [gd.data[TR.fill_behind].y.slice(), gd.data[TR.fill_ahead].y.slice()];
    return frames(3).then(function () {
      var c = out.frames.complete = collisions("complete");
      out.strips = {title: c.titleRowPx, top: c.topStripPx, bottom: c.bottomStripPx, budget: full ? M.budget : null};
      if (full && c.titleRowPx > M.budget.title) fail("the title row is " + c.titleRowPx + " px tall; the limit is " + M.budget.title);
      if (full && c.topStripPx > M.budget.top) fail("the top strip is " + c.topStripPx + " px tall; the limit is " + M.budget.top);
      if (full && c.bottomStripPx > M.budget.bottom) fail("the bottom strip is " + c.bottomStripPx + " px tall; the limit is " + M.budget.bottom);
      // The script's fill walk reproduces the module's at the end of the data.
      var f = fills(revealPair(T1));
      [f.behind.y, f.ahead.y].forEach(function (y, k) {
        var same = y.length === fill0[k].length && y.every(function (v, i) {
          return v === fill0[k][i] || Math.abs(v - fill0[k][i]) < 1e-9; });
        if (!same) fail("the script's fill differs from the module's (" + (k ? "ahead" : "behind") + ")");
      });
      // The two fills as drawn, flattened onto the page: clearly different colours?
      var page = rgb(P.paper).c, shade = [TR.fill_behind, TR.fill_ahead].map(function (i) {
        var q = rgb(gd._fullData[i].fillcolor);
        return [0, 1, 2].map(function (k) { return page[k] + (q.c[k] - page[k]) * q.a; });
      });
      out.fillContrast = +Math.hypot(shade[0][0] - shade[1][0], shade[0][1] - shade[1][1], shade[0][2] - shade[1][2]).toFixed(1);
      if (out.fillContrast < 40) fail("the two fills are too alike: RGB distance " + out.fillContrast);
      // No label has a box; every label has a halo; the band is hatched.
      var boxed = 0, bare = 0;
      gd.layout.annotations.forEach(function (a) {
        var bg = rgb(a.bgcolor), edge = rgb(a.bordercolor);
        if ((bg && bg.a > 0) || (edge && edge.a > 0)) boxed++;
        if (!a.font || !a.font.shadow || a.font.shadow === "none") bare++;
      });
      var sample = gd.querySelector(".annotation .annotation-text");
      out.text = {boxed: boxed, withoutHalo: bare, rendered: sample ? getComputedStyle(sample).textShadow !== "none" : null};
      if (boxed) fail(boxed + " labels have a background box");
      if (bare || out.text.rendered === false) fail("labels without a halo");
      out.hatch = gd._fullData[TR.band_none].fillpattern.shape + " / " + gd.querySelectorAll("pattern").length + " pattern";
      if (gd._fullData[TR.band_none].fillpattern.shape !== "/" || !gd.querySelector("pattern")) fail("the band is not hatched");
      // Each arrowhead lands on its point.
      var xa = gd._fullLayout.xaxis, y2 = gd._fullLayout.yaxis2, r = gd.getBoundingClientRect();
      out.tips = {};
      ARROWS.forEach(function (a) {
        if (!a.box) return;
        var el = gd.querySelector('.annotation[data-index="' + AN[a.role] + '"]');
        var paths = el ? el.querySelectorAll(".annotation-arrow-g path") : [];
        if (!paths.length) return fail("no arrow is drawn for " + a.role);
        var hb = paths[paths.length - 1].getBoundingClientRect();
        var px = r.left + xa._offset + xa.l2p(a.t), py = r.top + y2._offset + y2.l2p(a.y);
        var d = Math.hypot(Math.max(hb.left - px, 0, px - hb.right), Math.max(hb.top - py, 0, py - hb.bottom));
        out.tips[a.role] = +d.toFixed(2);
        if (d > 2) fail("the arrowhead of " + a.role + " is " + d.toFixed(1) + " px from its point");
      });
      // If a strip had too little room, things are given up in the agreed order.
      if (full) {
        var tight = fitStrip("economy", 300, lastW), tight2 = fitStrip("stocks", 300, lastW), te = fitEras(300, lastW);
        var all = EV.filter(function (e) { return e.panel === "economy" && e.annotation !== null; });
        var allB = EV.filter(function (e) { return e.panel === "stocks" && e.annotation !== null; });
        out.dropOrder = {eras: te.dropped, top: names(tight.dropped), bottom: names(tight2.dropped)};
        if (names(tight.dropped).join() !== names(all.slice(all.length - tight.dropped.length)).join()) fail("top events were not dropped from the end of the list");
        if (names(tight2.dropped).join() !== names(allB.slice(allB.length - tight2.dropped.length)).join()) fail("bottom events were not dropped from the end of the list");
        if (te.dropped.join() !== names(ERAS.filter(function (e) { return e.drop_first; })).join()) fail("the wrong eras were given up first: " + te.dropped.join());
      }
      // Tiers. A tick: a short navy mark, drawn, with no label. A parent's hover text: its own, then
      // its notes as dated lines in date order. (Asked of describe() at the middle of each mark's panel.)
      var fl5 = gd._fullLayout;
      function hoverAt(e) {
        var ax = e.panel === "economy" ? fl5.yaxis : fl5.yaxis2, hx = fl5.xaxis.l2p(e.t), hy = ax._offset + ax._length * 0.6;
        return describe(hx, hy, r.left + fl5.xaxis._offset + hx, r.top + hy, fl5.xaxis, fl5.yaxis, fl5.yaxis2);
      }
      out.ticks = [];
      EV.filter(function (e) { return e.tick; }).forEach(function (e) {
        var sh = fl5.shapes[e.shape], ax = e.panel === "economy" ? fl5.yaxis : fl5.yaxis2, tall = (sh.y1 - sh.y0) * ax._length;
        out.ticks.push(e.label + " (" + tall.toFixed(0) + " px)");
        if (sh.visible === false || !(sh.opacity > 0.5)) fail("a tick is not drawn: " + e.label);
        if (tall > 12 || sh.line.dash !== "solid" || sh.line.color !== P.tick) fail("a tick is not a short navy mark: " + e.label);
        if (hoverAt(e).indexOf(e.description) < 0) fail("a tick's column does not give its hover text: " + e.label);
      });
      out.notes = 0;
      EV.filter(function (e) { return e.on && e.notes.length; }).concat(ERAS.filter(function (e) { return e.on && e.notes.length; }))
        .forEach(function (parent) {
          out.notes += parent.notes.length;
          if (parent.t === undefined) return;                       // an era: its hover is over its bar, tested by hand
          var said = hoverAt(parent), at0 = said.indexOf(parent.description);
          var lines = said.slice(at0 + 1, at0 + 1 + parent.notes.length);
          var want = parent.notes.map(function (n) { return n.when + ": " + n.text; });
          if (at0 < 0 || lines.map(function (n) { return typeof n === "string" ? null : n.text; }).join("|") !== want.join("|"))
            fail("a parent's notes are not listed under it in date order: " + parent.label);
          // And the box as drawn says the same: the parent's own text, then one line per note.
          var ax = parent.panel === "economy" ? fl5.yaxis : fl5.yaxis2, hx = fl5.xaxis.l2p(parent.t);
          showTip(r.left + fl5.xaxis._offset + hx, r.top + ax._offset + ax._length * 0.6);
          var drawn = Array.prototype.map.call(tip.querySelectorAll(".china-tip-note"), function (d) { return d.textContent; });
          var from = drawn.indexOf(parent.description);
          if (from < 0 || drawn.slice(from + 1, from + 1 + want.length).join("|") !== want.join("|"))
            fail("the hover box does not show a parent's text and notes: " + parent.label + " / " + drawn.join(" ; "));
          if (tip.querySelectorAll(".china-tip-sub").length < want.length) fail("notes are not set apart in the hover box: " + parent.label);
          hideTip();
        });
      EV.filter(function (e) { return e.tick; }).forEach(function (e) {
        var ax = e.panel === "economy" ? fl5.yaxis : fl5.yaxis2, hx = fl5.xaxis.l2p(e.t);
        showTip(r.left + fl5.xaxis._offset + hx, r.top + ax._offset + ax._length * 0.6);
        var drawn = Array.prototype.map.call(tip.querySelectorAll(".china-tip-note"), function (d) { return d.textContent; });
        if (drawn.indexOf(e.description) < 0) fail("the hover box does not show a tick's text: " + e.label);
        hideTip();
      });
      // The speed toggle, and the label at the end of the slider.
      speedBtn.click();
      out.controls = {speed: speedBtn.textContent + " after one click", end: endOut.textContent};
      if (speed !== M.play.speeds[1] || speedBtn.textContent !== M.play.speeds[1] + "×") fail("the speed toggle did not switch");
      speedBtn.click();
      if (speed !== M.play.speeds[0]) fail("the speed toggle did not switch back");
      // A horizontal zoom and an autoscale leave the scale alone.
      return PL.relayout(gd, {"xaxis.range": ["2005-01-01", "2012-01-01"]});
    }).then(function () { return frames(4); }).then(function () {
      out.frames.zoomed = collisions("zoomed");
      return PL.relayout(gd, {"xaxis.autorange": true});
    }).then(function () { return frames(4); }).then(function () {
      var fl = gd._fullLayout;
      if (fl.xaxis.autorange) fail("the x-axis is still autoranged after autoscale");
      if (String(fl.xaxis.range[0]).slice(0, 10) !== M.view.x[0]) fail("autoscale did not return to the full view");
      if (!fl.yaxis.fixedrange || !fl.yaxis2.fixedrange) fail("a y-axis can be zoomed");
      // The first frame: one dot, a five-year window.
      return go(T0);
    }).then(function () {
      var c = collisions("first frame"), xa = gd._fullLayout.xaxis;
      c.windowYears = +((xa.r2l(xa.range[1]) - xa.r2l(xa.range[0])) / YEAR).toFixed(2);
      c.points = [gd.data[TR.gdp].x.length, gd.data[TR.gdp_head].x.length, gd.data[TR.stock].x.length];
      out.frames["first frame"] = c;
      if (c.points.join() !== "1,1,0") fail("the first frame is not a single dot: " + c.points.join());
      if (Math.abs(c.windowYears - M.play.min_window_years) > 0.01) fail("the first window is " + c.windowYears + " years");
      if (endOut.textContent !== String(new Date(T1).getUTCFullYear())) fail("the slider's end label changed: " + endOut.textContent);
      // Playback frames.
      var years = [1961.2, 1966.6, 1966.97, 1967.5, 1975, 1977.5, 1985, 1992.6, 1999.3, 2002.5, 2005, 2008.4, 2011.2, 2016, 2023], chain = Promise.resolve();
      years.forEach(function (y) {
        chain = chain.then(function () { return go(Date.UTC(Math.floor(y), 0, 1) + (y % 1) * YEAR); }).then(function () {
          var c = collisions("playback " + y), xa = gd._fullLayout.xaxis;
          c.windowYears = +((xa.r2l(xa.range[1]) - xa.r2l(xa.range[0])) / YEAR).toFixed(2);
          c.watermark = mark.style.display !== "none" ? mark.textContent : null;
          out.frames["playback " + y] = c;
          if (c.windowYears < M.play.min_window_years - 0.01) fail("window narrower than the minimum at " + y);
          if (c.watermark !== String(Math.floor(y))) fail("watermark does not show the year at " + y);
          if (endOut.textContent !== String(new Date(T1).getUTCFullYear())) fail("the slider's end label follows the playhead");
          BANDS.forEach(function (bd) {
            var lab = gd._fullLayout.annotations[bd.annotation];
            if (bd.span && lab.visible !== false && Math.abs(lab.x * GEO.plotW - (bd.span[0] + bd.span[1]) / 2) > 1)
              fail("a band label is off centre at " + y);
          });
        });
      });
      return chain;
    }).then(function () {
      // The scrubber's position is the date, linearly.
      scrub.value = Math.round(scrub.max * 0.5);
      busy = false; pending = null;
      scrub.dispatchEvent(new Event("input", {bubbles: true}));
      return frames(3).then(function () {
        var want = T0 + 0.5 * (T1 - T0);
        out.scrubber = {half: iso(playhead).slice(0, 10), expected: iso(want).slice(0, 10)};
        if (Math.abs(playhead - want) > (T1 - T0) / scrub.max) fail("the scrubber is not linear in the date");
      });
    }).then(function () {
      // Hover at an interpolated playhead: nothing from Plotly, only actual points from us.
      var k = Math.floor(G.t.length * 0.7), Tm = G.t[k] + 0.37 * (G.t[k + 1] - G.t[k]);
      return go(Tm).then(function () {
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
          rows.forEach(function (t) {
            if (known.indexOf(t) < 0) fail("hover row is not an actual data point: " + t);
            if (t.indexOf(" bits") < 0) fail("hover row is not in bits: " + t);
          });
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
          return go(T1);
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
      var after = TOTAL - tauOf(TA);
      out.play = {seconds: +TOTAL.toFixed(1), secondsAt2x: +(TOTAL / M.play.speeds[1]).toFixed(1),
                  stockEraSeconds: +after.toFixed(1), stockEraShare: +(after / TOTAL).toFixed(3)};
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
    T0 = toMs(M.play.start); T1 = toMs(M.play.end); TA = toMs(M.anchor); TG = toMs(M.anchors[0].date);
    X0 = toMs(M.view.x[0]); X1 = toMs(M.view.x[1]); FADE = M.play.fade_years * YEAR;
    EV = M.events.map(function (e) {
      return {t: toMs(e.date), tier: e.tier, tick: e.tier === "tick", panel: e.panel, label: e.label,
              text: e.text, short: e.short, say: e.text, lead: e.lead, description: e.description,
              notes: e.notes.map(function (n) { return {t: toMs(n.date), when: n.when, text: n.text}; }),
              shape: e.shape, annotation: e.annotation, on: true, labelled: e.annotation !== null, row: 0, spot: 0.5,
              ext: [0, 0], show: 0, stem: 0, lift: 3};
    });
    ERAS = M.eras.map(function (e) {
      return {t0: toMs(e.start), t1: toMs(e.end), label: e.label, description: e.description, drop_first: e.drop_first,
              notes: e.notes.map(function (n) { return {t: toMs(n.date), when: n.when, text: n.text}; }),
              bar: e.bar, tip: e.tip, annotation: e.annotation, on: true, labelled: true, live: false, text: false,
              cut: false, a: 0, b: 0, w: 0, show: 0};
    });
    LEADERS = M.leaders.map(function (l) {
      return {t0: toMs(l.start), t1: l.end ? toMs(l.end) : Infinity, label: l.label, description: l.description,
              tint: l.tint, shape: l.shape, tip: l.tip, annotation: l.annotation, labelled: true, live: false,
              text: false, cut: false, a: 0, b: 0, w: 0, show: 0};
    });
    BANDS = M.bands.map(function (bd) {
      return {t0: bd.start ? toMs(bd.start) : -Infinity, t1: toMs(bd.end), kind: bd.kind, wraps: bd.wraps,
              description: bd.description, trace: bd.trace, shape: bd.shape, annotation: bd.annotation, span: null,
              y: bd.trace === null ? null : gd.data[bd.trace].y.slice(),
              early: bd.early ? {t1: toMs(bd.early.end), shape: bd.early.shape, description: bd.early.description} : null};
    });
    ARROWS = M.arrows.map(function (a) {
      return {role: a.role, date: a.date, t: toMs(a.date), y: a.y, month: a.month, mode: a.mode, wraps: a.wraps,
              text: a.text, key: a.key, box: null};
    });
    FILLS = M.fills.map(function (f) {
      return {role: f.role, kind: f.kind, wraps: f.wraps, t0: toMs(f.start), t1: toMs(f.end), box: null};
    });
    ANCHORS = M.anchors.map(function (a) { return {trace: a.trace, panel: a.panel, date: a.date, t: toMs(a.date), text: a.text}; });
    // Integrate the pace profile (seconds per year on a uniform grid) into playback time.
    var spy = M.play.seconds_per_year, stepYears = (T1 - T0) / YEAR / (spy.length - 1);
    TAU = [0];
    for (var i = 1; i < spy.length; i++) TAU.push(TAU[i - 1] + (spy[i] + spy[i - 1]) / 2 * stepYears);
    NP = TAU.length - 1; TOTAL = TAU[NP];
    // The key: a row for the bottom panel's zero line and a numbered row for each arrowed annotation.
    function keyRow(sign, text, t, zero) {
      var row = document.createElement("div");
      row.className = "china-key-row"; row.setAttribute("data-t", t);
      if (zero) row.setAttribute("data-zero", "");
      row.appendChild(sign);
      row.appendChild(document.createTextNode(text));
      keyBox.appendChild(row);
    }
    var line = document.createElement("span");
    line.className = "china-key-line";
    keyRow(line, "Zero line: above it Chinese stocks are ahead since Dec 1998, below it American ones.", TA, true);
    ARROWS.forEach(function (a, n) {
      var num = document.createElement("span");
      num.className = "china-key-n"; num.textContent = n + 1;
      keyRow(num, a.key + ".", a.t, false);
    });
    endOut.textContent = new Date(T1).getUTCFullYear();     // static: the end of the timeline
    setSpeed(M.play.speeds[0]);
    playhead = T1;

    playBtn.addEventListener("click", function () { if (playing) pause(); else play(); });
    speedBtn.addEventListener("click", function () {
      setSpeed(M.play.speeds[(M.play.speeds.indexOf(speed) + 1) % M.play.speeds.length]);
    });
    scrub.addEventListener("input", function () { pause(); render(T0 + scrub.value / scrub.max * (T1 - T0)); });
    gd.on("plotly_relayout", onRelayout);

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
    fontsReady.then(function () { sizes = {}; fit(true); });
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
    the title, each panel's name and the hover overlay in front of it, the key
    used when direct labels do not fit, a play button, a speed toggle and a
    native ``<input type="range">`` scrubber, and the script that fits the
    figure to its column, places the text, draws the animation, follows the
    site's light/dark theme and shows the hover box. Everything the script
    needs comes from the figure itself (the traces and ``layout.meta``).
    """
    import plotly.io as pio

    fig_html = pio.to_html(
        fig, include_plotlyjs="cdn", full_html=False, div_id=_DIV_ID, auto_play=False,
        config={"displaylogo": False, "scrollZoom": False,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"]})
    style = _STYLE.replace("__GDP__", _GDP_COLOR).replace("__STOCK__", _STOCK_COLOR)
    markup = _MARKUP.replace("__TITLE__", TITLE).replace("__FIG__", fig_html)
    return markup + style + _SCRIPT.replace("__DIV__", _DIV_ID)


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


def _sentence_case(label: str) -> bool:
    """Only the first word is capitalised, apart from proper nouns and initialisms."""
    words = [w.strip(",.:;()") for w in label.replace("<br>", " ").split()]
    return all(not w[:1].isupper() or w in _PROPER for w in words[1:])


def _undefined_acronyms(text: str) -> list[str]:
    """The acronyms in a piece of hover text that it does not itself spell out.

    An acronym counts as spelled out if it stands next to its expansion in one
    of the usual ways: "expansion (ABC)", "ABC (expansion)", "(expansion, ABC)"
    or "ABC, or expansion". Names that happen to be capitals (``_NAMES``) pass.
    """
    found = []
    for word in dict.fromkeys(re.findall(r"\b[A-Z]{2,}s?\b", text)):
        if word in _NAMES or word.rstrip("s") in _NAMES:
            continue
        if not any(form in text for form in (f"({word}", f"{word})", f"{word} (", f"{word}, or ")):
            found.append(word)
    return found


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
    html = china_figure_html(fig)
    page = html.rsplit("<script>", 1)[0]             # everything but this module's own script, which comes last
    wide, light = _LAYOUTS["wide"], _ALPHA["light"]
    st = wide["strip"]

    # (1) Units and anchors: everything is in bits, and zero where it should be.
    raw = pd.read_csv(_DATA_PATH, comment="#", parse_dates=["date"])
    nats = raw[(raw["series"] == "gdp") & (raw["entity"] == "CHN")].set_index("date")["log_ratio"]
    year = lambda series, y: series[series.index.year == y].item()
    close(year(g, 2025), (year(nats, 2025) - year(nats, GDP_ANCHOR_YEAR)) / np.log(2), 2e-6, "g is not in bits")
    stock_nats = raw[raw["series"] == "stocks"].set_index("date")["log_ratio"]
    close(s[cutoff], stock_nats[cutoff] / np.log(2), 1e-6, "s is not in bits")
    assert year(g, GDP_ANCHOR_YEAR) == 0.0, "g(1978) != 0"
    assert s[STOCK_ANCHOR] == 0.0 and e[STOCK_ANCHOR] == 0.0, "s or e is not zero in Dec 1998"
    assert stock.x[0] == economy.x[0] == _iso(STOCK_ANCHOR) and stock.y[0] == economy.y[0] == 0.0
    by_hand = year(g, 1998) + (year(g, 1999) - year(g, 1998)) * 183 / 365     # Jul 1 -> Dec 31, 1998
    for d, v in list(e.items())[::37]:
        close(v, g_at(g, d)[0] - by_hand, 3e-6, f"e({d:%Y-%m}) is not g re-anchored at Dec 1998")
    assert gdp_tr.yaxis in (None, "y") and stock.yaxis == economy.yaxis == "y2", "a line is in the wrong panel"
    assert "nats" not in fig.to_json() and " nats" not in page, "something still says nats"

    # (2) One vertical scale: bits per pixel is the same in both panels, in both layouts, in every plan.
    top_span = fig.layout.yaxis.range[1] - fig.layout.yaxis.range[0]
    bottom_span = fig.layout.yaxis2.range[1] - fig.layout.yaxis2.range[0]
    dom_top, dom_bottom = fig.layout.yaxis.domain, fig.layout.yaxis2.domain
    close((dom_top[1] - dom_top[0]) / top_span, (dom_bottom[1] - dom_bottom[0]) / bottom_span, 1e-12,
          "the two panels have different scales as built")
    for name, layout in _LAYOUTS.items():
        plans = layout["strip"]["plans"]
        combos = [((p["rows"], p["pitch"]), (q["rows"], q["pitch"])) for p in plans["top"] for q in plans["bottom"]]
        for rows in combos + [((0, 0), (0, 0))]:
            geo = _geometry(layout, top_span, bottom_span, _strip_heights(layout, *rows))
            plot_px = geo["height"] - geo["t"] - layout["margin"]["b"]
            ppb = [(d[1] - d[0]) * plot_px / span for d, span in ((geo["top"], top_span), (geo["bottom"], bottom_span))]
            close(ppb[0], ppb[1], 1e-9, f"{name}: the panels have different scales")
            close(ppb[0], layout["px_per_bit"], 0.2, f"{name}: the scale is not px_per_bit")
    assert fig.layout.yaxis.fixedrange and fig.layout.yaxis2.fixedrange, "a y-zoom would break the shared scale"
    assert dom_top[0] > dom_bottom[1], "the panels overlap"

    # (3) The title row and the strips fit their budgets at the full column, whichever plan is used.
    assert wide["title_row"] <= TITLE_ROW_MAX_PX and wide["title"] * 1.3 <= wide["title_row"]
    tallest = {}
    for side, limit in (("top", TOP_STRIP_MAX_PX), ("bottom", BOTTOM_STRIP_MAX_PX)):
        for plan in st["plans"][side]:
            px = _strip_heights(wide, **{side: (plan["rows"], plan["pitch"])})[side]
            assert px <= limit, f"{side} strip {px} px > {limit} with {plan['rows']} rows"
            tallest[side] = max(tallest.get(side, 0), px)
            # A row is tall enough for its largest type, with a pixel to spare between rows.
            assert max(plan["fonts"]) * 1.3 + 1 <= plan["pitch"], f"{side}: a {plan['pitch']} px row is too low"
    assert st["era_font"] * 1.3 <= st["era_label"] and st["leader_font"] * 1.3 <= st["leader"] and st["era_bar"] <= 6

    # (4) The window: the bottom panel ends at the common cutoff, and nothing later is in the figure.
    assert cutoff == EXPECTED_CUTOFF, f"the common cutoff moved to {cutoff:%Y-%m-%d}: update the caption"
    assert stock.x[-1] == economy.x[-1] == _iso(EXPECTED_CUTOFF), "the bottom panel does not end at the cutoff"
    assert len(stock.x) == len(economy.x) == len(s) and list(stock.x) == list(economy.x)
    assert s_all.index[-1] > cutoff, "expected later stock data in the derived file (dropped from the plot)"
    latest = max(x for t in fig.data if t.yaxis == "y2" for x in t.x if x)
    assert latest[:10] <= _iso(cutoff), f"the bottom panel holds data after the cutoff: {latest}"

    # (5) The fill: periwinkle exactly where s > e, grey exactly where s < e, and plainly different.
    covered = {}
    for name, sign in (("fill_ahead", 1), ("fill_behind", -1)):
        t = fig.data[tr[name]]
        assert t.fill == "toself" and t.yaxis == "y2"
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
    contrast = {}
    for theme, paper, ink in (("light", PAPER, _INK), ("dark", "#222222", "#ffffff")):
        assert 0.45 <= _ALPHA[theme]["ahead"] <= 0.6, f"{theme}: the periwinkle fill should be about half opaque"
        ahead = _flat(_STOCK_COLOR, _ALPHA[theme]["ahead"], paper)
        behind = _flat(ink, _ALPHA[theme]["behind"], paper)
        contrast[theme] = color_difference(ahead, behind)
        assert contrast[theme] >= 12, f"{theme}: the two fills look too alike (delta-E {contrast[theme]:.1f})"
        assert color_difference(behind, paper) >= 1.5, f"{theme}: the grey fill is invisible"
    assert fig.data[tr["fill_ahead"]].fillcolor == with_alpha(_STOCK_COLOR, light["ahead"])
    assert fig.data[tr["fill_behind"]].fillcolor == with_alpha(_INK, light["behind"])

    # (6) The four annotated points come from the data, and each arrow ends ON its point.
    peak = max(s.index, key=lambda d: s[d])
    trough = min(s[:peak].index, key=lambda d: s[d])
    assert peak == s.idxmax() and trough == s[:peak].idxmin() and trough < peak

    def crossing_by_scanning(a, b):                # an independent route to the same point
        gap = a - b
        for i in range(len(gap) - 1, 0, -1):
            if gap.iloc[i - 1] >= 0 > gap.iloc[i]:
                f = gap.iloc[i - 1] / (gap.iloc[i - 1] - gap.iloc[i])
                return a.index[i - 1] + (a.index[i] - a.index[i - 1]) * f, a.iloc[i - 1] + f * (a.iloc[i] - a.iloc[i - 1])
    points = {"arrow_trough": (trough, float(s[trough])), "arrow_peak": (peak, float(s[peak])),
              "arrow_economy": final_crossing(s, e), "arrow_parity": final_crossing(s, 0.0)}
    for name, other in (("arrow_economy", e), ("arrow_parity", 0.0)):
        when, level = points[name]
        again = crossing_by_scanning(s, other)
        assert abs((when - again[0]).total_seconds()) < 1 and abs(level - again[1]) < 1e-6, f"{name}: two routes disagree"
        month_end = last_fall_below(s, other)       # the crossing lies in the month before that month-end
        assert s.index[s.index.get_loc(month_end) - 1] < when <= month_end
        assert (s[when:].iloc[1:] < (other[when:].iloc[1:] if isinstance(other, pd.Series) else other)).all()
    assert points["arrow_parity"][1] == 0.0, "the Jul 2022 arrow must end on the zero line"
    when = points["arrow_economy"][0]
    close(points["arrow_economy"][1], np.interp(_days(when)[0], _days(e.index), e.to_numpy()), 2e-6,
          "the Dec 2010 arrow is not where the two lines cross")
    assert [a["role"] for a in meta["arrows"]] == list(points), "the annotations are out of order"
    for a_meta in meta["arrows"]:
        when, level = points[a_meta["role"]]
        a = fig.layout.annotations[meta["ann"][a_meta["role"]]]
        assert a.x == a_meta["date"] == pd.Timestamp(when).strftime("%Y-%m-%d %H:%M:%S"), f"{a_meta['role']}: wrong date"
        assert a.y == a_meta["y"] == level and a.showarrow and a.standoff == 0, f"{a_meta['role']}: off its point"
    texts = {a["role"]: a["text"] for a in meta["arrows"]}
    assert texts["arrow_peak"] == f"{_month(peak)} peak: Chinese stocks ×{2 ** s[peak]:.1f} US stocks since Dec 1998"
    assert texts["arrow_trough"] == f"{_month(trough)} trough: Chinese stocks ×{2 ** s[trough]:.2f} US stocks since Dec 1998"
    expected = {"arrow_trough": "2002-01", "arrow_peak": "2007-10", "arrow_economy": "2010-12", "arrow_parity": "2022-07"}

    # (7) Hover: Plotly labels nothing; our box can only report actual points, in bits.
    assert fig.layout.hovermode is False, "Plotly hover must be off"
    assert all(t.hoverinfo == "skip" for t in fig.data), "a trace can still produce a Plotly hover label"
    assert not fig.frames, "no Plotly frames: interpolated points exist only inside the browser's draw call"
    hover = meta["hover"]
    assert len(hover["gdp"]) == len(gdp_tr.x) and len(hover["stock"]) == len(hover["economy"]) == len(stock.x)
    read = lambda text: float(text.split(": ")[1].split(" bits")[0].replace("−", "-"))
    for text, x, v in zip(hover["gdp"], gdp_tr.x, gdp_tr.y):
        assert text.startswith(f"Economy ({x[:4]})") and text.endswith(" bits"), "GDP hover names the wrong year"
        close(read(text), round(v, 2), 1e-9, "GDP hover is not g(t)")
    for d, ts, te in zip(s.index, hover["stock"], hover["economy"]):
        assert ts.startswith(f"Stocks ({_month(d)})") and te.startswith(f"Economy ({_month(d)})")
        close(read(ts), round(s[d], 2), 1e-9, "stock hover is not s(t)")
        close(read(te), round(e[d], 2), 1e-9, "economy hover is not e(t)")
    assert _bits(2.239, False) == "+2.24 bits" and _bits(-0.118, False) == "−0.12 bits"
    assert _bits(2.24, True) == "+2.24 bits (×4.7)" and _bits(-0.573, True) == "−0.57 bits (×0.67)"
    assert _bits(-0.004, False) == "+0.00 bits", "a rounded zero must not print as minus zero"
    assert [a["text"] for a in meta["anchors"]] == [f"{GDP_ANCHOR_YEAR} = 0", "Dec 1998 = 0"]
    for a in meta["anchors"]:
        marker = fig.data[tr[a["trace"]]]
        assert list(marker.x) == [a["date"]] and list(marker.y) == [0.0] and marker.mode == "markers"
        assert marker.marker.size >= 1.5 * 7, "the anchor dots should be half as big again as they were"
    assert fig.data[tr["anchor_top"]].x[0][:4] == str(GDP_ANCHOR_YEAR)

    # (8) Axes, title and names: no axis titles, no tick marks, signed labels, the unit once per panel.
    for axis in (fig.layout.yaxis, fig.layout.yaxis2):
        assert axis.ticks == "" and not axis.title.text and axis.side in (None, "left")
        text = list(axis.ticktext)
        assert sum("bit" in t for t in text) == 1 and "bit" in text[-1], "the unit belongs on the top tick alone"
        assert text[-1].endswith(" bit" if text[-1].startswith("+1 ") else " bits")
        assert all(t == "0" or t[0] in "+−" for t in text) and not any("-" in t for t in text)
    assert fig.layout.xaxis.ticks == "" and not fig.layout.showlegend
    assert sum(k.startswith("yaxis") for k in fig.layout.to_plotly_json()) == 2, "exactly one y-axis per panel"
    assert TITLE == "China ÷ United States" and f'<div class="china-title">{TITLE}</div>' in page
    for word in ("Economy", "Stocks"):
        assert re.search(rf'<div class="china-head china-head-\w+">{word}</div>', page), f"no panel name: {word}"
    # The zero lines: the same treatment in both panels, a little heavier than a gridline, and no "China = US".
    zero_top, zero_bottom = (fig.layout.shapes[meta["zero"][k]] for k in ("top", "bottom"))
    assert zero_top.line.to_plotly_json() == zero_bottom.line.to_plotly_json() == dict(color=_INK, width=1.2)
    assert zero_top.layer == zero_bottom.layer == "between" and zero_top.y0 == zero_bottom.y0 == 0
    assert (zero_top.yref, zero_bottom.yref, zero_bottom.x0) == ("y", "y2", _iso(STOCK_ANCHOR))
    assert [zero_top.x0, zero_top.x1] == list(fig.layout.xaxis.range) and zero_bottom.x1 == zero_top.x1
    assert "China = US" not in html and not any(axis.zeroline for axis in (fig.layout.yaxis, fig.layout.yaxis2))
    hints = {k: fig.layout.annotations[meta["ann"][k]] for k in _HINTS}
    assert {k: a.text for k, a in hints.items()} == _HINTS
    assert hints["gap_up"].text == "Gap narrower than in 1978" and hints["gap_down"].text == "Gap wider than in 1978"
    assert hints["gap_up"].yref == hints["gap_down"].yref == "y" and hints["gap_up"].xanchor == "left"
    assert hints["zero_up"].yref == "y2" and hints["zero_up"].x == _iso(STOCK_ANCHOR) and hints["zero_up"].xanchor == "right"
    assert (hints["gap_up"].yanchor, hints["gap_down"].yanchor) == ("bottom", "top")       # above and below zero

    # (9) Text: sentence case throughout; no label has a box, every label has a halo.
    labels = ([ev.label for ev in EVENTS] + [ev.short for ev in EVENTS if ev.short]
              + [ev["text"] for ev in meta["events"] if ev["text"]]
              + [era.label for era in ERAS] + [who.label for who in LEADERS]
              + [w for band in BANDS for w in band.wraps] + list(_HINTS.values())
              + [w for spec in _FILL_LABELS.values() for w in spec["wraps"]] + list(texts.values()))
    shouting = [label for label in labels if not _sentence_case(label)]
    assert not shouting, f"not in sentence case: {shouting}"
    assert any(spec["wraps"][0].replace("<br>", " ") == "Stocks outpace the economy" for spec in _FILL_LABELS.values())
    assert any(spec["wraps"][0].replace("<br>", " ") == "Stocks lag the economy" for spec in _FILL_LABELS.values())
    for a in fig.layout.annotations:
        assert a.bgcolor is None and a.bordercolor is None and not a.borderpad, f"a label has a box: {a.text}"
        assert a.font.shadow and a.font.shadow.startswith(_HALO_OFFSETS[0]), f"a label has no halo: {a.text}"
        assert not a.textangle, f"a label is not horizontal: {a.text}"
    names_css = [rule for rule in _STYLE.split("}") if ".china-head" in rule or ".china-title" in rule]
    assert names_css and not any("background" in rule for rule in names_css), "the title or a panel's name has a box"
    assert any("text-shadow" in rule for rule in names_css), "the panels' names have no halo"

    # (10) Events, by tier. Every event lies inside the plotted range, and each tier renders as it should:
    #      a labelled marker as a dashed ink line through its own panel with a label (its own, or its
    #      group's); a tick as a short solid navy mark at the top of its panel with no label; a stored
    #      event not at all.
    x0, x1 = fig.layout.xaxis.range
    assert all(ev.panel in ("economy", "stocks") and ev.tier in ("label", "tick", "stored") for ev in EVENTS)
    for ev in EVENTS:
        assert x0 <= ev.date <= _iso(cutoff) <= x1, f"event outside the plotted range: {ev.label} ({ev.date})"
        assert ev.narration_text is None and ev.image is None, "narration fields are unused this round"
        assert ev.description.endswith("."), f"hover text should end with a full stop: {ev.label}"
    chatgpt = next(ev for ev in EVENTS if "ChatGPT" in ev.label)
    assert not re.search(r"caus|led to|trigger|because|drove|sparked|sent ", chatgpt.description), chatgpt.description
    labelled, ticks, stored = ([ev for ev in EVENTS if ev.tier == tier] for tier in ("label", "tick", "stored"))
    in_time = lambda evs, panel: [ev.label for ev in sorted(evs, key=lambda ev: ev.date) if ev.panel == panel]
    assert in_time(labelled, "economy") == [
        "Nixon in Beijing", "Deng's reforms", "Joins World Bank, IMF", "Special economic zones", "Tiananmen",
        "Southern Tour", "Currency unification", "Hong Kong handover", "Joins WTO", "Chinese stimulus", "Property crisis"]
    assert in_time(labelled, "stocks") == [
        "Shenzhen exchange opens", "First B-shares", "First H-shares", "QFII", "Financial crisis", "Stock Connect",
        "Crash", "A-shares join MSCI", "US tariffs", "Chinese tech crackdown", "Chinese stimulus"]
    assert in_time(ticks, "economy") == ["Friedman visits"]
    assert in_time(ticks, "stocks") == ["Renminbi de-pegged", "ICBC IPO", "Chinese ADRs join MSCI"]
    # The order they are given up in (the round-4 order): from the end of each panel's list.
    kept = lambda panel: [ev.label for ev in labelled if ev.panel == panel]
    assert kept("economy")[::-1][:4] == ["Property crisis", "Currency unification", "Hong Kong handover", "Chinese stimulus"]
    assert kept("stocks")[::-1][:2] == ["Shenzhen exchange opens", "First H-shares"]
    drawn = meta["events"]
    assert [(ev["label"], ev["panel"]) for ev in drawn] == [
        (ev.label, ev.panel) for panel in ("economy", "stocks") for ev in EVENTS if ev.tier != "stored" and ev.panel == panel]
    assert not {ev.label for ev in stored} & {ev["label"] for ev in drawn}, "a stored event is drawn"
    domain = {"economy": "y domain", "stocks": "y2 domain"}
    built = _geometry(wide, top_span, bottom_span, _strip_heights(wide))
    panel_px = {"economy": built["top_h"], "stocks": built["bottom_h"]}
    for ev in drawn:
        line = fig.layout.shapes[ev["shape"]]
        assert line.type == "line" and line.x0 == line.x1 == ev["date"], f"{ev['label']} is not at its date"
        assert line.yref == domain[ev["panel"]], f"{ev['label']} leaves its panel"
        assert "narration_text" in ev and "image" in ev and "panel" in ev and ev["description"]
        if ev["tier"] == "tick":
            assert ev["annotation"] is None and ev["text"] is None and ev["lead"] is None, f"a tick has a label: {ev['label']}"
            assert line.line.dash in (None, "solid") and _rgb(line.line.color).tolist() == _rgb(_CONTEXT).tolist()
            assert line.line.width > 1 and line.opacity in (None, 1), f"a tick should be a firm navy mark: {ev['label']}"
            above, below = (line.y1 - 1) * panel_px[ev["panel"]], (1 - line.y0) * panel_px[ev["panel"]]
            close(above, wide["tick"]["up"], 1e-6, "a tick reaches the wrong height above its panel")
            close(below, wide["tick"]["down"], 1e-6, "a tick reaches the wrong depth into its panel")
            # It costs no height: it stops where the first row of labels starts, 3 px above the panel.
            assert above <= 3 and above + below <= 12, f"a tick should be short: {ev['label']}"
            continue
        assert line.line.dash == "dash" and line.line.color == _INK and line.y0 == 0 and line.y1 > 1
        if ev["lead"] is None:
            label = fig.layout.annotations[ev["annotation"]]
            assert label.x == ev["date"] and label.yref == domain[ev["panel"]] and label.text == ev["text"]
        else:                                      # under the label its group shares
            lead = drawn[ev["lead"]]
            assert ev["annotation"] is None and lead["annotation"] is not None and lead["panel"] == ev["panel"]
            assert ev["label"] in lead["text"] and lead["date"] < ev["date"]
            assert line.y1 == fig.layout.shapes[lead["shape"]].y1, f"{ev['label']} does not reach its shared label"
    for name in {ev.group for ev in EVENTS if ev.group}:
        at = [i for i, ev in enumerate(EVENTS) if ev.group == name]
        members = [EVENTS[i] for i in at]
        assert at == list(range(at[0], at[-1] + 1)) and len(members) > 1, f"group {name} is not together in the list"
        assert [m.date for m in members] == sorted(m.date for m in members) and len({m.panel for m in members}) == 1
        assert all(m.tier == "label" for m in members), f"group {name} mixes tiers"
    by_label = lambda label, panel: next(ev for ev in drawn if ev["label"] == label and ev["panel"] == panel)
    assert by_label("A-shares join MSCI", "stocks")["text"] == "2018: A-shares join MSCI · US tariffs"
    assert by_label("US tariffs", "stocks")["lead"] == drawn.index(by_label("A-shares join MSCI", "stocks"))
    assert sum(ev["annotation"] is not None for ev in drawn) == len(labelled) - 1, "one label per event or group"
    sez = by_label("Special economic zones", "economy")
    assert sez["date"] == "1980-08-26" and sez["short"] == "SEZs" and "special economic zones (SEZs)" in sez["description"]
    assert by_label("Chinese tech crackdown", "stocks")["date"] == "2020-11-03"
    stimulus = by_label("Chinese stimulus", "stocks")
    assert "central bank" in stimulus["description"] and "market-support" in stimulus["description"]
    both = build_china_figure(tiers=("label", "tick", "stored"))
    assert len(both.layout.meta["events"]) == len(EVENTS), "a stored event does not pass through the same builder"

    # (10b) Notes: each is attached to a parent that exists in the figure, lies inside the plotted
    #       range, and is listed under its parent in date order. And every acronym is spelled out in
    #       the hover text it appears in.
    era_meta = {era["label"]: era for era in meta["eras"]}
    parents = ([(ev, by_label(ev.label, ev.panel) if ev.tier != "stored" else None) for ev in EVENTS if ev.notes]
               + [(era, era_meta.get(era.label)) for era in ERAS if era.notes])
    assert {p.label: len(p.notes) for p, _ in parents} == {
        "Deng's reforms": 3, "Property crisis": 1, "QFII": 2, "Stock Connect": 2, "Crash": 1, "Cultural Revolution": 5}
    for parent, shown in parents:
        assert shown is not None, f"notes on something that is not drawn: {parent.label}"
        in_order = sorted(parent.notes, key=lambda n: n.date)
        assert [(n["date"], n["when"], n["text"]) for n in shown["notes"]] == [(n.date, n.when, n.text) for n in in_order]
        for n in parent.notes:
            assert x0 <= n.date <= _iso(cutoff), f"a note outside the plotted range: {n.when} ({parent.label})"
            assert n.when and n.text.endswith("."), f"{n.when}: {n.text}"
            assert pd.Timestamp(n.date).year == int(re.search(r"(19|20)\d\d", n.when).group()), f"{n.when} is not {n.date}"
    assert sum(len(ev["notes"]) for ev in drawn) + sum(len(era["notes"]) for era in meta["eras"]) == sum(
        len(p.notes) for p, _ in parents), "a note has no parent in the figure"
    hovers = {ev.label: " ".join([ev.description] + [n.text for n in ev.notes]) for ev in EVENTS}
    hovers.update({era.label: " ".join([era.description] + [n.text for n in era.notes]) for era in ERAS})
    hovers.update({who.label: who.description + " " + LEADER_NOTE for who in LEADERS})
    hovers.update({band.wraps[0]: band.description + " " + (band.early_description or "") for band in BANDS})
    for name, text in hovers.items():
        assert not _undefined_acronyms(text), f"{name}: {_undefined_acronyms(text)} not spelled out in its hover text"
    assert _undefined_acronyms("The WTO and the IMF (International Monetary Fund).") == ["WTO"]

    # (11) Leaders and eras: navy, in their own rows above the event labels, labels pinned to the bar's start.
    strips = _strip_heights(wide)
    top_h = _geometry(wide, top_span, bottom_span, strips)["top_h"]
    navy = _rgb(_CONTEXT).tolist()
    assert _CONTEXT.lower() == "#1e3a8a" and color_difference(_CONTEXT_DARK, "#222222") > color_difference(_CONTEXT, "#222222")
    assert [who["label"] for who in meta["leaders"]] == ["Mao", "Hua", "Deng", "Jiang", "Hu", "Xi"]
    assert LEADERS[0].start < x0 and LEADERS[-1].end is None, "the row should run off both ends of the plot"
    for before, after in zip(LEADERS, LEADERS[1:]):
        gap = (pd.Timestamp(after.start) - pd.Timestamp(before.end)).days
        assert 0 <= gap <= 31, f"the leaders' row is not continuous between {before.label} and {after.label}"
    assert meta["leader_note"] == LEADER_NOTE and "conventional" in LEADER_NOTE and "1992" in LEADER_NOTE
    for n, who in enumerate(meta["leaders"]):
        seg, label = fig.layout.shapes[who["shape"]], fig.layout.annotations[who["annotation"]]
        assert seg.type == "rect" and seg.yref == "y domain" and _rgb(seg.fillcolor).tolist() == navy
        close((seg.y0 - 1) * top_h, strips["leader"], 1e-6, "a leader's segment starts at the wrong height")
        close((seg.y1 - seg.y0) * top_h, st["leader"], 1e-6, "a leader's segment is the wrong height")
        assert fig.layout.shapes[who["tip"]].visible == (who["start"] < x0), "the began-earlier marker is misplaced"
        assert label.xanchor == "left" and label.x == max(who["start"], x0) and _rgb(label.font.color).tolist() == navy
        if n:                                      # two tints, alternating
            assert seg.fillcolor != fig.layout.shapes[meta["leaders"][n - 1]["shape"]].fillcolor
    assert len({fig.layout.shapes[who["shape"]].fillcolor for who in meta["leaders"]}) == 2
    assert [era["label"] for era in meta["eras"]] == ["Famine", "Cultural Revolution", "Retrenchment",
                                                      "WTO export boom", "Zero-COVID"]
    assert [era.label for era in ERAS if era.drop_first] == ["Retrenchment", "WTO export boom"]
    assert "Mao era" not in labels, "the leaders' row replaces the Mao era bar"
    for before, after in zip(ERAS, ERAS[1:]):
        assert before.end < after.start, f"{before.label} and {after.label} overlap, and the eras share a row"
    for era in meta["eras"]:
        bar, label = fig.layout.shapes[era["bar"]], fig.layout.annotations[era["annotation"]]
        assert bar.type == "rect" and bar.yref == "y domain" and _rgb(bar.fillcolor).tolist() == navy
        close((bar.y0 - 1) * top_h, strips["era"], 1e-6, "an era bar starts at the wrong height")
        close((bar.y1 - bar.y0) * top_h, st["era_bar"], 1e-6, "an era bar is not the height it should be")
        assert bar.y1 < fig.layout.shapes[meta["leaders"][0]["shape"]].y0, "an era bar reaches the leaders' row"
        assert fig.layout.shapes[era["tip"]].visible == (era["start"] < x0), "the began-earlier marker is misplaced"
        assert label.xanchor == "left" and label.yanchor == "bottom" and label.x == max(era["start"], x0)
        assert label.yshift == strips["era_label"] > strips["era"] + st["era_bar"], "an era's label is not above its bar"
        assert _rgb(label.font.color).tolist() == navy
    in_top = [sh for sh in fig.layout.shapes if sh.yref == "y domain" and sh.type == "rect" and sh.y0 < 1]
    assert not in_top and not any(t.fill for t in fig.data if t.yaxis in (None, "y")), "no shading in the top panel"

    # (12) Access bands: navy, quieter than the old grey, hatched while there was no exchange.
    assert [b["kind"] for b in meta["bands"]] == ["none", "limited"]
    assert [b["end"] for b in meta["bands"]] == [_EXCHANGE_OPENS, _iso(STOCK_ANCHOR)] and meta["bands"][0]["start"] is None
    hatched = fig.data[tr["band_none"]]
    assert meta["bands"][0]["trace"] == tr["band_none"] and hatched.yaxis == "y2" and hatched.fill == "toself"
    assert hatched.fillpattern.shape == "/" and _rgb(hatched.fillpattern.fgcolor).tolist() == navy
    assert _rgb(hatched.fillpattern.bgcolor).tolist() == navy and list(hatched.x)[1] == _EXCHANGE_OPENS
    assert tr["band_none"] < tr["fill_behind"] < tr["economy"] < tr["stock"], "the band must lie under the data"
    plain = meta["bands"][1]
    box, early = fig.layout.shapes[plain["shape"]], fig.layout.shapes[plain["early"]["shape"]]
    for sh in (box, early):
        assert sh.yref == "y2 domain" and (sh.y0, sh.y1) == (0, 1) and sh.layer == "below" and sh.x0 == _EXCHANGE_OPENS
        assert _rgb(sh.fillcolor).tolist() == navy
    first_b = next(ev for ev in EVENTS if ev.label == "First B-shares")
    assert box.x1 == _iso(STOCK_ANCHOR) and early.x1 == plain["early"]["end"] == first_b.date
    assert plain["early"]["description"] == "Dec 1990 – Feb 1992: A-shares only, closed to foreigners."
    assert plain["description"].startswith("From Feb 1992, a small B-share market for foreign investors;")
    assert "19 December 1990" in meta["bands"][0]["description"], "Shanghai's opening belongs in the hover text"
    assert [b["wraps"][0] for b in meta["bands"]] == ["No stock exchange", "Exchanges open, mostly closed to foreigners"]
    for theme, paper in (("light", PAPER), ("dark", "#222222")):
        al, ctx = _ALPHA[theme], _CONTEXT if theme == "light" else _CONTEXT_DARK
        assert al["band_limited"] < al["band_none"] <= 0.08 and al["band_early"] > 0, f"{theme}: the tints are out of order"
        quiet, old = _flat(ctx, al["band_none"], paper), _flat(_INK if theme == "light" else "#ffffff", 0.10, paper)
        assert color_difference(quiet, paper) < color_difference(old, paper), f"{theme}: the band is not quieter than it was"
    said = " ".join(b["description"] + " ".join(b["wraps"]) + ((b["early"] or {}).get("description") or "")
                    for b in meta["bands"])
    assert not re.search(r"capital control", said, re.I), "a band blames capital controls for the data gap"
    assert not re.search(r"red tape", html, re.I), "B-shares are not to be called red tape"
    # Lime and periwinkle are for data: no shape wears them, and no label but the one for the periwinkle fill.
    data_colours = [_rgb(_GDP_COLOR).tolist(), _rgb(_STOCK_COLOR).tolist()]
    for sh in fig.layout.shapes:
        assert _rgb(sh.fillcolor or sh.line.color).tolist() in (navy, _rgb(_INK).tolist()), "a shape is in a data colour"
    for i, a in enumerate(fig.layout.annotations):
        assert (_rgb(a.font.color).tolist() in data_colours) == (i == meta["ann"]["fill_ahead"]), a.text

    # (13) Playback: a single dot to start, a five-year window, 65-75 s at 1x, no jolts, two speeds.
    play = meta["play"]
    assert play["start"] == gdp_tr.x[0] and play["min_window_years"] == MIN_WINDOW_YEARS == 5
    assert play["speeds"] == [1, 2] and 'class="china-speed"' in page and 'class="china-end"' in page
    assert "china-year\"" not in page, "the slider's label no longer follows the playhead"
    profile = np.array(play["seconds_per_year"])
    start, end = pd.Timestamp(play["start"]), pd.Timestamp(play["end"])
    total = playback_seconds(profile, start, end)
    stock_era = playback_seconds(profile, start, end, since=STOCK_ANCHOR)
    assert 65 <= total <= 75, f"playback takes {total:.1f} s at 1x; tune the pacing constants"
    assert SECONDS_PER_YEAR_BEFORE - 1e-6 <= profile.min() and profile[:8].min() <= SECONDS_PER_YEAR_BEFORE * 1.05
    assert profile.max() <= SECONDS_PER_YEAR_AFTER * SLOWDOWN_NEAR_EVENTS + 1e-6
    # No jolts: from one tenth of a year to the next the pace never changes by as much as a tenth.
    jolt = (np.abs(np.diff(profile)) / profile[:-1]).max()
    assert jolt < 0.10, f"the pace changes abruptly somewhere: {jolt:.0%} in a tenth of a year"

    # (14) The top panel takes peer countries without restructuring.
    peers = build_china_figure(peers=("KOR", "JPN"))
    ptr = peers.layout.meta["trace"]
    assert len(ptr["peers"]) == 2 and all(peers.data[i].yaxis in (None, "y") for i in ptr["peers"])
    assert max(ptr["peers"]) < ptr["gdp"] and len(peers.data) == len(fig.data) + 2
    assert all(peers.data[ptr[k]].name == k for k in tr if k != "peers"), "a peer line shifted a named trace"
    assert gdp.shape[1] > 200, "the derived file should keep every World Bank entity"

    # (15) Licensing: no MSCI index level in the figure, the page HTML or the derived file.
    derived = _DATA_PATH.read_text(encoding="utf-8")
    published = {"figure JSON": fig.to_json(), "page HTML": html, "derived file": derived}
    assert '"bdata"' not in published["figure JSON"], "an array was binary-encoded; the JSON must stay readable"
    for name in ("figure JSON", "derived file"):
        # Log ratios are a few bits at most. Any decimal as large as an index
        # level (the smallest is above 50) would be a leak whatever its value.
        big = [v for v in _decimals_in(published[name]) if v >= 20]
        assert not big, f"{name} holds decimals too large to be log ratios: {big[:5]}"
    levels = _raw_msci_levels()
    if levels is None:
        print("  licensing: raw MSCI files not present, so the level-by-level comparison was skipped.")
    else:
        for name, text in published.items():
            decimals = _decimals_in(text)
            idx = np.clip(np.searchsorted(levels, decimals), 1, len(levels) - 1)
            gap = np.minimum(np.abs(levels[idx] - decimals), np.abs(levels[idx - 1] - decimals))
            # 0.006 also catches a level rounded to two decimals.
            leaked = decimals[gap <= 0.006]
            assert not len(leaked), f"{name} contains MSCI index levels: {leaked[:5]}"
        print(f"  licensing: none of the {len(levels)} raw MSCI levels appears in the figure JSON, "
              f"the page HTML or the derived file.")

    print(f"  units: bits throughout (1 bit = ln 2 = {np.log(2):.3f} nats); g({GDP_ANCHOR_YEAR}) = 0, "
          f"s(Dec 1998) = 0, e(Dec 1998) = 0.")
    print(f"  scale: {wide['px_per_bit']} px per bit in both panels (top {top_span:.2f} bits, "
          f"bottom {bottom_span:.2f} bits); y-axes fixed.")
    print(f"  space at the full column, at most, by construction: title row {wide['title_row']} px "
          f"(limit {TITLE_ROW_MAX_PX}), top strip {tallest['top']} px (limit {TOP_STRIP_MAX_PX}), bottom strip "
          f"{tallest['bottom']} px (limit {BOTTOM_STRIP_MAX_PX}). The measured heights are in the browser audit.")
    print(f"  window: stocks {s.index[0]:%Y-%m-%d} to {cutoff:%Y-%m-%d} ({len(s)} month-ends); "
          f"{len(s_all) - len(s)} later months in the derived file are not drawn.")
    months = s - e
    print(f"  fill: {int((months > 0).sum())} months ahead of the economy, {int((months < 0).sum())} behind; "
          f"the two tints differ by delta-E {contrast['light']:.0f} (light) and {contrast['dark']:.0f} (dark).")
    for name, label in (("arrow_trough", "the early trough of the stock ratio"),
                        ("arrow_peak", "the peak of the stock ratio"),
                        ("arrow_economy", "stocks cross below the economy for good"),
                        ("arrow_parity", "stocks cross below US stocks for good")):
        when, level = points[name]
        flag = "as expected" if f"{when:%Y-%m}" == expected[name] else f"NOT the expected {expected[name]}"
        print(f"  annotation: {label}: {when:%d %b %Y}, at {level:+.3f} bits (×{2 ** level:.2f}) ({flag}).")
    print(f"  hover: {len(hover['gdp'])} GDP + {len(hover['stock'])} stock + {len(hover['economy'])} economy "
          f"strings, one per actual point, in bits; Plotly hover off; no frames.")
    count = lambda evs: " + ".join(f"{sum(ev.panel == p for ev in evs)} {p}" for p in ("economy", "stocks"))
    print(f"  events: labelled markers {count(labelled)}; ticks {count(ticks)}; {len(stored)} stored; "
          f"{sum(len(p.notes) for p, _ in parents)} notes on {len(parents)} parents.")
    print(f"  context: {len(LEADERS)} leaders; {len(ERAS)} eras; {len(BANDS)} access bands.")
    print(f"  pacing: {total:.1f} s of playback at 1x ({total / SPEEDS[1]:.1f} s at {SPEEDS[1]}x), "
          f"{stock_era:.1f} s ({stock_era / total:.0%}) of it from Dec 1998 on.")
    print(f"  derived file: {gdp.shape[1]} GDP entities; page HTML {len(html) / 1024:.0f} KB.")

    end_g, end_e, end_s = g.iloc[-1], e.iloc[-1], s.iloc[-1]
    level = gdp["CHN"].dropna().iloc[-1]             # NOT re-based: China's level against America's
    low = s.idxmin()
    print("\n  For the caption (changes in bits, multiple in brackets):")
    print(f"  economy, {GDP_ANCHOR_YEAR} to {g.index[-1].year}:        {end_g:+.3f} (×{2 ** end_g:.1f})")
    print(f"  economy, Dec 1998 to {_month(cutoff)}: {end_e:+.3f} (×{2 ** end_e:.2f})")
    print(f"  stocks,  Dec 1998 to {_month(cutoff)}: {end_s:+.3f} (×{2 ** end_s:.2f})")
    print(f"  shortfall at {_month(cutoff)}:         {end_e - end_s:+.3f} (×{2 ** (end_e - end_s):.2f})")
    print(f"  level, {g.index[-1].year} (China ÷ US):     {level:+.3f} (×{2 ** level:.3f})")
    print(f"  stocks, lowest in the window: {_month(low)}, {s[low]:+.3f} (×{2 ** s[low]:.2f})")


if __name__ == "__main__":
    _run_checks()
