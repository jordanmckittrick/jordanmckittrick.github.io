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
  (total return, USD), re-based to zero on ``STOCK_ANCHOR``,

      s(t) = log2(C_t / U_t) - log2(C_0 / U_0),

  one point per month-end, against the SAME economy series re-based to that
  date, ``e(t) = g(t) - g(STOCK_ANCHOR)`` with ``g`` interpolated linearly to the
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

Animation. The default state is the finished chart, with the two chords and
rates that close the animation. Playback is a play in three ACTS, each with a
fixed x-axis that runs from the start of the plot to the act's own end, so the
stage widens at each act break and nothing but the data moves in between. A
break brings playback to rest, shows the next act's title card, widens the
axis and starts again. The pace within an act comes from BEATS, dated moments
set in the data: every labelled event is one, slowing playback as it passes,
and a beat may carry a card of narration that slows it further
(:func:`act_schedule`). The next labelled event in each strip waits as a
GHOST, faint and already in place. A thin playhead with a year pill marks the
date. At the end, in the bottom panel, a dashed CHORD is drawn from the anchor
to each series' last point, with the average rate it stands for (the final
value in bits over the years since the anchor); both stay on the finished chart. A play button, a 1x / 2x speed toggle and a native range input (not
Plotly's slider, whose handle sticks in a drag state) drive it; the scrubber's
position is the date, linearly, and is marked off in acts. The browser draws
each frame itself as a pure function of a clock: ``requestAnimationFrame``
works out the revealed part of every line, linearly interpolated to the
playhead, the fills between them, how far each bar and band has grown, and
one ``Plotly.update`` writes it all into traces, shapes and annotations that
always exist. (``Plotly.animate`` re-appends SVG trace groups, so a trace left
out of a frame changes its stacking order; nothing here is ever added, removed
or reordered.)

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
(one scale, strip heights, text collisions at rest and at every stage of the
play, one x-range per act, one ghost per strip, cards, chords and rates, arrow
tips, labels that stay put, hover) runs when the page URL carries
``?china-audit``, at whatever width the page has.
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

# ---- Playback (tune these; _run_checks prints what they add up to). Every duration is at 1x. ----
SPEEDS = (1, 2)                  # what the speed toggle steps through
EVENT_SLOWDOWN = 0.4             # near a labelled event the speed falls to this share of its act's base speed ...
EVENT_WINDOW_YEARS = 0.5         # ... eased down and back up over this long either side of the event
CARD_SLOWDOWN = 0.175            # while a beat's card is up, to this share ...
CARD_SECONDS = (1.5, 0.25)       # ... for this long: so much, plus so much a word
CARD_RAMP_YEARS = 0.4            # the easing into and out of a card's slow stretch
STOP_YEARS = 0.6                 # an act starts from rest, and comes to rest, over this long
TRANSITION = dict(card_in=0.6, hold=1.6, widen=1.0, ghost=0.4, card_out=0.6)   # an act break, step by step
FLOURISH = dict(chord=0.7, lag=0.3, labels=0.4)   # the end: each chord, the second one's delay, the rates' fade
GHOST_OPACITY = 0.3              # the next labelled event in each strip, until the playhead reaches it
REVEAL_SECONDS = 0.5             # how long a mark takes to come to full strength once reached
CARD_FADE_SECONDS = 0.4          # how long a beat's card takes to fade in or out
IMAGE_OPACITY = 0.22             # a beat's image, behind the data
WINDOW_MARGIN = 0.02             # room right of an act's end, as a fraction of its x-range

# ---- Space at the full column (hard limits) ----
TITLE_ROW_MAX_PX = 28
TOP_STRIP_MAX_PX = 96            # leaders + eras + event labels
BOTTOM_STRIP_MAX_PX = 52

# The anchors. STOCK_ANCHOR is where the stock series starts and is zero: a
# month-end in the derived file, at or after its first (if the file's month-end
# falls a day or two before the calendar's, the file's is meant). It is the ONLY
# place the date is named. Everything that depends on it follows it (build_china_figure
# takes it as a parameter, and _run_checks builds the figure with another).
GDP_ANCHOR_YEAR = 1978
STOCK_ANCHOR = pd.Timestamp("1998-12-31")
# If set, the stock line before this date is drawn dotted and its hover text says
# why: MSCI China was launched on 31 October 1995, and earlier values are
# back-tested.
STOCK_BACKTESTED_UNTIL: pd.Timestamp | None = None
BACKTEST_NOTE = "MSCI China was launched on 31 October 1995; earlier values are back-tested."
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
_TEXT_ALPHA = dict(event=0.9, hint=0.6, arrow=0.9, fill=0.66, rate=0.9, era=0.95, leader=0.95, band=0.8)
_EVENT_LINE_OPACITY = 0.4
_PLAYHEAD_OPACITY = 0.22  # the playhead: low contrast
_SCHEDULE_STEP_YEARS = 0.05   # the spacing of the schedule the script is given
# A text halo: the text's own outline, in the colour behind it, as eight
# offset copies (a CSS text-shadow). The same recipe as simplex_figure.py.
_HALO_OFFSETS = ("-1.5px 0", "1.5px 0", "0 -1.5px", "0 1.5px",
                 "-1.1px -1.1px", "1.1px -1.1px", "-1.1px 1.1px", "1.1px 1.1px")

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


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
    Event("1978-12-18", "Reform and opening",
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

    ``start`` None means "from the start of the plot"; ``end`` None means "until
    the stock data begin", which is wherever ``STOCK_ANCHOR`` puts it. ``kind`` "none" is the
    hatched band (no exchange at all), "limited" the plain one. ``wraps`` are
    the ways to break the label over lines, widest first; the script uses the
    first that fits the part of the band that is in view, centred there. A band
    may have a first stretch, up to ``early_end``, shaded a touch darker with
    its own hover text and no label. NO TEXT HERE MAY SAY THAT CAPITAL CONTROLS
    CAUSED THE GAP IN THE DATA (the index simply begins when it begins), OR CALL
    B-SHARES RED TAPE.
    """
    start: str | None
    end: str | None          # None: until the stock data begin (STOCK_ANCHOR)
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
    Band(_EXCHANGE_OPENS, None, "limited",
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


@dataclass(frozen=True)
class Act:
    """One act of the animation. Each starts where the one before it ends; the first, with the data.

    Within an act the x-axis is fixed: from the start of the plot to the act's
    end, plus a little room. ``seconds`` is how long the act plays at 1x, the
    breaks between acts apart: the act's base speed is whatever makes its beats
    add up to that (:func:`act_schedule`).
    """
    numeral: str
    title: str
    short: str               # for a scrubber segment too narrow for the title
    end: str | None          # None: the end of the data
    seconds: float


ACTS = [
    Act("I", "Mao's Mayhem", "Mao", "1978-12-18", 22.0),
    Act("II", "Deng's Reforms", "Deng", "1992-02-21", 20.0),
    # Slower: two lines are moving.
    Act("III", "An Investable China", "Investable", None, 55.0),
]


@dataclass(frozen=True)
class Beat:
    """A dated moment that playback slows for, and what it shows while it does.

    ``slow`` is the share of the act's base speed that playback falls to. A
    beat with a card (``lead``, a bold date lead-in, and ``text``) holds that
    speed for as long as the card takes to read, by its word count. It may put
    an ``image`` behind the data, which needs a ``credit`` (shown under the
    card's text, as written), and may pick out an ``event`` by its label. Every labelled event is a beat of its own, without
    a card; those are not listed here.
    """
    date: str
    slow: float = CARD_SLOWDOWN
    lead: str | None = None
    text: str | None = None
    image: str | None = None   # a URL, or a path beside the page
    credit: str | None = None
    event: str | None = None


# PLACEHOLDERS, to exercise the machinery: the narration proper comes later.
BEATS = [
    Beat("1961-06-30", lead="1959–61",
         text="The Great Leap Forward ends in famine. Output per person falls by almost a third."),
    Beat("1990-01-01", lead="1989–90",
         text="Inflation, Tiananmen, austerity. Growth per person falls to 2.5%; the catch-up stalls."),
    Beat("1993-07-15", lead="Jul 1993",
         text="Tsingtao Brewery becomes the first Chinese company to list in Hong Kong (H-shares).",
         event="First H-shares"),
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
        each month-end AS STORED, zero at the file's own first month; every
        month in the file, before and after the plotted window. Re-base it
        with :func:`stock_since`.
    """
    df = pd.read_csv(path, comment="#", parse_dates=["date"])
    gdp = df[df["series"] == "gdp"].pivot(index="date", columns="entity", values="log_ratio") / _LN2
    gdp.columns.name = None
    s = df[(df["series"] == "stocks") & (df["entity"] == "CHN")].set_index("date")["log_ratio"] / _LN2
    s = s.round(_DECIMALS) + 0.0
    s.name = "s"
    assert s.iloc[0] == 0.0 and s.index.is_monotonic_increasing, "the stock series is not as the prep script writes it"
    return gdp, s


def derived_info(path: str | Path = _DATA_PATH) -> dict:
    """What the derived file says of itself in its header: key: value comment lines.

    stocks_variant is "net" or "gross" (the return variant of BOTH indexes:
    they are never mixed) and stocks_start the first month-end of the stock
    series. Written by prepare_china_figure_data.py.
    """
    info = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            key, colon, value = line[1:].partition(":")
            if colon and key.strip() in ("stocks_variant", "stocks_start"):
                info[key.strip()] = value.strip()
    return info


def source_line() -> str:
    """For the caption: the credit both licences ask for, naming the return variant in the file."""
    return ("Sources: World Bank, World Development Indicators (CC BY 4.0), "
            "GDP per capita in constant 2015 US$; MSCI, MSCI China and MSCI USA "
            f"{derived_info()['stocks_variant']} total return indexes in US dollars.")


def anchor_month_end(s_file: pd.Series, anchor: pd.Timestamp | None = None) -> pd.Timestamp:
    """The month-end in the derived file that ``anchor`` names (``STOCK_ANCHOR`` by default).

    The file's month-ends are MSCI's, the last trading day of each month, so
    one can fall a day or two before the calendar's: an anchor is taken to mean
    the file's month-end in the anchor's own month, and that date is where the
    stock line starts.
    """
    anchor = pd.Timestamp(STOCK_ANCHOR if anchor is None else anchor)
    same = s_file.index[(s_file.index.year == anchor.year) & (s_file.index.month == anchor.month)]
    assert len(same) == 1, f"the derived file has no month-end in {anchor:%b %Y} for the stock anchor"
    return same[0]


def stock_since(s_file: pd.Series, anchor: pd.Timestamp | None = None) -> pd.Series:
    """The stock log ratio from ``anchor`` on, zero at ``anchor`` (``STOCK_ANCHOR`` by default).

    ``anchor`` names a month-end in the file (:func:`anchor_month_end`). A log
    ratio re-bases by subtraction, so nothing of the index levels is needed.
    """
    anchor = anchor_month_end(s_file, anchor)
    s = (s_file[anchor:] - s_file[anchor]).round(_DECIMALS) + 0.0
    s.name = "s"
    return s


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


def economy_since_anchor(g: pd.Series, month_ends: pd.DatetimeIndex,
                         anchor: pd.Timestamp | None = None) -> pd.Series:
    """``e(t) = g(t) - g(anchor)`` at the month-ends: the economy, re-anchored (at ``STOCK_ANCHOR`` by default).

    The same series as the top panel's, moved down so that it starts from zero
    where the stock line does. ``g`` is annual, so the values between its July
    points are straight-line interpolations.
    """
    anchor = STOCK_ANCHOR if anchor is None else anchor
    e = np.round(g_at(g, month_ends) - g_at(g, anchor)[0], _DECIMALS) + 0.0
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


def card_seconds(beat: Beat) -> float:
    """How long a beat's card stays up at 1x: by its word count."""
    words = len(f"{beat.lead or ''} {beat.text or ''}".split())
    return CARD_SECONDS[0] + CARD_SECONDS[1] * words


def act_schedule(start: pd.Timestamp, end: pd.Timestamp, seconds: float,
                 dips: list[tuple[pd.Timestamp, float]], cards: list[Beat]) -> dict:
    """One act's playback: time against date, built from its beats.

    Speed is the act's base speed times a factor between 0 and 1, the LEAST of:

    * the stops: playback starts the act from rest and ends it at rest, with a
      constant acceleration over ``STOP_YEARS`` at each end (the only full stops);
    * each of the ``dips`` (a date and a share of base speed: the labelled
      events), eased down and back up over ``EVENT_WINDOW_YEARS`` either side,
      so that overlapping ones merge into the slower;
    * each card, which holds its beat's share of base speed for as long as the
      card takes to read (:func:`card_seconds`), eased over ``CARD_RAMP_YEARS``.

    The base speed is then whatever makes the act last ``seconds``. Returns
    ``tau``, the playback time (s, at 1x) at dates spaced evenly from ``start``
    to ``end``, about ``_SCHEDULE_STEP_YEARS`` apart; ``base``, in years a
    second; and ``windows``, the dates between which each card holds.
    """
    years = (end - start).days / 365.25
    n = int(np.ceil(years / 0.002))                 # a fine grid; the factor is taken at each cell's middle
    x = (np.arange(n) + 0.5) * years / n
    at = lambda when: (pd.Timestamp(when) - start).days / 365.25
    ease = lambda d: 0.5 * (1 + np.cos(np.pi * np.clip(d, 0.0, 1.0)))       # 1 at the centre, 0 from the edge on

    def factor(base):
        f = np.sqrt(np.clip(np.minimum(x, years - x) / STOP_YEARS, 0.0, 1.0))
        for when, slow in dips:
            if -EVENT_WINDOW_YEARS < at(when) < years + EVENT_WINDOW_YEARS:
                f = np.minimum(f, 1 - (1 - slow) * ease(np.abs(x - at(when)) / EVENT_WINDOW_YEARS))
        windows = []
        for beat in cards:
            half = card_seconds(beat) * beat.slow * base / 2          # years covered while the card is up
            f = np.minimum(f, 1 - (1 - beat.slow) * ease((np.abs(x - at(beat.date)) - half) / CARD_RAMP_YEARS))
            windows.append((start + pd.Timedelta(days=365.25 * max(at(beat.date) - half, 0.0)),
                            start + pd.Timedelta(days=365.25 * min(at(beat.date) + half, years))))
        return f, windows

    took = lambda base: float((years / n / (base * factor(base)[0])).sum())
    slow_, fast = 1e-3, 1e3                         # the act gets shorter as the base speed rises: bisect
    for _ in range(40):
        middle = (slow_ * fast) ** 0.5
        slow_, fast = (middle, fast) if took(middle) > seconds else (slow_, middle)
    base = (slow_ * fast) ** 0.5
    f, windows = factor(base)
    edges = np.concatenate([[0.0], np.cumsum(years / n / (base * f))])
    nodes = int(np.ceil(years / _SCHEDULE_STEP_YEARS))
    tau = np.interp(np.linspace(0.0, years, nodes + 1), np.linspace(0.0, years, n + 1), edges)
    return dict(tau=tau, base=base, windows=windows, factor=f, years=x)


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
# rows. ``card`` sizes a beat's card, ``act_card`` an act's title card and
# ``pill`` the year pill under the playhead. ``bare_gap`` is the space between the panels when the bottom strip's
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
        arrow_fonts=[11.5, 10.5, 9.5], band_font=11, fill_font=10.5, hint_font=10, rate_font=10.5,
        card=dict(font=12.5, width=300), act_card=dict(kicker=11.5, title=23), pill=10.5),
    narrow=dict(
        margin=dict(l=46, r=10, b=24), px_per_bit=46, font=11, drop_from=None, modebar=False,
        gdp_width=2.2, stock_width=1.4, economy_width=1.4, head=13.5, title=14, title_row=24, anchor=9,
        tick=dict(up=3, down=6, width=2),
        strip=dict(
            plans=dict(top=[dict(rows=2, pitch=15, fonts=[10, 9.5])], bottom=[dict(rows=2, pitch=15, fonts=[10, 9.5])]),
            era_font=9.5, era_bar=6, era_label=13, leader=14, leader_font=9.5, bare_gap=12),
        arrow_fonts=[10, 9], band_font=9.5, fill_font=9.5, hint_font=9, rate_font=9.5,
        card=dict(font=11.5, width=250), act_card=dict(kicker=10.5, title=18), pill=10),
)
# The four arrowed annotations, in date order: how each may be broken over
# lines (fewest lines first; the script takes the first that fits clear of the
# data) and where its text goes. "above": over the arrow tip, which is the
# highest point of the stock line. "under": below both lines across its own
# width and at least ``gap`` px under the tip -- which, for a tip above the zero
# line, means hung just under that line.
_ARROWS = dict(
    arrow_trough=dict(mode="under", wraps=[
        "{trough} trough: Chinese stocks<br>×{trough_x} US stocks since {anchor}",
        "{trough} trough:<br>Chinese stocks ×{trough_x}<br>US stocks since {anchor}"]),
    arrow_peak=dict(mode="above", wraps=[
        "{peak} peak: Chinese stocks<br>×{peak_x} US stocks since {anchor}",
        "{peak} peak:<br>Chinese stocks ×{peak_x}<br>US stocks since {anchor}",
        "{peak} peak:<br>Chinese stocks<br>×{peak_x} US stocks<br>since {anchor}"]),
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
    stock_anchor: pd.Timestamp | None = None,
    backtested_until: pd.Timestamp | None = None,
    beats: list[Beat] | None = None,
) -> go.Figure:
    """Assemble the figure in its default state: the completed chart.

    Traces, top panel then bottom, each always present and only ever restyled
    (``layout.meta.trace`` names their positions): any peer-country lines, the
    economy line, its anchor marker and its playback head; the hatched band,
    the two fills, the re-anchored economy line, the back-tested stretch of the
    stock line if there is one, the stock line, the anchor marker, the head,
    and the numbered markers used when the arrowed annotations become a key.

    Everything else is a layout shape or annotation, so that it follows the
    data under zoom and during playback: the plain access band and its darker
    first stretch, the band labels, the two zero lines and the labels either
    side of them, the leaders' segments and the era bars with their labels, one
    dashed line per labelled event with a label of its own or one shared with its
    group, one short mark per tick, the arrowed annotations and the labels by
    the fills, the playhead, and the two chords and their rates that close the
    animation. ``layout.meta`` lists them all, and carries the acts, the beats
    and the schedule that playback follows. No annotation has a background:
    each carries a halo (``font.shadow``) in the colour behind it. (The title,
    the panels' names, the cards and the year pill are not in the figure at
    all: they are HTML, added by :func:`china_figure_html`.)

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
    stock_anchor
        Where the stock series starts and is zero; ``STOCK_ANCHOR`` if not
        given. Everything that depends on it follows: the stock line, the
        re-anchored economy line, the anchor marker, the end of the "closed to
        foreigners" band, the zero line, the wording "since ...", the four
        annotated points, and the rates that close the animation.
    backtested_until
        If given (``STOCK_BACKTESTED_UNTIL`` otherwise), the stock line before
        this date is drawn dotted and its hover text says it is back-tested.
    beats
        The beats with cards (``BEATS`` if not given). Every labelled event is
        a beat as well.

    Returns
    -------
    go.Figure
        Built at the wide layout; the script re-fits it to the column.
    """
    backtested = backtested_until if backtested_until is not None else STOCK_BACKTESTED_UNTIL
    gdp, s_file = load_derived()
    anchor_at = anchor_month_end(s_file, stock_anchor)
    g_full = rebased(gdp, "CHN")
    g = g_full[g_full.index.year >= start_year]
    assert g.index[0] < anchor_at and len(g) >= 2, "start_year must precede the stock anchor"
    s_all = stock_since(s_file, anchor_at)
    cutoff = common_cutoff(g, s_all)
    s = s_all[:cutoff]
    e = economy_since_anchor(g_full, s.index, anchor_at)
    since = _month(anchor_at)                                    # how the anchor is named in text: a month and a year
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

    # The acts. Each has a fixed x-range, from the start of the plot to its own
    # end plus a little room; the last act's is the finished chart's.
    first = pd.Timestamp(year=start_year, month=1, day=1)
    data_start = g.index[0]
    ends = [pd.Timestamp(act.end) if act.end else cutoff for act in ACTS]
    starts = [data_start] + ends[:-1]
    reach = [first + (end - first) * (1 + WINDOW_MARGIN) for end in ends]
    x_range = [_iso(first), _iso(reach[-1])]
    # Headroom over the top panel's line keeps its top gridline clear of the
    # panel's name. In the bottom panel the room over the stock line's peak
    # holds that peak's annotation, and the room under the line the other three.
    # These ranges hold in every act, so that magnitudes stay comparable.
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
    anchor = _iso(anchor_at)
    band_end = lambda band: band.end or anchor                   # the plain band ends where the data begin
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
    # The stock line. Where its early stretch is back-tested, that stretch is a
    # dotted trace of its own, and the solid line starts where it ends.
    solid_from = 0
    if backtested is not None and backtested > s.index[0]:
        solid_from = int(np.searchsorted(s.index, pd.Timestamp(backtested)))
        solid_from = min(solid_from, len(s) - 1)
    fig.add_trace(go.Scatter(x=month_x[:solid_from + 1] if solid_from else [], y=stock_y[:solid_from + 1] if solid_from else [],
                             mode="lines", name="stock_back",
                             line=dict(color=_STOCK_COLOR, width=wide["stock_width"], dash="dot"), **bottom, **quiet))
    fig.add_trace(go.Scatter(x=month_x[solid_from:], y=stock_y[solid_from:], mode="lines", name="stock",
                             line=dict(color=_STOCK_COLOR, width=wide["stock_width"]), **bottom, **quiet))
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
                                         "economy", "stock_back", "stock", "anchor_bottom", "stock_head", "markers")}
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
        start, end = x_range[0] if band.start is None else band.start, band_end(band)
        assert start < end, f"the band “{band.wraps[0]}” would end before it starts: move STOCK_ANCHOR or the band"
        none = band.kind == "none"
        entry = dict(start=band.start, end=end, kind=band.kind, wraps=list(band.wraps),
                     description=band.description, trace=trace["band_none"] if none else None, shape=None, early=None)
        if not none:
            entry["shape"] = shape(type="rect", xref="x", yref="y2 domain", x0=start, x1=end, y0=0, y1=1,
                                   fillcolor=with_alpha(_CONTEXT, light["band_limited"]), line=dict(width=0), layer="below")
        if band.early_end and band.early_end < end:
            entry["early"] = dict(
                end=band.early_end, description=band.early_description,
                shape=shape(type="rect", xref="x", yref="y2 domain", x0=start, x1=band.early_end, y0=0, y1=1,
                            fillcolor=with_alpha(_CONTEXT, light["band_early"]), line=dict(width=0), layer="below"))
        tint = light["band_none" if none else "band_limited"]
        entry["annotation"] = note(xref="x domain", yref="y2 domain", x=(frac(start) + frac(end)) / 2, y=band.y,
                                   xanchor="center", yanchor="middle", align="center", text=band.wraps[-2],
                                   size=wide["band_font"], color=navy("band"), behind=on(tint))
        entry["y"] = band.y
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

    # The playhead: a thin, quiet line through each panel at the current date.
    playhead = [shape(type="line", xref="x", yref=domain, x0=x_range[1], x1=x_range[1], y0=0, y1=1, visible=False,
                      line=dict(color=_INK, width=1), opacity=_PLAYHEAD_OPACITY, layer="below")
                for domain in ("y domain", "y2 domain")]

    # The arrowed annotations. Each arrow ends ON its point (no standoff). The
    # script decides where each text goes (ax, ay and the line breaks).
    words = dict(trough=_month(trough), trough_x=_times(2.0 ** s[trough]),
                 peak=_month(peak), peak_x=_times(2.0 ** s[peak]), anchor=since)
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
        head = text.split()[0]
        key = text if text.startswith(_month(when)) else (
            f"{_month(when)}: {text if head in _PROPER else text[0].lower() + text[1:]}")
        arrows.append(dict(role=name, date=stamp(when), y=level, month=_month(when), mode=_ARROWS[name]["mode"],
                           wraps=wraps, text=text, key=key))

    # The labels by the fills; placed by the script.
    fills = []
    for name, spec in _FILL_LABELS.items():
        behind = spec["kind"] == "behind"
        note(name, xref="x", yref="y2", x=anchor, y=1.0, text=spec["wraps"][0], align="center",
             xanchor="center", yanchor="middle", visible=False, size=wide["fill_font"],
             color=ink("fill") if behind else _STOCK_COLOR, behind=on(light["behind"], _INK) if behind else PAPER)
        fills.append(dict(role=name, **spec))

    # The end of the animation: a dashed chord from the anchor to each series'
    # last value, in the bottom panel, and the rate each chord stands for: the
    # final value in bits over the years since the anchor, and 2 to that power.
    years_since = (cutoff - anchor_at).days / 365.25
    last = _iso(cutoff)
    chords = []
    for key, name, value, color in (("economy", "Economy", economy_y[-1], _GDP_COLOR),
                                    ("stocks", "Stocks", stock_y[-1], _STOCK_COLOR)):
        rate = value / years_since
        figure = f"{'+' if rate >= 0 else '−'}{abs(rate):.3f} bits/yr"
        times = f"(×{2.0 ** rate:.3f}/yr)"
        lead = f'<span style="color:{color}"><b>{name}</b></span>: '
        wraps = [f"{lead}{figure} {times}", f"{lead}{figure}<br>{times}"]
        chords.append(dict(
            key=key, name=name, color=color, rate=round(rate, 6), value=value, date=last, wraps=wraps,
            text=f"{name}: {figure} {times}",
            shape=shape(type="line", xref="x", yref="y2", x0=anchor, y0=0, x1=last, y1=value,
                        line=dict(color=color, width=1.6, dash="dash"), layer="between"),
            # (Placed by the script, beside its chord or with the other in the empty stage; in data
            # coordinates, so that it stays put under zoom.)
            annotation=note(f"rate_{key}", xref="x", yref="y2", x=x_range[0], y=y_bottom[0] / (2 if key == "economy" else 4),
                            xanchor="left", yanchor="middle", align="left", text=wraps[0],
                            size=wide["rate_font"], color=ink("rate"), behind=on(light["band_none"]))))

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

    # ---- Playback: the acts, the beats, and the schedule they add up to ----
    # Every labelled event is a beat; so is every card. Within each act the
    # schedule turns them into a table of playback time against date.
    cards = BEATS if beats is None else beats
    dips = [(pd.Timestamp(ev.date), EVENT_SLOWDOWN) for ev in drawn if ev.tier != "tick"]
    acts, shown = [], []
    for n, act in enumerate(ACTS):
        mine = [b for b in cards if starts[n] < pd.Timestamp(b.date) <= ends[n]]
        table = act_schedule(starts[n], ends[n], act.seconds, dips, mine)
        acts.append(dict(
            numeral=act.numeral, title=act.title, short=act.short,
            kicker=f"Act {act.numeral} · {starts[n].year}–{ends[n].year}",
            start=_iso(starts[n]), end=_iso(ends[n]), range=[x_range[0], _iso(reach[n])],
            # The schedule, as the playback time each step of the date grid takes. (Steps, not a
            # running total: every number in the figure stays small enough to be seen not to be an
            # index level.)
            base=round(table["base"], 4), steps=[round(float(v), 5) for v in np.diff(table["tau"])]))
        for beat, (since_, until) in zip(mine, table["windows"]):
            picked = [i for i, ev in enumerate(events) if beat.event and ev["label"] == beat.event]
            assert bool(beat.event) == bool(picked), f"the beat of {beat.date} picks out an event that is not drawn"
            assert not beat.image or beat.credit, f"the image on the beat of {beat.date} needs a credit"
            shown.append(dict(
                date=beat.date, act=n, slow=beat.slow, lead=beat.lead, text=beat.text, seconds=card_seconds(beat),
                since=stamp(since_), until=stamp(until), image=beat.image, credit=beat.credit,
                event=picked[0] if picked else None,
                # Where the card goes: the empty stage of the bottom panel until the last act, then
                # the empty upper left of the top panel.
                panel="stocks" if n < len(ACTS) - 1 else "economy"))
    assert len(shown) == len(cards), "a beat lies outside the data"

    # ---- Axes: one y-axis per panel, no titles, no tick marks ----
    def y_axis(domain, y_range):
        ticks = list(range(int(np.ceil(y_range[0])), int(np.floor(y_range[1])) + 1))
        unit = " bit" if abs(ticks[-1]) == 1 else " bits"
        return dict(domain=domain, range=y_range, fixedrange=True, anchor="x", automargin=False,
                    tickvals=ticks, ticktext=[_signed(v, unit if v == ticks[-1] else "") for v in ticks],
                    ticks="", tickfont=dict(color=LABEL), gridcolor=GRID, zeroline=False)

    tested = None
    if solid_from:
        tested = dict(until=month_x[solid_from], note=BACKTEST_NOTE)
    stock_hover = [f"Stocks ({_month(d)}): {_bits(v, show_multiple)}" + (", back-tested" if i < solid_from else "")
                   for i, (d, v) in enumerate(s.items())]
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
            trace=trace, ann=role, zero=zero, playhead=playhead, events=events, eras=eras, leaders=leaders,
            leader_note=LEADER_NOTE, bands=bands, arrows=arrows, fills=fills, chords=chords, anchor=anchor,
            anchors=[dict(trace="anchor_top", panel="economy", date=gdp_anchor, text=f"{GDP_ANCHOR_YEAR} = 0"),
                     dict(trace="anchor_bottom", panel="stocks", date=anchor, text=f"{since} = 0")],
            key=dict(zero=f"Zero line: above it Chinese stocks are ahead since {since}, below it American ones."),
            backtest=tested,
            hover=dict(
                gdp=[f"Economy ({d.year}): {_bits(v, show_multiple)}" for d, v in g.items()],
                stock=stock_hover,
                economy=[f"Economy ({_month(d)}): {_bits(v, show_multiple)}" for d, v in e.items()],
            ),
            # Playback opens on a single dot, the first data point, and runs act by act.
            play=dict(start=_iso(data_start), end=_iso(cutoff), speeds=list(SPEEDS), acts=acts, beats=shown,
                      transition=TRANSITION, flourish=FLOURISH, reveal=REVEAL_SECONDS, ghost=GHOST_OPACITY,
                      card_fade=CARD_FADE_SECONDS, image_opacity=IMAGE_OPACITY),
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
<div class="china-beat-image" aria-hidden="true"></div>
__FIG__
<div class="china-title">__TITLE__</div>
<div class="china-head china-head-top">Economy</div>
<div class="china-head china-head-bottom">Stocks</div>
<div class="china-beat"><span class="china-beat-lead"></span> <span class="china-beat-text"></span>
  <div class="china-beat-credit"></div></div>
<div class="china-act-card"><div class="china-act-kicker"></div><div class="china-act-name"></div></div>
<div class="china-overlay" aria-hidden="true">
  <div class="china-pill"></div>
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
      <path class="china-ico-replay" d="M8 3.2V.8L4.4 3.9 8 7V4.8a3.9 3.9 0 1 1-3.9 3.9H2.5A5.5 5.5 0 1 0 8 3.2z"/>
    </svg>
  </button>
  <button type="button" class="china-speed" title="Playback speed">1×</button>
  <span class="china-edge china-start" title="The start of the timeline"></span>
  <div class="china-scrub-wrap">
    <input type="range" class="china-scrub" min="0" max="4000" step="1" value="4000"
      aria-label="Move through time">
    <div class="china-acts"></div>
  </div>
  <span class="china-edge china-end" title="The end of the timeline"></span>
</div>
"""

_STYLE = """<style>
/* The figure lives in a position:relative wrapper whose width fit() sets. The
   overlay is a SIBLING of the graph div (Plotly owns that div's children) and
   lets every click and drag through to the plot. */
.china-fig-wrap { position: relative; margin: 0 auto; }
.china-fig-wrap .js-plotly-plot { position: relative; z-index: 1; }
.china-fig-wrap.is-narrow .modebar-container { display: none !important; }
/* A beat's image sits BEHIND the plot, whose background is transparent, so the
   data draws over it. Faint: the script sets its opacity. */
.china-beat-image { position: absolute; left: 0; top: 0; z-index: 0; display: none; pointer-events: none;
  background-size: cover; background-position: center; }
/* Cards: a beat's narration, and an act's title. Page colours, all but opaque,
   so they read over whatever is behind them in either theme. */
.china-beat, .china-act-card { position: absolute; left: 0; top: 0; z-index: 2; display: none; pointer-events: none;
  box-sizing: border-box; color: var(--bs-body-color, #1f2328); background: var(--bs-body-bg, #fff);
  background: color-mix(in srgb, var(--bs-body-bg, #fff) 93%, transparent);
  border: 1px solid var(--bs-border-color, #cfd3d8); border-radius: 4px; }
.china-beat { padding: 6px 10px 7px; line-height: 1.4; text-align: left; }
.china-beat-lead { font-weight: 700; }
.china-beat-credit { margin-top: 3px; font-size: .8em; opacity: .7; }
.china-beat-credit:empty { display: none; }
.china-act-card { padding: 13px 30px 16px; text-align: center; white-space: nowrap; transform: translate(-50%, -50%);
  box-shadow: 0 2px 10px rgba(0, 0, 0, .12); }
.china-act-kicker { line-height: 1.4; letter-spacing: .05em; opacity: .75; font-variant-numeric: lining-nums; }
.china-act-name { margin-top: 2px; line-height: 1.2; font-weight: 700; }
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
/* The year, on the x-axis under the playhead. */
.china-pill { position: absolute; left: 0; top: 0; display: none; padding: 1px 6px; border-radius: 9px;
  line-height: 1.35; white-space: nowrap; font-variant-numeric: tabular-nums lining-nums;
  color: var(--bs-body-bg, #fff); background: var(--bs-body-color, #1f2328); opacity: .82; }
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
.china-tip-row + .china-tip-note { margin-top: 4px; }
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
.china-key-dash { border-top-style: dashed; border-top-width: 2px; }
/* Controls: play (replay, once the play has run), speed, and the scrubber: a
   track from the first year to the last, marked off in acts, each act's title
   under its own stretch. The track's centre line is --track-y from the top. */
.china-controls { --thumb-d: 12.5px; --track-y: 14px; display: flex; align-items: flex-start; gap: 10px;
  margin: .15rem auto 1.1rem; box-sizing: border-box; padding: 0 6px; }
.china-play { flex: none; width: 28px; height: 28px; padding: 0;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
  border-radius: 50%; border: 1px solid var(--bs-border-color, #cfd3d8);
  background: transparent; color: var(--bs-body-color, #1f2328); }
.china-play:hover, .china-speed:hover { border-color: var(--bs-body-color, #1f2328); }
.china-play:focus-visible, .china-speed:focus-visible, .china-scrub:focus-visible, .china-act-label:focus-visible {
  outline: 2px solid __STOCK__; outline-offset: 2px; }
.china-play svg { fill: currentColor; }
.china-play .china-ico-pause, .china-play .china-ico-replay, .china-play.is-playing .china-ico-play,
.china-play.is-done .china-ico-play { display: none; }
.china-play.is-playing .china-ico-pause, .china-play.is-done .china-ico-replay { display: inline; }
/* The speed toggle: small and quiet beside the play button. */
.china-speed { flex: none; min-width: 30px; height: 22px; margin: 3px 0 0 -4px; padding: 0 5px; cursor: pointer;
  border-radius: 11px; border: 1px solid var(--bs-border-color, #cfd3d8); background: transparent;
  font: inherit; font-size: 11.5px; line-height: 1; font-variant-numeric: tabular-nums lining-nums;
  color: var(--bs-body-color, #1f2328); opacity: .75; }
.china-speed.is-fast { opacity: 1; border-color: var(--bs-body-color, #1f2328); }
.china-edge { flex: none; font-size: 12px; line-height: 28px; font-variant-numeric: tabular-nums lining-nums;
  color: var(--bs-body-color, #1f2328); opacity: .85; }
.china-scrub-wrap { position: relative; flex: 1 1 auto; height: 44px; line-height: 0; margin: 0 2px; }
.china-scrub-wrap::before, .china-scrub-wrap::after { content: ""; position: absolute; left: 0; top: var(--track-y);
  height: 3px; border-radius: 2px; transform: translateY(-50%); }
.china-scrub-wrap::before { width: 100%; background: var(--bs-border-color, #cfd3d8); }
.china-scrub-wrap::after { width: var(--china-p, 100%); background: var(--bs-body-color, #1f2328); opacity: .5; }
/* Over the track: a gap in the page's colour where one act gives way to the
   next, and the acts' titles below. Under the thumb, which is the input's. */
.china-acts { position: absolute; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; pointer-events: none; }
.china-act-gap { position: absolute; top: calc(var(--track-y) - 4px); width: 4px; height: 8px; margin-left: -2px;
  background: var(--bs-body-bg, #fff); }
.china-act-label { position: absolute; top: 25px; transform: translateX(-50%); margin: 0; padding: 1px 4px;
  border: 0; border-radius: 3px; background: transparent; cursor: pointer; pointer-events: auto;
  font: inherit; font-size: 11px; line-height: 1.3; white-space: nowrap;
  color: var(--bs-body-color, #1f2328); opacity: .6; }
.china-act-label:hover, .china-act-label.is-current { opacity: 1; }
.china-act-label.is-current { font-weight: 700; }
/* A range thumb's centre travels from d/2 to W - d/2. The input overhangs the
   track by d/2 on each side, so the centre runs the track's full width. */
.china-scrub { -webkit-appearance: none; appearance: none; position: absolute; z-index: 2;
  left: calc(var(--thumb-d) / -2); top: var(--track-y); width: calc(100% + var(--thumb-d)); height: 22px;
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
  var scrubWrap = $(".china-scrub-wrap"), actsBox = $(".china-acts"), startOut = $(".china-start"), endOut = $(".china-end");
  var keyBox = $(".china-key"), guide = $(".china-guide"), tip = $(".china-tip"), title = $(".china-title");
  var pill = $(".china-pill"), actCard = $(".china-act-card"), beatCard = $(".china-beat"), beatImage = $(".china-beat-image");
  var heads = [$(".china-head-top"), $(".china-head-bottom")];
  var dotEl = {gdp: $(".china-dot-gdp"), stock: $(".china-dot-stock"), economy: $(".china-dot-economy")};
  var DAY = 86400000, YEAR = 31557600000, HOUR = 3600000;          // ms
  var PL, M, TR, AN, G, S, PEERS, EV, ERAS, LEADERS, BANDS, ARROWS, FILLS, CHORDS, ANCHORS, ACTS, BEATS, TL, END;
  var T0, T1, TA, TB, TG, X0, X1, FONT;
  var L = null, GEO = null, P = null, FIT = null, STATE = null, lastW = 0, sent = {};
  var clock = 0, playhead = 0, playing = false, played = false, raf = 0, busy = false, pending = null, speed = 1;
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

  // ---- The timeline: acts, the breaks between them, and the clock -----------------
  // Playback is a pure function of one number, the CLOCK: seconds at 1x since
  // play was pressed. The timeline it runs along is the opening title card,
  // then each act with a break after it, then the closing flourish. The 2x
  // toggle only makes the clock run faster, so it halves everything alike.
  // Within an act the playhead's date comes from the act's schedule (the table
  // the Python module built from its beats); in a break the date stands still.
  function actOf(T) {                      // the act that is playing at date T
    for (var k = 0; k < ACTS.length - 1; k++) if (T < ACTS[k].t1) return k;
    return ACTS.length - 1;
  }
  function ownAct(t) {                     // the act during which the playhead REACHES t (an act's last moment is its own)
    for (var k = 0; k < ACTS.length - 1; k++) if (t <= ACTS[k].t1) return k;
    return ACTS.length - 1;
  }
  function tauOf(k, T) {                   // seconds into act k at which the playhead is at T
    var A = ACTS[k], n = A.tau.length - 1, u = clamp((T - A.t0) / (A.t1 - A.t0), 0, 1) * n, i = Math.min(n - 1, Math.floor(u));
    return A.tau[i] + (u - i) * (A.tau[i + 1] - A.tau[i]);
  }
  function timeOf(k, tau) {                // and back
    var A = ACTS[k], n = A.tau.length - 1;
    if (tau <= 0) return A.t0;
    if (tau >= A.tau[n]) return A.t1;
    var j = upper(A.tau, tau) - 1;
    return A.t0 + (j + (tau - A.tau[j]) / (A.tau[j + 1] - A.tau[j])) / n * (A.t1 - A.t0);
  }
  // The clock at which the playhead reaches a date. (What is there before the first date is there from the start.)
  function clockOf(t) {
    if (t <= T0) return -Infinity;
    var k = ownAct(t);
    return ACTS[k].c0 + tauOf(k, t);
  }
  // Where the scrubber puts the clock for a date: in the act that plays at that
  // date, never in a break; at the very end, on the finished chart.
  function clockAt(T) {
    if (T >= T1) return END;
    var k = actOf(T);
    return ACTS[k].c0 + tauOf(k, T);
  }
  function smooth(u) { u = clamp(u, 0, 1); return u * u * (3 - 2 * u); }     // ease in and out
  // Everything about one moment of the timeline: the playhead's date T, where
  // the x-axis ends (r1), which title card is up and how strongly, and how far
  // the things that arrive with an act have arrived.
  //   newAct / newAlpha: marks belonging to acts before newAct may show; those
  //     of newAct itself at strength newAlpha (they arrive, as ghosts or as
  //     labels that had to wait for the wider axis, only after it has widened).
  //   layoutAct / layoutAlpha: labels that are placed afresh for each act's
  //     range cross-fade from one placing to the next while the axis widens.
  function stateAt(c) {
    c = clamp(c, 0, END);
    var tr = M.play.transition, seg = TL[0];
    for (var i = 1; i < TL.length; i++) if (c >= TL[i].c0) seg = TL[i];
    var s = c - seg.c0, k = seg.act, last = ACTS.length - 1;
    var st = {clock: c, kind: seg.kind, act: k, done: c >= END, card: -1, cardAlpha: 0, newAct: k, newAlpha: 1,
              layoutAct: k, layoutAlpha: 1, chords: [0, 0], rates: 0, beat: null, beatAlpha: 0};
    if (seg.kind === "play") {
      st.T = timeOf(k, s); st.r1 = ACTS[k].r1;
    } else if (seg.kind === "open") {      // the first act's title card, over the first frame
      st.T = T0; st.r1 = ACTS[0].r1; st.card = 0;
      st.cardAlpha = clamp(Math.min(s / tr.card_in, (seg.dur - s) / tr.card_out), 0, 1);
      st.newAlpha = clamp((s - tr.card_in - tr.hold) / tr.ghost, 0, 1);
    } else if (seg.kind === "break") {     // at rest at the end of act k: card in, hold, widen, ghost, card out
      var held = tr.card_in + tr.hold, u = clamp((s - held) / tr.widen, 0, 1);
      st.T = ACTS[k].t1; st.card = k + 1;
      st.cardAlpha = clamp(Math.min(s / tr.card_in, (seg.dur - s) / tr.card_out), 0, 1);
      st.r1 = ACTS[k].r1 + (ACTS[k + 1].r1 - ACTS[k].r1) * smooth(u);
      st.newAct = k + 1; st.newAlpha = clamp((s - held - tr.widen) / tr.ghost, 0, 1);
      st.layoutAct = u < 0.5 ? k : k + 1; st.layoutAlpha = u <= 0 || u >= 1 ? 1 : Math.abs(2 * u - 1);
    } else {                               // the end: two chords are drawn, the second a little after the first; then their rates
      var fl = M.play.flourish;
      st.T = T1; st.r1 = X1; st.act = st.newAct = st.layoutAct = last;
      st.chords = [clamp(s / fl.chord, 0, 1), clamp((s - fl.lag) / fl.chord, 0, 1)];
      st.rates = clamp((s - fl.lag - fl.chord) / fl.labels, 0, 1);
    }
    // A beat's card is up while the clock is between its two moments, with a short fade either side.
    if (!st.done) BEATS.forEach(function (b) {
      var a = Math.min(clamp((c - b.c0) / M.play.card_fade + 1, 0, 1), clamp((b.c1 - c) / M.play.card_fade + 1, 0, 1));
      if (a > st.beatAlpha) { st.beatAlpha = a; st.beat = b; }
    });
    return st;
  }
  // Within an act the x-axis is fixed, so a date has one position for the whole act.
  function scaleIn(k, plotW) { return plotW / (ACTS[k].r1 - X0); }
  // How far right of a date's position the figure extends in the act in which
  // the playhead reaches it: the room a label there has without sticking out.
  // (`late` Infinity: no limit. The label can wait for a later, wider act.)
  function roomAt(t, plotW, late) {
    if (late === Infinity) return Infinity;
    return plotW + L.margin.r - 2 - (t - X0) * scaleIn(ownAct(t), plotW);
  }
  // The first act, from the one in which t is reached, in whose x-range a box
  // reaching `off` px right of t's position lies inside the figure.
  function fitAct(t, off, plotW) {
    for (var k = ownAct(Math.max(t, T0)); k < ACTS.length - 1; k++)
      if ((t - X0) * scaleIn(k, plotW) + off <= plotW + L.margin.r - 2) return k;
    return ACTS.length - 1;
  }
  // The date at which the playhead is w px right of the date t, at the scale of the act it is then in.
  function passedAt(t, w, plotW) {
    for (var k = ownAct(Math.max(t, T0)); k < ACTS.length; k++) {
      var d = Math.max(t + w / scaleIn(k, plotW), ACTS[k].t0);
      if (d <= ACTS[k].t1 || k === ACTS.length - 1) return Math.min(d, T1);
    }
  }
  // The date from which a leader's name fits inside its segment and goes on
  // fitting: in the act it first has room in, provided it still has room when
  // each later act opens on a wider axis. null: never.
  function leaderShow(l, w, plotW) {
    var a = Math.max(l.t0, X0);
    for (var k = ownAct(Math.max(a, T0)); k < ACTS.length; k++) {
      var T = Math.max(ACTS[k].t0, a + w / scaleIn(k, plotW)), ok = T <= Math.min(ACTS[k].t1, l.t1);
      for (var j = k + 1; ok && j < ACTS.length; j++) ok = (Math.min(l.t1, ACTS[j].t0) - a) * scaleIn(j, plotW) >= w;
      if (ok) return T;
    }
    return null;
  }
  // What is in view: the act's range while the play is on, otherwise whatever
  // the reader has zoomed or panned to.
  function view() {
    if (!STATE.done) return [X0, STATE.r1];
    var xa = gd._fullLayout.xaxis;
    return [xa.r2l(xa.range[0]), xa.r2l(xa.range[1])];
  }

  // ---- Measured text ---------------------------------------------------------------
  var ctx = document.createElement("canvas").getContext("2d"), sizes = {};
  function textSize(html, px) {
    var key = px + "|" + html;
    if (sizes[key]) return sizes[key];
    ctx.font = px + "px " + FONT;
    // (Tags other than line breaks are styling and take no room; bold runs a little wider.)
    var lines = String(html).split("<br>"), w = 0;
    lines.forEach(function (ln) {
      w = Math.max(w, ctx.measureText(ln.replace(/<[^>]+>/g, "")).width + (ln.indexOf("<b>") < 0 ? 0 : 5));
    });
    return (sizes[key] = {w: w, h: lines.length * px * 1.3});       // 1.3 is Plotly's line spacing
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
  // scale of the FINISHED chart, which is the last act's: in the earlier acts
  // and under a zoom the lines are only further apart, so what fits there fits
  // throughout. What differs from act to act is the room on the right: with
  // `late` 0 a label must lie inside the figure in the act in which the
  // playhead reaches its line; with Infinity it may wait for a later, wider
  // act. `says` is what each label reads. Returns null if nothing fits.
  var SPOTS = [0.5, 1, 0.75, 0.625, 0.375, 0.25, 0.875, 0.125, 0];
  function reachOf(x, w, spot) {             // where a label starts and ends, for a line at x
    return spot === 1 ? [x - 3 - w, x - 3] : spot === 0 ? [x + 3, x + 3 + w] : [x - spot * w, x + (1 - spot) * w];
  }
  function placeStrip(evs, says, plotW, font, rows, late) {
    var scale = plotW / (X1 - X0), lo = -L.margin.l + 2, hi = plotW + L.margin.r - 2;
    var it = evs.map(function (e, i) {
      return {x: (e.t - X0) * scale, w: textSize(says[i], font).w + 4, room: roomAt(e.t, plotW, late)};
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
  // Fit one panel's strip of event labels. Everything, each label inside the
  // figure in the act its line appears in, in the largest type and then the
  // fewest rows that work; failing that, in the smallest type; only then with
  // labels that wait for the next, wider act. At each step the labels are
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
    // What to try, in order: [whether a label may wait for a later act, in which type and rows].
    var least = combos[combos.length - 1].font, tries = [];
    var main = combos.filter(function (c) { return c.font > least; }), small = combos.filter(function (c) { return c.font === least; });
    [[[0], main], [[0], small], [[Infinity], combos]].forEach(function (group) {
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
  // fixed pixel offset from its tip, and an earlier act's axis is more
  // stretched than a later one's, so every position is checked at the scale of
  // each act from the one its arrow appears in. No text may lie on one of the
  // chords that close the animation: a text that would is moved below it
  // ("under") or tried elsewhere ("above"). Each text goes where it
  // fits in its arrow's own act if it can (otherwise it waits for a wider
  // one), then in the fewest lines. A text may reach left of where the data begin,
  // over the plain band, but never over the hatched band or an event's line
  // there. Returns null if any of them cannot be placed.
  function placeArrows(font) {
    var plotW = GEO.plotW, ppb = GEO.ppb, zeroY = M.view.y2[1] * ppb, c = 5, placed = [];
    var end = plotW / (X1 - X0), edge = 0, waits = [0, Infinity];
    BANDS.forEach(function (bd) { if (bd.kind === "none") edge = Math.max(edge, (bd.t1 - X0) * end); });
    EV.forEach(function (e) { if (e.on && !e.tick && e.panel === "stocks" && e.t < TA) edge = Math.max(edge, (e.t - X0) * end); });
    function stages(t) {                   // px per ms in each act, from the one in which the playhead reaches t
      var out = [];
      for (var k = ownAct(t); k < ACTS.length; k++) out.push(scaleIn(k, plotW));
      return out;
    }
    // How high and how low the two lines get across [a, b] px from the tip, and each chord likewise, in px.
    function reach(tip, sc, a, b) {
      var hi = Infinity, lo = -Infinity, spans = CHORDS.map(function () { return [Infinity, -Infinity]; });
      for (var x = a; x <= b; x += 2) {
        var T = tip + x / sc, s = at(S.t, S.s, T), e = at(S.t, S.e, T);
        if (s === null) continue;
        hi = Math.min(hi, zeroY - Math.max(s, e) * ppb);
        lo = Math.max(lo, zeroY - Math.min(s, e) * ppb);
        CHORDS.forEach(function (ch, n) {
          var y = zeroY - ch.value * (T - TA) / (ch.t - TA) * ppb;
          spans[n] = [Math.min(spans[n][0], y), Math.max(spans[n][1], y)];
        });
      }
      return {hi: hi, lo: lo, spans: spans};
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
    // Each text in turn takes the first place that suits it, in its fewest lines. If a later one
    // is then left with nowhere to go, an earlier one gives up its widest wording and all are
    // placed afresh.
    var skip = ARROWS.map(function () { return 0; });
    for (var round = 0; round < 60; round++) {
      var failed = -1;
      placed = [];
      for (var n = 0; n < ARROWS.length && failed < 0; n++) {
        var A = ARROWS[n], tipX = (A.t - X0) * end, tipY = zeroY - A.y * ppb, scs = stages(A.t), found = null;
        for (var w8 = 0; w8 < waits.length && !found; w8++) for (var k = skip[n]; k < A.wraps.length && !found; k++) {
          var sz = textSize(A.wraps[k], font), W = sz.w + 8, H = sz.h + 6;
          var room = roomAt(A.t, plotW, waits[w8]);
          for (var step = 0; step <= 120 && !found; step++) for (var sign = -1; sign <= 1 && !found; sign += 2) {
            if (!step && sign > 0) continue;
            var dx0 = sign * step * 3 - W / 2, dx1 = dx0 + W, hi = Infinity, lo = -Infinity, top;
            if (tipX + dx0 < edge + 6 || tipX + dx1 > plotW - 3 || dx1 > room) continue;
            var spans = CHORDS.map(function () { return [Infinity, -Infinity]; });
            for (var j = 0; j < scs.length; j++) {
              var d = reach(A.t, scs[j], dx0 - c, dx1 + c);
              hi = Math.min(hi, d.hi); lo = Math.max(lo, d.lo);
              d.spans.forEach(function (sp, n) { spans[n] = [Math.min(spans[n][0], sp[0]), Math.max(spans[n][1], sp[1])]; });
            }
            var onChord = function (y) { return spans.filter(function (sp) { return y < sp[1] + c && y + H > sp[0] - c; })[0]; };
            if (A.mode === "above") {
              // As high as the panel allows (below any tick mark), up to 22 px clear of the tip, and never nearer than 10.
              top = Math.max(L.tick.down + 3, tipY - 22 - H);
              if (top + H > tipY - 10 || hi < top + H + c || onChord(top)) continue;
            } else {
              top = Math.max(tipY + 16, lo + c + 1);
              for (var pass = 0; pass < 3; pass++) {
                if (top < zeroY + 7 && top + H > zeroY - 4) top = zeroY + 7;
                var hit = onChord(top);
                if (hit) top = hit[1] + c + 1;
              }
              if (lo > top - c || onChord(top) || (top < zeroY + 7 && top + H > zeroY - 4)) continue;
            }
            if (top < 3 || top + H > GEO.botH - 3) continue;
            var q = {t: A.t, dx0: dx0, dx1: dx1, top: top, bottom: top + H};
            if (!clear(q)) continue;
            q.text = A.wraps[k]; q.ax = (dx0 + dx1) / 2; q.ay = top + H / 2 - tipY;
            q.a = tipX + dx0; q.b = tipX + dx1; q.tipX = tipX; q.tipY = tipY;    // on the finished chart
            q.showAct = fitAct(A.t, dx1, plotW); q.late = q.showAct - ownAct(A.t);
            found = q;
          }
        }
        if (found) placed.push(found); else failed = n;
      }
      if (failed < 0) return placed;
      var m = failed - 1;
      while (m >= 0 && skip[m] + 1 >= ARROWS[m].wraps.length) m--;
      if (m < 0) return null;
      skip[m]++;
      for (var later = m + 1; later < skip.length; later++) skip[later] = 0;
    }
    return null;
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

  // Is the box q clear of the annotations already placed: of their text, and
  // of the arrow from each text to its tip?
  function clearOf(q, boxes) {
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

  // ---- The two labels by the fills --------------------------------------------------
  // "behind": inside the grey, wherever between its two dates the grey is
  // deepest, with both lines clear of the text. "ahead": the periwinkle is too
  // thin to hold its label, so that goes in clear space as near as it can get
  // to the periwinkle between its two dates -- above both lines or below both
  // across its whole width, never between them. Both keep clear of the
  // annotations already placed and of the two chords that close the animation
  // (a chord through the grey divides it, and the label takes the deeper
  // part), and prefer not to lie over an event's line.
  // Worked out on the finished chart: a label is pinned to a date at its
  // centre, so a stretched chart only moves things away from it. Returns the
  // box, or null.
  function placeFill(F, boxes, COL) {
    var plotW = GEO.plotW, scale = plotW / (X1 - X0), zeroY = M.view.y2[1] * GEO.ppb, c = 4, best = null;
    var from = Math.max(0, Math.ceil((TA - X0) * scale) + 6), to = Math.floor(plotW) - 3;
    var lines = EV.filter(function (e) { return e.on && !e.tick && e.panel === "stocks"; }).map(function (e) { return (e.t - X0) * scale; });
    function crossings(a, b) { return lines.filter(function (x) { return x > a - 3 && x < b + 3; }).length; }
    function free(q) { return clearOf(q, boxes); }
    var x0 = Math.max(from, Math.round((F.t0 - X0) * scale)), x1 = Math.min(to, Math.round((F.t1 - X0) * scale)), pts = [];
    if (F.kind === "ahead") for (var x = x0; x <= x1; x++) if (COL.s[x] > COL.e[x]) pts.push([x, zeroY - (COL.s[x] + COL.e[x]) / 2]);
    if (F.kind === "ahead" && !pts.length) return null;
    for (var k = 0; k < F.wraps.length && !best; k++) {
      var sz = textSize(F.wraps[k], L.fill_font), W = sz.w + 6, H = sz.h + 4;
      var a0 = F.kind === "ahead" ? Math.max(from, Math.floor(pts[0][0] - W - 50)) : x0;
      var a1 = F.kind === "ahead" ? Math.min(to, pts[pts.length - 1][0] + 50 + W) : x1;
      for (var a = a0; a + W <= a1; a += 2) {
        var b = a + W, up = Infinity, down = -Infinity, roof = -Infinity, floor = Infinity, ok = true;
        var spans = CHORDS.map(function () { return [Infinity, -Infinity]; });   // how high and how low each chord gets
        for (var xx = Math.max(0, Math.floor(a - c)); ok && xx <= Math.min(COL.s.length - 1, Math.ceil(b + c)); xx++) {
          var ys = zeroY - COL.s[xx], ye = zeroY - COL.e[xx];
          if (isNaN(ys)) { ok = false; break; }
          CHORDS.forEach(function (ch, n) { var yc = chordY(ch, xx); spans[n] = [Math.min(spans[n][0], yc), Math.max(spans[n][1], yc)]; });
          up = Math.min(up, ys, ye); down = Math.max(down, ys, ye);        // the highest and the lowest any line gets
          if (F.kind === "behind") {
            if (ys <= ye) ok = false;                                      // the stock line must be the lower one throughout
            roof = Math.max(roof, ye); floor = Math.min(floor, ys);        // under the economy line, over the stock line
          }
        }
        if (!ok) continue;
        var cross = crossings(a, b), tops = [], q;
        if (F.kind === "behind") {
          var parts = [[roof, floor]];
          spans.forEach(function (sp) {
            var next = [];
            parts.forEach(function (p) {
              if (sp[1] <= p[0] || sp[0] >= p[1]) next.push(p); else next.push([p[0], sp[0]], [sp[1], p[1]]);
            });
            parts = next;
          });
          parts.sort(function (p, o) { return (o[1] - o[0]) - (p[1] - p[0]); });
          roof = parts[0][0]; floor = parts[0][1];
          if (floor - roof < H + 2 * c) continue;
          q = {a: a, b: b, top: (roof + floor - H) / 2, bottom: (roof + floor + H) / 2, score: floor - roof - 30 * cross};
          if (free(q) && (!best || q.score > best.score)) { q.text = F.wraps[k]; q.t = X0 + b / scale; best = q; }
          continue;
        }
        for (var t1 = up - c - H; t1 >= L.tick.down + 3; t1 -= 2) tops.push(t1);      // above both lines
        for (var t2 = down + c; t2 + H <= GEO.botH - 4; t2 += 2) tops.push(t2);       // or below both
        tops.forEach(function (top) {
          if (top < zeroY + 3 && top + H > zeroY - 3) return;             // never astride the zero line
          if (spans.some(function (sp) { return top < sp[1] + c && top + H > sp[0] - c; })) return;   // nor on a chord
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
      if (ok) return {t: X0 + x / scale, w: w, show: passedAt(X0 + x / scale, w + 8, plotW)};
    }
    return null;
  }

  // ---- The rates beside the closing chords -----------------------------------------
  // The two chords, as px down from the top of the bottom panel at a px column
  // of the finished chart.
  function chordY(ch, x) {
    var scale = GEO.plotW / (X1 - X0), x0 = (TA - X0) * scale, zeroY = M.view.y2[1] * GEO.ppb;
    return zeroY - ch.value * clamp((x - x0) / ((ch.t - X0) * scale - x0), 0, 1) * GEO.ppb;
  }
  // Each rate is a line of text beside its chord: clear of both lines and both
  // chords, outside the fills (so above both lines or below both), clear of
  // the annotations and of the other rate, never astride the zero line, right
  // of where the data begin, and as near its chord as all that allows. If
  // either cannot be had, the two go together, one above the other, at the
  // foot of the empty stage before the data. Returns null if that fails as
  // well (then they go in the key).
  function placeRates(boxes, COL) {
    var plotW = GEO.plotW, scale = plotW / (X1 - X0), ppb = GEO.ppb, zeroY = M.view.y2[1] * ppb, c = 4, f = L.rate_font;
    var x0 = (TA - X0) * scale, from = Math.ceil(x0) + 8, to = Math.floor(plotW) - 3, taken = boxes.slice(), spots = [];
    var lines = EV.filter(function (e) { return e.on && !e.tick && e.panel === "stocks"; }).map(function (e) { return (e.t - X0) * scale; });
    function crossings(a, b) { return lines.filter(function (x) { return x > a - 3 && x < b + 3; }).length; }
    function near(ch, n) {
      var best = null;
      for (var k = 0; k < ch.wraps.length && !best; k++) {
        var sz = textSize(ch.wraps[k], f), W = sz.w + 10, H = sz.h + 4;
        for (var a = from; a + W <= to; a += 3) {
          var b = a + W, cols = [];
          for (var x = Math.floor(a - c); x <= Math.ceil(b + c); x += 2) {
            var i = clamp(x, 0, COL.s.length - 1);
            if (isNaN(COL.s[i])) { cols = null; break; }
            cols.push([zeroY - COL.s[i], zeroY - COL.e[i], chordY(CHORDS[0], x), chordY(CHORDS[1], x)]);
          }
          if (!cols) continue;
          var cross = crossings(a, b);
          for (var top = L.tick.down + 3; top + H <= GEO.botH - 4; top += 2) {
            if (top < zeroY + 3 && top + H > zeroY - 3) continue;
            var ok = true, dist = Infinity;
            for (var j = 0; ok && j < cols.length; j++) {
              var y = cols[j], lo = Math.min(y[0], y[1]), hi = Math.max(y[0], y[1]), own = y[2 + n], other = y[3 - n];
              ok = (top + H <= lo - c || top >= hi + c) && (top + H <= own - c || top >= own + c)
                && (top + H <= other - c || top >= other + c);
              dist = Math.min(dist, Math.max(top - own, own - top - H));
            }
            if (!ok || dist > 34) continue;
            var q = {a: a, b: b, top: top, bottom: top + H, score: -dist - 8 * cross};
            if ((best && q.score <= best.score) || !clearOf(q, taken)) continue;
            q.text = ch.wraps[k]; q.on = "paper";
            q.x = iso(X0 + (a + 5) / scale); q.y = (zeroY - (top + H / 2)) / ppb;
            best = q;
          }
        }
      }
      return best;
    }
    for (var n = 0; n < CHORDS.length; n++) {
      var found = near(CHORDS[n], n);
      if (!found) break;
      spots.push(found); taken.push(found);
    }
    if (spots.length === CHORDS.length) return {mode: "beside the chords", spots: spots};
    // Together, before the data. Clear of the band labels and the zero line's labels there, and of event lines.
    var pre = [];
    BANDS.forEach(function (bd) {
      var a = (Math.max(bd.t0, X0) - X0) * scale, b = (Math.min(bd.t1, T1) - X0) * scale, text = null;
      for (var k = 0; k < bd.wraps.length && !text; k++) if (textSize(bd.wraps[k], L.band_font).w + 16 <= b - a) text = bd.wraps[k];
      if (!text) return;
      var sz = textSize(text, L.band_font), mid = (a + b) / 2, top = (1 - bd.yLabel) * GEO.botH - sz.h / 2;
      pre.push({a: mid - sz.w / 2, b: mid + sz.w / 2, top: top, bottom: top + sz.h});
    });
    if (FIT.hints.bottom) pre.push({a: x0 - 10 - FIT.hints.bottomW, b: x0 - 10, top: zeroY - 20, bottom: zeroY + 20});
    for (var k = 0; k < CHORDS[0].wraps.length; k++) {
      var sizes2 = CHORDS.map(function (ch) { return textSize(ch.wraps[k], f); });
      var W = Math.max(sizes2[0].w, sizes2[1].w) + 10, H = sizes2[0].h + sizes2[1].h + 6, top = GEO.botH - 8 - H;
      if (top < GEO.head[1].h + 4) continue;
      for (var a = 8; a + W <= x0 - 8; a += 4) {
        var q = {a: a, b: a + W, top: top, bottom: top + H};
        if (crossings(q.a, q.b) || !clearOf(q, pre)) continue;
        var under = "paper";
        BANDS.forEach(function (bd) {
          if ((bd.t0 - X0) * scale <= a + 4 && (bd.t1 - X0) * scale > a + 4) under = bd.kind === "none" ? "onNone" : "onLimited";
        });
        var y0 = top + 2;
        return {mode: "before the data", spots: CHORDS.map(function (ch, n) {
          var h = sizes2[n].h, s = {a: q.a, b: q.b, top: y0, bottom: y0 + h, text: ch.wraps[k], on: under,
                                    x: iso(X0 + (a + 5) / scale), y: (zeroY - (y0 + h / 2)) / ppb};
          y0 += h + 2;
          return s;
        })};
      }
    }
    return null;
  }

  // ---- A beat's card: in the empty part of its panel ----------------------------------
  // At the panel's left, under its name, if that keeps it off the playhead and
  // off the data drawn while it is up; otherwise beside the stretch the
  // playhead covers meanwhile, or wherever else along the panel is clear. (In
  // the first acts the bottom panel is an empty stage, and in the last the top
  // panel's upper left is empty.) It never covers data, and so never the dot
  // at the playhead; where the panel is too narrow to keep it off the
  // playhead's line as well (a phone), it may lie over the line, clear of the
  // dot. W and H are the card's measured size.
  function placeCard(b, plotW, W, H) {
    var k = b.panel === "economy" ? 0 : 1, sc = scaleIn(b.act, plotW), head = GEO.head[k];
    var s0 = (b.since - X0) * sc - 10, s1 = (b.until - X0) * sc + 10;      // the playhead's sweep while the card is up
    var top0 = (k ? M.view.y2[1] : M.view.y[1]) * GEO.ppb;                   // the panel's zero line, px down from its top
    function topOf(a) { return a < head.b + 6 ? head.h + 2 : 6; }
    function clear(a, offLine) {
      var top = topOf(a);
      if (a < 4 || a + W > plotW - 4 || top + H > GEO.panelH[k] - 4 || (offLine && a < s1 && a + W > s0)) return false;
      for (var x = a - 6; x <= a + W + 6; x += 2) {
        var T = X0 + x / sc;
        if (T > b.until) break;
        var vals = k ? [at(S.t, S.s, T), at(S.t, S.e, T)] : [at(G.t, G.y, T)];
        for (var j = 0; j < vals.length; j++) {
          if (vals[j] === null) continue;
          var y = top0 - vals[j] * GEO.ppb;
          if (y > top - 6 && y < top + H + 6) return false;
        }
      }
      return true;
    }
    var tries = [8, s1 + 4, s0 - 4 - W];
    for (var a = 8; a + W <= plotW - 4; a += 8) tries.push(a);
    for (var pass = 0; pass < 2; pass++) for (var n = 0; n < tries.length; n++)
      if (clear(tries[n], !pass)) return {k: k, a: tries[n], top: topOf(tries[n]), w: W, h: H, overLine: !!pass, forced: false};
    return {k: k, a: 8, top: topOf(8), w: W, h: H, overLine: true, forced: true};
  }

  // ---- Everything in the layout that depends on the moment and the window ---------
  // A pure function of a moment of the timeline (stateAt) and the visible
  // window [V0, V1]: which events, bars, bands and annotations are showing and
  // how strongly, how far each bar and band has grown, where the playhead is,
  // and how much of the closing chords is drawn. Stateless, so scrubbing,
  // playing and zooming all agree. Within an act nothing here moves but the
  // playhead and what it reveals: a leader's or an era's label is pinned to the
  // start of its bar, an event's to its line, a band's to one spot per act.
  // Phase 2 hook: a zoom-dependent rule for stored events belongs in since().
  function scene(st, V0, V1) {
    var p = {}, T = st.T, scale = GEO.plotW / (V1 - V0), done = st.done, play = M.play;
    var lo = -L.margin.l + 2, hi = GEO.plotW + L.margin.r - 2;
    function A(i, props) { for (var k in props) p["annotations[" + i + "]." + k] = props[k]; }
    function H(i, props) { for (var k in props) p["shapes[" + i + "]." + k] = props[k]; }
    // How far something has come since the playhead reached the date t: nothing before, all of it soon after.
    function since(t) { return done ? 1 : clamp((st.clock - clockOf(t)) / play.reveal, 0, 1); }
    function gate(k) { return done || k < st.newAct ? 1 : k === st.newAct ? st.newAlpha : 0; }
    function px(t) { return (t - V0) * scale; }

    // Events. A tick appears when reached. A labelled event that has been
    // reached comes up to full strength; the NEXT one in each strip, if it
    // belongs to the act on stage, waits as a ghost: faint, and already where
    // it will be. Only ever one: an event that shares another's label is the
    // ghost (its line alone) once the one that carries the label is reached.
    // A label is shown only where its whole box is inside the figure, which
    // could mean waiting for the next, wider act. A line with no label (a
    // phone) that would run through its panel's name starts below the name
    // instead. A beat can pick an event out, once reached, while its card is up.
    var next = {};
    if (!done) EV.forEach(function (e) {
      if (e.tick || !e.on || st.clock >= e.clock) return;
      if (!next[e.panel] || e.t < next[e.panel].t) next[e.panel] = e;
    });
    EV.forEach(function (e, n) {
      var x = px(e.t), k = e.panel === "economy" ? 0 : 1, head = GEO.head[k];
      e.ghost = false;
      if (e.tick) { var seen = e.on ? since(e.t) : 0; H(e.shape, {visible: seen > 0, opacity: seen}); return; }
      var lead = e.lead === null ? e : EV[e.lead], a = 0;
      if (e.on && (done || st.clock >= e.clock)) a = play.ghost + (1 - play.ghost) * since(e.t);
      else if (next[e.panel] === e) { a = play.ghost * gate(e.act); e.ghost = a > 0; }
      var hot = st.beat && st.beat.event === n ? st.beatAlpha * since(e.t) : 0;
      var b = lead === e && e.labelled && x + e.ext[0] >= lo - 0.5 && x + e.ext[1] <= hi + 0.5 ? a * gate(e.showAct) : 0;
      var top = e.labelled ? e.stem : (x > head.a - 4 && x < head.b + 4 ? -head.h : 0);
      H(e.shape, {visible: a > 0, opacity: a * (M.event_line_opacity + (0.85 - M.event_line_opacity) * hot),
                  y1: 1 + top / GEO.panelH[k]});
      if (e.annotation !== null) A(e.annotation, {visible: b > 0, opacity: b});
    });
    var az = since(TA), roomZ = px(TA) - 10 - FIT.hints.bottomW >= 2;
    H(M.zero.bottom, {visible: az > 0, opacity: az});
    ["zero_up", "zero_down"].forEach(function (r) { A(AN[r], {visible: az > 0 && FIT.hints.bottom && roomZ, opacity: az}); });
    var ht = FIT.hints.top, ag = ht && px(ht.t) + ht.w <= GEO.plotW - 2 ? since(ht.show) : 0;
    ["gap_up", "gap_down"].forEach(function (r) { A(AN[r], {visible: ag > 0, opacity: ag}); });
    ARROWS.forEach(function (a) {
      var q = a.box, x = px(a.t), f = 0;
      // Clear of the plot's edges, and of the panel's name if it is level with it.
      if (q && x + q.dx0 >= (q.top < 28 ? GEO.head[1].b + 6 : 2) && x + q.dx1 <= hi + 0.5) f = since(a.t) * gate(q.showAct);
      A(AN[a.role], {visible: f > 0, opacity: f});
    });
    FILLS.forEach(function (f) {
      var q = f.box, x = q ? px(q.at) : 0, a = q && x - q.w / 2 >= 2 && x + q.w / 2 <= GEO.plotW - 2 ? since(q.t) : 0;
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
      var f = !e.live ? 0 : done ? (eraText[n] ? 1 : 0) : e.labelled ? since(Math.max(e.t0, X0)) * gate(e.showAct) : 0;
      e.text = f > 0;
      A(e.annotation, f > 0 ? {visible: true, opacity: f, x: iso(Math.max(e.t0, V0 + HOUR))} : {visible: false});
    });
    // A leader's name shows once its segment is long enough to hold it, and to go on holding it.
    LEADERS.forEach(function (l) {
      var start = Math.max(l.t0, V0), end = Math.min(l.t1, T, V1);
      l.cut = l.t0 < V0; l.a = px(start); l.b = px(end);
      l.live = l.b > l.a + 0.5;
      H(l.shape, {visible: l.live, x1: iso(Math.max(l.t0, Math.min(l.t1, T, X1)))});
      H(l.tip, {visible: l.live && l.cut});
      var f = !l.live ? 0 : done ? (l.b - l.a >= l.w + 12 ? 1 : 0) : l.labelled && l.show !== null ? since(l.show) : 0;
      l.text = f > 0;
      A(l.annotation, f > 0 ? {visible: true, opacity: f, x: iso(Math.max(l.t0, V0 + HOUR))} : {visible: false});
    });

    // Access bands grow with the playhead too. (The hatched one is a trace:
    // render() grows it.) During the play each label has one spot per act, in
    // the middle of what that act will show of its band, and appears once the
    // band has grown under it; on the finished chart it is centred in whatever
    // part of the band is in view, in the widest wording that fits there.
    BANDS.forEach(function (bd) {
      var from = Math.max(bd.t0, X0), start = Math.max(bd.t0, V0), end = Math.min(bd.t1, T, V1), a = px(start), b = px(end);
      var live = b > a + 0.5, text = null;
      if (bd.shape !== null) H(bd.shape, {visible: T > from, x1: iso(Math.max(from, Math.min(bd.t1, T)))});
      if (bd.early) H(bd.early.shape, {visible: T > from, x1: iso(Math.max(from, Math.min(bd.early.t1, T)))});
      bd.span = live ? [a, b] : null;
      if (!done) {
        var spot = bd.spots[st.layoutAct], f = spot ? since(spot.t) * st.layoutAlpha : 0;
        A(bd.annotation, f > 0 ? {visible: true, opacity: f, text: spot.text, x: spot.x, y: spot.y} : {visible: false});
        return;
      }
      if (live) for (var k = 0; k < bd.wraps.length && !text; k++)
        if (textSize(bd.wraps[k], L.band_font).w + 16 <= b - a) text = bd.wraps[k];
      A(bd.annotation, text ? {visible: true, opacity: 1, text: text, x: (a + b) / 2 / GEO.plotW, y: bd.yLabel} : {visible: false});
    });

    // The playhead, while the play is on. And the end: each chord drawn out from
    // the anchor to its series' last point, then the rates.
    M.playhead.forEach(function (i) { H(i, {visible: !done, x0: iso(T), x1: iso(T)}); });
    CHORDS.forEach(function (ch, n) {
      var f = done ? 1 : st.chords[n], r = done ? 1 : st.rates;
      H(ch.shape, {visible: f > 0, x1: iso(TA + f * (ch.t - TA)), y1: f * ch.value});
      A(ch.annotation, {visible: !!ch.spot && r > 0, opacity: r});
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

  // ---- Draw the chart at one moment of the timeline: one Plotly.update, all traces --
  function render(c) {
    c = clamp(c, 0, END);
    if (busy) { pending = c; return; }
    var st = STATE = stateAt(c), T = st.T, done = st.done, data = {x: [], y: []}, idx = [];
    clock = c; playhead = T;
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
    // The stock line: its back-tested stretch, if it has one, is a trace of its own; they share the point between.
    put(TR.stock_back, S.solid ? p.x.slice(0, S.solid + 1) : [], S.solid ? p.s.slice(0, S.solid + 1) : []);
    put(TR.stock, p.x.slice(S.solid), p.s.slice(S.solid));
    put(TR.stock_head, live && p.x.length ? [last(p.x)] : [], live && p.x.length ? [last(p.s)] : []);
    put(TR.markers, mk.x, mk.y);
    ANCHORS.forEach(function (a) { put(TR[a.trace], T >= a.t ? [a.date] : [], T >= a.t ? [0] : []); });
    var layout = scene(st, X0, done ? X1 : st.r1);
    // The x-range is the act's (or, in a break, on its way to the next act's), which also undoes any zoom.
    layout["xaxis.range"] = [M.view.x[0], done ? M.view.x[1] : iso(st.r1)];
    syncHead();
    overlays(st);
    hideTip();
    busy = true;
    function freed() { busy = false; syncPill(); if (pending !== null) { var q = pending; pending = null; render(q); } }
    Promise.resolve(send(layout, data, idx)).then(freed, freed);
  }
  // Re-place whatever depends on the window, after a zoom or pan or a re-fit.
  function refresh() { var v = view(), p = scene(STATE, v[0], v[1]); syncHead(); return send(p).then(syncPill); }

  // ---- What is not in the figure: controls and cards ---------------------------------
  function fillCard(b) {
    if (beatCard._beat === b) return;
    beatCard._beat = b;
    beatCard.querySelector(".china-beat-lead").textContent = b.lead || "";
    beatCard.querySelector(".china-beat-text").textContent = b.text || "";
    beatCard.querySelector(".china-beat-credit").textContent = b.image && b.credit ? b.credit : "";
  }
  function overlays(st) {
    var done = st.done, f = (st.T - T0) / (T1 - T0);
    scrub.value = Math.round(f * scrub.max);          // the thumb's position IS the date, linearly
    scrubWrap.style.setProperty("--china-p", (100 * f).toFixed(2) + "%");
    // Once the play has run, the play button at its end is a replay button.
    var again = done && played && !playing;
    playBtn.classList.toggle("is-done", again);
    if (!playing) {
      playBtn.title = again ? "Replay" : "Play";
      playBtn.setAttribute("aria-label", again ? "Replay the animation" : "Play the animation");
    }
    Array.prototype.forEach.call(actsBox.querySelectorAll(".china-act-label"), function (b, k) {
      b.classList.toggle("is-current", !done && k === (st.card >= 0 ? st.card : st.act));
    });
    Array.prototype.forEach.call(keyBox.querySelectorAll("[data-t]"), function (row) {
      row.style.opacity = done ? 1 : clamp((st.clock - clockOf(+row.getAttribute("data-t"))) / M.play.reveal, 0, 1);
    });
    // The act's title card: its number and years, then its title.
    if (st.card >= 0 && st.cardAlpha > 0) {
      if (actCard._act !== st.card) {
        actCard._act = st.card;
        actCard.querySelector(".china-act-kicker").textContent = ACTS[st.card].kicker;
        actCard.querySelector(".china-act-name").textContent = ACTS[st.card].title;
      }
      actCard.style.display = "block";
      actCard.style.opacity = st.cardAlpha;
    } else actCard.style.display = "none";
    // A beat's card, in the empty part of its panel, and its image (if any) behind that panel's data.
    var b = st.beat, k = b ? b.box.k : 0, top = GEO.t + (k ? GEO.topH + GEO.gap : 0);
    if (b) {
      fillCard(b);
      beatCard.style.display = "block";
      beatCard.style.opacity = st.beatAlpha;
      beatCard.style.transform = "translate(" + (L.margin.l + b.box.a) + "px," + (top + b.box.top) + "px)";
    } else beatCard.style.display = "none";
    if (b && b.image) {
      if (beatImage._src !== b.image) { beatImage._src = b.image; beatImage.style.backgroundImage = 'url("' + b.image + '")'; }
      beatImage.style.display = "block";
      beatImage.style.opacity = st.beatAlpha * M.play.image_opacity;
      beatImage.style.transform = "translate(" + L.margin.l + "px," + top + "px)";
      beatImage.style.width = GEO.plotW + "px";
      beatImage.style.height = GEO.panelH[k] + "px";
    } else beatImage.style.display = "none";
  }
  // The year pill, on the x-axis under the playhead: placed after each draw, from the axis as
  // drawn, so it is right under a reader's own zoom as well (and gone if the playhead is out of
  // view). An axis label that the pill would sit on is hidden while it does. Neither the pill
  // nor the playhead is there on the finished chart.
  function syncPill() {
    var xa = gd._fullLayout.xaxis, x = STATE.done ? -9 : xa.l2p(STATE.T), on = x >= -1 && x <= xa._length + 1;
    pill.style.display = on ? "block" : "none";
    if (on) {
      pill.textContent = new Date(STATE.T).getUTCFullYear();
      var w = pill.offsetWidth;
      x = clamp(x, w / 2 - L.margin.l + 2, GEO.plotW + L.margin.r - w / 2 - 2);
      pill.style.transform = "translate(" + (L.margin.l + x - w / 2) + "px," + (GEO.t + GEO.plotH + 4) + "px)";
    }
    var r = on ? pill.getBoundingClientRect() : null;
    Array.prototype.forEach.call(gd.querySelectorAll(".xtick text"), function (el) {
      var b = on ? el.getBoundingClientRect() : null;
      el.style.visibility = on && b.left < r.right + 3 && r.left < b.right + 3 ? "hidden" : "";
    });
  }

  // ---- Playback -------------------------------------------------------------------
  function reducedMotion() { return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }
  function setPlaying(on) {
    playing = on;
    playBtn.classList.toggle("is-playing", on);
    if (on) { playBtn.classList.remove("is-done"); playBtn.title = "Pause"; playBtn.setAttribute("aria-label", "Pause the animation"); }
  }
  function pause() { if (playing) { setPlaying(false); cancelAnimationFrame(raf); overlays(STATE); } }
  // Play from where the clock stands; from the top if the play is over.
  function play(from) {
    if (reducedMotion()) { render(END); return; }   // reduced motion: straight to the finished chart
    var c = from !== undefined ? from : clock >= END ? 0 : clock, prev = null;
    played = true;
    setPlaying(true);
    render(c);
    function step(now) {
      if (!playing) return;
      // Advance by wall-clock time (times the chosen speed), capped so a backgrounded tab resumes, not jumps.
      if (prev !== null) c += Math.min(now - prev, 100) / 1000 * speed;
      prev = now;
      if (c >= END) { setPlaying(false); render(END); return; }
      if (!busy) render(c);
      raf = requestAnimationFrame(step);
    }
    raf = requestAnimationFrame(step);
  }
  // Start an act from its title card. (Reduced motion: show where the act starts, and stay there.)
  function jump(k) {
    pause();
    if (reducedMotion()) render(ACTS[k].c0); else play(k === 0 ? 0 : ACTS[k - 1].b0);
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
    } else if (STATE.done) refresh();
    else syncPill();
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
      e.on = false; e.labelled = false; e.row = 0; e.spot = 0.5; e.ext = [0, 0]; e.showAct = e.act; e.stem = 0; e.lift = 3;
    });
    [FIT.top, FIT.bottom].forEach(function (F) {
      F.events.forEach(function (e, j) {
        e.on = true; e.labelled = F.labels; e.font = F.font; e.say = F.says[j];
        if (!F.placed) return;
        e.row = F.placed[j].row; e.spot = F.placed[j].spot;
        e.stem = 2 + e.row * F.pitch; e.lift = 3 + e.row * F.pitch;      // where its line stops and its label stands, px above the panel
        // How far the label reaches either side of its line, and the first act whose axis has room for it.
        e.ext = reachOf(0, textSize(e.say, F.font).w + 2, e.spot);
        e.showAct = fitAct(e.t, e.ext[1], plotW);
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
    // The eras and the leaders: which are drawn, which are labelled, and from which act or date.
    ERAS.forEach(function (e) { e.w = textSize(e.label, st.era_font).w + 2; });
    FIT.eras = fitEras(plotW, w);
    ERAS.forEach(function (e, n) {
      e.on = FIT.eras.on[n]; e.labelled = !!FIT.eras.labelled[n];
      e.showAct = fitAct(Math.max(e.t0, X0), e.w, plotW);
    });
    LEADERS.forEach(function (l) {
      l.w = textSize(l.label, st.leader_font).w + 2;
      l.labelled = (Math.min(l.t1, T1) - Math.max(l.t0, X0)) * scale >= l.w + 12;
      l.show = l.labelled ? leaderShow(l, l.w + 12, plotW) : null;
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

    // The beats' cards (HTML): each is measured with its own words, then given its place.
    beatCard.style.fontSize = L.card.font + "px";
    beatCard.style.width = Math.min(L.card.width, plotW - 16) + "px";
    beatCard.style.visibility = "hidden"; beatCard.style.display = "block";
    BEATS.forEach(function (b) { fillCard(b); b.box = placeCard(b, plotW, beatCard.offsetWidth, beatCard.offsetHeight); });
    beatCard.style.display = "none"; beatCard.style.visibility = "";
    // Each band label's place in each act: the middle of what that act shows of its band, in the
    // widest wording that fits there, and under a card if one would otherwise be in its way.
    // It shows once its band has grown under it (t).
    BANDS.forEach(function (bd) {
      bd.spots = ACTS.map(function (act, k) {
        var sc = scaleIn(k, plotW), a = (Math.max(bd.t0, X0) - X0) * sc, b = (Math.min(bd.t1, act.t1) - X0) * sc, text = null, sz;
        for (var n = 0; n < bd.wraps.length && !text; n++) {
          sz = textSize(bd.wraps[n], L.band_font);
          if (sz.w + 16 <= b - a) text = bd.wraps[n];
        }
        if (!text) return null;
        var mid = (a + b) / 2, top = (1 - bd.yLabel) * GEO.botH - sz.h / 2;
        BEATS.forEach(function (beat) {
          var q = beat.box;
          if (beat.act !== k || q.k !== 1 || mid + sz.w / 2 < q.a - 8 || mid - sz.w / 2 > q.a + q.w + 8) return;
          if (top + sz.h >= q.top - 6 && top <= q.top + q.h + 6) top = q.top + q.h + 10;
        });
        if (top + sz.h > GEO.botH - 4) return null;
        return {text: text, x: mid / plotW, y: 1 - (top + sz.h / 2) / GEO.botH, t: X0 + (mid + sz.w / 2 + 8) / sc};
      });
    });

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
    // type that lets every one of them show in its arrow's own act (failing
    // that, whichever type waits least); otherwise numbered markers and a key.
    // Then the labels by the fills, and the rates beside the closing chords.
    var tries = L.arrow_fonts.map(function (f) { return {font: f, boxes: placeArrows(f)}; })
      .filter(function (t) { return t.boxes; });
    tries.forEach(function (t) { t.late = Math.max.apply(null, t.boxes.map(function (q) { return q.late; })); });
    var pick = tries.filter(function (t) { return t.late <= 0; })[0]
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
    FIT.rates = placeRates(boxes, COL);
    CHORDS.forEach(function (ch, n) {
      ch.spot = FIT.rates ? FIT.rates.spots[n] : null;
      if (ch.spot) A(ch.annotation, {text: ch.spot.text, x: ch.spot.x, y: ch.spot.y, "font.size": L.rate_font,
                                     "font.shadow": haloOf(P[ch.spot.on])});
    });

    // The key under the plot: whatever could not be labelled directly.
    var keyed = false;
    Array.prototype.forEach.call(keyBox.children, function (row) {
      row.hidden = row.hasAttribute("data-zero") ? FIT.hints.bottom : row.hasAttribute("data-rate") ? !!FIT.rates : !!FIT.arrows;
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
    // The title card, over the middle of the plot; the year pill; and the scrubber's act labels:
    // the acts' titles, or their short forms, or just their numerals -- whichever is the longest
    // form that every act's stretch of the track has room for, so that the three read alike.
    actCard.style.left = (L.margin.l + plotW / 2) + "px";
    actCard.style.top = (GEO.t + GEO.plotH / 2) + "px";
    actCard.querySelector(".china-act-kicker").style.fontSize = L.act_card.kicker + "px";
    actCard.querySelector(".china-act-name").style.fontSize = L.act_card.title + "px";
    pill.style.fontSize = L.pill + "px";
    var track = scrubWrap.clientWidth, names = actsBox.querySelectorAll(".china-act-label"), form = 0;
    function forms(k) { return [ACTS[k].title, ACTS[k].short, ACTS[k].numeral]; }
    Array.prototype.forEach.call(names, function (btn, k) {
      var cs = getComputedStyle(btn), room = (ACTS[k].t1 - ACTS[k].t0) / (T1 - T0) * track - 9;
      ctx.font = "700 " + cs.fontSize + " " + cs.fontFamily;
      while (form < 2 && ctx.measureText(forms(k)[form]).width > room) form++;
    });
    Array.prototype.forEach.call(names, function (btn, k) { btn.textContent = forms(k)[form]; });
    hideTip();
    var v = view(), where = scene(STATE, v[0], v[1]), mk = markersAt(playhead);
    syncHead();
    for (var key in where) patch[key] = where[key];
    send(patch, {"line.width": [L.gdp_width, L.economy_width, L.stock_width, L.stock_width]}, [TR.gdp, TR.economy, TR.stock, TR.stock_back])
      .then(function () { return PL.restyle(gd, {"marker.size": L.anchor}, [TR.anchor_top, TR.anchor_bottom]); })
      .then(function () { return PL.restyle(gd, {x: [mk.x], y: [mk.y]}, [TR.markers]); })
      .then(syncPill);
    overlays(STATE);
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
    M.playhead.forEach(function (i) { H(i, {"line.color": P.ink}); });
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
    CHORDS.forEach(function (ch) { A(ch.annotation, P.text("rate"), P[ch.spot ? ch.spot.on : "paper"]); });
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
  // An event the playhead has not reached says nothing, ghost or not.
  function describe(px, py, cx, cy, xa, ya, y2) {
    var out = [], st = L.strip, done = STATE.done, up = ya._offset - py;          // up: px above the Economy panel
    function shown(t) { return done || clock >= clockOf(t); }
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
      // A back-tested month says why it is drawn differently.
      if (S.t[hit.month] < TB) tip.appendChild(tipRow("china-tip-note china-tip-why", M.backtest.note));
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

  // ---- Audit (?china-audit): the play, moment by moment; one scale; no text on anything; hover ---
  function runAudit() {
    var full = L.drop_from !== null && lastW >= L.drop_from;
    var out = {width: lastW, layout: lastW < M.narrow_below ? "narrow" : "wide",
               dark: document.body.classList.contains("quarto-dark"), hidden: document.hidden, fails: [], frames: {}};
    function names(list) { return list.map(function (e) { return e.label; }); }
    function plain(html) { return String(html).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(); }
    out.top = {labels: FIT.top.labels, font: FIT.top.font, rows: FIT.top.rows, dropped: names(FIT.top.dropped), lineOnly: names(FIT.top.bare)};
    out.bottom = {labels: FIT.bottom.labels, font: FIT.bottom.font, rows: FIT.bottom.rows, dropped: names(FIT.bottom.dropped), lineOnly: names(FIT.bottom.bare)};
    out.eras = {dropped: FIT.eras.dropped, hoverOnly: names(ERAS.filter(function (e) { return e.on && !e.labelled; }))};
    out.leaders = {hoverOnly: names(LEADERS.filter(function (l) { return !l.labelled; }))};
    out.rows = EV.filter(function (e) { return e.on; }).map(function (e) {
      var how = e.tick ? "tick" : e.lead !== null ? "under the label of " + EV[e.lead].label
        : e.labelled ? "“" + e.say + "”, row " + e.row + ", at " + e.spot : "no label";
      return e.label + " [" + e.panel + ", act " + ACTS[e.act].numeral + ", " + how + (e.notes.length ? ", " + e.notes.length + " notes" : "") + "]"; });
    out.arrows = FIT.arrows ? "in plot at " + FIT.arrowFont + " px" : "key";
    // Labels that wait for a later, wider act than the one their line or bar appears in.
    out.waiting = EV.filter(function (e) { return e.on && e.labelled && e.annotation !== null && e.showAct > e.act; })
      .concat(ERAS.filter(function (e) { return e.on && e.labelled && e.showAct > ownAct(Math.max(e.t0, T0)); }))
      .map(function (e) { return e.label + " (until act " + ACTS[e.showAct].numeral + ")"; });
    out.fillLabels = FILLS.map(function (f) { return f.role + (f.box ? " at " + f.box.x.slice(0, 7) : " hidden"); });
    out.hints = {bottom: FIT.hints.bottom ? "in plot" : "key", top: FIT.hints.top ? "from " + iso(FIT.hints.top.t).slice(0, 7) : "hidden"};
    out.rates = (FIT.rates ? FIT.rates.mode : "key") + ": " + CHORDS.map(function (ch) { return ch.text; }).join(" | ");
    out.cards = BEATS.map(function (b) {
      return iso(b.t).slice(0, 10) + " [act " + ACTS[b.act].numeral + ", " + b.panel + " panel, " + Math.round(b.box.w) + "×" + Math.round(b.box.h)
        + " at " + Math.round(b.box.a) + "," + Math.round(b.box.top) + (b.box.forced ? ", FORCED" : b.box.overLine ? ", over the playhead's line" : "")
        + ", " + (b.c1 - b.c0).toFixed(2) + " s]"; });
    out.bandLabels = BANDS.map(function (bd) {
      return plain(bd.wraps[0]) + ": " + bd.spots.map(function (s) { return s ? plain(s.text) : "none"; }).join(" / "); });
    out.actLabels = Array.prototype.map.call(actsBox.querySelectorAll(".china-act-label"), function (b) { return b.textContent; });
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
    function go(c) { busy = false; pending = null; render(c); return frames(3); }
    // What each label is. `over`: text inside a panel that may lie over a band,
    // a fill or an event's line, which is what its halo is for.
    var who = {};
    EV.forEach(function (e) {
      if (e.annotation !== null) who[e.annotation] = {name: "event: " + e.label, kind: "event", strip: e.panel};
    });
    ERAS.forEach(function (e) { who[e.annotation] = {name: "era: " + e.label, kind: "era", strip: "economy", bar: e, inset: 0}; });
    LEADERS.forEach(function (l) { who[l.annotation] = {name: "leader: " + l.label, kind: "leader", strip: "economy", bar: l, inset: 5}; });
    BANDS.forEach(function (bd) { who[bd.annotation] = {name: "band: " + plain(bd.wraps[0]), kind: "band", over: true}; });
    ["zero_up", "zero_down", "gap_up", "gap_down"].forEach(function (r) { who[AN[r]] = {name: r, kind: "hint", over: true}; });
    ARROWS.forEach(function (a) { who[AN[a.role]] = {name: a.role, kind: "arrow", over: true}; });
    FILLS.forEach(function (f) { who[AN[f.role]] = {name: f.role, kind: "fill", over: true, infill: f.kind === "behind"}; });
    CHORDS.forEach(function (ch) { who[ch.annotation] = {name: "rate: " + ch.key, kind: "rate", over: true}; });

    // Every visible text box against every other, the bars, the event lines and
    // the data; that each bar's label is still at the bar's start; and how tall
    // the title row and the two strips actually are. A beat's card counts as a
    // text box: it may cover an event's line (it is opaque), nothing else.
    function collisions(tag) {
      var fl = gd._fullLayout, xa = fl.xaxis, ya = fl.yaxis, y2 = fl.yaxis2, r = gd.getBoundingClientRect(), st = L.strip;
      var X = function (t) { return r.left + xa._offset + xa.l2p(t); }, left = r.left + xa._offset, zoomed = tag === "zoomed";
      var panels = [{ax: ya, top: r.top + ya._offset}, {ax: y2, top: r.top + y2._offset}];
      var boxes = [], bars = [], minText = 1e9, minData = 1e9, minLine = 1e9, crossed = 0;
      var topMost = panels[0].top, midMost = panels[1].top, chordsOn = gd.layout.shapes[CHORDS[0].shape].visible !== false;
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
      if (beatCard.style.display !== "none" && +beatCard.style.opacity > 0.05) {
        var cb = beatCard.getBoundingClientRect();
        boxes.push({i: -20, name: "card", kind: "card", over: true, l: cb.left, r: cb.right, t: cb.top, b: cb.bottom});
      }
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
        // Event lines that are drawn, ghosts included. Haloed text inside a panel may lie over one
        // (they are counted); everything else must stand clear -- the panels' names too, except
        // under a reader's own zoom.
        if (a.kind !== "card") EV.forEach(function (e) {
          var sh = gd.layout.shapes[e.shape];
          if (e.annotation === a.i || !e.on || sh.visible === false) return;
          var pn = panels[e.panel === "economy" ? 0 : 1], x = X(e.t);
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
        // Data: the lines of whichever panel the box is in, as far as the playhead has drawn
        // them, and the closing chords when they are up. A label inside a fill must clear both
        // lines; anything else must clear the whole tinted area between them. (Not the panels'
        // names under a reader's own zoom: a zoom can bring data up beneath them.)
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
            if (k === 1 && chordsOn) CHORDS.forEach(function (ch) {
              var y = pn.top + pn.ax.l2p(ch.value * (T - TA) / (ch.t - TA));
              if (Math.max(a.t - y, y - a.b) < 2) fail(tag + ": text on a chord: " + a.name + " / " + ch.key);
            });
          }
        });
      });
      if (tb.bottom > topMost - 0.5) fail(tag + ": the title runs into the top strip");
      var ppb = [ya._length / (ya.range[1] - ya.range[0]), y2._length / (y2.range[1] - y2.range[0])];
      if (Math.abs(ppb[0] - ppb[1]) > 0.02) fail(tag + ": panels have different scales: " + ppb.join(" vs ") + " px per bit");
      return {texts: boxes.length, minGapText: +minText.toFixed(1), minGapData: +minData.toFixed(1),
              minGapEventLine: +minLine.toFixed(1), overEventLines: crossed, pxPerBit: +ppb[0].toFixed(3),
              xEnd: String(xa.range[1]).slice(0, 10), titleRowPx: +(tb.bottom - r.top).toFixed(1),
              topStripPx: +(panels[0].top - topMost).toFixed(1), bottomStripPx: +(panels[1].top - midMost).toFixed(1),
              boxes: boxes};
    }
    function hoverAt(e) {
      var fl = gd._fullLayout, r = gd.getBoundingClientRect();
      var ax = e.panel === "economy" ? fl.yaxis : fl.yaxis2, hx = fl.xaxis.l2p(e.t), hy = ax._offset + ax._length * 0.6;
      return describe(hx, hy, r.left + fl.xaxis._offset + hx, r.top + hy, fl.xaxis, fl.yaxis, fl.yaxis2);
    }

    // One moment of the play: the axes, the scrubber, the playhead and its pill,
    // the ghosts, the cards, and the usual collisions. `seen` is where each label
    // was the last time it showed in this act: nothing may move within an act.
    var yRanges = JSON.stringify([gd._fullLayout.yaxis.range, gd._fullLayout.yaxis2.range]), seen = {}, ghostsSeen = {};
    function moment(tag, c) {
      return go(c).then(function () {
        var st = STATE, fl = gd._fullLayout, xa = fl.xaxis, r = gd.getBoundingClientRect(), tr = M.play.transition;
        var seg = TL.filter(function (s) { return c >= s.c0; }).pop(), s = c - seg.c0, k = seg.act;
        var cl = collisions(tag), x1 = xa.r2l(xa.range[1]), held = tr.card_in + tr.hold;
        if (JSON.stringify([fl.yaxis.range, fl.yaxis2.range]) !== yRanges) fail(tag + ": a y-range has changed");
        if (Math.abs(xa.r2l(xa.range[0]) - X0) > 1000) fail(tag + ": the x-axis no longer starts where the plot does");
        // The x-range: the act's own, except while a break is widening it.
        var widening = seg.kind === "break" && s > held && s < held + tr.widen;
        var want = seg.kind === "end" ? X1 : seg.kind === "break" && s >= held + tr.widen ? ACTS[k + 1].r1 : ACTS[k].r1;
        if (widening) { if (!(x1 > ACTS[k].r1 + DAY && x1 < ACTS[k + 1].r1 - DAY)) fail(tag + ": the axis is not between two acts' ranges while it widens"); }
        else if (Math.abs(x1 - want) > 1000) fail(tag + ": the x-range is not the act's: it ends " + iso(x1).slice(0, 10) + ", not " + iso(want).slice(0, 10));
        if (Math.abs(scrub.value / scrub.max - (st.T - T0) / (T1 - T0)) > 1 / scrub.max) fail(tag + ": the scrubber is not at the playhead's date");
        // The playhead, with the year under it; no axis label under the year.
        M.playhead.forEach(function (i) {
          var sh = fl.shapes[i];
          if (sh.visible === false || Math.abs(toMs(sh.x0) - st.T) > 1000) fail(tag + ": the playhead is not at the date");
        });
        var pr = pill.getBoundingClientRect();
        if (pill.style.display === "none" || pill.textContent !== String(new Date(st.T).getUTCFullYear())) fail(tag + ": the year pill does not show the year");
        if (pr.left < r.left - 1 || pr.right > r.right + 1 || pr.bottom > r.bottom + 1) fail(tag + ": the year pill is outside the figure");
        Array.prototype.forEach.call(gd.querySelectorAll(".xtick text"), function (el) {
          var b = el.getBoundingClientRect();
          if (el.style.visibility !== "hidden" && b.left < pr.right && pr.left < b.right && b.top < pr.bottom && pr.top < b.bottom)
            fail(tag + ": the year pill is on an axis label");
        });
        // Ghosts: at most one in each strip, the next labelled event there, faint, and deaf to the cursor.
        var ghosts = EV.filter(function (e) { return e.ghost; });
        ["economy", "stocks"].forEach(function (panel) {
          var mine = ghosts.filter(function (e) { return e.panel === panel; });
          if (mine.length > 1) fail(tag + ": " + mine.length + " ghosts in the " + panel + " strip");
          var faint = EV.filter(function (e) {
            var sh = fl.shapes[e.shape];
            return !e.tick && e.panel === panel && sh.visible !== false && c < e.clock;
          });
          if (faint.length > 1) fail(tag + ": more than one unreached event is drawn in the " + panel + " strip");
        });
        ghosts.forEach(function (e) {
          var sh = fl.shapes[e.shape], next = EV.filter(function (o) { return !o.tick && o.on && o.panel === e.panel && c < o.clock; })
            .sort(function (a, b) { return a.t - b.t; })[0];
          ghostsSeen[e.label] = true;
          if (next !== e) fail(tag + ": the ghost is not the next event: " + e.label);
          if (sh.opacity > M.play.ghost * M.event_line_opacity + 1e-6) fail(tag + ": a ghost's line is too strong: " + e.label);
          if (e.annotation !== null && fl.annotations[e.annotation].visible !== false && fl.annotations[e.annotation].opacity > M.play.ghost + 1e-6)
            fail(tag + ": a ghost's label is too strong: " + e.label);
          if (seg.kind === "break" && s < held + tr.widen) fail(tag + ": a ghost is up before the axis has widened: " + e.label);
          if (hoverAt(e).indexOf(e.description) >= 0) fail(tag + ": a ghost answers the cursor: " + e.label);
        });
        // The cards.
        var cardUp = actCard.style.display !== "none";
        if (cardUp !== (st.card >= 0 && st.cardAlpha > 0)) fail(tag + ": the act's title card is " + (cardUp ? "up" : "missing"));
        if (cardUp && (actCard.querySelector(".china-act-kicker").textContent !== M.play.acts[st.card].kicker
            || actCard.querySelector(".china-act-name").textContent !== M.play.acts[st.card].title)) fail(tag + ": the title card has the wrong words");
        if (seg.kind !== "end" && gd.layout.shapes[CHORDS[0].shape].visible !== false) fail(tag + ": a chord is drawn before the end");
        // Nothing moves within an act but the data: every label is where it was.
        if (seg.kind === "play") cl.boxes.forEach(function (b) {
          if (b.i < 0) return;
          var at0 = seen[b.i], now = [b.l - r.left, b.t - r.top];
          if (at0 && at0.act === k && Math.hypot(at0.at[0] - now[0], at0.at[1] - now[1]) > 0.75)
            fail(tag + ": a label moved within the act: " + b.name + " by " + Math.hypot(at0.at[0] - now[0], at0.at[1] - now[1]).toFixed(1) + " px");
          seen[b.i] = {act: k, at: now};
        });
        out.frames[tag] = {texts: cl.texts, minGapText: cl.minGapText, minGapData: cl.minGapData, xEnd: cl.xEnd,
                           year: pill.textContent, ghosts: names(ghosts)};
        return cl;
      });
    }

    var fill0 = [gd.data[TR.fill_behind].y.slice(), gd.data[TR.fill_ahead].y.slice()];
    return frames(3).then(function () {
      var c = collisions("complete");
      delete c.boxes;
      out.frames.complete = c;
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
      var fl5 = gd._fullLayout, xa = fl5.xaxis, y2 = fl5.yaxis2, r = gd.getBoundingClientRect();
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
      // The finished chart is what the page opens on: both chords, from the anchor to each
      // series' last point; each rate, the final value over the years since the anchor; no
      // playhead, no pill, no card; and a play button that says play, not replay.
      var years = (T1 - TA) / YEAR;
      out.end = {years: +years.toFixed(4), chords: []};
      CHORDS.forEach(function (ch, n) {
        var sh = fl5.shapes[ch.shape], lab = fl5.annotations[ch.annotation], finish = n ? last(S.s) : last(S.e), rate = finish / years;
        var says = (rate >= 0 ? "+" : "−") + Math.abs(rate).toFixed(3) + " bits/yr (×" + Math.pow(2, rate).toFixed(3) + "/yr)";
        out.end.chords.push(ch.key + ": " + finish + " bits / " + years.toFixed(3) + " yr = " + rate.toFixed(5) + " → " + says);
        if (sh.visible === false) fail("a chord is missing from the finished chart: " + ch.key);
        if (toMs(sh.x0) !== TA || sh.y0 !== 0 || toMs(sh.x1) !== last(S.t) || Math.abs(sh.y1 - finish) > 1e-9)
          fail("a chord does not run from the anchor to its series' last point: " + ch.key);
        if (sh.line.dash !== "dash" || sh.line.color !== (n ? M.colors.stock : M.colors.gdp)) fail("a chord is not dashed in its series' colour: " + ch.key);
        if (Math.abs(ch.rate - rate) > 1e-5 || ch.text.indexOf(says) < 0) fail("a rate is not the final value over the years: " + ch.text + " vs " + says);
        if (FIT.rates) {
          if (lab.visible === false || !(lab.opacity > 0.99) || plain(lab.text).replace(" (", "(").indexOf(says.replace(" (", "(")) < 0)
            fail("a rate is not shown on the finished chart: " + ch.key);
        } else if (!Array.prototype.some.call(keyBox.children, function (row) { return !row.hidden && row.textContent.indexOf(says) >= 0; }))
          fail("a rate is neither in the plot nor in the key: " + ch.key);
      });
      M.playhead.forEach(function (i) { if (fl5.shapes[i].visible !== false) fail("the playhead is drawn on the finished chart"); });
      if (pill.style.display !== "none") fail("the year pill is showing on the finished chart");
      if (actCard.style.display !== "none" || beatCard.style.display !== "none") fail("a card is showing on the finished chart");
      if (playBtn.classList.contains("is-done") || playBtn.classList.contains("is-playing")) fail("the play button does not say play when the page opens");
      // The speed toggle, and the labels at the ends of the scrubber.
      speedBtn.click();
      out.controls = {speed: speedBtn.textContent + " after one click", start: startOut.textContent, end: endOut.textContent};
      if (speed !== M.play.speeds[1] || speedBtn.textContent !== M.play.speeds[1] + "×") fail("the speed toggle did not switch");
      speedBtn.click();
      if (speed !== M.play.speeds[0]) fail("the speed toggle did not switch back");
      if (startOut.textContent !== String(new Date(T0).getUTCFullYear()) || endOut.textContent !== String(new Date(T1).getUTCFullYear()))
        fail("the scrubber's ends are not labelled with the first and last years");
      // The scrubber's segments: one label per act, in order, each over its own stretch of the track.
      var track = scrubWrap.getBoundingClientRect(), labels = actsBox.querySelectorAll(".china-act-label");
      if (labels.length !== ACTS.length || actsBox.querySelectorAll(".china-act-gap").length !== ACTS.length - 1) fail("the scrubber is not marked off in acts");
      Array.prototype.forEach.call(labels, function (b, k) {
        var q = b.getBoundingClientRect(), a = track.left + (ACTS[k].t0 - T0) / (T1 - T0) * track.width, e = track.left + (ACTS[k].t1 - T0) / (T1 - T0) * track.width;
        var form = [ACTS[0].title, ACTS[0].short, ACTS[0].numeral].indexOf(labels[0].textContent);
        if (form < 0 || b.textContent !== [ACTS[k].title, ACTS[k].short, ACTS[k].numeral][form]) fail("the acts' labels are not all titles, all short forms or all numerals: " + b.textContent);
        if (q.left < a - 1 || q.right > e + 1) fail("an act's label runs outside its segment: " + b.textContent);
      });
      // A horizontal zoom and an autoscale leave the scale alone.
      return PL.relayout(gd, {"xaxis.range": ["2005-01-01", "2012-01-01"]});
    }).then(function () { return frames(4); }).then(function () {
      var c = collisions("zoomed");
      delete c.boxes;
      out.frames.zoomed = c;
      return PL.relayout(gd, {"xaxis.autorange": true});
    }).then(function () { return frames(4); }).then(function () {
      var fl = gd._fullLayout;
      if (fl.xaxis.autorange) fail("the x-axis is still autoranged after autoscale");
      if (String(fl.xaxis.range[0]).slice(0, 10) !== M.view.x[0]) fail("autoscale did not return to the full view");
      if (!fl.yaxis.fixedrange || !fl.yaxis2.fixedrange) fail("a y-axis can be zoomed");
      // The whole play, segment by segment. First the opening card over the first frame: one dot.
      var tr = M.play.transition, held = tr.card_in + tr.hold, chain = Promise.resolve();
      function then(tag, c, also) { chain = chain.then(function () { return moment(tag, c); }).then(also || function () {}); }
      TL.forEach(function (seg) {
        var A = ACTS[seg.act], name = "act " + A.numeral;
        if (seg.kind === "open") {
          then("opening: card", seg.c0 + tr.card_in + tr.hold / 2, function () {
            var pts = [gd.data[TR.gdp].x.length, gd.data[TR.gdp_head].x.length, gd.data[TR.stock].x.length];
            if (pts.join() !== "1,1,0") fail("the first frame is not a single dot: " + pts.join());
            if (!(+actCard.style.opacity > 0.99)) fail("the opening title card is not fully up while it holds");
          });
          then("opening: ghost", seg.c0 + held + tr.ghost);
        } else if (seg.kind === "play") {
          [0.004, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.996].forEach(function (f) { then(name + " " + (100 * f).toFixed(1) + "%", seg.c0 + f * seg.dur); });
        } else if (seg.kind === "break") {
          var into = "break after " + name;
          then(into + ": card in", seg.c0 + tr.card_in / 2);
          then(into + ": hold", seg.c0 + tr.card_in + tr.hold / 2, function () {
            if (!(+actCard.style.opacity > 0.99)) fail(into + ": the title card is not fully up while it holds");
            if (EV.some(function (e) { return e.act > seg.act && gd._fullLayout.shapes[e.shape].visible !== false; })) fail(into + ": the next act's events are up before the axis has widened");
          });
          then(into + ": widening", seg.c0 + held + tr.widen / 2);
          then(into + ": ghost", seg.c0 + held + tr.widen + tr.ghost, function () {
            if (!EV.some(function (e) { return e.ghost && e.act === seg.act + 1; })) fail(into + ": no ghost appears once the axis has widened");
          });
          then(into + ": card out", seg.c0 + seg.dur - tr.card_out / 2);
        }
      });
      // The dates where the strips are busiest.
      [1961.2, 1966.6, 1966.97, 1967.5, 1972.3, 1977.5, 1980.2, 1985, 1989.6, 1992.6, 1994.2, 1999.3, 2002.5, 2005, 2008.4, 2011.2, 2016, 2019, 2023].forEach(function (y) {
        var T = Date.UTC(Math.floor(y), 0, 1) + (y % 1) * YEAR;
        then("date " + y + " (act " + ACTS[actOf(T)].numeral + ")", clockAt(T));
      });
      return chain;
    }).then(function () {
      // Each beat's card, three quarters of the way through: its words, inside the figure, off the
      // playhead; and its image, if it has one, faint behind its panel. (That it is off the data and
      // off every label is in the collisions.)
      var chain = Promise.resolve();
      BEATS.forEach(function (b, n) {
        var tag = "card " + (n + 1) + " (" + iso(b.t).slice(0, 7) + ")";
        chain = chain.then(function () { return moment(tag, b.c0 + 0.75 * (b.c1 - b.c0)); }).then(function () {
          var fl = gd._fullLayout, r = gd.getBoundingClientRect(), q = beatCard.getBoundingClientRect();
          if (beatCard.style.display === "none" || !(+beatCard.style.opacity > 0.99)) return fail(tag + ": the card is not up");
          if (beatCard.querySelector(".china-beat-lead").textContent !== (b.lead || "") || beatCard.querySelector(".china-beat-text").textContent !== (b.text || ""))
            fail(tag + ": the card does not say what the beat says");
          if (getComputedStyle(beatCard.querySelector(".china-beat-lead")).fontWeight < 600) fail(tag + ": the card's date is not bold");
          if (q.left < r.left || q.right > r.right || q.top < r.top || q.bottom > r.bottom) fail(tag + ": the card is outside the figure");
          var ax = b.panel === "economy" ? fl.yaxis : fl.yaxis2;
          if (q.top < r.top + ax._offset - 1 || q.bottom > r.top + ax._offset + ax._length + 1 || q.left < r.left + fl.xaxis._offset - 1 || q.right > r.left + fl.xaxis._offset + fl.xaxis._length + 1)
            fail(tag + ": the card is not inside the " + b.panel + " panel");
          if (b.box.forced) fail(tag + ": no clear place was found for the card");
          // The playhead for as long as the card is up: never on its dot (the current value of each
          // line in the card's panel); and off its line too, unless the panel was too narrow for that.
          [b.since, playhead, b.until].forEach(function (T) {
            var x = r.left + fl.xaxis._offset + fl.xaxis.l2p(T);
            (b.panel === "economy" ? [at(G.t, G.y, T)] : [at(S.t, S.s, T), at(S.t, S.e, T)]).forEach(function (v) {
              var y = v === null ? null : r.top + ax._offset + ax.l2p(v);
              if (y !== null && x > q.left - 6 && x < q.right + 6 && y > q.top - 6 && y < q.bottom + 6) fail(tag + ": the card is on the playhead's dot");
            });
            if (!b.box.overLine && x > q.left - 4 && x < q.right + 4) fail(tag + ": the card is on the playhead's line");
          });
          var shade = beatImage.style.display !== "none";
          if (shade !== !!b.image) fail(tag + ": the image is " + (shade ? "showing" : "missing"));
          if (shade && Math.abs(+beatImage.style.opacity - M.play.image_opacity) > 0.01) fail(tag + ": the image is not faint");
          if ((beatCard.querySelector(".china-beat-credit").textContent || "") !== (b.image ? b.credit : "")) fail(tag + ": the image's credit is wrong");
          if (b.event !== null && gd._fullLayout.shapes[EV[b.event].shape].opacity < 0.8) fail(tag + ": the card's event is not picked out");
          out.frames[tag].card = [Math.round(q.left - r.left), Math.round(q.top - r.top), Math.round(q.width), Math.round(q.height)];
        });
      });
      return chain;
    }).then(function () {
      // The closing flourish: the lime chord first, the periwinkle one a moment later, then the rates.
      var seg = last(TL), fl = M.play.flourish;
      function chord(n) { var sh = gd._fullLayout.shapes[CHORDS[n].shape]; return sh.visible === false ? 0 : (toMs(sh.x1) - TA) / (T1 - TA); }
      function rate(n) { var a = gd._fullLayout.annotations[CHORDS[n].annotation]; return a.visible === false ? 0 : a.opacity; }
      return moment("flourish: first chord", seg.c0 + fl.lag * 0.9).then(function () {
        if (!(chord(0) > 0.2 && chord(0) < 1) || chord(1) !== 0) fail("the economy's chord does not lead: " + chord(0).toFixed(2) + " / " + chord(1).toFixed(2));
        return moment("flourish: both chords", seg.c0 + fl.lag + fl.chord * 0.6);
      }).then(function () {
        if (chord(0) !== 1 || !(chord(1) > 0.3 && chord(1) < 1)) fail("the stocks' chord does not follow: " + chord(0).toFixed(2) + " / " + chord(1).toFixed(2));
        if (rate(0) || rate(1)) fail("a rate shows before its chord is drawn");
        return moment("flourish: rates", seg.c0 + fl.lag + fl.chord + fl.labels / 2);
      }).then(function () {
        if (FIT.rates && !(rate(0) > 0.2 && rate(0) < 1 && rate(1) > 0.2 && rate(1) < 1)) fail("the rates do not fade in after the chords");
      });
    }).then(function () {
      // The scrubber: its position is the date, linearly, and the axis is at once the act's.
      var chain = Promise.resolve(), at0 = [0.05, 0.2, 0.5, 0.8, 0.95];
      ACTS.slice(0, -1).forEach(function (A) { var f = (A.t1 - T0) / (T1 - T0); at0.push(f - 0.004, f + 0.004); });
      out.scrubber = {};
      at0.forEach(function (f) {
        chain = chain.then(function () {
          scrub.value = Math.round(scrub.max * f);
          busy = false; pending = null;
          scrub.dispatchEvent(new Event("input", {bubbles: true}));
          return frames(3);
        }).then(function () {
          var want = T0 + scrub.value / scrub.max * (T1 - T0), xa = gd._fullLayout.xaxis, k = actOf(want);
          out.scrubber[(+f).toFixed(3)] = iso(playhead).slice(0, 10) + " in act " + ACTS[k].numeral;
          if (Math.abs(playhead - want) > (T1 - T0) / scrub.max) fail("the scrubber is not linear in the date at " + f);
          if (STATE.kind !== "play" || STATE.act !== k || Math.abs(xa.r2l(xa.range[1]) - ACTS[k].r1) > 1000) fail("scrubbing to " + f + " does not show that date's act at once");
          if (gd._fullLayout.shapes[CHORDS[0].shape].visible !== false || gd._fullLayout.annotations[CHORDS[0].annotation].visible !== false)
            fail("scrubbing back does not hide the chords and rates");
          if (playing) fail("scrubbing does not pause");
        });
      });
      // To the very end: the finished chart.
      return chain.then(function () {
        scrub.value = scrub.max;
        busy = false; pending = null;
        scrub.dispatchEvent(new Event("input", {bubbles: true}));
        return frames(3);
      }).then(function () {
        if (!STATE.done || gd._fullLayout.shapes[CHORDS[1].shape].visible === false) fail("the end of the scrubber is not the finished chart");
      });
    }).then(function () {
      // An act's label starts that act from its title card; then play runs out and says replay.
      var labels = actsBox.querySelectorAll(".china-act-label"), chain = Promise.resolve();
      if (reducedMotion()) { out.jumps = "skipped: reduced motion"; return; }
      out.jumps = [];
      Array.prototype.forEach.call(labels, function (b, k) {
        chain = chain.then(function () { busy = false; pending = null; b.click(); return frames(2); }).then(function () {
          var was = playing, st = stateAt(k ? ACTS[k - 1].b0 : 0);
          pause();
          out.jumps.push(ACTS[k].numeral + " → " + st.kind + ", card " + ACTS[st.card].numeral + ", at " + iso(st.T).slice(0, 10));
          if (!was) fail("an act's label does not start playback: " + b.textContent);
          if (st.card !== k || Math.abs(st.T - ACTS[k].t0) > DAY) fail("an act's label does not lead to its title card: " + b.textContent);
          if (Math.abs(clock - (k ? ACTS[k - 1].b0 : 0)) > 3) fail("an act's label did not move the clock to its card: " + b.textContent);
        });
      });
      return chain.then(function () {
        // The last moments, played for real (if frames are being given out).
        busy = false; pending = null;
        play(END - 0.05);
        return new Promise(function (ok) { setTimeout(ok, document.hidden ? 50 : 700); });
      }).then(function () {
        out.replay = document.hidden ? "not observed: page hidden" : (playBtn.classList.contains("is-done") ? "replay" : "play");
        if (!document.hidden && (playing || !STATE.done || !playBtn.classList.contains("is-done"))) fail("play does not become replay at the end");
        pause();
        return go(END);
      });
    }).then(function () {
      // Hover at an interpolated playhead: nothing from Plotly, only actual points from us.
      var k = Math.floor(G.t.length * 0.7), Tm = G.t[k] + 0.37 * (G.t[k + 1] - G.t[k]);
      return go(clockAt(Tm)).then(function () {
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
        // A back-tested month says so, and why.
        if (M.backtest) {
          var month = Math.max(0, S.solid - 2), by = fl.yaxis2;
          showTip(r.left + xa._offset + xa.l2p(S.t[month]), r.top + by._offset + by.l2p(S.s[month]));
          out.hover.backtest = Array.prototype.map.call(tip.children, function (d) { return d.textContent; });
          if (out.hover.backtest.indexOf(M.backtest.note) < 0 || !/back-tested/.test(out.hover.backtest.join(" "))) fail("a back-tested month does not say so");
          if (gd._fullData[TR.stock_back].line.dash !== "dot" || gd.data[TR.stock_back].x.length !== S.solid + 1) fail("the back-tested stretch is not drawn dotted");
          hideTip();
        }
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
        // Cost of one draw call (the synchronous part of a frame), across the whole timeline.
        var n = 80, i = 0, worst = 0, total = 0;
        function one() {
          if (i >= n) return Promise.resolve();
          busy = false; pending = null;
          var t0 = performance.now();
          render(END * (i++ / n));
          var dt = performance.now() - t0;
          worst = Math.max(worst, dt); total += dt;
          return frames(1).then(one);
        }
        return one().then(function () {
          out.drawMs = {mean: +(total / n).toFixed(1), worst: +worst.toFixed(1)};
          return go(END);
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
      if (String(fl.xaxis.range[1]).slice(0, 10) !== M.view.x[1]) fail("the finished chart does not show the full range");
      // Every labelled event that is drawn was, at some point, the ghost in its strip (or was there from the start).
      out.ghosts = Object.keys(ghostsSeen).length + " of " + EV.filter(function (e) { return !e.tick && e.on; }).length + " labelled events seen as ghosts";
      // What the play adds up to, in seconds at 1x.
      var tr = M.play.transition, open = tr.card_in + tr.hold + tr.ghost + tr.card_out, flo = last(TL).dur;
      out.play = {opening: +open.toFixed(2), acts: ACTS.map(function (A) { return A.numeral + ": " + A.total.toFixed(2); }),
                  eachBreak: +(open + tr.widen).toFixed(2), flourish: +flo.toFixed(2), total: +END.toFixed(2),
                  totalAt2x: +(END / M.play.speeds[1]).toFixed(2)};
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
    function notes(list) { return list.map(function (n) { return {t: toMs(n.date), when: n.when, text: n.text}; }); }
    G = series(TR.gdp); G.hover = M.hover.gdp;
    // The stock line is two traces where its early stretch is back-tested; they share the point between them.
    var back = series(TR.stock_back), fore = series(TR.stock);
    S = {x: back.x.slice(0, -1).concat(fore.x), s: back.y.slice(0, -1).concat(fore.y), solid: Math.max(0, back.x.length - 1)};
    S.t = S.x.map(toMs); S.e = gd.data[TR.economy].y.slice(); S.hoverS = M.hover.stock; S.hoverE = M.hover.economy;
    PEERS = TR.peers.map(series);
    T0 = toMs(M.play.start); T1 = toMs(M.play.end); TA = toMs(M.anchor); TG = toMs(M.anchors[0].date);
    TB = M.backtest ? toMs(M.backtest.until) : -Infinity;
    X0 = toMs(M.view.x[0]); X1 = toMs(M.view.x[1]);
    // The acts, and the timeline they make with the opening card, the breaks and the flourish.
    ACTS = M.play.acts.map(function (a) {
      var tau = [0];                                   // seconds into the act at each step of its date grid
      a.steps.forEach(function (d) { tau.push(last(tau) + d); });
      return {numeral: a.numeral, title: a.title, short: a.short, kicker: a.kicker, t0: toMs(a.start), t1: toMs(a.end),
              r1: toMs(a.range[1]), tau: tau, total: last(tau), c0: 0, b0: 0};
    });
    var tr = M.play.transition, fl = M.play.flourish, open = tr.card_in + tr.hold + tr.ghost + tr.card_out, c = open;
    TL = [{kind: "open", act: 0, c0: 0, dur: open}];
    ACTS.forEach(function (A, k) {
      A.c0 = c; TL.push({kind: "play", act: k, c0: c, dur: A.total}); c += A.total;
      if (k === ACTS.length - 1) return;
      A.b0 = c; TL.push({kind: "break", act: k, c0: c, dur: open + tr.widen}); c += open + tr.widen;
    });
    TL.push({kind: "end", act: ACTS.length - 1, c0: c, dur: fl.lag + fl.chord + fl.labels});
    END = c + fl.lag + fl.chord + fl.labels;
    EV = M.events.map(function (e) {
      var t = toMs(e.date);
      return {t: t, tier: e.tier, tick: e.tier === "tick", panel: e.panel, label: e.label,
              text: e.text, short: e.short, say: e.text, lead: e.lead, description: e.description, notes: notes(e.notes),
              shape: e.shape, annotation: e.annotation, on: true, labelled: e.annotation !== null, row: 0, spot: 0.5,
              ext: [0, 0], stem: 0, lift: 3, act: ownAct(t), showAct: ownAct(t), clock: clockOf(t), ghost: false};
    });
    ERAS = M.eras.map(function (e) {
      return {t0: toMs(e.start), t1: toMs(e.end), label: e.label, description: e.description, drop_first: e.drop_first,
              notes: notes(e.notes), bar: e.bar, tip: e.tip, annotation: e.annotation, on: true, labelled: true,
              live: false, text: false, cut: false, a: 0, b: 0, w: 0, showAct: 0};
    });
    LEADERS = M.leaders.map(function (l) {
      return {t0: toMs(l.start), t1: l.end ? toMs(l.end) : Infinity, label: l.label, description: l.description,
              tint: l.tint, shape: l.shape, tip: l.tip, annotation: l.annotation, labelled: true, live: false,
              text: false, cut: false, a: 0, b: 0, w: 0, show: null};
    });
    BANDS = M.bands.map(function (bd) {
      return {t0: bd.start ? toMs(bd.start) : -Infinity, t1: toMs(bd.end), kind: bd.kind, wraps: bd.wraps,
              description: bd.description, trace: bd.trace, shape: bd.shape, annotation: bd.annotation, span: null,
              y: bd.trace === null ? null : gd.data[bd.trace].y.slice(), yLabel: bd.y, spots: [],
              early: bd.early ? {t1: toMs(bd.early.end), shape: bd.early.shape, description: bd.early.description} : null};
    });
    ARROWS = M.arrows.map(function (a) {
      return {role: a.role, date: a.date, t: toMs(a.date), y: a.y, month: a.month, mode: a.mode, wraps: a.wraps,
              text: a.text, key: a.key, box: null};
    });
    FILLS = M.fills.map(function (f) {
      return {role: f.role, kind: f.kind, wraps: f.wraps, t0: toMs(f.start), t1: toMs(f.end), box: null};
    });
    CHORDS = M.chords.map(function (ch) {
      return {key: ch.key, name: ch.name, color: ch.color, rate: ch.rate, value: ch.value, t: toMs(ch.date), wraps: ch.wraps,
              text: ch.text, shape: ch.shape, annotation: ch.annotation, spot: null};
    });
    ANCHORS = M.anchors.map(function (a) { return {trace: a.trace, panel: a.panel, date: a.date, t: toMs(a.date), text: a.text}; });
    // A beat's card is up between two moments of the clock: those at which the playhead is at its two dates.
    BEATS = M.play.beats.map(function (b) {
      var since = toMs(b.since), until = toMs(b.until);
      return {t: toMs(b.date), act: b.act, panel: b.panel, lead: b.lead, text: b.text, image: b.image, credit: b.credit,
              event: b.event, since: since, until: until, c0: ACTS[b.act].c0 + tauOf(b.act, since),
              c1: ACTS[b.act].c0 + tauOf(b.act, until), box: null};
    });
    // The key: a row for the bottom panel's zero line, a numbered row for each arrowed annotation,
    // and a row for each closing rate. A row shows only if the plot has no room for what it says.
    function keyRow(sign, text, t, kind) {
      var row = document.createElement("div");
      row.className = "china-key-row"; row.setAttribute("data-t", t);
      if (kind) row.setAttribute("data-" + kind, "");
      row.appendChild(sign);
      row.appendChild(document.createTextNode(text));
      keyBox.appendChild(row);
    }
    var line = document.createElement("span");
    line.className = "china-key-line";
    keyRow(line, M.key.zero, TA, "zero");
    ARROWS.forEach(function (a, n) {
      var num = document.createElement("span");
      num.className = "china-key-n"; num.textContent = n + 1;
      keyRow(num, a.key + ".", a.t, null);
    });
    CHORDS.forEach(function (ch) {
      var dash = document.createElement("span");
      dash.className = "china-key-line china-key-dash"; dash.style.borderTopColor = ch.color;
      keyRow(dash, ch.text + ".", T1, "rate");
    });
    // The scrubber: a gap in the track where one act gives way to the next, and each act's title
    // under its own stretch. A title starts its act, from the title card.
    ACTS.forEach(function (A, k) {
      var a = (A.t0 - T0) / (T1 - T0), b = (A.t1 - T0) / (T1 - T0);
      if (k) {
        var gap = document.createElement("span");
        gap.className = "china-act-gap"; gap.style.left = (100 * a).toFixed(3) + "%";
        actsBox.appendChild(gap);
      }
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "china-act-label"; btn.style.left = (50 * (a + b)).toFixed(3) + "%";
      btn.textContent = A.title; btn.title = A.kicker;
      btn.setAttribute("aria-label", A.kicker + ": " + A.title);
      btn.addEventListener("click", function () { jump(k); });
      actsBox.appendChild(btn);
    });
    startOut.textContent = new Date(T0).getUTCFullYear();   // static: the two ends of the timeline
    endOut.textContent = new Date(T1).getUTCFullYear();
    setSpeed(M.play.speeds[0]);
    // The page opens on the finished chart.
    clock = END; playhead = T1; STATE = stateAt(END);

    playBtn.addEventListener("click", function () { if (playing) pause(); else play(); });
    speedBtn.addEventListener("click", function () {
      setSpeed(M.play.speeds[(M.play.speeds.indexOf(speed) + 1) % M.play.speeds.length]);
    });
    // The scrubber's position is a date. It shows that date as its own act plays it: never a break.
    scrub.addEventListener("input", function () { pause(); render(clockAt(T0 + scrub.value / scrub.max * (T1 - T0))); });
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
    // For checking by hand or by script (?china-debug, ?china-audit): show any moment of the timeline.
    if (location.search.indexOf("china-") >= 0) window.__CHINA__ = {
      show: function (c) { pause(); busy = false; pending = null; render(c); return STATE; },
      state: function () { return STATE; }, clockAt: clockAt, timeline: TL, acts: ACTS, beats: BEATS, end: END};
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
    scroll-zoom off so the page still scrolls), a slot for a beat's image
    behind it, the title, each panel's name, the two kinds of card, the year
    pill and the hover overlay in front of it, the key used when direct labels
    do not fit, a play button, a speed toggle and a native
    ``<input type="range">`` scrubber marked off in acts, and the script that
    fits the figure to its column, places the text, plays the animation,
    follows the site's light/dark theme and shows the hover box. Everything the
    script needs comes from the figure itself (the traces and ``layout.meta``):
    every word on a card is set in this module's data, none in the script.
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

    gdp, s_file = load_derived()
    g = rebased(gdp, "CHN")
    s_all = stock_since(s_file)
    cutoff = common_cutoff(g, s_all)
    s = s_all[:cutoff]
    e = economy_since_anchor(g, s.index)
    since = _month(STOCK_ANCHOR)                     # how the anchor is named wherever text names it
    assert anchor_month_end(s_file) == STOCK_ANCHOR == s.index[0], "STOCK_ANCHOR should be a month-end in the derived file"
    fig = build_china_figure()
    meta = dict(fig.layout.meta)
    tr = meta["trace"]
    gdp_tr, stock, economy = fig.data[tr["gdp"]], fig.data[tr["stock"]], fig.data[tr["economy"]]
    html = china_figure_html(fig)
    page, script = html.rsplit("<script>", 1)        # this module's own script comes last; the page is the rest
    wide, light = _LAYOUTS["wide"], _ALPHA["light"]
    st = wide["strip"]

    # (1) Units and anchors: everything is in bits, and zero where it should be.
    raw = pd.read_csv(_DATA_PATH, comment="#", parse_dates=["date"])
    nats = raw[(raw["series"] == "gdp") & (raw["entity"] == "CHN")].set_index("date")["log_ratio"]
    year = lambda series, y: series[series.index.year == y].item()
    close(year(g, 2025), (year(nats, 2025) - year(nats, GDP_ANCHOR_YEAR)) / np.log(2), 2e-6, "g is not in bits")
    stock_nats = raw[raw["series"] == "stocks"].set_index("date")["log_ratio"]
    close(s[cutoff], (stock_nats[cutoff] - stock_nats[STOCK_ANCHOR]) / np.log(2), 2e-6, "s is not in bits")
    assert year(g, GDP_ANCHOR_YEAR) == 0.0, "g(1978) != 0"
    assert s[STOCK_ANCHOR] == 0.0 and e[STOCK_ANCHOR] == 0.0, f"s or e is not zero in {since}"
    assert stock.x[0] == economy.x[0] == _iso(STOCK_ANCHOR) and stock.y[0] == economy.y[0] == 0.0
    # g at the anchor, by hand: on the straight line between the July points either side of it.
    before, after = g[:STOCK_ANCHOR].index[-1], g[STOCK_ANCHOR:].index[0]
    by_hand = g[before] + (g[after] - g[before]) * (STOCK_ANCHOR - before).days / (after - before).days
    for d, v in list(e.items())[::37]:
        close(v, g_at(g, d)[0] - by_hand, 3e-6, f"e({d:%Y-%m}) is not g re-anchored at {since}")
    # The derived file says what it holds, and the figure takes it at its word.
    info = derived_info()
    assert info["stocks_variant"] in ("net", "gross") and info["stocks_variant"] in source_line()
    assert pd.Timestamp(info["stocks_start"]) == s_file.index[0] <= STOCK_ANCHOR, "the anchor precedes the stock data"
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
    assert texts["arrow_peak"] == f"{_month(peak)} peak: Chinese stocks ×{2 ** s[peak]:.1f} US stocks since {since}"
    assert texts["arrow_trough"] == f"{_month(trough)} trough: Chinese stocks ×{2 ** s[trough]:.2f} US stocks since {since}"
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
    assert [a["text"] for a in meta["anchors"]] == [f"{GDP_ANCHOR_YEAR} = 0", f"{since} = 0"]
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
        "Nixon in Beijing", "Reform and opening", "Joins World Bank, IMF", "Special economic zones", "Tiananmen",
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
        "Reform and opening": 3, "Property crisis": 1, "QFII": 2, "Stock Connect": 2, "Crash": 1, "Cultural Revolution": 5}
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
    # Lime and periwinkle are for data: no shape wears them but the two closing chords (which ARE
    # data: each joins two points of its series), and no label but the one for the periwinkle fill.
    data_colours = [_rgb(_GDP_COLOR).tolist(), _rgb(_STOCK_COLOR).tolist()]
    chord_shapes = {chord["shape"] for chord in meta["chords"]}
    for i, sh in enumerate(fig.layout.shapes):
        colour = _rgb(sh.fillcolor or sh.line.color).tolist()
        assert colour in (data_colours if i in chord_shapes else (navy, _rgb(_INK).tolist())), "a shape is in a data colour"
    for i, a in enumerate(fig.layout.annotations):
        assert (_rgb(a.font.color).tolist() in data_colours) == (i == meta["ann"]["fill_ahead"]), a.text

    # (13) Playback: three acts that tile the data, each with one x-range; beats; what it adds up to.
    play = meta["play"]
    acts, beats = play["acts"], play["beats"]
    assert play["start"] == gdp_tr.x[0] == acts[0]["start"] and play["end"] == _iso(cutoff) == acts[-1]["end"]
    assert play["speeds"] == [1, 2] and 'class="china-speed"' in page
    assert [(a["numeral"], a["title"]) for a in acts] == [
        ("I", "Mao's Mayhem"), ("II", "Deng's Reforms"), ("III", "An Investable China")]
    assert [a["end"] for a in acts[:-1]] == ["1978-12-18", "1992-02-21"], "the act breaks have moved"
    assert [a["kicker"] for a in acts] == ["Act I · 1960–1978", "Act II · 1978–1992", f"Act III · 1992–{cutoff.year}"]
    # The acts tile the data: the first starts with it, each starts where the one before ends, the last ends with it.
    for earlier, later in zip(acts, acts[1:]):
        assert earlier["start"] < earlier["end"] == later["start"] < later["end"], "the acts do not tile the data"
    # One x-range per act: from the start of the plot to the act's end and a little room. The last
    # act's is the finished chart's. (The script takes each act's range from here, and changes the
    # x-range only between one act's and the next's.)
    for act in acts:
        lo, end, hi = (pd.Timestamp(v) for v in (act["range"][0], act["end"], act["range"][1]))
        assert act["range"][0] == x0, f"act {act['numeral']} does not start where the plot does"
        close((hi - end) / (end - lo), WINDOW_MARGIN, 2e-3, f"act {act['numeral']}: the room right of its end")
    assert acts[-1]["range"] == list(fig.layout.xaxis.range), "the last act's range is not the finished chart's"
    assert [a["range"][1] for a in acts] == sorted({a["range"][1] for a in acts}), "the stage should widen act by act"
    # The y-ranges are the same in every act because there is only one of each: nothing changes them.
    assert meta["view"]["y"] == list(fig.layout.yaxis.range) and meta["view"]["y2"] == list(fig.layout.yaxis2.range)
    assert '"yaxis.range' not in script and '"yaxis2.range' not in script, "the script must never set a y-range"
    # The renamed event sits on the first act break; the second break is the Southern Tour's end.
    reform = by_label("Reform and opening", "economy")
    assert reform["date"] == acts[0]["end"] and "Deng's reforms" not in html

    # The schedule: each act lasts what it was given, starts from rest and comes to rest, slows to
    # 40% of its base speed at every labelled event and further for a card, and never stops between.
    assert EVENT_SLOWDOWN == 0.4 and 0.15 <= CARD_SLOWDOWN <= 0.2 and CARD_SECONDS == (1.5, 0.25)
    marks = [pd.Timestamp(ev["date"]) for ev in drawn if ev["tier"] != "tick"]
    durations, bases, n_cards = [], [], 0
    for act, spec in zip(acts, ACTS):
        start, end = pd.Timestamp(act["start"]), pd.Timestamp(act["end"])
        years = (end - start).days / 365.25
        tau = np.concatenate([[0.0], np.cumsum(act["steps"])])
        assert min(act["steps"]) > 0, f"act {act['numeral']}: playback time does not run forwards"
        close(tau[-1], spec.seconds, 0.01, f"act {act['numeral']} does not last what it was given")
        assert abs(years / (len(tau) - 1) - _SCHEDULE_STEP_YEARS) < 0.01, "the schedule's spacing"
        mine = [b for b in BEATS if start < pd.Timestamp(b.date) <= end]
        table = act_schedule(start, end, spec.seconds, [(d, EVENT_SLOWDOWN) for d in marks], mine)
        f, x, cell = table["factor"], table["years"], years / len(table["years"])
        close(table["base"], act["base"], 1e-3, "the schedule in the figure is not the one built here")
        assert f[0] < 0.1 and f[-1] < 0.1 and f.max() > 0.999, f"act {act['numeral']} should start and end at rest"
        for d in marks:                              # every labelled event is a beat
            at = (d - start).days / 365.25
            if 0 <= at <= years:
                assert f[np.abs(x - at).argmin()] <= EVENT_SLOWDOWN + 0.01, f"no slowdown at the event of {d:%Y-%m-%d}"
        for beat, (opens, closes) in zip(mine, table["windows"]):
            day = pd.Timedelta(days=365.25)
            up = (x >= (opens - start) / day) & (x <= (closes - start) / day)
            assert f[up].max() <= beat.slow + 1e-9, f"playback is not slowed throughout the card of {beat.date}"
            close(float((cell / (table["base"] * f[up])).sum()), card_seconds(beat), 0.2,
                  f"the card of {beat.date} is not up for as long as it takes to read")
            n_cards += 1
        between = (x > STOP_YEARS) & (x < years - STOP_YEARS)
        assert f[between].min() >= min([EVENT_SLOWDOWN] + [b.slow for b in mine]) - 1e-9, "a full stop inside an act"
        jolt = (np.abs(np.diff(f[between])) / f[between][:-1]).max()
        assert jolt < 0.03, f"act {act['numeral']}: the pace changes abruptly somewhere ({jolt:.1%} in {cell * 365:.1f} days)"
        durations.append(float(tau[-1]))
        bases.append(table["base"])
    assert n_cards == len(BEATS) == len(beats), "a beat falls in no act"
    assert [spec.seconds for spec in ACTS] == [22.0, 20.0, 55.0], "the acts' lengths have been retuned: update the report"
    opening = sum(TRANSITION[k] for k in ("card_in", "hold", "ghost", "card_out"))
    transition = opening + TRANSITION["widen"]
    flourish = FLOURISH["lag"] + FLOURISH["chord"] + FLOURISH["labels"]
    assert 4 <= transition <= 5 and TRANSITION["widen"] == 1.0, "an act break should take 4 to 5 s, a second of it widening"
    assert 0.6 <= FLOURISH["chord"] <= 0.8 and FLOURISH["lag"] == 0.3 and 0.25 <= GHOST_OPACITY <= 0.35 and REVEAL_SECONDS == 0.5
    total = opening + sum(durations) + transition * (len(acts) - 1) + flourish
    assert play["transition"] == TRANSITION and play["flourish"] == FLOURISH

    # Beats: the three placeholder cards, word for word, each in its act and its panel; no images.
    # Every word on a card comes from this module's data: the script holds none of it.
    assert [(b["date"], b["lead"], b["text"]) for b in beats] == [
        ("1961-06-30", "1959–61", "The Great Leap Forward ends in famine. Output per person falls by almost a third."),
        ("1990-01-01", "1989–90", "Inflation, Tiananmen, austerity. Growth per person falls to 2.5%; the catch-up stalls."),
        ("1993-07-15", "Jul 1993", "Tsingtao Brewery becomes the first Chinese company to list in Hong Kong (H-shares).")]
    assert [(b["act"], b["panel"]) for b in beats] == [(0, "stocks"), (1, "stocks"), (2, "economy")]
    assert all(b["image"] is None and b["credit"] is None for b in beats), "the figure ships with no images"
    for b, beat in zip(beats, BEATS):
        assert b["since"] < b["date"] < b["until"] and acts[b["act"]]["start"] < b["since"] and b["until"][:10] <= acts[b["act"]]["end"]
        close(b["seconds"], 1.5 + 0.25 * len(f"{beat.lead} {beat.text}".split()), 1e-9, "a card's reading time")
        assert 0.15 <= b["slow"] <= 0.2
    assert beats[2]["event"] == drawn.index(by_label("First H-shares", "stocks")) and beats[0]["event"] is None
    for words in [b.text for b in BEATS] + [b.lead for b in BEATS] + [a.title for a in ACTS] + [a["kicker"] for a in acts]:
        assert words not in script, f"card text is hard-coded in the script: {words}"
    # The image slot, with a dummy (here only): it needs a credit, and travels with its beat.
    dummy = Beat("1985-06-30", lead="1985", text="A dummy card.", image="dummy.png", credit="Image: nobody")
    with_image = build_china_figure(beats=BEATS + [dummy]).layout.meta["play"]["beats"]
    assert [(b["image"], b["credit"]) for b in with_image if b["image"]] == [("dummy.png", "Image: nobody")]
    try:
        build_china_figure(beats=[Beat("1985-06-30", text="No credit.", image="dummy.png")])
        raise RuntimeError("an image without a credit was accepted")
    except AssertionError:
        pass
    assert 0.2 <= IMAGE_OPACITY <= 0.25
    # The controls: no year watermark; a scrubber from the first year to the last, marked off by the script.
    for cls in ("china-play", "china-ico-replay", "china-scrub", "china-acts", "china-start", "china-end",
                "china-pill", "china-act-card", "china-beat", "china-beat-image"):
        assert cls in page, f"the page has no {cls}"
    assert "china-year-mark" not in html, "the year watermark should be gone"
    playhead = [fig.layout.shapes[i] for i in meta["playhead"]]
    assert [sh.yref for sh in playhead] == ["y domain", "y2 domain"] and all(sh.visible is False for sh in playhead)
    assert all(sh.opacity <= 0.3 and sh.line.width <= 1 and (sh.y0, sh.y1) == (0, 1) for sh in playhead), "a quiet playhead"

    # (13b) The end: a dashed chord from the anchor to each series' last point, in the bottom panel,
    #       and the rate each stands for: the final value over the years since the anchor.
    span_years = (cutoff - STOCK_ANCHOR).days / 365.25
    chords = meta["chords"]
    assert [c["key"] for c in chords] == ["economy", "stocks"], "the lime chord is drawn first"
    for chord, series, colour in zip(chords, (e, s), (_GDP_COLOR, _STOCK_COLOR)):
        line, label = fig.layout.shapes[chord["shape"]], fig.layout.annotations[chord["annotation"]]
        finish = float(series.iloc[-1])
        assert (line.xref, line.yref, line.line.dash, line.line.color) == ("x", "y2", "dash", colour)
        assert (line.x0, line.y0) == (_iso(STOCK_ANCHOR), 0), "a chord does not start at the anchor"
        assert (line.x1, line.y1) == (stock.x[-1], finish) == (chord["date"], chord["value"]), "a chord misses its last point"
        rate = finish / span_years
        close(chord["rate"], rate, 1e-6, "a rate is not the final value over the years since the anchor")
        said = f"{'+' if rate >= 0 else '−'}{abs(rate):.3f} bits/yr (×{2 ** rate:.3f}/yr)"
        assert chord["text"] == f"{chord['name']}: {said}", f"{chord['text']} != {said}"
        assert all(part in wrap for wrap in chord["wraps"] for part in said.split(" (")), "a rate label's wording"
        assert label.yref == "y2" and not label.textangle and label.text == chord["wraps"][0]
    # What was expected: about +0.084, and about -0.021 to -0.022, bits a year.
    close(chords[0]["rate"], 0.084, 0.0006, "the economy's rate is not about +0.084 bits a year")
    assert -0.0225 <= chords[1]["rate"] <= -0.0205, f"the stocks' rate is {chords[1]['rate']:+.4f} bits a year"

    # (13c) The stock anchor is a parameter. Build the figure with another one, two years on, and
    #       check that everything that depends on the anchor has followed it.
    asked = pd.Timestamp(year=STOCK_ANCHOR.year + 2, month=STOCK_ANCHOR.month, day=STOCK_ANCHOR.day)
    other = anchor_month_end(s_file, asked)          # that month's last trading day, which is what the file holds
    assert other.to_period("M") == asked.to_period("M") and 0 <= (asked - other).days <= 3
    alt = build_china_figure(stock_anchor=asked)
    am, at_ = dict(alt.layout.meta), alt.layout.meta["trace"]
    s2 = stock_since(s_file, other)[:cutoff]
    e2 = economy_since_anchor(g, s2.index, other)
    since2 = _month(other)
    alt_stock, alt_economy = alt.data[at_["stock"]], alt.data[at_["economy"]]
    # Where the stock line starts, and the lime line re-based to zero there.
    assert alt_stock.x[0] == alt_economy.x[0] == _iso(other) and alt_stock.y[0] == alt_economy.y[0] == 0.0
    assert list(alt_stock.y) == [float(v) for v in s2] and list(alt_economy.y) == [float(v) for v in e2]
    for d in s2.index[::29]:
        close(s2[d], s[d] - s[other], 2e-6, "the stock line is not the same series re-based")
        close(e2[d], e[d] - e[other], 2e-6, "the economy line is not the same series re-based")
    # The anchor circle, its hover text, the zero line and its labels, and the end of the plain band.
    assert list(alt.data[at_["anchor_bottom"]].x) == [_iso(other)] and am["anchor"] == _iso(other)
    assert am["anchors"][1]["date"] == _iso(other) and am["anchors"][1]["text"] == f"{since2} = 0"
    assert alt.layout.shapes[am["zero"]["bottom"]].x0 == _iso(other)
    assert alt.layout.annotations[am["ann"]["zero_up"]].x == alt.layout.annotations[am["ann"]["zero_down"]].x == _iso(other)
    assert am["bands"][1]["end"] == _iso(other) and alt.layout.shapes[am["bands"][1]["shape"]].x1 == _iso(other)
    assert am["bands"][0]["end"] == _EXCHANGE_OPENS, "the hatched band does not depend on the anchor"
    # The wording, and the four annotated points, recomputed.
    assert am["key"]["zero"].count(since2) == 1 and meta["key"]["zero"].count(since) == 1
    peak2 = s2.idxmax()
    trough2 = s2[:peak2].idxmin()
    said2 = {a["role"]: a for a in am["arrows"]}
    assert said2["arrow_peak"]["text"] == f"{_month(peak2)} peak: Chinese stocks ×{2 ** s2[peak2]:.1f} US stocks since {since2}"
    assert said2["arrow_trough"]["text"] == f"{_month(trough2)} trough: Chinese stocks ×{2 ** s2[trough2]:.2f} US stocks since {since2}"
    assert (said2["arrow_peak"]["y"], said2["arrow_trough"]["y"]) == (float(s2[peak2]), float(s2[trough2]))
    for name, other_line in (("arrow_economy", e2), ("arrow_parity", 0.0)):
        when, level = final_crossing(s2, other_line)
        assert said2[name]["date"] == pd.Timestamp(when).strftime("%Y-%m-%d %H:%M:%S") and said2[name]["y"] == level
        assert (alt.layout.annotations[am["ann"][name]].x, alt.layout.annotations[am["ann"][name]].y) == (said2[name]["date"], level)
    assert said2["arrow_economy"]["date"] != {a["role"]: a for a in meta["arrows"]}["arrow_economy"]["date"], (
        "the crossing with the economy should move when the anchor does")
    # The hover text, and the rates that close the animation.
    assert am["hover"]["stock"][0].startswith(f"Stocks ({since2})") and len(am["hover"]["stock"]) == len(s2)
    span2 = (cutoff - other).days / 365.25
    for chord, series in zip(am["chords"], (e2, s2)):
        line = alt.layout.shapes[chord["shape"]]
        assert (line.x0, line.y0, line.x1, line.y1) == (_iso(other), 0, _iso(cutoff), float(series.iloc[-1]))
        close(chord["rate"], float(series.iloc[-1]) / span2, 1e-6, "a rate did not follow the anchor")
        assert f"{abs(series.iloc[-1] / span2):.3f} bits/yr" in chord["text"]
    # Nothing in that figure, or in the page made from it, still names the default anchor.
    alt_html = china_figure_html(alt)
    for where, text in (("figure JSON", alt.to_json()), ("page", alt_html)):
        assert _iso(STOCK_ANCHOR) not in text and since not in text, f"the {where} still names {since} with the anchor moved"
    assert since2 in alt.to_json() and since in fig.to_json()
    # Nor does the source: the anchor's year is written once, on the line that sets STOCK_ANCHOR
    # (and nowhere in the prep script, which starts wherever its files do).
    needle = str(STOCK_ANCHOR.year)
    for path, allowed in ((Path(__file__), ["STOCK_ANCHOR = "]), (_HERE / "prepare_china_figure_data.py", [])):
        named = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if needle in ln]
        assert len(named) == len(allowed) and all(ln.startswith(a) for ln, a in zip(named, allowed)), (
            f"{path.name} names the anchor's year outside the parameter: {named}")
    # An anchor in a month the derived file does not cover is refused.
    for bad in (s_file.index[0] - pd.Timedelta(days=45), s_file.index[-1] + pd.Timedelta(days=45)):
        try:
            build_china_figure(stock_anchor=bad)
            raise RuntimeError(f"an impossible anchor was accepted: {bad:%Y-%m-%d}")
        except AssertionError:
            pass

    # (13d) A back-tested stretch, if one is declared: dotted, sharing a point with the solid line,
    #       and saying why in its hover text. None is declared by default.
    assert STOCK_BACKTESTED_UNTIL is None and meta["backtest"] is None and len(fig.data[tr["stock_back"]].x) == 0
    until = s.index[30]
    tested = build_china_figure(backtested_until=until)
    tm, tt = tested.layout.meta, tested.layout.meta["trace"]
    dotted, solid = tested.data[tt["stock_back"]], tested.data[tt["stock"]]
    assert dotted.line.dash == "dot" and solid.line.dash in (None, "solid") and dotted.line.color == solid.line.color
    assert dotted.x[-1] == solid.x[0] == tm["backtest"]["until"] == _iso(until), "the two stretches do not meet"
    assert list(dotted.x[:-1]) + list(solid.x) == list(stock.x) and list(dotted.y[:-1]) + list(solid.y) == list(stock.y)
    assert tm["backtest"]["note"] == BACKTEST_NOTE and "31 October 1995" in BACKTEST_NOTE and "back-tested" in BACKTEST_NOTE
    flagged = [h.endswith(", back-tested") for h in tm["hover"]["stock"]]
    assert flagged == [d < until for d in s.index], "the hover text flags the wrong months as back-tested"
    assert tt["stock_back"] < tt["stock"] and tested.data[tt["economy"]].x == economy.x

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
          f"s({since}) = 0, e({since}) = 0.")
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
    fast = SPEEDS[1]
    print(f"  playback, in seconds at 1x ({fast}x): opening card {opening:.1f} ({opening / fast:.1f}); "
          + "; ".join(f"act {a['numeral']} {d:.1f} ({d / fast:.1f})" for a, d in zip(acts, durations))
          + f"; each of the {len(acts) - 1} act breaks {transition:.1f} ({transition / fast:.1f}); "
          f"closing chords {flourish:.1f} ({flourish / fast:.1f}); in all {total:.1f} ({total / fast:.1f}).")
    print("  base speeds, in years a second: " + ", ".join(f"act {a['numeral']} {b:.2f}" for a, b in zip(acts, bases))
          + "; cards up for " + ", ".join(f"{b['seconds']:.2f}" for b in beats) + " s.")
    print(f"  rates since {since} ({span_years:.3f} years): " + "; ".join(c["text"] for c in chords) + ".")
    print(f"  anchor as a parameter: rebuilt at {since2} and every dependent element followed "
          f"(rates there: {'; '.join(c['text'] for c in am['chords'])}).")
    print(f"  derived file: {gdp.shape[1]} GDP entities; page HTML {len(html) / 1024:.0f} KB.")

    end_g, end_e, end_s = g.iloc[-1], e.iloc[-1], s.iloc[-1]
    level = gdp["CHN"].dropna().iloc[-1]             # NOT re-based: China's level against America's
    low = s.idxmin()
    print("\n  For the caption (changes in bits, multiple in brackets):")
    print(f"  economy, {GDP_ANCHOR_YEAR} to {g.index[-1].year}:        {end_g:+.3f} (×{2 ** end_g:.1f})")
    print(f"  economy, {since} to {_month(cutoff)}: {end_e:+.3f} (×{2 ** end_e:.2f})")
    print(f"  stocks,  {since} to {_month(cutoff)}: {end_s:+.3f} (×{2 ** end_s:.2f})")
    print(f"  shortfall at {_month(cutoff)}:         {end_e - end_s:+.3f} (×{2 ** (end_e - end_s):.2f})")
    print(f"  level, {g.index[-1].year} (China ÷ US):     {level:+.3f} (×{2 ** level:.3f})")
    print(f"  stocks, lowest in the window: {_month(low)}, {s[low]:+.3f} (×{2 ** s[low]:.2f})")


if __name__ == "__main__":
    _run_checks()
