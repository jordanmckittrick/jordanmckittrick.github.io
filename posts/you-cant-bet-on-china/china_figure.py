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

Animation. The default state is the finished chart, with what closes the
animation on it. Playback is a play in three parts (``PART_TITLES``; "acts" in
the code). Each has a fixed x-axis: the first two run from the start of the
plot to the part's own end, so the stage widens at the first break; the last is
framed more closely, on the years in which there is something to invest in,
and at the very end the view pulls back to the whole chart. Nothing but the
data moves within a part. A break brings playback to rest, dims the figure
behind the next part's title card ("PART II · 1978–1992" over its title), moves
the axis and starts again. Before the break after Part II, playback rests at
its end while an arrow is drawn up the economy's line from its 1978 level and
a box says what it measures.

Narration and tempo. The pace within a part comes from BEATS, set in the data
(:func:`act_schedule`). Every labelled event is a gentle one: playback dips a
little, briefly, as it passes. A TEXT BOX (a bold date and a sentence or two)
slows playback right down for as long as it takes to read (``BOX_SECONDS``: so
much, plus so much a word), and a PICTURE CARD (a box with an image) slower
still, for longer; a click dismisses either. A box comes up as the playhead
reaches its date, never more than ``SYNC_DAYS`` from it: where dates crowd
together, the boxes before run slower, or a box waits for the one before it to
go. Playback is never slow without a box up to explain it (``SLOW_LIMIT``),
and :func:`pacing_chart` draws the whole tempo for review. A box stands in the
empty space nearest the playhead, clear of the playhead, the data and every
label (on a phone, where the plot is too small for that, directly under the
plot). Every number a box quotes is computed from the data
(:func:`narration_numbers`), never typed in. A box that quotes a rate comes
up as the playhead reaches the last point of the span it is over, and a RATE
ARROW draws itself over that span, tail to head (with an earlier span's
arrow, faint, beside it where a comparison is the point); its numbers are
computed too (:func:`rate_arrow`). Two of the arrowed annotations are beats of
their own: playback slows as the playhead reaches each point, and the point
pulses once. The next labelled event in each strip waits as a GHOST, faint
and already in place, and a thin playhead with a pill marks the date: the
year, and while a box is up the month and the year. Playback starts at 1.5x
(``DEFAULT_SPEED``); the toggle cycles through ``SPEEDS``.

The ending, in the bottom panel: a dashed CHORD is drawn from the anchor to
each series' last point, and the average rate it stands for (the final value
in bits over the years since the anchor) appears at its end, in the gutter
right of the plot; then an arrow measures the gap between the two ends; then
a last box says it in words. All but the box stay on the finished chart.

Controls. A play button, a 1x / 2x speed toggle and a native range input (not
Plotly's slider, whose handle sticks in a drag state) drive it; the scrubber's
position is the date, linearly, and is marked off in parts, each under its
title. The browser draws
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
Python, so an interpolated animation point can never produce a label: the date
as a heading, then each series' change compared to its own anchor, in bits and
as a multiple. It also describes whatever event, era, leader or band the cursor
is on, each text led by its date in bold; and picks the event out on the chart
(a labelled event's line solid and dark, its label bold; a tick taller and
darker).

The plot background is transparent and the ink and the navy are re-read from the
page, so the figure follows the site's dark mode (with a lighter navy there).

Run the checks with ``uv run python china_figure.py``; the browser-side audit
(one scale, strip heights, text collisions at rest and at every stage of the
play, one x-range per part, one ghost per strip, title cards, every box and
picture card in its place (its own panel) and on its date, the pill, the
anchors' markers, the rate arrows and the annotation beats, the ending step by step, arrow tips, labels that stay put, hover
and its highlight) runs when the page URL carries ``?china-audit``, at whatever
width the page has.

House style, for every string a reader sees: American spelling and American
dates; "Part", not "Act"; every hover text led by a bold date and a colon.
``_run_checks`` scans for British spellings.
"""

from __future__ import annotations

import base64
import io
import re
import warnings
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
# The strings the figure composes with numbers in them, as templates ({name}: a computed value), and
# the panels' names. Everything a reader sees is a literal in this module, so that
# china_figure_copy.xlsx (export_copy) can list it and apply_copy.py can rewrite it.
COPY_TEXT = dict(
    panel_economy="Economy",
    panel_stocks="Stocks",
    kicker="Part {numeral} · {start_year}–{end_year}",
    hover_economy_1978="Economy compared to {anchor_year}: {change}",
    hover_stocks="Stocks compared to {since}: {change}",
    hover_economy="Economy compared to {since}: {change}",
    anchor="{anchor} = 0",
    zero_key="Zero line: above it Chinese stocks are ahead since {since}, below it American ones.",
    chord_rate="{rate} bits/yr (×{multiple}/yr)",
    # An era's chord in the top panel (ERA_CHORDS); without the multiple where it would read ×1.00.
    era_rate="{name}, {span}: {rate} bits/yr (×{multiple}/yr)",
    era_rate_flat="{name}, {span}: {rate} bits/yr",
    climb="{bits} bits since {anchor_year} (×{multiple})",
    chord_economy="Economy",
    chord_stocks="Stocks",
    gap="Gap: {gap_bits} bits (×{gap_multiple})",
)
# The three parts of the animation, as their title cards and the scrubber name them.
PART_TITLES = ["Mao's Mayhem", "“Seeking Truth from Facts”", "An Investable China"]
START_YEAR = 1960        # first GDP year drawn; playback starts here
SHOW_MULTIPLE = True     # hover: append the multiple 2^x after each value, e.g. "+2.31 bits (×4.96)"

# ---- Playback (tune these; _run_checks prints what they add up to). Every duration is at 1x. ----
SPEEDS = (1, 1.5, 2)             # what the speed toggle steps through ...
DEFAULT_SPEED = 1.5              # ... and where it starts
EVENT_SLOWDOWN = 0.7             # passing a labelled event, the speed dips to this share of its act's base speed ...
EVENT_WINDOW_YEARS = 0.25        # ... eased down and back up over this long either side of the event
BOX_SLOWDOWN = 0.2               # while a text box is up, playback runs at this share of base speed ...
BOX_SECONDS = (1.2, 0.27)        # ... for this long: so much, plus so much a word (a beat may trim it: Beat.trim)
PICTURE_SLOWDOWN = 0.1           # a picture card: slower ...
PICTURE_SECONDS = (2.2, 0.27)    # ... and longer
LAST_BOX_EXTRA = 0.5             # the box that closes the ending stays up this much longer than its words need
SYNC_DAYS = 45                   # a box comes up at its date, and never more than this many days from it:
CROWD_SHARE = 0.05               # boxes whose dates crowd together run slower to keep to their dates, down to this
                                 # share; past that a box waits for the one before it (no more than SYNC_DAYS) ...
MIN_SHARE = 0.003                # ... and the boxes before it slow on down to this share (all but a stop)
MAX_BASE = 1.3                   # the fastest a part's base speed may be, in years a second
BOX_RAMP_YEARS = 0.3             # the easing into and out of a box's slow stretch, in years of travel
STOP_YEARS = 0.6                 # an act starts from rest, and comes to rest, over this long
SLOW_LIMIT = (0.6, 1.5)          # the tempo rule: never under this share of base speed for longer than this (s) with no box up
# An act break, step by step: the title card and its scrim come up, hold, the x-axis moves to the
# next act's range, the next ghosts appear, the card goes.
TRANSITION = dict(card_in=0.7, hold=2.0, move=1.1, ghost=0.4, card_out=0.6)
# The ending. When the data ends the view pulls back to the whole chart, and the rest happens there,
# so that the finished chart is what the reader last saw. In the top panel, the chord across each
# era (ERA_CHORDS) is drawn in turn, then its rate fades in, then a short beat (half a pause); the
# arrow from the 1978 level up to the line's last point, its label, a pause. Then in the bottom
# panel each chord, its rate, a pause; the gap's arrow, its label; the last box holds (for its
# reading time, ``LAST_BOX_EXTRA`` included).
ENDING = dict(chord=1.4, label=0.4, pause=0.8, arrow=0.7, pullback=1.8)
# At the end of Part II, before its break: an arrow is drawn up the economy's line from its 1978
# level, and a box says what it measures.
INTERLUDE = dict(arrow=0.7, pause=0.3)
# A RATE ARROW, for a box that quotes a rate: drawn tail to head over ``draw`` seconds as the box
# comes up, ``lift`` px clear above the line, ``width`` px; a reference arrow (an earlier span, for
# comparison) at ``reference`` of the strength, its label at ``reference_label``.
RATE_ARROW = dict(draw=0.6, lift=7, width=1.5, reference=0.35, reference_label=0.6)
# The two annotations that are beats: playback slows to a text box's speed for this long as the
# playhead reaches each point, the annotation fades in, and the point pulses once (``pulse`` s).
NOTE_BEAT = dict(seconds=3.0, pulse=0.9)
GHOST_OPACITY = 0.3              # the next labelled event in each strip, until the playhead reaches it
REVEAL_SECONDS = 0.5             # how long a mark takes to come to full strength once reached
CARD_FADE_SECONDS = 0.4          # how long a box or card takes to fade in or out
SCRIM_OPACITY = 0.62             # how far the figure is dimmed behind an act's title card
WINDOW_MARGIN = 0.02             # room right of an act's end, as a fraction of its x-range
PICTURE_MAX_PX = 600             # a picture is embedded no larger than this on its long side ...
PICTURE_QUALITY = 82             # ... as a JPEG of this quality (the files beside the module are left as they are)

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
BACKTEST_NOTE = "MSCI China was launched on October 31, 1995; earlier values are back-tested."
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
FINAL_EVENT_LINE_SHARE = 0.375   # on the finished chart, a labelled event's line at this share of that (hover: full)
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
_EXCHANGE_OPENS = "1990-12-19"          # the Shanghai Stock Exchange begins trading
_SHENZHEN_OPENS = "1991-07-03"          # the Shenzhen Stock Exchange opens formally (it had traded since December 1990)


@dataclass(frozen=True)
class Note:
    """A dated line in the hover text of the event or era it is attached to. No mark of its own.

    ``date`` (ISO) puts the notes of one parent in order; ``when`` is how the
    date reads in the hover box, in bold ("Jul 1977", "Jan 1, 1979", "1966–67");
    ``text`` is the line.
    """
    date: str
    when: str
    text: str


@dataclass(frozen=True)
class Event:
    """A point in time, shown according to its ``tier``.

    HOUSE STYLE, for every string a reader sees: American spelling; American
    dates ("May 16, 1966" in prose, "Dec 1990" in a short label). Every hover
    text (an event's, a note's, an era's, a leader's, a band's) opens with a
    bold lead, a date or a range of dates, then a colon: ``**Dec 19,
    1990**: ...``. ``**`` marks bold.

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
    #      this order; dropped from the end (Bombard the Headquarters first). ----
    Event("1972-02-21", "Nixon in Beijing",
          ("**Feb 21, 1972**: Richard Nixon arrives in Beijing, the first visit to the PRC by an American "
           "president, laying the groundwork for the eventual complete normalization of diplomatic ties in "
           "1979."), "label", "economy"),
    Event("1978-12-18", "“Reform and opening up”",
          ("**Dec 18–22, 1978**: Deng Xiaoping launches his campaign of “reform and opening up” at the Third "
           "Plenum of the 11th Central Committee."), "label", "economy"),
    Event("1989-06-04", "Tiananmen",
          ("**Jun 4, 1989**: the army clears the Tiananmen Square protests by force. The next day “Tank Man” "
           "stares down a column of tanks."), "label", "economy"),
    Event("1992-01-18", "Southern Tour",
          ("**Jan 18 – Feb 21, 1992**: Deng Xiaoping tours the south, and economic reform regains its "
           "momentum. Deng's political influence remains decisive; conservatives retreat."),
          "label", "economy"),
    Event("2001-12-11", "Joins WTO",
          "**Dec 11, 2001**: China joins the World Trade Organization.", "label", "economy"),
    # UNSURE of one name in the text, which is as given to me. On August 26, 1980
    # the National People's Congress Standing Committee approved the regulations
    # for the zones in Guangdong: Shenzhen, Zhuhai and Shantou. Xiamen's zone, in
    # Fujian, was approved by the State Council in October 1980.
    Event("1980-08-26", "Special economic zones",
          ("**Aug 1980**: Special Economic Zones (SEZs) — special coastal enclaves with lower taxes, lighter "
           "regulations, and stronger property rights protections — are established to experiment with "
           "free-market reforms while insulating the rest of China from potential upheaval."),
          "label", "economy", short="SEZs"),
    # UNSURE: two dates, one line. The IMF's board recognized the People's
    # Republic as China's representative on April 17, 1980 and the World Bank's
    # followed on May 15, 1980 (both days are from memory); the line is drawn at
    # the first.
    Event("1980-04-17", "Joins World Bank, IMF",
          ("**Apr–May 1980**: the PRC takes China's seat at the International Monetary Fund and the World "
           "Bank, displacing Taiwan."), "label", "economy"),
    Event("1976-09-09", "Mao dies", ("**Sep 9, 1976**: Mao Zedong dies, leaving the relatively weak Hua "
                                     "Guofeng as his chosen successor."), "label", "economy"),
    Event("1966-05-16", "May 16 Notification",
          ("**May 16, 1966**: the Party circulates the “May 16 Notification,” launching the Cultural "
           "Revolution."), "label", "economy"),
    # The Seven Thousand Cadres Conference, January 11 - February 7, 1962.
    Event("1962-01-11", "7,000 Cadres Conference",
          ("**Jan 11 – Feb 7, 1962**: some 7,000 CCP officials gather in Beijing to assess the impact of the "
           "Great Leap Forward."), "label", "economy"),
    # UNSURE of the day: I have September 22 - October 12, 1980 for Friedman's first visit.
    Event("1980-09-22", "Friedman visits",
          ("**Sep 1980**: As part of its efforts to successfully liberalize its economy, China invites "
           "Milton Friedman to give a series of lectures on free markets, deregulation, and the price "
           "mechanism."), "label", "economy"),
    # UNSURE of the day, which I chose: August 16, 2010 is when Japan's second-quarter
    # figures showed its output below China's (the full-year figures followed in
    # February 2011). The share per person is computed (narration_numbers).
    Event("2010-08-16", "Overtakes Japan",
          "**2010**: China's total output passes Japan's, though on a per capita basis it remains far behind.", "label", "economy"),
    Event("2008-11-09", "¥4 trillion stimulus",
          "**Nov 9, 2008**: China floods the economy with a massive stimulus package worth ¥4 trillion.",
          "label", "economy"),
    Event("1997-07-01", "Hong Kong handover",
          "**Jul 1, 1997**: Britain formally cedes Hong Kong to China.", "label", "economy"),
    Event("1994-01-01", "Currency unification",
          ("**Jan 1, 1994**: China eliminates its two-tier currency system, streamlining foreign direct "
           "investment."), "label", "economy"),
    # UNSURE of the day, and of the label: December 9, 2021 is when Fitch declared
    # Evergrande in "restricted default"; it had been missing payments since
    # September, and "property crisis" names something that has no single date.
    Event("2021-12-09", "Property crisis",
          ("**Dec 9, 2021**: Fitch declares the massive Chinese property developer Evergrande to be in "
           "default, the emblem of a crisis in the wider property market, which had been fueled by easy "
           "credit and rampant speculation."), "label", "economy"),
    # The lowest priority: the first to go wherever the strip is short of room.
    Event("1966-08-05", "“Bombard the Headquarters”",
          ("**Aug 5, 1966**: Mao writes his big-character poster “Bombard the Headquarters,” aimed at the "
           "“bourgeois dictatorship,” an implicit though unmistakable attack on Liu and Deng."), "label", "economy"),

    # ---- Economy, ticks ----
    Event("2008-08-08", "Beijing Olympics", "**Aug 8–24, 2008**: Beijing hosts the Summer Olympics.", "tick", "economy"),

    # ---- Stocks, labelled: drawn above and through the bottom panel. Dropped
    #      from the end (Exchanges open first). ----
    # UNSURE of the day: February 21, 1992 for the first B-share listing in
    # Shanghai (Shanghai Vacuum Electron Devices). February 1992 is solid.
    Event("1992-02-21", "First B-shares",
          ("**Feb 1992**: the first B-shares list in Shanghai. In contrast to A-shares, B-shares are open to "
           "foreign capital."),
          "label", "stocks"),
    # UNSURE which date is meant: the QFII rules were issued in early November
    # 2002 and took effect on December 1, 2002; the first QFII trade was in July
    # 2003. This uses the effective date.
    Event("2002-12-01", "QFII",
          ("**Dec 1, 2002**: the Qualified Foreign Institutional Investor (QFII) program is launched, "
           "allowing certain foreign institutions to participate in the A-share market."), "label", "stocks",
          notes=(Note("2019-09-10", "Sep 2019", "QFII and Renminbi QFII (RQFII) quota limits abolished."),)),
    Event("2008-09-15", "Financial crisis",
          "**Sep 15, 2008**: Lehman Brothers files for bankruptcy and the global financial crisis enters its most "
          "acute phase.", "label", "stocks"),
    Event("2014-11-17", "Stock Connect",
          ("**Nov 2014**: Stock Connect, a link between mainland and Hong Kong stock exchanges, is created, "
           "significantly opening mainland China to foreign capital."), "label", "stocks",
          notes=(
              Note("2014-11-17", "Nov 17, 2014", "Shanghai–Hong Kong link opens."),
              Note("2016-12-05", "Dec 5, 2016", "Shenzhen–Hong Kong link opens."),
          )),
    # A choice: the Shanghai Composite's peak. The fall began the next trading
    # day; the other candidate is "Black Monday", August 24, 2015.
    Event("2015-06-12", "Crash",
          "**Jun 12, 2015**: the Shanghai Composite peaks, losing about a third of its value within a month.",
          "label", "stocks"),
    # These two share one label: five weeks apart, they stand about a pixel apart.
    Event("2018-06-01", "A-shares join MSCI",
          ("**Jun 2018**: MSCI incorporates a small amount of mainland-listed A-shares into its index, "
           "eventually reaching 20% by Nov 2019, fundamentally altering what the index measures."),
          "label", "stocks", group="2018"),
    Event("2018-07-06", "US tariffs",
          "**Jul 6, 2018**: the first of President Trump's tariffs take effect. China answers in kind.", "label", "stocks", group="2018"),
    # Re-dated from the Didi review (July 2, 2021) to the start of the crackdown.
    # The Ant listing had been due on November 5, 2020.
    Event("2020-11-03", "Chinese tech crackdown",
          ("**Nov 3, 2020**: In an apparent retaliation against Jack Ma's public criticism of Chinese "
           "regulators, Ant Group's initial public offering (IPO) is suspended just days before listing. The crackdown spreads to "
           "tech, tutoring and property firms."), "label", "stocks"),
    # UNSURE of the day: September 24, 2024 for the central bank's announcement
    # (the Politburo followed two days later). September 2024 is solid.
    Event("2024-09-24", "Stimulus rally",
          ("**Sep 2024**: after years of economic malaise wrought by the ongoing crisis in the property "
           "market, the People's Bank of China unveils an aggressive stimulus package that sparks a sharp "
           "rally in Chinese equities."),
          "label", "stocks"),
    Event("1993-07-15", "First H-shares",
          ("**Jul 15, 1993**: Tsingtao Brewery lists in Hong Kong, the first mainland company to issue "
           "H-shares, opening the way for foreign investment."),
          "label", "stocks"),
    # One label for both exchanges, at Shanghai's opening (the start of the plain band).
    Event(_EXCHANGE_OPENS, "Exchanges open",
          f"**{{exchange_day}}**: the Shanghai Stock Exchange opens. **{{shenzhen_day}}**: the Shenzhen Stock "
          f"Exchange formally opens.", "label", "stocks"),

    # ---- Stocks, ticks ----
    Event("2005-07-21", "Renminbi de-pegged",
          ("**Jul 21, 2005**: the renminbi's fixed peg to the US dollar ends, allowing for managed "
           "appreciation to follow."), "tick", "stocks"),
    # China Construction Bank listed on October 27, 2005 and Bank of China on June 1, 2006.
    Event("2006-10-27", "ICBC IPO",
          ("**Oct 27, 2006**: the Industrial and Commercial Bank of China (ICBC) lists in Hong Kong, then "
           "the largest initial public offering (IPO) ever. With China Construction Bank (Oct 2005) and Bank of China (Jun 2006) "
           "before it, the big banks reshape MSCI China."), "tick", "stocks"),
    # Effective at the close of November 30, 2015; the second half on May 31, 2016.
    Event("2015-11-30", "Chinese ADRs join MSCI",
          ("**Nov 2015**: MSCI China begins including US-listed Chinese companies (American depositary "
           "receipts, ADRs), e.g. Alibaba. This changes what the index measures."), "tick", "stocks"),

    # ---- Stored: not drawn ----
    Event("1971-10-25", "UN seat",
          "**Oct 25, 1971**: the United Nations General Assembly seats the People's Republic as China's "
          "representative.", "stored", "economy"),
    # A date only: this text must not say it caused anything.
    Event("2022-11-30", "ChatGPT launches", "**Nov 30, 2022**: OpenAI releases ChatGPT.", "stored", "stocks"),
]
# Capitalised words that may follow the first word of a label written in
# sentence case: proper nouns and initialisms. _run_checks holds labels to it.
_PROPER = {"Beijing", "World", "Bank", "IMF", "WTO", "Tour", "Hong", "Kong", "B-shares", "H-shares", "A-shares",
           "Connect", "US", "Revolution", "UN", "MSCI", "Dec", "Chinese", "IPO", "ADRs", "SEZs", "Japan", "Olympics",
           "Cadres", "Conference", "Notification", "Headquarters"}
# All-capitals words that are names in their own right and need no spelling out
# in hover text. Every other one must be spelled out where it appears.
_NAMES = {"US", "MSCI", "COVID", "JD", "PRC", "CCP"}        # JD: the company JD.com


@dataclass(frozen=True)
class Leader:
    """A paramount leader: one segment of the continuous row above the eras.

    ``end`` None means "still in office when the plot ends". The label goes
    inside the segment, left-aligned, wherever the segment is long enough to
    hold it (a short one, like Hua's, holds it only just); a segment too short
    for its name in some view has hover text only there. ``description`` is the
    segment's hover text, which says what the dates of that leader mean.
    """
    start: str
    end: str | None
    label: str
    description: str


# UNSURE: every boundary here is a convention rather than a fact. Mao died on
# 9 September 1976 and Hua became chairman on 7 October (the four weeks between
# are left blank). Hua's end and Deng's start are both put at the close of the
# Third Plenum, 22 December 1978, though Hua kept his titles until 1980-81.
# From Jiang on, the dates are those of the general-secretaryship. Each hover
# text is as given to me.
LEADERS = [
    Leader("1949-10-01", "1976-09-09", "Mao", "**Oct 1949 – Sep 1976**: Mao Zedong, Party chairman until his death."),
    Leader("1976-10-07", "1978-12-22", "Hua",
           ("**Oct 1976 – Dec 1978**: Hua Guofeng, Mao's chosen successor; swiftly sidelined by Deng by Dec "
            "1978.")),
    Leader("1978-12-22", "1989-06-24", "Deng",
           ("**Dec 1978 – Jun 1989**: Though he never officially holds the top post, Deng Xiaoping is the de "
            "facto paramount leader of China; retired 1989–90 but decisive until about 1992, the year of his "
            "Southern Tour.")),
    Leader("1989-06-24", "2002-11-15", "Jiang", ("**Jun 1989 – Nov 2002**: Jiang Zemin, Party general "
                                                 "secretary. As paramount leader, Jiang broadly continues "
                                                 "Deng's reformist, market-oriented policies.")),
    Leader("2002-11-15", "2012-11-15", "Hu", "**Nov 2002 – Nov 2012**: Hu Jintao, Party general secretary."),
    Leader("2012-11-15", None, "Xi", "**Nov 2012 – present**: Xi Jinping, Party general secretary."),
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
    Era("1959-01-01", "1961-12-31", "Famine", "**1959–61**: the Great Chinese Famine."),
    Era("1966-05-16", "1976-10-06", "Cultural Revolution",
        ("**May 16, 1966 – Oct 6, 1976**: the Cultural Revolution, lasting from the “May 16 Notification” "
         "till Hua's arrest of the Gang of Four.")),
    # UNSURE, INTERPRETIVE: there is no agreed start or end. The start is the
    # Third Plenum of the 13th Central Committee (26-30 September 1988), which
    # launched the austerity programme; the end is put at the close of 1991,
    # just before the Southern Tour.
    Era("1988-09-26", "1991-12-31", "Retrenchment",
        ("**1989–91**: Credit is tightened and Party conservatives attempt to roll back Deng's market "
         "reforms after the 1988 inflation and the 1989 protests."),
        drop_first=True),
    # UNSURE, INTERPRETIVE: whole calendar years, from the first year of WTO
    # membership to the last year before the global financial crisis.
    Era("2002-01-01", "2007-12-31", "WTO export boom",
        "**About 2002–07**: exports surge in the years after China joins the World Trade Organization (WTO).",
        drop_first=True),
    # UNSURE of both days: 23 January 2020 is the lockdown of Wuhan and
    # 7 December 2022 the "ten new measures" that ended most controls.
    Era("2020-01-23", "2022-12-07", "Zero-COVID",
        ("**Jan 2020 – Dec 2022**: from the initial lockdown of Wuhan to the lifting of most zero-COVID "
         "controls.")),
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


BANDS = [
    Band(None, _EXCHANGE_OPENS, "none",
         ("No stock exchange", "No stock<br>exchange"),
         "**Before Dec 19, 1990**: mainland China has no stock exchange.",
         y=0.56),
    Band(_EXCHANGE_OPENS, None, "limited",
         ("Exchanges open, mostly closed to foreigners", "Exchanges open,<br>mostly closed to foreigners",
          "Exchanges open,<br>mostly closed<br>to foreigners", "Exchanges<br>open, mostly<br>closed to<br>foreigners"),
         ("**From Feb 1992**: a small B-share market opens for foreign investors. **From Jul 1993**: "
          "B-shares fail to attract much foreign capital, so H-shares list in Hong Kong as an alternative. "
          "A-shares remain forbidden to foreigners."),
         y=0.76,
         # Ends where the "First B-shares" event stands.
         early_end="1992-02-21",
         early_description=("**Dec 1990 – Feb 1992**: Only A-shares trade on the stock exchanges, so "
                            "foreigners are unable to invest.")),
]


@dataclass(frozen=True)
class Act:
    """One part of the animation (an "act" in the code). Each starts where the one before it ends; the first, with the data.

    Readers see "Part": the title card's overline reads "PART II · 1978–1992",
    and the scrubber shows the titles alone (``PART_TITLES``, quotation marks
    and all). Within a part the x-axis is fixed: from ``view_from`` (the start
    of the plot, if None) to the part's end, plus a little room. ``seconds``
    is how long the part should play at 1x, the breaks apart: its base speed
    is whatever makes its beats add up to that, up to ``MAX_BASE``
    (:func:`act_schedule`). ``panel`` is where its boxes go unless a beat
    says otherwise.
    """
    numeral: str
    title: str
    short: str               # for a scrubber segment too narrow for the title
    end: str | None          # None: the end of the data
    seconds: float
    panel: str = "economy"
    view_from: str | None = None


ACTS = [
    Act("I", PART_TITLES[0], "Mao", "1978-12-18", 55.0),
    Act("II", PART_TITLES[1], "Deng", "1992-02-21", 70.0),
    # Framed on the years in which there is something to invest in: from just
    # before the Shanghai exchange opens (the start of the plain access band).
    Act("III", PART_TITLES[2], "Investable", None, 73.0, panel="stocks", view_from="1990-07-01"),
]


@dataclass(frozen=True)
class Picture:
    """An image for a picture card. ``file`` sits beside this module, next to the post's ``.qmd``.

    If the file is missing, or has no ``credit`` yet, the card is a text box
    (with a warning). ``credit`` is the full credit, for the caption
    (:func:`picture_credits`); ``short`` is what the card itself shows, in
    small type. ``max_px`` caps the picture's size (its long side) below what
    the layout would offer. ``room`` is the most its card's words may run to
    (lead and text, in characters) and still leave the picture a place at the
    full 920 px column: measured in the page (``?china-debug``,
    ``__CHINA__.pictureRoom(i)``) and used by apply_copy.py to refuse a rewrite
    that would cost a card its picture. The page carries the image itself (:func:`picture_data`), so
    nothing has to be published alongside it.
    """
    file: str
    credit: str | None
    short: str | None
    max_px: int | None = None     # the largest the picture may be shown, on its long side (None: as the layout allows)
    room: int | None = None       # how many characters of lead and text its card holds at 920 px, as measured


PICTURES = dict(
    cr_1966=Picture(
        "cr_1966.jpg",
        "Shanghai People's Fine Arts Publishing House Propaganda Poster Group, 以毛泽东思想为武器批判旧世界建设新世界 "
        "[Criticize the old world and build a new world with Mao Zedong Thought as a weapon], 1966. "
        "IISH, BG E15/699. Image: chineseposters.net.",
        "IISH / chineseposters.net", room=600),
    # From the file's page on Wikimedia Commons: the signing ceremony of January 31, 1979, by Karl H.
    # Schumacher (National Archives NAID 183286). (The brief had the arrival ceremony of January 29.)
    deng_carter_1979=Picture(
        "deng_carter_1979.jpg",
        "Deng Xiaoping and Jimmy Carter, Sino-American signing ceremony, Jan 31, 1979. Photo: Karl H. Schumacher, "
        "White House Photographic Office. Public domain, via the U.S. National Archives (NAID 183286) and Wikimedia "
        "Commons (https://commons.wikimedia.org/wiki/File:Carter_DengXiaoping.jpg)",
        "Photo: White House / public domain", room=484),
    time_1985=Picture("time_1985.jpg", "TIME, cover, Jan 6, 1986.", "TIME, cover, Jan 6, 1986", room=368),
    hkex_2007=Picture(
        "hkex_2007.jpg",
        "Hong Kong Stock Exchange trading hall, Feb 21, 2007. Photo: WiNG, CC BY-SA 3.0 "
        "(https://creativecommons.org/licenses/by-sa/3.0/), via Wikimedia Commons "
        "(https://commons.wikimedia.org/wiki/File:Hong_Kong_Exchange_Trade_Lobby_2007.jpg)",
        "Photo: WiNG, CC BY-SA 3.0", room=600),
    # From the file's page on Wikimedia Commons: Davos, January 24, 2018; licensed CC BY 2.0 (not
    # BY-NC-SA, as the brief had it). The file there is a crop of the Flickr original, hence "cropped".
    jack_ma=Picture(
        "jack_ma.jpg",
        "Jack Ma, World Economic Forum Annual Meeting, Davos, 2018. Photo: World Economic Forum / Ciaran McCrickard, "
        "CC BY 2.0 (https://creativecommons.org/licenses/by/2.0/), via Flickr "
        "(https://flickr.com/photos/49344088@N04/39008130265); cropped",
        # (At 920 px there is room for it in the top panel only at 150 px tall, with about 100
        # characters of words, its lead included.)
        "Photo: World Economic Forum, CC BY 2.0", max_px=150, room=100),
)


@dataclass(frozen=True)
class Beat:
    """A moment of narration: a box that playback slows right down for.

    A TEXT BOX is a bold lead-in (``lead``) and a sentence or two (``text``). A
    PICTURE CARD is one with a ``picture`` (a key of ``PICTURES``), for which
    playback all but stops. ``date`` is where the playhead is when the box
    comes up: always within ``SYNC_DAYS`` of it (boxes whose dates crowd
    together run slower to keep it so). ``after`` dates a beat from the data
    instead ("trough": a month after the stock ratio's early low). ``panel``
    says which panel the box goes in: its part's, unless it says otherwise
    (economy boxes in the top panel, market boxes in the bottom one; the other
    panel only if there is no room). ``event`` picks a labelled event out while
    the box is up, and ``trim`` takes seconds off (or adds them to) its reading
    time. ``cross`` lets its box run from one panel into the other in its own
    panel's turn.

    RATE ARROWS. A box that quotes a rate has ``rate``, the span of the
    economy's annual points it is over (first year, last year): an arrow is
    drawn over the span as the box comes up, and the box's ``date`` is the
    span's last point (Jul 1 of its last year), so that both come up as the
    playhead reaches it. ``reference`` is an earlier span, drawn faint beside
    it for comparison; ``rate_note`` is a sentence added to the arrow's hover
    text. The rates and their hover text are computed (:func:`rate_arrow`).

    NUMBERS. A number that comes from the figure's data is never typed into
    ``lead`` or ``text``: it is a ``{placeholder}``, filled in by
    :func:`narration_numbers`, and ``_run_checks`` asserts each one. What is
    typed is history that the data cannot know (7,000 officials, Deng's age).
    Every labelled event is a gentler beat of its own; those are not listed.
    """
    date: str | None
    lead: str
    text: str
    picture: str | None = None
    panel: str | None = None
    event: str | None = None
    after: str | None = None
    rate: tuple[int, int] | None = None
    reference: tuple[int, int] | None = None
    rate_note: str | None = None
    trim: float = 0.0
    cross: bool = False


# The spans of years that the narration's own-growth numbers are taken over.
NARRATION_SPANS = dict(famine=(1960, 1962), factions=(1966, 1968), rebound=(1968, 1970), y1976=(1975, 1976),
                       since_reform=(1978, 1985), austerity=(1988, 1990), fdi=(1993, 1997))

BEATS = [
    # ---- Part I ----
    Beat("1961-06-30", "1959–61",
         "The Great Chinese Famine. 15–45 million people die."),
    Beat("1962-01-30", "Jan–Feb 1962",
         ("At the 7,000 Cadres Conference, Liu Shaoqi blames the famine primarily on bad policy. Mao makes a "
          "rare self-criticism and cedes power over the economy to Liu and Deng Xiaoping.")),
    Beat("1965-07-01", "1962–65",
         "Liu and Deng steer a recovery with pragmatic policies and greater market influences.",
         rate=(1962, 1965)),
    Beat("1966-05-16", "May 16, 1966",
         ("The “May 16 Notification” launches the Cultural Revolution. The text at the bottom of the poster "
          "says, “Use Mao Zedong Thought as a weapon!”"),
         picture="cr_1966"),
    Beat("1968-07-01", "1966–68",
         ("Mao's “Bombard the Headquarters” poster targets pragmatists; Liu and Deng arrested; Red Guards "
          "attack “bourgeois elements.”"), rate=(1966, 1968)),
    Beat("1970-07-01", "1968–70",
         "The PLA restores order. Output per person rebounds {rebound_rise}%.", rate=(1968, 1970)),
    Beat("1977-07-01", "1976–77",
         ("Mao dies; Hua arrests the Gang of Four, the Cultural Revolution's radical leaders; Deng "
          "rehabilitated.")),
    # ---- Part II ----
    Beat("1978-12-22", "Dec 1978",
         "At the Third Plenum, Deng emerges as paramount leader of China.", trim=-1.0),
    Beat("1979-01-15", "1979–84",
         "Beijing implements the Household Responsibility System, ending the communes."),
    # Deng at the rodeo in Simonton, Texas, February 2, 1979.
    Beat("1979-02-02", "1979",
         "Deng tours America; attends a rodeo. Coca-Cola begins selling in China.", picture="deng_carter_1979"),
    Beat("1980-08-26", "1980",
         "China joins the IMF and the World Bank; establishes special economic zones."),
    Beat("1985-12-30", "Dec 1985",
         "TIME names Deng its Man of the Year.", picture="time_1985"),
    Beat("1988-08-15", "1988",
         ("Deng pushes to rapidly free state-set prices; inflation nears 20%. The plan is replaced by "
          "gradual reform, spanning several years."), trim=-1.0),
    Beat("1989-05-15", "Spring 1989",
         ("Protests over inflation, corruption, and a lack of democracy erupt in Tiananmen Square; the army "
          "quashes them.")),
    Beat("1990-07-01", "1989–91",
         "Credit is tightened, and conservatives try to roll back market reforms.",
         rate=(1988, 1990), reference=(1978, 1988)),
    # A market box, in Part II: in the bottom panel.
    Beat(_EXCHANGE_OPENS, "{exchange_month}",
         ("Shanghai's stock exchange opens; Shenzhen's follows in {shenzhen_month}. Foreigners are unable to "
          "invest."), panel="stocks"),
    Beat("1992-01-18", "Jan–Feb 1992",
         "Deng embarks on his Southern Tour to advocate for continued market reforms."),
    # ---- Part III (market boxes in the bottom panel, economy boxes in the top one) ----
    # A week into the act: the listing itself (February 21) is the moment the act opens on.
    Beat("1992-02-28", "{bshares_month}",
         ("Foreigners can buy Chinese shares for the first time: B-shares. The market fails to attract "
          "significant foreign capital.")),
    Beat("1993-07-15", "{hshares_month}",
         "H-shares are launched at Hong Kong's far more open and internationally connected stock exchange.",
         event="First H-shares"),
    # It quotes a rate, so it has an arrow, and comes up at the span's end (the brief's table left it out).
    Beat("1997-07-01", "1993–97",
         "Foreign direct investment surges by nearly an order of magnitude.", panel="economy", rate=(1993, 1997)),
    Beat("1998-06-30", "1994–2003",
         ("Zhu Rongji, vice premier then premier, enacts sweeping market-oriented reforms, laying off tens "
          "of millions of state employees, and reinforcing Deng's vision of “reform and opening up.”"), panel="economy"),
    Beat(None, "{wto_month}",
         "China joins the WTO. {trough_lag} its stocks bottom: {trough_falls}.",
         after="trough"),
    Beat("2002-12-01", "{qfii_month}",
         "QFII allows foreigners to buy A-shares for the first time.", event="QFII"),
    Beat("2006-10-27", "2005–{peak_yy}",
         ("China's big state banks list in Hong Kong; ICBC's {icbc_year} IPO is then the world's largest. "
          "The boom peaks in {peak_month}."),
         picture="hkex_2007"),
    Beat("2012-07-01", "{hu_from}–{hu_to_yy}",
         ("China carries out further market-oriented reforms, gaining on America faster than ever: {hu_rate} "
          "bits a year (about {hu_pct}%)."), panel="economy", rate=(2002, 2012)),
    Beat("2018-06-01", "2014–18",
         ("Stock Connect allows anyone, including foreigners, with a Hong Kong brokerage account to buy "
          "mainland A-shares."),
         event="A-shares join MSCI"),
    Beat("2019-07-01", "{xi_from}–{xi_to_yy}",
         "Xi Jinping tightens the state's grip on the economy. China's catch-up with America {xi_change}.", panel="economy", rate=(2012, 2019),
         reference=(2002, 2012)),
    Beat("2020-11-03", "2020–21",
         "Jack Ma criticizes regulators; Beijing halts Ant's IPO and Ma vanishes for months.",
         picture="jack_ma", event="Chinese tech crackdown",
         # Tried first in the top panel, below the economy's line, where there is room near the playhead.
         panel="economy", cross=True),
]
# The two annotations that are beats of their own (NOTE_BEAT): the stocks falling behind the
# economy for good, and behind US stocks for good. The other two keep a labelled event's gentle dip.
NOTE_BEATS = ("arrow_economy", "arrow_parity")
# The year the comparison in the Xi box runs to: the year of that beat.
_XI_COMPARED_TO = 2019
# The part at whose end playback stops for the arrow up the economy's line and the box that says what it measures.
_INTERLUDE_ACT = 1
# How a share is put in words, by its denominator: "about a sixth".
_FRACTIONS = {2: "a half", 3: "a third", 4: "a quarter", 5: "a fifth", 6: "a sixth", 7: "a seventh", 8: "an eighth",
              9: "a ninth", 10: "a tenth"}
# The box at the end of Part II, with the arrow up the economy's line: computed at the playhead,
# which stands at the end of the part.
INTERLUDE_BOX = Beat(None, "{part2_from}–{part2_end_year}",
                     ("Against America, China's output per person has {part2_change}: {part2_bits} bits, "
                      "{part2_rate} bits a year."))
# The last box, which closes the ending. Every number in it is a placeholder.
FINAL_BOX = Beat(None, "{since} – {end_month}",
                 "Against America, China's economy {economy_verb} {economy_bits} bits; its stocks {stocks_verb} "
                 "{stocks_bits}. Stocks finished {gap_bits} bits, a factor of {gap_factor}, {gap_side} the economy.")


@dataclass(frozen=True)
class EraChord:
    """An era the ending's top-panel chords span: the economy's line from one point to another.

    ``name`` leads the chord's label ("Mao, 1960–78: …"). ``start`` and
    ``end`` are the years of the line's points it runs between (``end``
    None: the line's last point). ``hover`` is what the label says on
    hover, a template: ``{span}`` (the years, as "1960–78"), ``{china}``
    and ``{usa}`` (each one's output per person: its growth, % a year).
    """
    name: str
    start: int
    end: int | None
    hover: str


# The top panel's chords at the ending, in the order they are drawn. (The Mao hover's last sentence is
# typed: the checks assert China's output per person grew no faster than America's over the span.)
ERA_CHORDS = [
    EraChord("Mao", 1960, 1978,
             "**{span}**: China's output per person grew {china}% a year, America's {usa}%. Starting far poorer, "
             "China did not catch up at all."),
    EraChord("Deng to Hu", 1978, 2012, "**{span}**: {china}% a year against America's {usa}%."),
    EraChord("Xi", 2012, None, "**{span}**: {china}% a year against America's {usa}%."),
]
# How the fall of each market to the bottom is put, and what is said instead if
# the derived file has no MSCI USA return for the anchor in use.
_TROUGH_FALLS = "down {trough_china}% since {since}, against {trough_usa}% for US stocks through the dot-com bust"
_TROUGH_FALLS_UNKNOWN = "at ×{trough_x} of US stocks' value since {since}"
# A rate arrow's hover text (the change over its span), and its label: its rate, sign and all; a
# reference arrow's label says it is the rate before.
RATE_HOVER = "**{lead}**: Against America, output per person {verb} {change} bits."
RATE_LABEL = "{rate} bits/yr"
REFERENCE_LABEL = "({rate} before)"


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


def load_narration_data(path: str | Path = _DATA_PATH) -> tuple[pd.Series, dict]:
    """What the narration quotes that the two plotted ratios cannot give, in bits.

    Returns
    -------
    (usa, returns)
        ``usa``: ``log2`` of America's own GDP per capita by date (July 1 of
        each year), so that China's own level is its ratio plus this.
        ``returns``: MSCI USA's own ``log2`` return from a stock anchor to the
        month the stock ratio bottoms, keyed ``(anchor, bottom)``. The prep
        script writes one for each anchor the figure may be given, and nothing
        else of either index taken alone.
    """
    df = pd.read_csv(path, comment="#", parse_dates=["date"])
    usa = df[(df["series"] == "gdp_level") & (df["entity"] == "USA")].set_index("date")["log_ratio"] / _LN2
    usa.name = "usa"
    rows = df[df["series"] == "usa_return"]
    returns = {(pd.Timestamp(a), pd.Timestamp(d)): float(v) / _LN2
               for a, d, v in zip(rows["entity"], rows["date"], rows["log_ratio"])}
    return usa, returns


def derived_info(path: str | Path = _DATA_PATH) -> dict:
    """What the derived file says of itself in its header: key: value comment lines.

    stocks_variant is "net" or "gross" (the return variant of BOTH indexes:
    they are never mixed), stocks_start the first month-end of the stock
    series, and aggregates the World Bank's codes for its regions, income
    groups and the world (not countries). Written by prepare_china_figure_data.py.
    """
    info = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            key, colon, value = line[1:].partition(":")
            if colon and key.strip() in ("stocks_variant", "stocks_start", "aggregates"):
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


def catch_up_ranking(gdp: pd.DataFrame, start: int, end: int, aggregates=()) -> list[tuple[str, float]]:
    """Every country's gain on America from ``start`` to ``end``, in bits, largest first.

    ``gdp`` is :func:`load_derived`'s (each entity against America, in bits).
    A country counts if it has an observation in both years; the World Bank's
    aggregates (``aggregates``: regions, income groups, the world) are not
    countries and are left out.
    """
    a, b = (gdp[gdp.index.year == year].iloc[0] for year in (start, end))
    gain = (b - a).dropna().drop(labels=list(aggregates), errors="ignore")
    return sorted(((code, float(v)) for code, v in gain.items()), key=lambda kv: -kv[1])


def _day(when) -> str:
    """A day as a short label or a bold lead gives it: "Dec 19, 1990"."""
    when = pd.Timestamp(when)
    return f"{_MONTHS[when.month - 1]} {when.day}, {when.year}"


def _month_name(when) -> str:
    """A month as running prose gives it: "July 1991"."""
    when = pd.Timestamp(when)
    return f"{when:%B} {when.year}"


def _span(a: int, b: int) -> str:
    """Two years as a span, the second cut to its last two digits within a century: 1960–78, 1978–2012."""
    return f"{a}–{b % 100:02d}" if a // 100 == b // 100 else f"{a}–{b}"


def era_numbers(gdp: pd.DataFrame, usa: pd.Series) -> list[dict]:
    """The top panel's closing chords, one per ``ERA_CHORDS``, from the data.

    Each: the era; its first and last years and dates (the economy's July 1
    points); the line's value at each, in bits against America since 1978
    (as plotted); the chord's ``rate``, bits a year (the change over the
    years between); its ``multiple`` a year, ``2 ** rate``; and ``china`` and
    ``usa``, each one's own output per person, growth in % a year.
    """
    ratio = gdp["CHN"].dropna()
    point = {d.year: (d, float(v)) for d, v in ratio.items()}
    own = {d.year: float(v) for d, v in (gdp["CHN"] + usa).dropna().items()}
    us = {d.year: float(v) for d, v in usa.dropna().items()}
    base = point[GDP_ANCHOR_YEAR][1]
    out = []
    for era in ERA_CHORDS:
        a, b = era.start, era.end if era.end is not None else max(point)
        growth = lambda level: 100.0 * (2.0 ** ((level[b] - level[a]) / (b - a)) - 1.0)
        rate = (point[b][1] - point[a][1]) / (b - a)
        out.append(dict(era=era, start=a, end=b, t0=point[a][0], t1=point[b][0], y0=point[a][1] - base,
                        y1=point[b][1] - base, rate=rate, multiple=2.0 ** rate, china=growth(own), usa=growth(us),
                        span=_span(a, b)))
    return out


def narration_numbers(gdp: pd.DataFrame, usa: pd.Series, s: pd.Series, e: pd.Series,
                      anchor: pd.Timestamp, cutoff: pd.Timestamp, returns: dict) -> tuple[dict, dict]:
    """Every number the narration quotes, computed from the data and the parameters.

    Returns ``(words, values)``: ``words`` fills the ``{placeholders}`` in the
    beats' text and the events' hover text (each number as it is to be
    printed); ``values`` holds the same quantities unrounded, for
    ``_run_checks`` to assert.

    * Own growth. ``gdp`` holds China's GDP per capita against America's;
      adding America's own level (``usa``) gives China's own, and so how far
      its output per person fell or grew over each of ``NARRATION_SPANS``.
    * Catch-up. The rate at which the ratio itself rose, in bits a year: under
      a leader (from the leaders' own dates), in 1962-66, in 1993-97. And how
      China's gain on America since 1978 ranks among every country's.
    * The end of Part II: at the playhead there, the economy's change since
      1978 against America and in its own terms (the arrow up its line).
    * The bottom. How far each market had fallen, from the anchor to the stock
      ratio's early low: MSCI USA's fall is ``returns[(anchor, low)]`` and
      MSCI China's is that plus the ratio's. Without that number (an anchor the
      prep script did not write one for) the box gives the ratio alone.
    * Dates named in the text come from the events and leaders they name.
    * The ending: where the two lines finish, and the gap between them.
    """
    own = (gdp["CHN"] + usa).dropna()
    level = {d.year: float(v) for d, v in own.items()}                   # log2 of China's own GDP per capita
    ratio = {d.year: float(v) for d, v in gdp["CHN"].dropna().items()}   # log2 of China's against America's
    growth = lambda a, b: 100.0 * (2.0 ** ((level[b] - level[a]) / (b - a)) - 1.0)     # % a year, own
    catch_up = lambda a, b: (ratio[b] - ratio[a]) / (b - a)                             # bits a year
    event = lambda label: pd.Timestamp(next(ev.date for ev in EVENTS if ev.label == label))
    leader = lambda label: next(who for who in LEADERS if who.label == label)
    signed = lambda x, places: f"{'+' if round(x, places) >= 0 else '−'}{abs(x):.{places}f}"
    v, w = {}, {}

    for name in ("famine", "factions", "y1976"):
        a, b = NARRATION_SPANS[name]
        v[f"{name}_fall"] = 100.0 * (1.0 - 2.0 ** (level[b] - level[a]))
        w[f"{name}_fall"] = f"{v[f'{name}_fall']:.0f}"
    for name in ("rebound", "since_reform"):
        a, b = NARRATION_SPANS[name]
        v[f"{name}_rise"] = 100.0 * (2.0 ** (level[b] - level[a]) - 1.0)
        w[f"{name}_rise"] = f"{v[f'{name}_rise']:.0f}"
    w["famine_from"], w["famine_to"] = (str(y) for y in NARRATION_SPANS["famine"])
    w["reform_from"] = str(NARRATION_SPANS["since_reform"][0])
    v["austerity_growth"] = growth(*NARRATION_SPANS["austerity"])
    w["austerity_growth"] = f"{v['austerity_growth']:.1f}"

    # The climb of 1993-97. (Every rate a box quotes has an arrow, whose numbers are rate_arrow()'s.)
    v["fdi_rate"] = catch_up(*NARRATION_SPANS["fdi"])
    w["fdi_rate"] = f"{v['fdi_rate']:.2f}"

    # "The biggest catch-up with America in the World Bank's records": China's gain since 1978, against
    # every other country's with data in both years.
    aggregates = derived_info().get("aggregates", "").split()
    ranking = catch_up_ranking(gdp, GDP_ANCHOR_YEAR, max(ratio), aggregates)
    v["catch_up_ranking"] = ranking
    v["catch_up_rank"] = 1 + [code for code, _ in ranking].index("CHN")
    if v["catch_up_rank"] == 1:
        w["catch_up_claim"] = "the biggest catch-up with America in the World Bank's records"
    else:
        warnings.warn(f"China's gain on America since {GDP_ANCHOR_YEAR} ranks {v['catch_up_rank']}, not first: "
                      "the Dec 1978 box no longer says it is the biggest", stacklevel=2)
        w["catch_up_claim"] = "one of the biggest catch-ups with America in the World Bank's records"

    # Overtaking Japan: China's output per person against Japan's that year, as a simple fraction.
    japan_year = event("Overtakes Japan").year
    pair = gdp.loc[gdp.index.year == japan_year, ["CHN", "JPN"]].iloc[0]
    v["japan_share"] = 2.0 ** float(pair["CHN"] - pair["JPN"])
    w["japan_share"] = _FRACTIONS.get(round(1.0 / v["japan_share"]), f"{v['japan_share']:.0%}")

    # The end of Part II: where the economy's line stands at the playhead, against its 1978 level.
    g = rebased(gdp, "CHN")
    stop = pd.Timestamp(ACTS[_INTERLUDE_ACT].end)
    since_anchor = g.index[g.index.year == GDP_ANCHOR_YEAR][0]
    own_at = lambda when: float(np.interp(_days(when), _days(own.index), own.to_numpy())[0])
    v["part2_date"], v["part2_bits"] = stop, float(g_at(g, stop)[0])
    v["part2_rate"] = v["part2_bits"] / ((stop - since_anchor) / pd.Timedelta(days=365.25))
    v["part2_multiple"] = 2.0 ** v["part2_bits"]
    v["part2_own"] = 2.0 ** (own_at(stop) - own_at(since_anchor))
    w["part2_from"], w["part2_end_year"] = str(GDP_ANCHOR_YEAR), str(stop.year)
    w["part2_change"] = ("roughly doubled" if 1.8 <= v["part2_multiple"] <= 2.3
                         else f"grown ×{v['part2_multiple']:.1f}")
    w["part2_bits"], w["part2_rate"] = signed(v["part2_bits"], 1), f"{v['part2_rate']:.2f}"
    w["part2_own"] = f"{v['part2_own']:.1f}"

    # The two exchanges: the day each opened, for the hover text, and the month, for the box.
    w["exchange_month"], w["exchange_day"] = _month(pd.Timestamp(_EXCHANGE_OPENS)), _day(_EXCHANGE_OPENS)
    w["shenzhen_month"], w["shenzhen_day"] = _month_name(_SHENZHEN_OPENS), _day(_SHENZHEN_OPENS)
    for name, label in (("bshares", "First B-shares"), ("hshares", "First H-shares"), ("wto", "Joins WTO"),
                        ("qfii", "QFII")):
        w[f"{name}_month"] = _month(event(label))
    w["icbc_year"] = str(event("ICBC IPO").year)

    # The bottom of the stock ratio, and how far each market had fallen by then.
    peak = s.idxmax()
    low = s[:peak].idxmin()
    wto = event("Joins WTO")
    months = (low.year - wto.year) * 12 + low.month - wto.month
    w["trough_lag"] = ("A month later" if months == 1 else f"{months} months later" if months > 1
                       else "That month" if months == 0 else f"Already, in {_month(low)},")
    w["since"], w["end_month"] = _month(anchor), _month(cutoff)
    w["peak_month"], w["peak_yy"] = _month(peak), f"{peak.year % 100:02d}"
    v["trough"], v["peak"], v["trough_months_after_wto"] = low, peak, months
    v["trough_ratio"] = float(s[low])
    usa_return = returns.get((anchor, low))
    if usa_return is not None:
        v["trough_usa"] = 100.0 * (1.0 - 2.0 ** usa_return)
        v["trough_china"] = 100.0 * (1.0 - 2.0 ** (usa_return + float(s[low])))
    if usa_return is not None and v["trough_usa"] > 0 and v["trough_china"] > 0:
        w["trough_falls"] = _TROUGH_FALLS.format(trough_china=f"{v['trough_china']:.0f}",
                                                 trough_usa=f"{v['trough_usa']:.0f}", since=w["since"])
    else:
        if usa_return is None:
            warnings.warn(f"the derived file has no MSCI USA return from {anchor:%Y-%m-%d} to the bottom of "
                          f"{low:%b %Y}: that box gives the ratio alone (re-run the prep script with this anchor)",
                          stacklevel=2)
        w["trough_falls"] = _TROUGH_FALLS_UNKNOWN.format(trough_x=_times(2.0 ** float(s[low])), since=w["since"])

    # The catch-up under Hu, and since.
    hu, xi = leader("Hu"), leader("Xi")
    hu_from, hu_to, xi_from = pd.Timestamp(hu.start).year, pd.Timestamp(hu.end).year, pd.Timestamp(xi.start).year
    v["hu_rate"] = catch_up(hu_from, hu_to)
    v["xi_rate"] = catch_up(xi_from, _XI_COMPARED_TO)
    v["xi_share"] = v["xi_rate"] / v["hu_rate"]
    v["era_rates"] = {}
    for who in LEADERS:
        a = max(pd.Timestamp(who.start).year, min(ratio))
        b = min(pd.Timestamp(who.end).year if who.end else max(ratio), max(ratio))
        if b - a >= 5:
            v["era_rates"][who.label] = catch_up(a, b)
    w["hu_from"], w["hu_to_yy"], w["xi_from"] = str(hu_from), f"{hu_to % 100:02d}", str(xi_from)
    w["xi_to_yy"] = f"{_XI_COMPARED_TO % 100:02d}"
    w["hu_rate"] = f"{v['hu_rate']:.2f}"
    w["hu_pct"] = f"{100.0 * (2.0 ** v['hu_rate'] - 1.0):.0f}"
    w["xi_change"] = ("roughly halves" if 0.4 <= v["xi_share"] <= 0.6
                      else f"slows to {v['xi_share']:.0%} of its pace under Hu")

    # The ending.
    v["economy_end"], v["stocks_end"] = float(e.iloc[-1]), float(s.iloc[-1])
    v["gap"] = v["economy_end"] - v["stocks_end"]
    v["years"] = (cutoff - anchor).days / 365.25
    factor = 2.0 ** abs(v["gap"])
    w["economy_verb"], w["stocks_verb"] = ("gained" if v[k] >= 0 else "lost" for k in ("economy_end", "stocks_end"))
    w["economy_bits"], w["stocks_bits"] = f"{abs(v['economy_end']):.2f}", f"{abs(v['stocks_end']):.2f}"
    w["gap_bits"] = f"{abs(v['gap']):.2f}"
    w["gap_factor"] = f"{factor:.0f}" if abs(factor - round(factor)) < 0.06 else f"{factor:.1f}"
    w["gap_side"] = "behind" if v["gap"] >= 0 else "ahead of"
    return w, v


def rate_arrow(g: pd.Series, span: tuple[int, int], note: str | None = None, reference: bool = False) -> dict:
    """A rate arrow over a span of the economy's annual points: where it runs, what it says.

    ``g`` is the economy's ratio (rebased or not: only differences count) at
    its July points; ``span`` is the first and last year. The arrow runs from
    above the first point to above the last (``start``, ``end``; ``y0``,
    ``y1`` the points themselves), parallel to the chord between them; the
    script lifts it clear of the line by ``dev`` (how far the highest point
    between rises above the chord, in bits) and ``RATE_ARROW["lift"]`` px. Its
    label is the rate, its hover text the change (``note`` added); a
    ``reference`` arrow's label says it is the rate before.
    """
    a, b = span
    (t_a, y_a), (t_b, y_b) = ((g.index[g.index.year == y][0], float(g[g.index.year == y].iloc[0])) for y in (a, b))
    between = g[(g.index > t_a) & (g.index < t_b)]
    chord = y_a + (_days(between.index) - _days(t_a)[0]) / (_days(t_b)[0] - _days(t_a)[0]) * (y_b - y_a)
    change, rate = y_b - y_a, (y_b - y_a) / (b - a)
    lead = f"{a}–{b % 100:02d}"
    shown = round(rate, 2) + 0.0
    sign = "+" if shown >= 0 else "−"
    label = (REFERENCE_LABEL.format(rate=("" if shown >= 0 else "−") + f"{abs(shown):.2f}") if reference
             else RATE_LABEL.format(rate=f"{sign}{abs(shown):.2f}"))
    hover = RATE_HOVER.format(lead=lead, verb="rose" if change >= 0 else "fell", change=f"{abs(change):.2f}")
    return dict(span=[a, b], lead=lead, start=_iso(t_a), end=_iso(t_b), y0=y_a, y1=y_b,
                dev=round(max(0.0, float((between.to_numpy() - chord).max())) if len(between) else 0.0, 6),
                change=round(change, 6), rate=round(rate, 6), text=label, reference=reference,
                hover=hover + (f" {note}" if note else ""))


def annotated_points(s: pd.Series, e: pd.Series) -> dict:
    """The four points the arrowed annotations end on: the stock ratio's early low and its peak, and
    where the stock line falls for good below the economy's and below zero."""
    peak = s.idxmax()
    trough = s[:peak].idxmin()
    return dict(arrow_trough=(trough, float(s[trough])), arrow_peak=(peak, float(s[peak])),
                arrow_economy=final_crossing(s, e), arrow_parity=final_crossing(s, 0.0))


def has_picture(beat: Beat) -> bool:
    """Is this beat a picture card whose picture is there to show, and credited?"""
    if not beat.picture:
        return False
    picture = PICTURES[beat.picture]
    return picture.credit is not None and (_HERE / picture.file).exists()


def box_seconds(beat: Beat, words: dict) -> float:
    """How long a beat's box is up to be read at 1x (not counting its fades): so much, plus so much a word.

    A text box takes ``BOX_SECONDS``, a picture card ``PICTURE_SECONDS``; and
    the beat's own ``trim`` on top.
    """
    said = f"{beat.lead} {beat.text}".format(**words)
    start, per_word = PICTURE_SECONDS if has_picture(beat) else BOX_SECONDS
    return start + per_word * len(said.split()) + beat.trim


def interlude_seconds(words: dict) -> float:
    """How long the stop at the end of Part II lasts at 1x: the arrow drawn, a pause, then its box (fades included)."""
    return INTERLUDE["arrow"] + INTERLUDE["pause"] + 2 * CARD_FADE_SECONDS + box_seconds(INTERLUDE_BOX, words)


def final_seconds(words: dict) -> float:
    """How long the box that closes the ending is up to be read, at 1x: its words' time and ``LAST_BOX_EXTRA``."""
    return box_seconds(FINAL_BOX, words) + LAST_BOX_EXTRA


def beat_date(beat: Beat, trough: pd.Timestamp) -> pd.Timestamp:
    """When a beat falls: its own date, or the one the data give it."""
    if beat.after == "trough":
        return trough + pd.DateOffset(months=1)
    return pd.Timestamp(beat.date)


_SCHEDULE_TOLERANCE = 0.01    # s: how far the script's table, linear between its dates, may be from the schedule


def _schedule_nodes(x: np.ndarray, tau: np.ndarray, forced: np.ndarray) -> np.ndarray:
    """Which of the dates ``x`` (times ``tau``) the script's table needs, as indices.

    Enough that the table, read linearly between them, is never more than
    ``_SCHEDULE_TOLERANCE`` from ``tau``: always the first and last and the
    ``forced`` ones (every box's edges), and never two more than
    ``_SCHEDULE_STEP_YEARS`` apart.
    """
    must = np.zeros(len(x), dtype=bool)
    must[[0, -1]] = True
    must[np.searchsorted(x, forced)] = True
    keep, i = [0], 0
    while i < len(x) - 1:
        best, j = i + 1, i + 1
        while j < len(x) and x[j] - x[i] <= _SCHEDULE_STEP_YEARS + 1e-12:
            if j - i > 1:
                inner = slice(i + 1, j)
                line = tau[i] + (x[inner] - x[i]) / (x[j] - x[i]) * (tau[j] - tau[i])
                if np.abs(line - tau[inner]).max() > _SCHEDULE_TOLERANCE:
                    break
            best = j
            if must[j]:
                break
            j += 1
        keep.append(best)
        i = best
    return np.array(keep)


def act_schedule(start: pd.Timestamp, end: pd.Timestamp, seconds: float,
                 dips: list[tuple[pd.Timestamp, float]], boxes: list[tuple[pd.Timestamp, float, float]]) -> dict:
    """One part's playback: time against date, built from its beats.

    Speed is the part's base speed times a factor between 0 and 1, the LEAST of:

    * the stops: playback starts the part from rest and ends it at rest, with a
      constant acceleration over ``STOP_YEARS`` at each end (the only full stops);
    * each of the ``dips`` (a date and a share of base speed: the labelled
      events), eased down and back up over ``EVENT_WINDOW_YEARS`` either side:
      gentle, and brief;
    * each of the ``boxes`` (a date, how long the box takes to read, and the
      share of base speed playback keeps meanwhile). A box comes up AT ITS
      DATE (or as the part starts, if its date is within ``SYNC_DAYS`` of
      that) and holds its share over a stretch of dates just long enough for
      it to fade in, be read and fade out. Where a box's date comes while the
      one before it is still up, the boxes before it run slower so that it
      comes up on its date, down to ``CROWD_SHARE``; past that it waits, and
      comes up as soon as the one before has gone (the two then run straight
      into each other), but never more than ``SYNC_DAYS`` late: the boxes
      before it slow on, down to ``MIN_SHARE`` (all but a stop), to see to
      that. A box that would otherwise run past the end of its part slows too.
      Playback eases down into a box and up out of one over ``BOX_RAMP_YEARS``.

    The base speed is then whatever makes the part last ``seconds``, but never
    more than ``MAX_BASE``: where the boxes alone take about that long, the
    part runs over. Returns the base speed (``base``, years a second); for each
    box the stretch of years into the part it is up for and its share of base
    speed (``stretches``: from when it starts to fade in until it has faded
    out), the same as dates with the moment it starts to fade out instead of
    the stretch's end (``windows``), and how far after its date it came up
    (``late``, in days); the table the script is given (``nodes``, years into
    the part, and ``tau``, the playback time there, linear between them); and,
    on a fine grid of ``years`` into the part (the middles of its cells), the
    speed ``factor``, the playback ``time`` and the time each cell takes (``dt``).
    """
    year_ = pd.Timedelta(days=365.25)
    years = (end - start) / year_
    at = lambda when: (pd.Timestamp(when) - start) / year_
    # (Three days' margin: a box shows from the first frame after its moment, by when a 2x playhead
    # on a 60 Hz screen may have moved a day or two on.)
    tol = (SYNC_DAYS - 3) / 365.25
    ease = lambda d: 0.5 * (1 + np.cos(np.pi * np.clip(d, 0.0, 1.0)))       # 1 at the centre, 0 from the edge on
    order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
    own = {i: at(boxes[i][0]) for i in order}
    due = {i: 0.0 if own[i] <= tol else own[i] for i in order}               # where each box would come up
    up = {i: 2 * CARD_FADE_SECONDS + boxes[i][1] for i in order}              # fade in, read, fade out
    uniform = np.linspace(0.0, years, int(np.ceil(years / 0.002)) + 1)

    def stretches(base):
        """Each box's stretch of years into the part, and how far its share is scaled down: in turn, from its date."""
        q = {i: 1.0 for i in order}
        soft = {i: min(1.0, CROWD_SHARE / boxes[i][2]) for i in order}
        hard = {i: MIN_SHARE / boxes[i][2] for i in order}

        def place():
            spans, prev = {}, 0.0
            for i in order:
                lo = prev if prev >= due[i] - 1e-6 else due[i]      # straight after the one before, or at its date
                spans[i] = (lo, lo + up[i] * boxes[i][2] * q[i] * base)
                prev = spans[i][1]
            return spans

        def chain(spans, k):                 # the boxes, each straight after the one before, that lead up to the k-th
            j = k - 1
            while j > 0 and spans[order[j]][0] > due[order[j]] + 1e-12:
                j -= 1
            return order[j:k]

        def squeeze(spans, run, limit, floor):
            """Slow the run of boxes, in proportion, so that it ends by ``limit``; none slower than ``floor``."""
            width = {i: spans[i][1] - spans[i][0] for i in run}
            room = limit - spans[run[0]][0] - 1e-9
            free = [i for i in run if q[i] > floor[i] * (1 + 1e-12)]
            slowed = False
            while free:
                scale = (room - sum(width[i] for i in run if i not in free)) / sum(width[i] for i in free)
                if scale >= 1:
                    break
                floored = [i for i in free if q[i] * scale <= floor[i]]
                if not floored:
                    for i in free:
                        q[i] *= scale
                    return True
                for i in floored:
                    width[i] *= floor[i] / q[i]
                    q[i] = floor[i]
                slowed = True
                free = [i for i in free if i not in floored]
            return slowed

        for _ in range(5000):
            spans = place()
            for k, i in enumerate(order):
                late = spans[i][0] - own[i]
                if k == 0 or late <= 1e-9:
                    continue
                # A box the one before it is still up at: the run before it slows, to bring it up on its
                # date, down to CROWD_SHARE; past that it waits, but never past SYNC_DAYS, the run before
                # it slowing on as far as MIN_SHARE to see to that.
                run = chain(spans, k)
                if squeeze(spans, run, own[i], soft):
                    break
                if late > tol + 1e-12:
                    if squeeze(spans, run, own[i] + tol, hard):
                        break
                    raise ValueError(f"boxes near {start + own[i] * year_:%Y-%m} crowd too closely to come up "
                                     f"within {SYNC_DAYS} days of their dates, even at MIN_SHARE")
            else:
                if not order or spans[order[-1]][1] <= years + 1e-12:
                    return spans, q
                if not squeeze(spans, chain(spans, len(order)), years, hard):     # a box would run past the end
                    raise ValueError(f"the last box of the part from {start:%Y-%m} cannot end with it, even at MIN_SHARE")
        raise ValueError("the boxes' schedule did not settle")

    def factor(base):
        spans, q = stretches(base)
        reads = {i: spans[i][0] + (CARD_FADE_SECONDS + boxes[i][1]) * boxes[i][2] * q[i] * base for i in order}
        cuts = np.clip(np.array([v for i in order for v in (spans[i][0], reads[i], spans[i][1])]), 0.0, years)
        near = np.abs(uniform[:, None] - cuts[None, :]).min(axis=1) < 2e-6 if len(cuts) else np.zeros(len(uniform), bool)
        xs = np.unique(np.concatenate([uniform[~near | (uniform == 0) | (uniform == years)], cuts]))
        mid = (xs[:-1] + xs[1:]) / 2
        f = np.sqrt(np.clip(np.minimum(mid, years - mid) / STOP_YEARS, 0.0, 1.0))
        for when, slow in dips:
            if -EVENT_WINDOW_YEARS < at(when) < years + EVENT_WINDOW_YEARS:
                f = np.minimum(f, 1 - (1 - slow) * ease(np.abs(mid - at(when)) / EVENT_WINDOW_YEARS))
        for n_, i in enumerate(order):
            lo, hi = spans[i]
            # From one box straight into the next, the speed changes in a step: no easing between them.
            joined_before = n_ > 0 and spans[order[n_ - 1]][1] == lo
            joined_after = n_ < len(order) - 1 and spans[order[n_ + 1]][0] == hi
            before = (lo - mid) / (1e-9 if joined_before else BOX_RAMP_YEARS)
            after = (mid - hi) / (1e-9 if joined_after else BOX_RAMP_YEARS)
            f = np.minimum(f, 1 - (1 - boxes[i][2] * q[i]) * ease(np.maximum(before, after)))
        return xs, mid, f, spans, q, reads, cuts

    def took(base):
        xs, _, f, *_ = factor(base)
        return float((np.diff(xs) / (base * f)).sum())

    if took(MAX_BASE) >= seconds:                   # the boxes alone take that long: as fast as allowed
        base = MAX_BASE
    else:
        slow_, fast = 1e-3, MAX_BASE                # the part gets shorter as the base speed rises: bisect
        for _ in range(50):
            middle = (slow_ * fast) ** 0.5
            slow_, fast = (middle, fast) if took(middle) > seconds else (slow_, middle)
        base = (slow_ * fast) ** 0.5
    xs, mid, f, spans, q, reads, cuts = factor(base)
    dt = np.diff(xs) / (base * f)                   # the playback time each cell of the grid takes
    edges = np.concatenate([[0.0], np.cumsum(dt)])
    keep = _schedule_nodes(xs, edges, cuts)
    windows, held, late = [None] * len(boxes), [None] * len(boxes), [None] * len(boxes)
    for i in order:
        lo, hi = spans[i]
        share = boxes[i][2] * q[i]
        windows[i] = (start + lo * year_, start + reads[i] * year_, share)
        held[i] = (lo, hi, share)
        late[i] = (lo - own[i]) * 365.25
    return dict(nodes=xs[keep], tau=edges[keep], base=base, windows=windows, stretches=held, late=late,
                factor=f, years=mid, dt=dt, time=(edges[:-1] + edges[1:]) / 2)


def playback_plan(starts: list, ends: list, dips: list, beats: list[Beat], words: dict,
                  trough: pd.Timestamp, notes: list[tuple[str, pd.Timestamp]] = ()) -> list[dict]:
    """Each part's beats and the schedule they make: what the builder, the checks and the pacing chart share.

    One dict per part: the ``act``, its ``start`` and ``end``, its ``beats`` in
    date order with the ``dates`` they fall on and what each ``says`` (lead and
    text, numbers filled in), its ``boxes`` (date, reading time, nominal
    share) and the ``table`` from :func:`act_schedule`. ``notes`` are the
    annotations that are beats (a role and the date its point is reached):
    each slows playback to a text box's speed for ``NOTE_BEAT["seconds"]``
    with no box; they come after the beats in ``boxes`` and in the table's
    lists, and a part lists its own as ``notes``.
    """
    dated = sorted(((beat_date(b, trough), b) for b in beats), key=lambda pair: pair[0])
    plan = []
    for n, act in enumerate(ACTS):
        mine = [(when, b) for when, b in dated if starts[n] < when <= ends[n]]
        boxes = [(when, box_seconds(b, words), PICTURE_SLOWDOWN if has_picture(b) else BOX_SLOWDOWN) for when, b in mine]
        own = [(role, when) for role, when in notes if starts[n] < when <= ends[n]]
        boxes += [(when, NOTE_BEAT["seconds"] - 2 * CARD_FADE_SECONDS, BOX_SLOWDOWN) for _, when in own]
        plan.append(dict(act=act, start=starts[n], end=ends[n], beats=[b for _, b in mine], dates=[d for d, _ in mine],
                         says=[(b.lead.format(**words), b.text.format(**words)) for _, b in mine], boxes=boxes,
                         notes=own,
                         table=act_schedule(starts[n], ends[n], act.seconds, [(d, EVENT_SLOWDOWN) for d in dips], boxes)))
    assert sum(len(part["beats"]) for part in plan) == len(beats), "a beat lies outside every part"
    return plan


def unexplained_slow_stretches(table: dict) -> list[tuple[float, float]]:
    """Where a part breaks the tempo rule: (years into the part, seconds) for each stretch that does.

    The rule (``SLOW_LIMIT``): playback is never under so much of base speed
    for longer than so many seconds unless a box is up to explain it. A box is
    up over its whole stretch, from when it starts to fade in until it has
    faded out.
    """
    share, limit = SLOW_LIMIT
    f, x, step = table["factor"], table["years"], table["dt"]
    explained = np.zeros(len(x), dtype=bool)
    for lo, hi, _ in table["stretches"]:
        explained |= (x >= lo) & (x <= hi)
    slow = (f < share) & ~explained
    found, run_start, run = [], None, 0.0
    for i in range(len(x) + 1):
        if i < len(x) and slow[i]:
            run_start, run = (x[i] if run_start is None else run_start), run + step[i]
        elif run_start is not None:
            if run > limit:
                found.append((float(run_start), float(run)))
            run_start, run = None, 0.0
    return found


def picture_data(key: str) -> dict | None:
    """A picture, ready for the page: None, with a warning, if its file is missing.

    The page carries the image itself (a data URI: scaled down to
    ``PICTURE_MAX_PX`` on its long side, a JPEG of ``PICTURE_QUALITY``; the
    file is left as it is), so nothing has to be copied alongside it. Also its
    shape (width over height), the short credit its card shows, and its size
    as embedded (``kb``, the JPEG's) against the file's (``file_kb``).
    """
    picture = PICTURES[key]
    path = _HERE / picture.file
    if not path.exists():
        warnings.warn(f"picture card “{key}”: {picture.file} is missing, so the card is a text box", stacklevel=2)
        return None
    if picture.credit is None:
        warnings.warn(f"picture card “{key}”: {picture.file} has no credit in PICTURES, so the card is a text box",
                      stacklevel=2)
        return None
    try:
        from PIL import Image
    except ImportError:                              # no Pillow: the file as it is
        kind = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}[path.suffix.lstrip(".").lower()]
        return dict(src=f"data:image/{kind};base64," + base64.b64encode(path.read_bytes()).decode("ascii"),
                    aspect=None, credit=picture.short, max_px=picture.max_px)
    with Image.open(path) as image:
        image = image.convert("RGBA")
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image, mask=image.split()[-1])
        scale = PICTURE_MAX_PX / max(flat.size)
        if scale < 1:
            flat = flat.resize((round(flat.width * scale), round(flat.height * scale)), Image.LANCZOS)
        held = io.BytesIO()
        flat.save(held, "JPEG", quality=PICTURE_QUALITY, optimize=True)
        jpeg = held.getvalue()
        # A JPEG small enough already, and smaller as it is: as it is.
        if scale >= 1 and image.format in (None, "JPEG") and path.suffix.lower() in (".jpg", ".jpeg") \
                and path.stat().st_size < len(jpeg):
            jpeg = path.read_bytes()
    return dict(src="data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii"),
                aspect=round(flat.width / flat.height, 4), credit=picture.short, max_px=picture.max_px,
                size=[flat.width, flat.height], kb=round(len(jpeg) / 1024, 1),
                file_kb=round(path.stat().st_size / 1024, 1))


def picture_credits(beats: list[Beat] | None = None) -> str:
    """For the caption: the full credit of every picture the animation shows, in the order it shows them."""
    used = [b.picture for b in sorted(BEATS if beats is None else beats, key=lambda b: b.date or "") if has_picture(b)]
    return "Images: " + " ".join(PICTURES[key].credit.rstrip(".") + "." for key in dict.fromkeys(used))


def default_plan() -> tuple[list[dict], list[pd.Timestamp], dict, dict]:
    """The playback plan of the figure as it is built by default, with its labelled events' dates and the narration's numbers."""
    gdp, s_file = load_derived()
    g_full = rebased(gdp, "CHN")
    g = g_full[g_full.index.year >= START_YEAR]
    anchor = anchor_month_end(s_file)
    s_all = stock_since(s_file, anchor)
    cutoff = common_cutoff(g, s_all)
    s = s_all[:cutoff]
    e = economy_since_anchor(g_full, s.index, anchor)
    usa, returns = load_narration_data()
    words, numbers = narration_numbers(gdp, usa, s, e, anchor, cutoff, returns)
    ends = [pd.Timestamp(act.end) if act.end else cutoff for act in ACTS]
    starts = [g.index[0]] + ends[:-1]
    first = pd.Timestamp(year=START_YEAR, month=1, day=1)
    marks = [pd.Timestamp(ev.date) for ev in EVENTS if ev.tier == "label" and first <= pd.Timestamp(ev.date) <= cutoff]
    # The annotations: two are beats of their own; the other two dip gently, as a labelled event does.
    points = annotated_points(s, e)
    notes = [(role, pd.Timestamp(points[role][0])) for role in NOTE_BEATS]
    dips = marks + [pd.Timestamp(when) for role, (when, _) in points.items() if role not in NOTE_BEATS]
    return playback_plan(starts, ends, dips, BEATS, words, numbers["trough"], notes), marks, words, numbers


def pacing_chart(path: str | Path | None = None):
    """The tempo, to review without watching: playback speed against date, part by part.

    Speed is in years of chart a second at 1x, on a log scale (a box can run at
    a fraction of a percent of base speed). Each part's base speed and the line
    60% of the way up to it (the tempo rule's threshold) are drawn in; boxes
    are shaded for as long as they are up (text boxes grey, picture cards
    amber, the annotations that are beats blue) and named by their lead-in and
    their date; a tick along the foot
    marks each labelled event; the part breaks are the heavy verticals. Saved
    to ``path`` if given; returns the matplotlib figure.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plan, marks, words, _ = default_plan()
    year = lambda when: when.year + (when.dayofyear - 1) / 365.25
    chart, ax = plt.subplots(figsize=(16, 6.2), dpi=110)
    top = 4.0 * max(part["table"]["base"] for part in plan)
    floor = 0.5 * min(part["table"]["base"] * share for part in plan for _, _, share in part["table"]["stretches"])
    for part in plan:
        table, x0, x1 = part["table"], year(part["start"]), year(part["end"])
        base = table["base"]
        ax.plot(x0 + table["years"], base * table["factor"], color="#1e3a8a", lw=1.3, zorder=3)
        ax.hlines(base, x0, x1, color="#1e3a8a", lw=0.7, ls=":", zorder=2)
        ax.hlines(SLOW_LIMIT[0] * base, x0, x1, color="#b91c1c", lw=0.7, ls="--", zorder=2)
        for beat, when, (lead, _), (lo, hi, share) in zip(part["beats"], part["dates"], part["says"], table["stretches"]):
            picture = has_picture(beat)
            ax.axvspan(x0 + lo, x0 + hi, color="#f59e0b" if picture else "#6b7280", alpha=0.28 if picture else 0.2, lw=0, zorder=1)
            ax.text(x0 + (lo + hi) / 2, top * 0.9, f"{lead} ({when:%b %-d, %Y})", rotation=90, ha="center", va="top",
                    fontsize=7, zorder=4)
        for (role, when), (lo, hi, share) in zip(part["notes"], table["stretches"][len(part["beats"]):]):
            ax.axvspan(x0 + lo, x0 + hi, color="#2563eb", alpha=0.22, lw=0, zorder=1)
            ax.text(x0 + (lo + hi) / 2, top * 0.9, f"annotation ({when:%b %-d, %Y})", rotation=90, ha="center",
                    va="top", fontsize=7, zorder=4)
        ax.axvline(x1, color="black", lw=1.6, zorder=5)
        took = float(table["tau"][-1])
        ax.text((x0 + x1) / 2, top * 1.15, f"Part {part['act'].numeral} · {part['act'].title}\n{took:.1f} s at 1x, "
                f"{took / DEFAULT_SPEED:.1f} s at {DEFAULT_SPEED}x · base {base:.2f} yr/s", ha="center", va="bottom",
                fontsize=8.5, weight="bold", linespacing=1.35)
    stop = year(plan[_INTERLUDE_ACT]["end"])
    ax.text(stop + 0.15, floor * 1.6, f"then {interlude_seconds(words):.1f} s at rest:\nthe arrow and its box",
            fontsize=7.5, ha="left", va="bottom", zorder=6)
    for when in marks:
        ax.plot([year(when)] * 2, [floor, floor * 1.25], color="black", lw=1.0, zorder=6)
    ax.axvline(year(plan[0]["start"]), color="black", lw=1.6, zorder=5)
    ax.set_xlim(year(plan[0]["start"]) - 0.4, year(plan[-1]["end"]) + 0.4)
    ax.set_yscale("log")
    ax.set_ylim(floor, top)
    ax.set_xticks(range(1960, int(year(plan[-1]["end"])) + 1, 5))
    ax.set_xlabel("date at the playhead")
    ax.set_ylabel("playback speed (years of chart a second, at 1x)")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    keys = [plt.Line2D([], [], color="#1e3a8a", lw=1.3, label="speed"),
            plt.Line2D([], [], color="#1e3a8a", lw=0.7, ls=":", label="the part's base speed"),
            plt.Line2D([], [], color="#b91c1c", lw=0.7, ls="--", label=f"{SLOW_LIMIT[0]:.0%} of base (the tempo rule)"),
            plt.Rectangle((0, 0), 1, 1, color="#6b7280", alpha=0.2, label="text box up"),
            plt.Rectangle((0, 0), 1, 1, color="#f59e0b", alpha=0.28, label="picture card up"),
            plt.Rectangle((0, 0), 1, 1, color="#2563eb", alpha=0.22, label="annotation beat"),
            plt.Line2D([], [], color="black", lw=1.0, marker="|", ls="", label="labelled event (tick at the foot)"),
            plt.Line2D([], [], color="black", lw=1.6, label="part break (full stop, title card)")]
    ax.legend(handles=keys, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=8, frameon=False, fontsize=8.5)
    chart.subplots_adjust(left=0.05, right=0.99, top=0.86, bottom=0.18)
    if path is not None:
        chart.savefig(path)
    return chart


def _schedule_steps(table: dict) -> list[list[float]]:
    """A part's schedule as the script is given it: from one of its dates to the next, the years and the seconds.

    Steps, not running totals: every number in the figure stays small enough
    to be seen not to be an index level. (Rounded as running totals first, so
    that the script's sums land where these do.)
    """
    x, tau = np.round(table["nodes"], 6), np.round(table["tau"], 5)
    keep = np.concatenate([[True], (np.diff(x) > 0) & (np.diff(tau) > 0)])
    x, tau = x[keep], tau[keep]
    return [[float(v) for v in np.round(np.diff(x), 6)], [float(v) for v in np.round(np.diff(tau), 5)]]


def _bits(x: float, show_multiple: bool) -> str:
    """A change in bits for the hover box: ``+2.24 bits``, with a true minus sign."""
    shown = round(float(x), 2) + 0.0                # "+ 0.0" turns -0.0 into 0.0
    text = f"{'+' if shown >= 0 else '−'}{abs(shown):.2f} bits"
    if show_multiple:
        m = float(2.0 ** x)
        # Three significant figures from 1 up, two below: ×16.2, ×4.96, ×0.67.
        text += f" (×{m:.1f})" if round(m, 2) >= 10 else f" (×{m:.2f})"
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
# rows. ``card`` sizes a beat's box (its type, its width, and the sizes a
# picture may take in it, largest first, each the picture's longer side, so
# that an upright one is that tall; ``below``: the plot is too small to
# hold a text box clear of the playhead, so text boxes go directly under it),
# ``act_card`` an act's title card (its
# width is a share of the plot's) and ``pill`` the year pill under the
# playhead. ``end`` places what closes the animation, in px right of the last
# data point: the gap's arrow and the labels beside it (None: no room, so they
# go in the key). The right margin is the gutter those labels stand in.
# ``bare_gap`` is the space between the panels when the bottom strip's
# labels are hidden. ``tick`` sizes a tick mark: how far it reaches above and
# below the top edge of its panel, and how thick it is; it sits in the few
# pixels between the panel and the first row of labels, so it costs no height.
# ``drop_from`` is the column width from which a strip that
# cannot hold everything DROPS items in order rather than hiding its labels
# (None: never).
_NARROW_BELOW_PX = 560
_LAYOUTS = dict(
    wide=dict(
        margin=dict(l=54, r=88, b=26), px_per_bit=58, font=12.5, drop_from=900, modebar=True,
        gdp_width=2.5, stock_width=1.8, economy_width=1.7, head=15, title=15.5, title_row=26, anchor=10.5,
        tick=dict(up=3, down=7, width=2),
        strip=dict(
            plans=dict(top=[dict(rows=2, pitch=16, fonts=[11.5, 10.5, 10]), dict(rows=3, pitch=16, fonts=[11.5, 10.5, 10])],
                       bottom=[dict(rows=2, pitch=16, fonts=[11.5, 10.5, 10]), dict(rows=3, pitch=15, fonts=[10.5, 10])]),
            era_font=10.5, era_bar=6, era_label=14, leader=16, leader_font=10.5, bare_gap=14),
        arrow_fonts=[11.5, 10.5, 9.5], band_font=11, fill_font=10.5, hint_font=10, rate_font=10.5,
        card=dict(font=12.5, width=300, pictures=[260, 230, 200, 170], below=False), end=dict(arrow=9, label=19),
        act_card=dict(kicker=13, title=27, width=0.56), pill=10.5),
    narrow=dict(
        margin=dict(l=46, r=10, b=24), px_per_bit=46, font=11, drop_from=None, modebar=False,
        gdp_width=2.2, stock_width=1.4, economy_width=1.4, head=13.5, title=14, title_row=24, anchor=9,
        tick=dict(up=3, down=6, width=2),
        strip=dict(
            plans=dict(top=[dict(rows=2, pitch=15, fonts=[10, 9.5])], bottom=[dict(rows=2, pitch=15, fonts=[10, 9.5])]),
            era_font=9.5, era_bar=6, era_label=13, leader=14, leader_font=9.5, bare_gap=12),
        arrow_fonts=[10, 9], band_font=9.5, fill_font=9.5, hint_font=9, rate_font=9.5,
        card=dict(font=11.5, width=250, pictures=[150, 125, 100], below=True), end=dict(arrow=3, label=None),
        act_card=dict(kicker=10, title=19, width=0.8), pill=10),
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
              gap_up="Gap narrower than in {anchor_year}", gap_down="Gap wider than in {anchor_year}")


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
    the fills, the playhead, each box's rate arrow (and reference arrow) with
    its label, the arrow at the end of Part II, and what closes the animation:
    the two chords, their rates, and the arrow that measures the gap between
    the lines' ends.
    ``layout.meta`` lists them all, and carries the acts, the beats (text boxes
    and picture cards, pictures included) and the schedule playback follows. No annotation has a background:
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
        The narration (``BEATS`` if not given): text boxes and picture cards.
        Every labelled event is a gentler beat as well.

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
    usa, returns = load_narration_data()
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

    # The acts. Each has a fixed x-range: from where it is framed (the start of
    # the plot, unless the act says otherwise) to its own end, plus a little
    # room. The finished chart's runs from the start of the plot to the end of
    # the data, with the same room in proportion.
    first = pd.Timestamp(year=start_year, month=1, day=1)
    data_start = g.index[0]
    ends = [pd.Timestamp(act.end) if act.end else cutoff for act in ACTS]
    starts = [data_start] + ends[:-1]
    froms = [pd.Timestamp(act.view_from) if act.view_from else first for act in ACTS]
    views = [(a, a + (end - a) * (1 + WINDOW_MARGIN)) for a, end in zip(froms, ends)]
    x_range = [_iso(first), _iso(first + (cutoff - first) * (1 + WINDOW_MARGIN))]
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
    note("gap_up", yanchor="bottom", yshift=3, text=_HINTS["gap_up"].format(anchor_year=GDP_ANCHOR_YEAR), **hint, **right_of)
    note("gap_down", yanchor="top", yshift=-3, text=_HINTS["gap_down"].format(anchor_year=GDP_ANCHOR_YEAR), **hint,
         **right_of)

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

    # The end of the animation, in the bottom panel. A dashed chord from the
    # anchor to each series' last value, and the rate each chord stands for: the
    # final value in bits over the years since the anchor, and 2 to that power.
    # Each rate stands at its chord's end, in its series' colour, in the gutter
    # right of the plot. (Where there is no gutter, a phone, they go in the key.)
    words, numbers = narration_numbers(gdp, usa, s, e, anchor_at, cutoff, returns)
    years_since = numbers["years"]
    last = _iso(cutoff)
    beside = wide["end"]

    def chord_said(rate: float) -> tuple[str, list[str]]:
        """A chord's rate as its label says it, on one line and on two (broken before the multiple)."""
        said = COPY_TEXT["chord_rate"].format(rate=f"{'+' if rate >= 0 else '−'}{abs(rate):.3f}",
                                              multiple=f"{2.0 ** rate:.3f}")
        return said, [f"<b>{said}</b>", f"<b>{said.replace(' (', '<br>(', 1)}</b>"]

    # First, in the top panel: a chord across each era (ERA_CHORDS), from the economy line's point at
    # its start to the one at its end, each with its rate in bits a year against America, and what that
    # was in growth on hover. The script places each rate near its chord, or in the gutter.
    def wrapped(said: str) -> list[str]:
        """A label in bold on one line, then broken after the colon, before the multiple, after the name."""
        forms = [said]
        for at, broken in ((": ", ":<br>"), (" (", "<br>("), (", ", ",<br>")):
            forms.append(forms[-1].replace(at, broken, 1))
        return [f"<b>{form}</b>" for form in dict.fromkeys(forms)]

    era_chords, plotted = [], dict(zip(gdp_x, gdp_y))
    for n, era in enumerate(era_numbers(gdp, usa)):
        y0, y1 = plotted[_iso(era["t0"])], plotted[_iso(era["t1"])]       # (on the points as drawn)
        signed_rate = f"{'+' if era['rate'] >= 0 else '−'}{abs(era['rate']):.3f}"
        flat = f"{era['multiple']:.2f}" == "1.00"
        said = COPY_TEXT["era_rate_flat" if flat else "era_rate"].format(
            name=era["era"].name, span=era["span"], rate=signed_rate, multiple=f"{era['multiple']:.3f}")
        mid = era["t0"] + (era["t1"] - era["t0"]) / 2
        era_chords.append(dict(
            key=f"era{n}", name=era["era"].name, span=era["span"], color=_GDP_COLOR, rate=round(era["rate"], 6),
            start=_iso(era["t0"]), end=_iso(era["t1"]), y0=y0, y1=y1,
            said=said, text=said, wraps=wrapped(said),
            hover=era["era"].hover.format(span=era["span"], china=f"{era['china']:.1f}", usa=f"{era['usa']:.1f}"),
            shape=shape(type="line", xref="x", yref="y", x0=_iso(era["t0"]), y0=y0, x1=_iso(era["t1"]),
                        y1=y1, line=dict(color=_GDP_COLOR, width=1.6, dash="dash"), layer="between"),
            annotation=note(f"rate_era{n}", xref="x", yref="y", x=_iso(mid), y=(y0 + y1) / 2,
                            xanchor="center", yanchor="middle", align="center", text=wrapped(said)[-1],
                            visible=False, size=wide["rate_font"], color=_GDP_COLOR)))
    # Then the climb since 1978: a double-headed arrow in ink, just right of the line's last point,
    # from the 1978 level (zero) up to it; and in the gutter what it measures.
    g_end, climbed = g.index[-1], gdp_y[-1]
    climb_multiple = 2.0 ** climbed
    climb_text = COPY_TEXT["climb"].format(
        bits=f"{'+' if climbed >= 0 else '−'}{abs(climbed):.2f}", anchor_year=GDP_ANCHOR_YEAR,
        multiple=f"{climb_multiple:.0f}" if climb_multiple >= 10 else f"{climb_multiple:.1f}")
    climb_forms = [climb_text, climb_text.replace(" (", "<br>(", 1)]
    climb_forms.append(climb_forms[-1].replace(" since ", "<br>since ", 1))
    climb = dict(
        value=round(climbed, 6), date=_iso(g_end), text=climb_text, wraps=list(dict.fromkeys(climb_forms)),
        arrow=note("climb_arrow", xref="x", yref="y", x=_iso(g_end), y=climbed, ax=_iso(g_end), ay=0.0,
                   axref="x", ayref="y", showarrow=True, arrowside="end+start", arrowhead=2, startarrowhead=2,
                   arrowsize=1, startarrowsize=1, arrowwidth=1.3, arrowcolor=ink("arrow"), standoff=0,
                   startstandoff=0, xshift=beside["arrow"], text="", visible=False, size=wide["rate_font"],
                   color=ink("arrow")),
        label=note("climb_label", xref="x", yref="y", x=_iso(g_end), y=climbed / 2, xanchor="left",
                   yanchor="middle", align="left", xshift=beside["label"], text=climb_forms[1], visible=False,
                   size=wide["rate_font"], color=ink("rate")))
    chords = []
    for key, name, value, color in (("economy", COPY_TEXT["chord_economy"], economy_y[-1], _GDP_COLOR),
                                    ("stocks", COPY_TEXT["chord_stocks"], stock_y[-1], _STOCK_COLOR)):
        rate = value / years_since
        said, wraps = chord_said(rate)
        chords.append(dict(
            key=key, name=name, color=color, rate=round(rate, 6), value=value, date=last, wraps=wraps,
            said=said, text=f"{name}: {said}",
            shape=shape(type="line", xref="x", yref="y2", x0=anchor, y0=0, x1=last, y1=value,
                        line=dict(color=color, width=1.6, dash="dash"), layer="between"),
            annotation=note(f"rate_{key}", xref="x", yref="y2", x=last, y=value, xanchor="left", yanchor="middle",
                            align="left", xshift=beside["label"], text=wraps[1], size=wide["rate_font"], color=color)))
    # Then the gap between the two ends: a double-headed arrow in ink, just
    # right of the last data point, and what it measures.
    gap = numbers["gap"]
    gap_text = COPY_TEXT["gap"].format(gap_bits=f"{abs(gap):.2f}", gap_multiple=f"{2.0 ** abs(gap):.1f}")
    gap_end = dict(
        value=round(gap, 6), text=gap_text, wraps=[gap_text, gap_text.replace(" (", "<br>(")],
        top=economy_y[-1], bottom=stock_y[-1], date=last,
        arrow=note("gap_arrow", xref="x", yref="y2", x=last, y=economy_y[-1], ax=last, ay=stock_y[-1],
                   axref="x", ayref="y2", showarrow=True, arrowside="end+start", arrowhead=2, startarrowhead=2,
                   arrowsize=1, startarrowsize=1, arrowwidth=1.3, arrowcolor=ink("arrow"), standoff=0,
                   startstandoff=0, xshift=beside["arrow"], text="", size=wide["rate_font"], color=ink("arrow")),
        label=note("gap_label", xref="x", yref="y2", x=last, y=(economy_y[-1] + stock_y[-1]) / 2, xanchor="left",
                   yanchor="middle", align="left", xshift=beside["label"], text=gap_text.replace(" (", "<br>("),
                   size=wide["rate_font"], color=ink("rate")))

    # The arrow at the end of Part II: from the economy's 1978 level (zero) up to where its line
    # stands at the playhead, double-headed, while the playhead rests there.
    stop = pd.Timestamp(ACTS[_INTERLUDE_ACT].end)
    interlude = dict(
        act=_INTERLUDE_ACT, date=_iso(stop), value=round(numbers["part2_bits"], 6),
        lead=INTERLUDE_BOX.lead.format(**words), text=INTERLUDE_BOX.text.format(**words),
        seconds=round(box_seconds(INTERLUDE_BOX, words), 3), arrow_seconds=INTERLUDE["arrow"], pause=INTERLUDE["pause"],
        arrow=note("inter_arrow", xref="x", yref="y", x=_iso(stop), y=numbers["part2_bits"], ax=_iso(stop), ay=0.0,
                   axref="x", ayref="y", showarrow=True, arrowside="end+start", arrowhead=2, startarrowhead=2,
                   arrowsize=1, startarrowsize=1, arrowwidth=1.4, arrowcolor=ink("arrow"), standoff=0,
                   startstandoff=0, text="", visible=False, size=wide["rate_font"], color=ink("arrow")))

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
    # own panel (in two strokes: through the panel, and from the panel up to
    # the label, so that the first can yield to the panel's name where a view
    # puts it there) and a label in the strip above it; events in one group share a
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
            entry = dict(date=ev.date, tier=ev.tier, panel=ev.panel, label=ev.label,
                         description=ev.description.format(**words) if "{" in ev.description else ev.description,
                         notes=dated(ev.notes), text=None, short=None, lead=None, annotation=None, stalk=None,
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
            dashed = dict(type="line", xref="x", yref=domain, x0=ev.date, x1=ev.date, opacity=_EVENT_LINE_OPACITY,
                          line=dict(color=_INK, width=1, dash="dash"), layer="below")
            entry["shape"] = shape(y0=0, y1=1, **dashed)
            entry["stalk"] = shape(y0=1, y1=1 + (2 + row * pitch[panel]) / height, **dashed)
            events.append(entry)

    def rate_marks(span, note_=None, reference=False) -> dict:
        """A rate arrow and its label, as the figure carries them (hidden: the script shows them with their box)."""
        spec = rate_arrow(g, span, note_, reference)
        spec["arrow"] = note(xref="x", yref="y", x=spec["end"], y=spec["y1"], ax=spec["start"], ay=spec["y0"],
                             axref="x", ayref="y", showarrow=True, arrowhead=2, arrowsize=1,
                             arrowwidth=RATE_ARROW["width"], arrowcolor=ink("arrow"), text="",
                             # (Plotly's head reaches 1.3 widths past the point it is given: this puts its tip on it.)
                             standoff=round(1.3 * RATE_ARROW["width"], 2),
                             visible=False, size=wide["rate_font"], color=ink("arrow"))
        spec["label"] = note(xref="x", yref="y", x=spec["start"], y=(spec["y0"] + spec["y1"]) / 2, xanchor="center",
                             yanchor="bottom", text=spec["text"], visible=False, size=wide["rate_font"],
                             color=ink("arrow"))
        return spec

    # ---- Playback: the acts, the beats, and the schedule they add up to ----
    # Every labelled event is a gentle beat; every text box and picture card a
    # deep one. Within each act the schedule turns them into a table of playback
    # time against date (:func:`act_schedule`).
    script = BEATS if beats is None else beats
    marks = [pd.Timestamp(ev.date) for ev in drawn if ev.tier != "tick"]
    # Two of the arrowed annotations are beats of their own (NOTE_BEATS); the other two dip gently.
    notes_at = [(role, pd.Timestamp(points[role][0])) for role in NOTE_BEATS]
    dips = marks + [pd.Timestamp(points[role][0]) for role in points if role not in NOTE_BEATS]
    plan = playback_plan(starts, ends, dips, script, words, trough, notes_at)
    acts, shown, noted = [], [], []
    for n, part in enumerate(plan):
        act, table = part["act"], part["table"]
        acts.append(dict(
            numeral=act.numeral, title=act.title, card_title=act.title, short=act.short,
            kicker=COPY_TEXT["kicker"].format(numeral=act.numeral, start_year=starts[n].year, end_year=ends[n].year),
            start=_iso(starts[n]), end=_iso(ends[n]), range=[_iso(views[n][0]), _iso(views[n][1])],
            # The schedule: playback time against date, linear between the dates given.
            base=round(table["base"], 4), grid=_schedule_steps(table)))
        for beat, when, (lead, text), (_, seconds, _), (opens, closes, share) in zip(
                part["beats"], part["dates"], part["says"], part["boxes"], table["windows"]):
            picked = [i for i, ev in enumerate(events) if beat.event and ev["label"] == beat.event]
            assert bool(beat.event) == bool(picked), f"the beat of {when:%Y-%m-%d} picks out an event that is not drawn"
            picture = picture_data(beat.picture) if beat.picture else None
            if picture:                          # (its sizes in KB are for the report, not the page)
                picture = {k: v for k, v in picture.items() if k not in ("kb", "file_kb")}
            shown.append(dict(
                date=_iso(when), act=n, kind="picture" if picture else "text", lead=lead, text=text,
                seconds=round(seconds, 3), share=round(float(share), 4), since=stamp(opens), until=stamp(closes),
                picture=picture, event=picked[0] if picked else None, panel=beat.panel or act.panel, cross=beat.cross,
                rate=rate_marks(beat.rate, beat.rate_note) if beat.rate else None,
                reference=rate_marks(beat.reference, reference=True) if beat.reference else None))
        # The annotations that are beats: when each is reached, and for how long playback slows.
        for (noted_role, when), (opens, closes, share) in zip(part["notes"], table["windows"][len(part["beats"]):]):
            noted.append(dict(role=noted_role, act=n, date=stamp(when), since=stamp(opens), until=stamp(closes),
                              share=round(float(share), 4)))
    final = dict(lead=FINAL_BOX.lead.format(**words), text=FINAL_BOX.text.format(**words), panel="economy",
                 seconds=round(final_seconds(words), 3))

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
    # The hover box: the date as a heading, then each series' change since its own anchor.
    stock_hover = [COPY_TEXT["hover_stocks"].format(since=since, change=_bits(v, show_multiple))
                   + (", back-tested" if i < solid_from else "") for i, v in enumerate(stock_y)]
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
            bands=bands, arrows=arrows, fills=fills, chords=chords, era_chords=era_chords, climb=climb, gap=gap_end, anchor=anchor, anchor_moved=anchor != _iso(STOCK_ANCHOR),
            anchors=[dict(trace="anchor_top", panel="economy", date=gdp_anchor,
                          text=COPY_TEXT["anchor"].format(anchor=GDP_ANCHOR_YEAR)),
                     dict(trace="anchor_bottom", panel="stocks", date=anchor, text=COPY_TEXT["anchor"].format(anchor=since))],
            key=dict(zero=COPY_TEXT["zero_key"].format(since=since)),
            backtest=tested,
            hover=dict(
                year=[str(d.year) for d in g.index],
                gdp=[COPY_TEXT["hover_economy_1978"].format(anchor_year=GDP_ANCHOR_YEAR, change=_bits(v, show_multiple))
                     for v in gdp_y],
                month=[_month(d) for d in s.index],
                stock=stock_hover,
                economy=[COPY_TEXT["hover_economy"].format(since=since, change=_bits(v, show_multiple)) for v in economy_y],
            ),
            # Playback opens on a single dot, the first data point, and runs act by act.
            play=dict(start=_iso(data_start), end=_iso(cutoff), speeds=list(SPEEDS), speed=DEFAULT_SPEED, acts=acts,
                      beats=shown, notes=noted, note=NOTE_BEAT, rate=RATE_ARROW, sync=SYNC_DAYS,
                      final=final, interlude=interlude, transition=TRANSITION, ending=ENDING, reveal=REVEAL_SECONDS,
                      ghost=GHOST_OPACITY, card_fade=CARD_FADE_SECONDS, scrim=SCRIM_OPACITY),
            view=dict(x=x_range, y=y_top, y2=y_bottom),
            layouts=_LAYOUTS, narrow_below=_NARROW_BELOW_PX,
            budget=dict(title=TITLE_ROW_MAX_PX, top=TOP_STRIP_MAX_PX, bottom=BOTTOM_STRIP_MAX_PX),
            alpha=_ALPHA, text_alpha=_TEXT_ALPHA, event_line_opacity=_EVENT_LINE_OPACITY,
            final_line_share=FINAL_EVENT_LINE_SHARE, halo=list(_HALO_OFFSETS),
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
__FIG__
<div class="china-title">__TITLE__</div>
<div class="china-head china-head-top">__HEAD_TOP__</div>
<div class="china-head china-head-bottom">__HEAD_BOTTOM__</div>
<div class="china-hots" aria-hidden="true"><div class="china-pulse"></div><div class="china-pulse-dot"></div></div>
<div class="china-scrim" aria-hidden="true"></div>
<div class="china-beat" title="Click to dismiss"><div class="china-beat-in"><img class="china-beat-img" alt="">
  <div class="china-beat-body"><span class="china-beat-lead"></span> <span class="china-beat-text"></span>
    <div class="china-beat-credit"></div></div></div></div>
<div class="china-act-card"><div class="china-act-kicker"></div><div class="china-act-rule"></div>
  <div class="china-act-name"></div></div>
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
/* The scrim: while an act's title card is up, the figure behind it is dimmed
   towards the page's colour (lighter on a light page, darker on a dark one). */
.china-scrim { position: absolute; inset: 0; z-index: 3; display: none; pointer-events: none;
  background: var(--bs-body-bg, #fff); }
/* An act's title card: a small-capital overline, a hairline, the title. */
.china-act-card { position: absolute; left: 0; top: 0; z-index: 4; display: none; pointer-events: none;
  box-sizing: border-box; padding: 24px 26px 28px; text-align: center; transform: translate(-50%, -50%);
  color: var(--bs-body-color, #1f2328); background: var(--bs-body-bg, #fff);
  border: 1px solid var(--bs-border-color, #cfd3d8); border-radius: 3px; box-shadow: 0 8px 30px rgba(0, 0, 0, .16); }
.china-act-kicker { line-height: 1.3; text-transform: uppercase; letter-spacing: .17em;
  font-variant-numeric: lining-nums; }
.china-act-rule { height: 0; margin: 12px auto 14px; width: 100%; border-top: 1px solid currentColor; opacity: .45; }
.china-act-name { line-height: 1.16; font-weight: 700; text-wrap: balance; }
/* A beat's box: a text box, or a picture card (the picture beside the words,
   or above them). Page colours, all but opaque, so it reads over whatever is
   behind it in either theme. A click or a tap dismisses it. */
.china-beat { position: absolute; left: 0; top: 0; z-index: 4; display: none; cursor: pointer;
  box-sizing: border-box; padding: 6px 10px 7px; line-height: 1.4; text-align: left;
  color: var(--bs-body-color, #1f2328); background: var(--bs-body-bg, #fff);
  background: color-mix(in srgb, var(--bs-body-bg, #fff) 94%, transparent);
  border: 1px solid var(--bs-border-color, #cfd3d8); border-radius: 4px; box-shadow: 0 2px 10px rgba(0, 0, 0, .1); }
.china-beat.is-picture { padding: 8px 9px 8px 8px; }
.china-beat.is-side .china-beat-in { display: flex; align-items: flex-start; gap: 10px; }
.china-beat-img { display: none; flex: none; height: auto; border-radius: 2px; }
.china-beat.is-picture .china-beat-img { display: block; }
.china-beat.is-stacked .china-beat-img { margin-bottom: 6px; }
.china-beat-body { min-width: 0; }
.china-beat-lead { font-weight: 700; }
.china-beat-credit { margin-top: 4px; font-size: .74em; line-height: 1.3; opacity: .65; }
.china-beat-credit:empty { display: none; }
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
.china-overlay { position: absolute; inset: 0; z-index: 5; pointer-events: none; overflow: hidden; }
/* What the cursor is on: a labelled event's line, solid and dark; a tick, taller and darker. Over
   the plot, under the boxes and cards. */
.china-hots { position: absolute; inset: 0; z-index: 2; pointer-events: none; overflow: hidden; }
.china-hot { position: absolute; left: 0; top: 0; display: none; }
/* An annotation that is a beat: its point, and one ring that spreads from it and fades. */
.china-pulse { position: absolute; left: 0; top: 0; display: none; box-sizing: border-box; border-radius: 50%;
  border: 1.5px solid currentColor; }
.china-pulse-dot { position: absolute; left: 0; top: 0; width: 7px; height: 7px; display: none; border-radius: 50%;
  background: currentColor; }
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
.china-tip-when, .china-tip b { font-weight: 700; }
.china-tip-note + .china-tip-when { margin-top: 4px; padding-top: 4px; border-top: 1px solid var(--bs-border-color, #cfd3d8); }
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
  var pill = $(".china-pill"), scrim = $(".china-scrim"), actCard = $(".china-act-card"), beatCard = $(".china-beat");
  var heads = [$(".china-head-top"), $(".china-head-bottom")];
  var dotEl = {gdp: $(".china-dot-gdp"), stock: $(".china-dot-stock"), economy: $(".china-dot-economy")};
  var DAY = 86400000, YEAR = 31557600000, HOUR = 3600000;          // ms
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var hotBox = $(".china-hots"), pulseRing = $(".china-pulse"), pulseDot = $(".china-pulse-dot");
  var PL, M, TR, AN, G, S, PEERS, EV, ERAS, LEADERS, BANDS, ARROWS, FILLS, CHORDS, ERACHORDS, CLIMB, GAP, ANCHORS, ACTS, VIEWS, BEATS, FINAL, INTER, NOTES, TL, END;
  var T0, T1, TA, TB, TG, X0, X1, FONT;
  var L = null, GEO = null, P = null, FIT = null, STATE = null, lastW = 0, sent = {};
  var clock = 0, want = 0, playhead = 0, playing = false, played = false, raf = 0, busy = false, pending = null, speed = 1;
  var dismissed = {}, hurry = 0, hurrying = null;      // boxes the reader has waved away, and playback hurrying past one
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

  // ---- The timeline: acts, the breaks between them, the ending, and the clock -----
  // Playback is a pure function of one number, the CLOCK: seconds at 1x since
  // play was pressed. The timeline it runs along is the opening title card,
  // then each act with a break after it, then the ending (the chords, the gap,
  // the last box) and the pull-back to the whole chart. The 2x toggle only
  // makes the clock run faster, so it halves everything alike. Within an act
  // the playhead's date comes from the act's schedule (the table the Python
  // module built from its beats); everywhere else the date stands still.
  function actOf(T) {                      // the act that is playing at date T
    for (var k = 0; k < ACTS.length - 1; k++) if (T < ACTS[k].t1) return k;
    return ACTS.length - 1;
  }
  function ownAct(t) {                     // the act during which the playhead REACHES t (an act's last moment is its own)
    for (var k = 0; k < ACTS.length - 1; k++) if (t <= ACTS[k].t1) return k;
    return ACTS.length - 1;
  }
  function tauOf(k, T) {                   // seconds into act k at which the playhead is at T
    var A = ACTS[k], n = A.t.length - 1;
    if (T <= A.t0) return 0;
    if (T >= A.t[n]) return A.total;
    var j = upper(A.t, T) - 1;
    return A.tau[j] + (T - A.t[j]) / (A.t[j + 1] - A.t[j]) * (A.tau[j + 1] - A.tau[j]);
  }
  function timeOf(k, tau) {                // and back
    var A = ACTS[k], n = A.tau.length - 1;
    if (tau <= 0) return A.t0;
    if (tau >= A.total) return A.t1;
    var j = upper(A.tau, tau) - 1;
    return A.t[j] + (tau - A.tau[j]) / (A.tau[j + 1] - A.tau[j]) * (A.t[j + 1] - A.t[j]);
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
  // A VIEW is one x-range: each act has its own, and the last view is the
  // finished chart's. Within an act the axis is fixed, so a date has one
  // position for the whole act.
  function scaleIn(v, plotW) { return plotW / (VIEWS[v].r1 - VIEWS[v].r0); }
  function pxIn(v, t, plotW) { return (t - VIEWS[v].r0) * scaleIn(v, plotW); }
  function inView(v, t) { return t >= VIEWS[v].r0 && t <= VIEWS[v].r1; }
  // Does a box reaching from a to b px either side of the date t lie inside the figure in view v?
  function fitsView(v, t, a, b, plotW) {
    if (!inView(v, t)) return false;
    var x = pxIn(v, t, plotW);
    return x + a >= -L.margin.l + 1.5 && x + b <= plotW + L.margin.r - 1.5;
  }
  // How far left and right of a date's position a label may reach and still
  // lie inside the figure in EVERY view that shows the date, from the act that
  // reaches it to the finished chart. (Not strict: no limit. The label is then
  // hidden in the views it does not fit.)
  function limits(t, plotW, strict) {
    var left = -Infinity, right = Infinity;
    if (strict) for (var v = ownAct(Math.max(t, T0)); v < VIEWS.length; v++) {
      if (!inView(v, t)) continue;
      var x = pxIn(v, t, plotW);
      left = Math.max(left, -L.margin.l + 2 - x); right = Math.min(right, plotW + L.margin.r - 2 - x);
    }
    return [left, right];
  }
  // What is true in one view and not in the next changes across the break
  // between them: out of the first in its first half, into the second after.
  function blend(a, b, u) { return a === b ? a : a * (1 - clamp(2 * u, 0, 1)) + b * clamp(2 * u - 1, 0, 1); }
  // Everything about one moment of the timeline: the playhead's date T, the
  // x-range [r0, r1], which title card is up and how strongly, and how far
  // the things that arrive with an act or with the ending have arrived.
  //   va, vb, vu: the view on stage, the view it is moving to (the same one,
  //     except in a break or the pull-back) and how far it has moved.
  //   newAct / newAlpha: marks belonging to acts before newAct may show; those
  //     of newAct itself at strength newAlpha (the next ghosts arrive only
  //     after the axis has moved).
  //   eras, eraRates, climb, climbLabel, chords, rates, arrow, gap, last: the ending, piece by piece (0 to 1).
  //   inter, interAlpha: the arrow at the end of the interlude's act: how far drawn, and how strong.
  function stateAt(c) {
    c = clamp(c, 0, END);
    var tr = M.play.transition, en = M.play.ending, fade = M.play.card_fade, seg = TL[0];
    for (var i = 1; i < TL.length; i++) if (c >= TL[i].c0) seg = TL[i];
    var s = c - seg.c0, k = seg.act, last = ACTS.length - 1, whole = VIEWS.length - 1;
    var st = {clock: c, kind: seg.kind, act: k, done: c >= END, card: -1, cardAlpha: 0, newAct: k, newAlpha: 1,
              va: k, vb: k, vu: 0, chords: [0, 0], rates: [0, 0], eras: ERACHORDS.map(function () { return 0; }),
              eraRates: ERACHORDS.map(function () { return 0; }), climb: 0, climbLabel: 0, arrow: 0, gap: 0, last: 0,
              beat: null, beatAlpha: 0,
              inter: 0, interAlpha: 0, note: null, noteAlpha: 0, pulse: 0};
    if (st.done) {
      st.kind = "done"; st.T = T1; st.act = st.newAct = last; st.va = st.vb = whole;
      st.chords = [1, 1]; st.rates = [1, 1]; st.arrow = st.gap = 1;
      st.eras = st.eras.map(function () { return 1; }); st.eraRates = st.eraRates.map(function () { return 1; });
      st.climb = st.climbLabel = 1;
    } else if (seg.kind === "play") {
      st.T = timeOf(k, s);
    } else if (seg.kind === "inter") {     // at rest at the end of act k: the arrow is drawn up, then its box comes
      st.T = ACTS[k].t1; st.inter = clamp(s / M.play.interlude.arrow_seconds, 0, 1); st.interAlpha = 1;
    } else if (seg.kind === "open") {      // the first act's title card, over the first frame
      st.T = T0; st.card = 0;
      st.cardAlpha = clamp(Math.min(s / tr.card_in, (seg.dur - s) / tr.card_out), 0, 1);
      st.newAlpha = clamp((s - tr.card_in - tr.hold) / tr.ghost, 0, 1);
    } else if (seg.kind === "break") {     // at rest at the end of act k: card in, hold, the axis moves, ghosts, card out
      var held = tr.card_in + tr.hold;
      st.T = ACTS[k].t1; st.card = k + 1;
      st.cardAlpha = clamp(Math.min(s / tr.card_in, (seg.dur - s) / tr.card_out), 0, 1);
      st.vb = k + 1; st.vu = smooth((s - held) / tr.move);
      st.newAct = k + 1; st.newAlpha = clamp((s - held - tr.move) / tr.ghost, 0, 1);
      // The interlude's arrow fades as the title card comes up.
      if (k === M.play.interlude.act) { st.inter = 1; st.interAlpha = clamp(1 - s / tr.card_in, 0, 1); }
    } else if (seg.kind === "end") {       // in the whole chart's view: the top panel's chords and arrow, then the bottom's; the last box
      var E = seg.marks;
      st.T = T1; st.newAct = last; st.va = st.vb = whole;
      st.eras = E.era.map(function (t) { return clamp((s - t) / en.chord, 0, 1); });
      st.eraRates = E.eraRate.map(function (t) { return clamp((s - t) / en.label, 0, 1); });
      st.climb = clamp((s - E.climb) / en.arrow, 0, 1); st.climbLabel = clamp((s - E.climbLabel) / en.label, 0, 1);
      st.chords = E.chord.map(function (t) { return clamp((s - t) / en.chord, 0, 1); });
      st.rates = E.rate.map(function (t) { return clamp((s - t) / en.label, 0, 1); });
      st.arrow = clamp((s - E.arrow) / en.arrow, 0, 1);
      st.gap = clamp((s - E.gap) / en.label, 0, 1);
      st.last = clamp(Math.min((s - E.box) / fade, (E.boxOut + fade - s) / fade), 0, 1);
    } else {                               // the pull-back, as the data ends: from the last act's view to the whole chart
      st.T = T1; st.newAct = last; st.vb = whole; st.vu = smooth(s / seg.dur);
    }
    var A = VIEWS[st.va], B = VIEWS[st.vb];
    st.r0 = A.r0 + (B.r0 - A.r0) * st.vu; st.r1 = A.r1 + (B.r1 - A.r1) * st.vu;
    // A beat's box fades in as the clock reaches its first moment (the playhead at the box's date, or
    // within a month of it), is up until its second, and then fades out.
    if (!st.done && seg.kind !== "end" && seg.kind !== "pull") BEATS.forEach(function (b) {
      var a = Math.min(clamp((c - b.c0) / fade, 0, 1), clamp((b.c1 - c) / fade + 1, 0, 1));
      if (a > st.beatAlpha) { st.beatAlpha = a; st.beat = b; }
    });
    // An annotation that is a beat: playback slows for it (the schedule), its point is marked, and one
    // ring spreads from it as the playhead arrives.
    if (seg.kind === "play") NOTES.forEach(function (n) {
      var a = Math.min(clamp((c - n.c0) / fade, 0, 1), clamp((n.c1 - c) / fade + 1, 0, 1));
      if (a > st.noteAlpha) { st.note = n; st.noteAlpha = a; st.pulse = clamp((c - n.c0) / M.play.note.pulse, 0, 1); }
    });
    return st;
  }
  // What is in view: the stage's range while the play is on, otherwise whatever
  // the reader has zoomed or panned to.
  function view() {
    if (!STATE.done) return [STATE.r0, STATE.r1];
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
  // scale of the FINISHED chart, where the lines stand closest: in every act's
  // view and under a zoom they are only further apart, so what fits there
  // fits throughout. What differs from view to view is where the figure's
  // edges fall: with `late` 0 a label must lie inside the figure in every view
  // that shows its line (limits); with Infinity it need not, and is hidden in
  // the views it does not fit. `says` is what each label reads. Returns null
  // if nothing fits.
  var SPOTS = [0.5, 1, 0.75, 0.625, 0.375, 0.25, 0.875, 0.125, 0];
  function reachOf(x, w, spot) {             // where a label starts and ends, for a line at x
    return spot === 1 ? [x - 3 - w, x - 3] : spot === 0 ? [x + 3, x + 3 + w] : [x - spot * w, x + (1 - spot) * w];
  }
  function placeStrip(evs, says, plotW, font, rows, late) {
    var scale = plotW / (X1 - X0), lo = -L.margin.l + 2, hi = plotW + L.margin.r - 2;
    var it = evs.map(function (e, i) {
      return {x: (e.t - X0) * scale, w: textSize(says[i], font).w + 4, lim: limits(e.t, plotW, late === 0)};
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
        var ok = s[0] >= lo && s[1] <= hi && s[0] - x >= it[i].lim[0] && s[1] - x <= it[i].lim[1]
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
  // figure in every view that shows its line, in the largest type and then the
  // fewest rows that work; failing that, in the smallest type; only then with
  // labels that are hidden in the views they do not fit. At each step the labels are
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
    // What to try, in order: [whether a label may be hidden in some views, in which type and rows].
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
  // fixed pixel offset from its tip, and the views differ in scale (the last
  // act's is closer in than the finished chart's), so every position is
  // checked in each view that shows the arrow, from its own act on. No text
  // may lie on one of the chords that close the animation: a text that would
  // is moved below it ("under") or tried elsewhere ("above"). Each text goes
  // where it fits in every such view if it can (otherwise it shows only where
  // it fits), then in the fewest lines. A text may reach left of where the
  // data begin, over the plain band, but never over the hatched band or an
  // event's line there. Returns null if any of them cannot be placed.
  function placeArrows(font) {
    var plotW = GEO.plotW, ppb = GEO.ppb, zeroY = M.view.y2[1] * ppb, c = 5, placed = [], whole = VIEWS.length - 1;
    var waits = [0, Infinity];
    // In each view: where the data's neighbours on the left end (the hatched band; the last event line before the data).
    var edges = VIEWS.map(function (V, v) {
      var edge = 0;
      BANDS.forEach(function (bd) { if (bd.kind === "none") edge = Math.max(edge, pxIn(v, bd.t1, plotW)); });
      EV.forEach(function (e) { if (e.on && !e.tick && e.panel === "stocks" && e.t < TA) edge = Math.max(edge, pxIn(v, e.t, plotW)); });
      return edge;
    });
    function views(t) {                    // the views that show the date t, from the act that reaches it on
      var out = [];
      for (var v = ownAct(t); v < VIEWS.length; v++) if (inView(v, t)) out.push(v);
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
    function inside(q, v) {                // in view v: inside the plot, and right of the data's neighbours on the left
      var x = pxIn(v, q.t, plotW);
      return x + q.dx0 >= edges[v] + 6 && x + q.dx1 <= plotW - 3;
    }
    function clear(q) {
      return placed.every(function (o) {
        if (q.top >= o.bottom + 6 || o.top >= q.bottom + 6) return true;
        return views(Math.max(q.t, o.t)).every(function (v) {
          var xq = pxIn(v, q.t, plotW), xo = pxIn(v, o.t, plotW);
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
        var A = ARROWS[n], tipX = pxIn(whole, A.t, plotW), tipY = zeroY - A.y * ppb, vs = views(A.t), found = null;
        for (var w8 = 0; w8 < waits.length && !found; w8++) for (var k = skip[n]; k < A.wraps.length && !found; k++) {
          var sz = textSize(A.wraps[k], font), W = sz.w + 8, H = sz.h + 6;
          for (var step = 0; step <= 120 && !found; step++) for (var sign = -1; sign <= 1 && !found; sign += 2) {
            if (!step && sign > 0) continue;
            var q = {t: A.t, dx0: sign * step * 3 - W / 2}, hi = Infinity, lo = -Infinity, top;
            q.dx1 = q.dx0 + W;
            if (!inside(q, whole) || (waits[w8] === 0 && !vs.every(function (v) { return inside(q, v); }))) continue;
            var spans = CHORDS.map(function () { return [Infinity, -Infinity]; });
            for (var j = 0; j < vs.length; j++) {
              var d = reach(A.t, scaleIn(vs[j], plotW), q.dx0 - c, q.dx1 + c);
              hi = Math.min(hi, d.hi); lo = Math.max(lo, d.lo);
              d.spans.forEach(function (sp, m) { spans[m] = [Math.min(spans[m][0], sp[0]), Math.max(spans[m][1], sp[1])]; });
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
            q.top = top; q.bottom = top + H;
            if (!clear(q)) continue;
            q.text = A.wraps[k]; q.ax = (q.dx0 + q.dx1) / 2; q.ay = top + H / 2 - tipY;
            q.a = tipX + q.dx0; q.b = tipX + q.dx1; q.tipX = tipX; q.tipY = tipY;    // on the finished chart
            q.fits = VIEWS.map(function (V, v) { return inView(v, A.t) && inside(q, v); });
            q.late = q.fits[ownAct(A.t)] ? 0 : 1;
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
      if (ok) return {t: X0 + x / scale, w: w};
    }
    return null;
  }

  // ---- Rate arrows ------------------------------------------------------------------
  // Over a span of the economy's points, from above its first to above its last: parallel to the
  // straight line between them, lifted M.play.rate.lift px clear of the highest point between; its
  // rate over its middle, lifted by the arrow's rise across half the label's width and 6 px more,
  // so that the two never touch. And where the zero line would run through the rate, the rate
  // stands just above the zero line instead. (In the view v of the box's act.)
  function rateGeometry(R, v, plotW) {
    var sz = textSize(R.text, L.rate_font), t0 = toMs(R.start), t1 = toMs(R.end);
    var slope = Math.abs(R.y1 - R.y0) * GEO.ppb / ((t1 - t0) * scaleIn(v, plotW)), lift = R.dev + M.play.rate.lift / GEO.ppb;
    var yshift = 6 + slope * sz.w / 2, base = ((R.y0 + R.y1) / 2 + lift) * GEO.ppb;      // px above the zero line
    if (base + yshift < 4 && base + yshift + sz.h > -4) yshift = 4 - base;
    return {t0: t0, t1: t1, y0: R.y0, y1: R.y1, lift: lift, w: sz.w, h: sz.h, yshift: yshift};
  }
  function ratesOf(b) { return [b.rate, b.reference].filter(function (R) { return R; }); }

  // ---- The top panel's labels at the ending ------------------------------------------
  // Each era's rate near the middle of its chord, in the whole chart's view: along the chord, above
  // or below it, on one line or broken, whichever is nearest its middle and clear of the line, the
  // chords, the event lines, the ticks, the panel's name, the anchor's marker, the labels by the zero
  // line, and the rates placed before it. Where there is no such place, in the gutter right of the
  // plot, as near its chord's height as the climb's label there allows (each on as few lines as the
  // gutter's width allows). The climb's label stands in the gutter beside its arrow. Where there is
  // no gutter (a phone), each goes in the key. Sets ERACHORDS[n].place and CLIMB.place (null: the
  // key) and, through A (fit's), the annotations.
  function placeEras(plotW, A) {
    var whole = VIEWS.length - 1, sc = scaleIn(whole, plotW), X = function (t) { return pxIn(whole, t, plotW); };
    var Y = function (v) { return (M.view.y[1] - v) * GEO.ppb; }, f = L.rate_font, room = GEO.topH;
    // (Measured in the bold they are set in, every line of them.)
    function bold(html) {
      ctx.font = "700 " + f + "px " + FONT;
      var lines = String(html).split("<br>"), w = 0;
      lines.forEach(function (ln) { w = Math.max(w, ctx.measureText(ln.replace(/<[^>]+>/g, "")).width); });
      return {w: w + 2, h: lines.length * f * 1.3};
    }
    var chordAt = function (ec, T) { return ec.y0 + (ec.y1 - ec.y0) * (T - ec.t0) / (ec.t1 - ec.t0); };
    var lines = EV.filter(function (e) { return e.panel === "economy" && e.on && !e.tick && inView(whole, e.t); })
      .map(function (e) { return X(e.t); });
    var taken = [{a: -L.margin.l, b: GEO.head[0].b + 4, top: 0, bottom: GEO.head[0].h + 4}];
    var ht = FIT.hints.top;
    if (ht && ht.fits[whole]) taken.push({a: X(ht.t) - 2, b: X(ht.t) + ht.w + 2, top: Y(0) - 18, bottom: Y(0) + 18});
    ANCHORS.forEach(function (a) { if (a.panel === "economy") taken.push({a: X(a.t) - 9, b: X(a.t) + 9, top: Y(0) - 9, bottom: Y(0) + 9}); });
    function offTheLines(q) {
      for (var x = q.a - 3; x <= q.b + 3; x += 2) {
        var T = VIEWS[whole].r0 + x / sc, g = at(G.t, G.y, T), ys = g === null ? [] : [Y(g)];
        ERACHORDS.forEach(function (ec) { if (T >= ec.t0 && T <= ec.t1) ys.push(Y(chordAt(ec, T))); });
        if (ys.some(function (y) { return y > q.top - 5 && y < q.bottom + 5; })) return false;
      }
      return true;
    }
    function clear(q) {
      if (q.a < 3 || q.b > plotW - 3 || q.top < L.tick.down + 4 || q.bottom > room - 3) return false;
      if (lines.some(function (x) { return x > q.a - 4 && x < q.b + 4; })) return false;
      if (taken.some(function (o) { return q.a < o.b + 4 && o.a < q.b + 4 && q.top < o.bottom + 4 && o.top < q.bottom + 4; })) return false;
      return offTheLines(q);
    }
    function toData(x, y) { return {x: iso(VIEWS[whole].r0 + x / sc), y: M.view.y[1] - y / GEO.ppb}; }
    var gx = X(T1) + L.end.label, gw = plotW + L.margin.r - 3 - gx, inGutter = [];
    function narrowest(wraps) {
      for (var k = 0; k < wraps.length; k++) if (bold(wraps[k]).w <= gw) return wraps[k];
      return null;
    }
    ERACHORDS.forEach(function (ec) {
      ec.place = null;
      if (!FIT.ends) return;
      var x0 = X(ec.t0), x1 = X(ec.t1), mid = (x0 + x1) / 2, best = null;
      ec.wraps.forEach(function (w, k) {
        var sz = bold(w), W = sz.w, h = sz.h;
        for (var xc = x0 + W / 2; xc <= x1 - W / 2; xc += 3) {
          var yc = Y(chordAt(ec, VIEWS[whole].r0 + xc / sc));
          [1, -1].forEach(function (side) {
            for (var off = 5; off <= 120; off += 5) {
              var top = side > 0 ? yc + off : yc - off - h, cost = Math.abs(xc - mid) + off + 40 * k;
              if (best && cost >= best.cost) return;
              var q = {a: xc - W / 2, b: xc + W / 2, top: top, bottom: top + h};
              if (clear(q)) { best = {cost: cost, q: q, text: w, x: xc}; return; }
            }
          });
        }
      });
      if (!best) { inGutter.push(ec); return; }
      taken.push(best.q);
      var d = toData(best.x, (best.q.top + best.q.bottom) / 2);
      ec.place = {gutter: false, text: best.text, rect: best.q};
      A(ec.annotation, {text: best.text, x: d.x, y: d.y, xshift: 0, xanchor: "center", yanchor: "middle", align: "center", "font.size": f});
    });
    // The gutter: the climb's label beside its arrow's middle, then each rate that found no place in
    // the plot, as near its chord's middle height as it can be without touching another.
    CLIMB.place = null;
    if (!FIT.ends) return;
    var stack = [], ct = narrowest(CLIMB.wraps);
    if (ct) {
      var ch = textSize(ct, f).h, cy = clamp(Y(CLIMB.value / 2), ch / 2 + 2, room - ch / 2 - 2);
      CLIMB.place = {gutter: true, text: ct, rect: {a: gx, b: gx + textSize(ct, f).w + 2, top: cy - ch / 2, bottom: cy + ch / 2}};
      stack.push(CLIMB.place.rect);
      A(CLIMB.label, {text: ct, y: M.view.y[1] - cy / GEO.ppb, xshift: L.end.label, "font.size": f});
    }
    inGutter.forEach(function (ec) {
      var text = narrowest(ec.wraps);
      if (!text) return;
      var h = bold(text).h, want = Y((ec.y0 + ec.y1) / 2), got = null;
      for (var d = 0; d <= room && got === null; d += 2) [want + d, want - d].forEach(function (y) {
        if (got !== null || y - h / 2 < 2 || y + h / 2 > room - 2) return;
        if (stack.every(function (o) { return y + h / 2 + 4 <= o.top || y - h / 2 - 4 >= o.bottom; })) got = y;
      });
      if (got === null) return;
      var rect = {a: gx, b: gx + bold(text).w, top: got - h / 2, bottom: got + h / 2};
      stack.push(rect);
      ec.place = {gutter: true, text: text, rect: rect};
      A(ec.annotation, {text: text, x: iso(T1), y: M.view.y[1] - got / GEO.ppb, xshift: L.end.label, xanchor: "left",
                        yanchor: "middle", align: "left", "font.size": f});
    });
  }

  // ---- The ending's chords, and the boxes of narration --------------------------------
  // The two chords, as px down from the top of the bottom panel at a px column
  // of the finished chart.
  function chordY(ch, x) {
    var whole = VIEWS.length - 1, x0 = pxIn(whole, TA, GEO.plotW), zeroY = M.view.y2[1] * GEO.ppb;
    return zeroY - ch.value * clamp((x - x0) / (pxIn(whole, ch.t, GEO.plotW) - x0), 0, 1) * GEO.ppb;
  }
  // The ways a beat's box may be set, best first. A text box: at the usual
  // width, then narrower (and so taller), for a crowded panel or a phone. A
  // picture card: the picture beside the words (where there is a gutter: not
  // on a phone), then above them, each at the sizes the layout allows,
  // largest first (a size is the picture's longer side: an upright picture,
  // like a magazine cover, is that tall); and at last with no picture, as a
  // text box.
  function ways(b, plotW) {
    var out = [], width = Math.min(L.card.width, plotW - 16);
    if (b.picture) {
      var wide = function (px) { return b.picture.aspect && b.picture.aspect < 1 ? Math.round(px * b.picture.aspect) : px; };
      // (A picture may be capped below the layout's sizes: then it is shown at its cap.)
      var cap = b.picture.max_px, sizes = cap ? L.card.pictures.filter(function (px) { return px <= cap; }) : L.card.pictures;
      if (cap && !sizes.length) sizes = [cap];
      if (!L.card.below) sizes.forEach(function (px) { out.push({kind: "side", img: wide(px), text: 190}); });
      sizes.forEach(function (px) { out.push({kind: "stacked", img: wide(px), width: wide(px) + 19}); });
    }
    if (!L.card.below) [width, 210, 170, 135].forEach(function (px) { if (px === width || px < width - 25) out.push({kind: "text", width: px}); });
    return out;
  }
  // Where the plot is too small to hold a text box clear of the playhead and
  // the data (a phone), the box goes directly under the plot instead, across
  // the figure's width, over the key: nothing in the plot is covered. (A
  // picture card that found no place in the plot goes there too, as words.)
  function under(b) {
    var how = {kind: "text", width: lastW - 12};
    dress(b, how);
    return {a: 6 - L.margin.l, top: GEO.plotH + L.margin.b + 8, k: 1, side: 0, spans: false, below: true,
            how: how, w: beatCard.offsetWidth, h: beatCard.offsetHeight};
  }
  // Everything a box must keep off while it is up, in the view of its act, in
  // px from the plot's top-left corner: the panels' names, and whatever labels
  // and annotations are showing by then (`rects`, with an arrow's shaft where
  // it has one); and the strip of labels between the panels (`strip`), which a
  // card tall enough to run from one panel into the other must keep off too.
  function inTheWay(b, plotW) {
    var v = b.view !== undefined ? b.view : b.act, sc = scaleIn(v, plotW), y1 = GEO.topH + GEO.gap, zero = [M.view.y[1] * GEO.ppb, y1 + M.view.y2[1] * GEO.ppb];
    var rects = [], strip = [], X = function (t) { return pxIn(v, t, plotW); };
    GEO.head.forEach(function (h, k) { rects.push({a: 0, b: h.b + 2, top: k ? y1 : 0, bottom: (k ? y1 : 0) + h.h}); });
    BANDS.forEach(function (bd) {
      var s = bd.spots[v];
      if (s && s.t <= b.until) rects.push({a: s.a, b: s.b, top: y1 + s.top, bottom: y1 + s.top + s.h});
    });
    if (FIT.hints.bottomFits[v] && TA <= b.until)
      rects.push({a: X(TA) - 12 - FIT.hints.bottomW, b: X(TA) - 8, top: zero[1] - 20, bottom: zero[1] + 20});
    var ht = FIT.hints.top;
    if (ht && ht.fits[v] && ht.show[v] <= b.until) rects.push({a: X(ht.t), b: X(ht.t) + ht.w, top: zero[0] - 20, bottom: zero[0] + 20});
    ARROWS.forEach(function (a) {
      var q = a.box;
      if (q && q.fits[v] && a.t <= b.until)
        rects.push({a: X(a.t) + q.dx0, b: X(a.t) + q.dx1, top: y1 + q.top, bottom: y1 + q.bottom, tipX: X(a.t), tipY: y1 + q.tipY});
    });
    FILLS.forEach(function (f) {
      var q = f.box;
      if (q && q.fits[v] && q.t <= b.until) rects.push({a: X(q.at) - q.w / 2, b: X(q.at) + q.w / 2, top: y1 + q.top, bottom: y1 + q.bottom});
    });
    ANCHORS.forEach(function (a) {
      if (a.t <= b.until) rects.push({a: X(a.t) - 8, b: X(a.t) + 8, top: zero[a.panel === "economy" ? 0 : 1] - 8, bottom: zero[a.panel === "economy" ? 0 : 1] + 8});
    });
    // (The last box: the eras' rates placed in the plot, which are up by then.)
    if (b.last) ERACHORDS.forEach(function (ec) { if (ec.place && !ec.place.gutter) rects.push(ec.place.rect); });
    // The box's rate arrows and their rates, which are up with it.
    ratesOf(b).forEach(function (spec) {
      var R = rateGeometry(spec, v, plotW), Y = function (y) { return zero[0] - y * GEO.ppb; };
      var ya = Y(R.y0 + R.lift), yb = Y(R.y1 + R.lift), mx = X((R.t0 + R.t1) / 2), my = Y((R.y0 + R.y1) / 2 + R.lift);
      rects.push({a: X(R.t0) - 4, b: X(R.t1) + 4, top: Math.min(ya, yb) - 4, bottom: Math.max(Y(R.y0), Y(R.y1)) + 4});
      rects.push({a: mx - R.w / 2 - 3, b: mx + R.w / 2 + 3, top: my - R.yshift - R.h - 2, bottom: my});
    });
    // The labels in the strip between the panels: those reached by then, and the ghost of the next.
    var ahead = EV.filter(function (e) { return e.panel === "stocks" && !e.tick && e.on && e.t > b.until && e.act === b.act; })
      .sort(function (p, q) { return p.t - q.t; })[0];
    EV.forEach(function (e) {
      if (e.panel !== "stocks" || e.annotation === null || !e.labelled || !e.fits[v] || !(e.t <= b.until || e === ahead)) return;
      strip.push({a: X(e.t) + e.ext[0], b: X(e.t) + e.ext[1]});
    });
    return {rects: rects, strip: strip};
  }
  // Is the box q (px from the plot's top-left) clear of the data drawn by the
  // time the beat's box comes down? In the top panel, of the economy's line
  // (and, at the ending, the eras' chords); in the bottom one, of both lines
  // and the fill between them, and, at the ending, of the chords. The dot at the playhead is on the lines, so it is
  // covered by this too.
  function offTheData(q, b, plotW) {
    var v = b.view !== undefined ? b.view : b.act, V = VIEWS[v], sc = scaleIn(v, plotW), y1 = GEO.topH + GEO.gap, c = 7;
    var zero = [M.view.y[1] * GEO.ppb, y1 + M.view.y2[1] * GEO.ppb], top = q.top < GEO.topH, bottom = q.bottom > y1;
    for (var x = q.a - c; x <= q.b + c; x += 2) {
      var T = V.r0 + x / sc;
      if (T > b.until) break;
      if (top) {
        var g = at(G.t, G.y, T), ys0 = g === null ? [] : [zero[0] - g * GEO.ppb];
        if (b.last) ERACHORDS.forEach(function (ec) {
          if (T >= ec.t0 && T <= ec.t1) ys0.push(zero[0] - (ec.y0 + (ec.y1 - ec.y0) * (T - ec.t0) / (ec.t1 - ec.t0)) * GEO.ppb);
        });
        if (ys0.some(function (y) { return y > q.top - c && y < q.bottom + c; })) return false;
      }
      if (bottom) {
        var s = at(S.t, S.s, T), e = at(S.t, S.e, T);
        if (s === null) continue;
        var ys = [zero[1] - s * GEO.ppb, zero[1] - e * GEO.ppb];
        if (b.last) CHORDS.forEach(function (ch) { ys.push(zero[1] - ch.value * (T - TA) / (ch.t - TA) * GEO.ppb); });
        if (Math.max.apply(null, ys) > q.top - c && Math.min.apply(null, ys) < q.bottom + c) return false;
      }
    }
    return true;
  }
  // Where a beat's box goes: in the empty space nearest the playhead. It keeps
  // off the playhead itself for as long as it is up (the stretch of the axis
  // the playhead covers meanwhile), off the data and the dots, and off every
  // label and annotation showing by then. Of the places left it takes the one
  // nearest the playhead, in the beat's own panel (economy boxes in the top
  // one, market boxes in the bottom one: its act's, unless it names one; the
  // other panel, or across both, only if there is no room in its own) and
  // towards the top of that panel, and near where the box before it in the
  // act stood, so that boxes do not jump about. A text box stays inside one
  // panel; a picture card may run from one into the other. The beat's ways of
  // being set are tried in turn until one has a place near enough. Returns
  // the place (a, top: px from the plot's top-left; `fallback` if it is not in
  // its own panel) and the way, or null.
  function placeBox(b, plotW, before, pictureOnly) {
    var v = b.view !== undefined ? b.view : b.act, sc = scaleIn(v, plotW), y1 = GEO.topH + GEO.gap, prefer = b.panel === "economy" ? 0 : 1;
    var panels = [{y0: 0, y1: GEO.topH}, {y0: y1, y1: GEO.plotH}], right = plotW + L.margin.r - 6;
    // The playhead's sweep while the box is up. (The last box has no playhead to keep off: it keeps left of the ending.)
    var s0 = b.last ? pxIn(v, T1, plotW) - 14 : pxIn(v, b.since, plotW) - 12, s1 = b.last ? Infinity : pxIn(v, b.until, plotW) + 12;
    var way = inTheWay(b, plotW);
    if (L.card.below && !b.picture) return under(b);
    // (A picture card keeps its picture if it can, in the other panel if need be, before it is set as words.)
    var best = null, rounds = b.picture ? [[true, true], [false, true], [true, false], [false, false]] : [[true, false], [false, false]];
    if (pictureOnly) rounds = rounds.slice(0, 2);
    rounds.some(function (r) { best = search(r[0], r[1]); if (best && !r[0]) best.fallback = true; return !!best; });
    return best || (L.card.below ? under(b) : null);
    function search(own, pictured) {
    var best = null;
    ways(b, plotW).filter(function (how) { return (how.kind !== "text") === pictured; }).some(function (how, rank) {
      dress(b, how);
      var W = beatCard.offsetWidth, H = beatCard.offsetHeight, tries = [];
      if (H > 0.72 * GEO.plotH) return false;
      panels.forEach(function (pn, k) {
        if (own && k !== prefer) return;
        var lo = pn.y0 + L.tick.down + 3, hi = pn.y1 - 4 - H, spans = false;
        if (hi < lo) {                       // too tall for the panel: a picture card may run into the other one
          if (how.kind === "text" || (own && !b.cross)) return;
          spans = true; lo = k ? Math.max(4, GEO.plotH - 4 - H - 60) : L.tick.down + 3; hi = k ? GEO.plotH - 4 - H : Math.min(GEO.plotH - 4 - H, lo + 60);
          if (hi < lo) return;
        }
        for (var top = lo; top <= hi; top += 6) {
          var cost = (k === prefer ? 0 : 130) + (spans ? 50 : 0) + 0.3 * (top - lo);
          if (before && before.k === k) cost += 0.25 * Math.abs(top - before.top);
          for (var a = s1 + 2; a + W <= right; a += 8)
            tries.push({a: a, top: top, k: k, spans: spans, side: 1, cost: cost + (a - s1) + (before && before.side !== 1 ? 30 : 0)});
          for (a = s0 - 2 - W; a >= 4; a -= 8)
            tries.push({a: a, top: top, k: k, spans: spans, side: -1, cost: cost + (s0 - a - W) + (before && before.side !== -1 ? 30 : 0)});
        }
      });
      tries.sort(function (p, q) { return p.cost - q.cost; });
      for (var n = 0; n < tries.length; n++) {
        var q = tries[n];
        if (best && q.cost + 45 * rank >= best.cost) break;
        q.b = q.a + W; q.bottom = q.top + H;
        if (!clearOf(q, way.rects) || !offTheData(q, b, plotW)) continue;
        if (q.spans && way.strip.some(function (s) { return q.a < s.b + 6 && s.a < q.b + 6; })) continue;
        q.cost += 45 * rank; q.how = how; q.w = W; q.h = H;
        best = q;
        break;
      }
      // Good enough: near the playhead, in a way that keeps the picture if there is one.
      return !!best && best.cost < 170 + 45 * rank;
    });
    return best;
    }
  }

  // ---- Everything in the layout that depends on the moment and the window ---------
  // A pure function of a moment of the timeline (stateAt) and the visible
  // window [V0, V1]: which events, bars, bands and annotations are showing and
  // how strongly, how far each bar and band has grown, where the playhead is,
  // and how much of the ending is drawn. Stateless, so scrubbing, playing and
  // zooming all agree. Within an act nothing here moves but the playhead and
  // what it reveals: a leader's or an era's label is pinned to the start of
  // its bar, an event's to its line, a band's to one spot per view. A label
  // that fits one view and not the next goes, or comes, as the axis moves
  // between them (`fits`); under a reader's own zoom of the finished chart it
  // is simply there or not.
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
    function fits(list) { return blend(list[st.va] ? 1 : 0, list[st.vb] ? 1 : 0, st.vu); }

    // Events. A tick appears when reached. A labelled event that has been
    // reached comes up to full strength; the NEXT one in each strip, if it
    // belongs to the act on stage, waits as a ghost: faint, and already where
    // it will be. Only ever one: an event that shares another's label is the
    // ghost (its line alone) once the one that carries the label is reached.
    // A label shows only where its whole box is inside the figure. A line is
    // two strokes: one through the panel, and a stalk from the panel's top up
    // to its label. Where the first would run through the panel's name (the
    // last act's view puts three events there) it starts below the name
    // instead. A beat can pick an event out, once reached, while its box is up.
    var next = {}, faint = done || st.kind === "end" ? M.final_line_share : st.kind === "pull" ? 1 - (1 - M.final_line_share) * st.vu : 1;
    if (!done) EV.forEach(function (e) {
      if (e.tick || !e.on || st.clock >= e.clock) return;
      if (!next[e.panel] || e.t < next[e.panel].t) next[e.panel] = e;
    });
    EV.forEach(function (e, n) {
      var x = px(e.t), k = e.panel === "economy" ? 0 : 1, head = GEO.head[k];
      e.ghost = false;
      if (e.tick) { var seen = e.on ? since(e.t) : 0; H(e.shape, {visible: seen > 0, opacity: seen}); return; }
      var lead = e.lead === null ? e : EV[e.lead], a = 0, b = 0;
      if (e.on && (done || st.clock >= e.clock)) a = play.ghost + (1 - play.ghost) * since(e.t);
      else if (next[e.panel] === e) { a = play.ghost * gate(e.act); e.ghost = a > 0; }
      var hot = st.beat && st.beat.event === n && !dismissed[st.beat.id] ? st.beatAlpha * since(e.t) : 0;
      if (lead === e && e.labelled) b = a * (done ? (x + e.ext[0] >= lo - 0.5 && x + e.ext[1] <= hi + 0.5 ? 1 : 0) : fits(e.fits));
      // (On the finished chart the lines step back, to M.final_line_share of their strength, as the view pulls back.)
      var strength = a * (M.event_line_opacity + (0.85 - M.event_line_opacity) * hot) * faint;
      H(e.shape, {visible: a > 0, opacity: strength, y1: 1 - (x > head.a - 4 && x < head.b + 4 ? head.h : 0) / GEO.panelH[k]});
      H(e.stalk, {visible: a > 0 && e.labelled, opacity: strength, y1: 1 + e.stem / GEO.panelH[k]});
      if (e.annotation !== null) A(e.annotation, {visible: b > 0, opacity: b});
    });
    // The bottom panel's zero line, and the small labels either side of each zero line.
    var az = since(TA), zf = done ? (FIT.hints.bottom && px(TA) - 10 - FIT.hints.bottomW >= 2 ? 1 : 0) : fits(FIT.hints.bottomFits);
    H(M.zero.bottom, {visible: az > 0, opacity: az});
    ["zero_up", "zero_down"].forEach(function (r) { A(AN[r], {visible: az * zf > 0, opacity: az * zf}); });
    var ht = FIT.hints.top, ag = 0;
    if (ht && done) ag = px(ht.t) >= 2 && px(ht.t) + ht.w <= GEO.plotW - 2 ? 1 : 0;
    else if (ht) ag = blend(ht.fits[st.va] ? since(ht.show[st.va]) : 0, ht.fits[st.vb] ? since(ht.show[st.vb]) : 0, st.vu);
    ["gap_up", "gap_down"].forEach(function (r) { A(AN[r], {visible: ag > 0, opacity: ag}); });
    ARROWS.forEach(function (a) {
      var q = a.box, x = px(a.t), f = 0;
      // (Under a zoom: clear of the plot's edges, and of the panel's name if it is level with it.)
      if (q && done) f = x + q.dx0 >= (q.top < 28 ? GEO.head[1].b + 6 : 2) && x + q.dx1 <= hi + 0.5 ? 1 : 0;
      else if (q) f = since(a.t) * fits(q.fits);
      A(AN[a.role], {visible: f > 0, opacity: f});
    });
    FILLS.forEach(function (f) {
      var q = f.box, a = 0;
      if (q && done) a = px(q.at) - q.w / 2 >= 2 && px(q.at) + q.w / 2 <= GEO.plotW - 2 ? 1 : 0;
      else if (q) a = since(q.t) * fits(q.fits);
      A(AN[f.role], {visible: a > 0, opacity: a});
    });

    // Bars grow with the playhead; Plotly cuts them off at the plot's edge, and
    // a bar that runs off the left edge gets its marker there.
    var eraNow = done ? eraLabels(V0, V1, GEO.plotW, ERAS.map(function (e) { return e.on; })) : null;
    ERAS.forEach(function (e, n) {
      var start = Math.max(e.t0, V0), end = Math.min(e.t1, T, V1);
      e.cut = e.t0 < V0; e.a = px(start); e.b = px(end);
      e.live = e.on && e.b > e.a + 0.5;
      H(e.bar, {visible: e.live, x1: iso(Math.max(e.t0, Math.min(e.t1, T)))});
      H(e.tip, {visible: e.live && e.cut});
      var f = !e.live ? 0 : done ? (eraNow[n] ? 1 : 0) : since(e.t0) * fits(e.fits);
      e.text = f > 0;
      A(e.annotation, f > 0 ? {visible: true, opacity: f, x: iso(Math.max(e.t0, V0 + HOUR))} : {visible: false});
    });
    // A leader's name shows once its segment is long enough to hold it: with
    // room to spare, or (a short segment) only just, the name set a little
    // closer to the segment's start.
    LEADERS.forEach(function (l) {
      var start = Math.max(l.t0, V0), end = Math.min(l.t1, T, V1), f = 0, inset = 5;
      l.cut = l.t0 < V0; l.a = px(start); l.b = px(end);
      l.live = l.b > l.a + 0.5;
      H(l.shape, {visible: l.live, x1: iso(Math.max(l.t0, Math.min(l.t1, T, X1)))});
      H(l.tip, {visible: l.live && l.cut});
      if (l.live && done) {
        var room = l.b - l.a - l.w;
        f = room >= 4 ? 1 : 0; inset = room >= 12 ? 5 : room / 2;
      } else if (l.live) {
        f = blend(l.from[st.va] === null ? 0 : since(l.from[st.va]), l.from[st.vb] === null ? 0 : since(l.from[st.vb]), st.vu);
        inset = l.inset[st.vu < 0.5 ? st.va : st.vb];
      }
      l.text = f > 0; l.at = inset;
      A(l.annotation, f > 0 ? {visible: true, opacity: f, x: iso(Math.max(l.t0, V0 + HOUR)), xshift: inset} : {visible: false});
    });

    // Access bands grow with the playhead too. (The hatched one is a trace:
    // render() grows it.) During the play each label has one spot per view, in
    // the middle of what that view shows of its band, and appears once the
    // band has grown under it; on the finished chart it is centred in whatever
    // part of the band is in view, in the widest wording that fits there.
    BANDS.forEach(function (bd) {
      var from = Math.max(bd.t0, X0), start = Math.max(bd.t0, V0), end = Math.min(bd.t1, T, V1), a = px(start), b = px(end);
      var live = b > a + 0.5, text = null;
      if (bd.shape !== null) H(bd.shape, {visible: T > from, x1: iso(Math.max(from, Math.min(bd.t1, T)))});
      if (bd.early) H(bd.early.shape, {visible: T > from, x1: iso(Math.max(from, Math.min(bd.early.t1, T)))});
      bd.span = live ? [a, b] : null;
      if (!done) {
        var spot = bd.spots[st.vu < 0.5 ? st.va : st.vb], f = spot ? since(spot.t) * (st.va === st.vb ? 1 : Math.abs(2 * st.vu - 1)) : 0;
        A(bd.annotation, f > 0 ? {visible: true, opacity: f, text: spot.text, x: spot.x, y: spot.y} : {visible: false});
        return;
      }
      if (live) for (var k = 0; k < bd.wraps.length && !text; k++)
        if (textSize(bd.wraps[k], L.band_font).w + 16 <= b - a) text = bd.wraps[k];
      A(bd.annotation, text ? {visible: true, opacity: 1, text: text, x: (a + b) / 2 / GEO.plotW, y: bd.yLabel} : {visible: false});
    });

    // The playhead, while the play is on. And the ending: each chord drawn out
    // from the anchor to its series' last point, then its rate at the chord's
    // end; then the arrow that measures the gap between the two ends, grown
    // from the economy's end to the stocks', and what it measures.
    var head = !done && st.kind !== "end" && st.kind !== "pull";
    M.playhead.forEach(function (i) { H(i, {visible: head, x0: iso(T), x1: iso(T)}); });
    CHORDS.forEach(function (ch, n) {
      var f = st.chords[n], r = FIT.ends ? st.rates[n] : 0;
      H(ch.shape, {visible: f > 0, x1: iso(TA + f * (ch.t - TA)), y1: f * ch.value});
      A(ch.annotation, {visible: r > 0, opacity: r});
    });
    // (In the top panel: each era's chord, drawn from its start, then its rate wherever it was placed;
    // the arrow from the 1978 level up to the line's last point, grown upwards, then its label.)
    ERACHORDS.forEach(function (ec, n) {
      var f = st.eras[n], r = ec.place ? st.eraRates[n] : 0;
      H(ec.shape, {visible: f > 0, x1: iso(ec.t0 + f * (ec.t1 - ec.t0)), y1: ec.y0 + f * (ec.y1 - ec.y0)});
      A(ec.annotation, {visible: r > 0, opacity: r});
    });
    var cl = CLIMB.place ? st.climbLabel : 0;
    A(CLIMB.arrow, {visible: st.climb > 0, y: Math.max(st.climb, 0.04) * CLIMB.value});
    A(CLIMB.label, {visible: cl > 0, opacity: cl});
    var grown = Math.max(st.arrow, 0.04), gl = FIT.ends ? st.gap : 0;
    A(GAP.arrow, {visible: st.arrow > 0, ay: GAP.top + grown * (GAP.bottom - GAP.top)});
    A(GAP.label, {visible: gl > 0, opacity: gl});
    // A box's rate arrow: drawn tail to head as the box comes up (the playhead at the span's last
    // point), its rate once it is drawn, both going with the box; its reference arrow, faint, with it.
    BEATS.forEach(function (b) {
      if (!b.rate) return;
      var on = !done && st.beat === b && !dismissed[b.id] ? st.beatAlpha : 0;
      var f = on ? clamp((st.clock - b.c0) / M.play.rate.draw, 0, 1) : 0;
      ratesOf(b).forEach(function (R) {
        var g_ = R.geo, ref = R.reference, a = ref ? on * M.play.rate.reference : on, grow = ref ? 1 : Math.max(f, 0.02);
        A(R.arrow, {visible: a > 0 && (ref || f > 0), opacity: a, x: iso(g_.t0 + grow * (g_.t1 - g_.t0)),
                    y: g_.y0 + g_.lift + grow * (g_.y1 - g_.y0)});
        var la = ref ? on * M.play.rate.reference_label : on * clamp(2 * f - 1, 0, 1);
        A(R.label, {visible: la > 0, opacity: la});
      });
    });
    // The arrow at the end of the interlude's act, drawn up from the 1978 level.
    var ia = done ? 0 : st.interAlpha;
    A(AN.inter_arrow, {visible: ia > 0 && st.inter > 0, opacity: ia, y: Math.max(st.inter, 0.04) * M.play.interlude.value});
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
    var g = reveal(G, T), p = revealPair(T), f = fills(p), mk = markersAt(T), live = !done && st.kind !== "pull" && st.kind !== "end";
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
    // An anchor's marker, once reached, while its date is in view. (Plotly hides a point that leaves
    // the x-range and never shows it again: one out of view is taken out, and put back in view.)
    ANCHORS.forEach(function (a) {
      var on = T >= a.t && a.t >= st.r0 && a.t <= st.r1;
      a.shown = on; put(TR[a.trace], on ? [a.date] : [], on ? [0] : []);
    });
    var layout = scene(st, st.r0, st.r1);
    // The x-range is the stage's (in a break, on its way to the next act's), which also undoes any zoom.
    layout["xaxis.range"] = done ? M.view.x.slice() : [iso(st.r0), iso(st.r1)];
    syncHead();
    overlays(st);
    hideTip();
    busy = true;
    function freed() { busy = false; syncPill(); if (pending !== null) { var q = pending; pending = null; render(q); } }
    Promise.resolve(send(layout, data, idx)).then(freed, freed);
  }
  // Re-place whatever depends on the window, after a zoom or pan or a re-fit.
  function refresh() {
    var v = view(), p = scene(STATE, v[0], v[1]), data = {x: [], y: []}, idx = [];
    syncHead();
    // An anchor's marker that the reader's zoom has taken out of view, or brought back into it (see render()).
    ANCHORS.forEach(function (a) {
      var on = playhead >= a.t && a.t >= v[0] && a.t <= v[1];
      if (on === a.shown) return;
      a.shown = on; idx.push(TR[a.trace]); data.x.push(on ? [a.date] : []); data.y.push(on ? [0] : []);
    });
    return send(p, idx.length ? data : null, idx).then(syncPill);
  }

  // ---- What is not in the figure: controls, the scrim and the cards ------------------
  // Put a beat's words, and its picture laid out one way or another (`how`), into the box.
  function dress(b, how) {
    if (beatCard._beat === b && beatCard._how === how) return;
    beatCard._beat = b; beatCard._how = how;
    var img = beatCard.querySelector(".china-beat-img"), body = beatCard.querySelector(".china-beat-body");
    var pic = how.img ? b.picture : null;
    beatCard.querySelector(".china-beat-lead").textContent = b.lead;
    beatCard.querySelector(".china-beat-text").textContent = b.text;
    beatCard.querySelector(".china-beat-credit").textContent = pic ? pic.credit : "";
    beatCard.classList.toggle("is-picture", !!pic);
    beatCard.classList.toggle("is-side", !!pic && how.kind === "side");
    beatCard.classList.toggle("is-stacked", !!pic && how.kind === "stacked");
    if (pic) {
      if (img._src !== pic.src) { img._src = pic.src; img.setAttribute("src", pic.src); }
      img.style.width = how.img + "px";
      img.style.height = Math.round(how.img / pic.aspect) + "px";
    }
    beatCard.style.fontSize = L.card.font + "px";
    beatCard.style.width = how.kind === "side" ? "auto" : how.width + "px";
    body.style.width = how.kind === "side" ? how.text + "px" : "";
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
    // The key's rows arrive with what they stand for: an annotation, a rate, the gap.
    Array.prototype.forEach.call(keyBox.querySelectorAll("[data-t]"), function (row) {
      var part = row.getAttribute("data-end"), era = row.getAttribute("data-era");
      row.style.opacity = done ? 1 : era !== null ? st.eraRates[+era] : part === "gap" ? st.gap : part === "climb" ? st.climbLabel
        : part ? st.rates[+part]
        : clamp((st.clock - clockOf(+row.getAttribute("data-t"))) / M.play.reveal, 0, 1);
    });
    // An act's title card, and the scrim that dims the figure behind it.
    if (st.card >= 0 && st.cardAlpha > 0) {
      if (actCard._act !== st.card) {
        actCard._act = st.card;
        actCard.querySelector(".china-act-kicker").textContent = ACTS[st.card].kicker;
        actCard.querySelector(".china-act-name").textContent = ACTS[st.card].cardTitle;
      }
      actCard.style.display = scrim.style.display = "block";
      actCard.style.opacity = st.cardAlpha;
      scrim.style.opacity = st.cardAlpha * M.play.scrim;
    } else actCard.style.display = scrim.style.display = "none";
    // A beat's box, or the last box of all, where fit() found room for it. One the reader has dismissed stays away.
    var b = st.last > 0 ? FINAL : st.beat, alpha = st.last > 0 ? st.last : st.beatAlpha;
    if (b && b.box && alpha > 0 && !dismissed[b.id]) {
      dress(b, b.box.how);
      beatCard.style.display = "block";
      beatCard.style.opacity = alpha;
      beatCard.style.transform = "translate(" + (L.margin.l + b.box.a) + "px," + (GEO.t + b.box.top) + "px)";
    } else beatCard.style.display = "none";
    // An annotation that is a beat: a dot on its point while playback slows for it, and one ring spreading from it.
    var n = st.note;
    if (n && !done && GEO && st.noteAlpha > 0) {
      var x = L.margin.l + pxIn(st.va, n.t, GEO.plotW), y = GEO.t + GEO.topH + GEO.gap + (M.view.y2[1] - n.y) * GEO.ppb;
      var d = 6 + 22 * st.pulse;
      pulseRing.style.color = pulseDot.style.color = P.ink;
      pulseRing.style.display = st.pulse < 1 ? "block" : "none";
      pulseRing.style.width = pulseRing.style.height = d + "px";
      pulseRing.style.opacity = (1 - st.pulse) * 0.9 * st.noteAlpha;
      pulseRing.style.transform = "translate(" + (x - d / 2) + "px," + (y - d / 2) + "px)";
      pulseDot.style.display = "block"; pulseDot.style.opacity = st.noteAlpha;
      pulseDot.style.transform = "translate(" + (x - 3.5) + "px," + (y - 3.5) + "px)";
    } else pulseRing.style.display = pulseDot.style.display = "none";
  }
  // The year pill, on the x-axis under the playhead: placed after each draw, from the axis as
  // drawn, so it is right under a reader's own zoom as well (and gone if the playhead is out of
  // view). An axis label that the pill would crowd, or that only says the same year, is hidden
  // while it is there. Neither the pill nor the playhead outlives the play.
  function syncPill() {
    var xa = gd._fullLayout.xaxis, off = STATE.done || STATE.kind === "end" || STATE.kind === "pull";
    var x = off ? -9 : xa.l2p(STATE.T), on = x >= -1 && x <= xa._length + 1;
    pill.style.display = on ? "block" : "none";
    var d = new Date(STATE.T), year = String(d.getUTCFullYear());
    if (on) {
      // While a box is up, the month as well as the year.
      var boxed = STATE.beat && STATE.beatAlpha > 0 && !dismissed[STATE.beat.id];
      pill.textContent = boxed ? MONTHS[d.getUTCMonth()] + " " + year : year;
      var w = pill.offsetWidth;
      x = clamp(x, w / 2 - L.margin.l + 2, GEO.plotW + L.margin.r - w / 2 - 2);
      pill.style.transform = "translate(" + (L.margin.l + x - w / 2) + "px," + (GEO.t + GEO.plotH + 4) + "px)";
    }
    var r = on ? pill.getBoundingClientRect() : null;
    Array.prototype.forEach.call(gd.querySelectorAll(".xtick text"), function (el) {
      var b = on ? el.getBoundingClientRect() : null;
      var near = on && ((b.left < r.right + 8 && r.left < b.right + 8) || el.textContent === year);
      el.style.visibility = near ? "hidden" : "";
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
  // How fast the playhead is moving, in years a second at 1x, at a moment of an act.
  function paceAt(c) {
    var seg = TL[0];
    for (var i = 1; i < TL.length; i++) if (c >= TL[i].c0) seg = TL[i];
    if (seg.kind !== "play") return null;
    var s = c - seg.c0;
    return {base: ACTS[seg.act].base, now: (timeOf(seg.act, s + 0.05) - timeOf(seg.act, s)) / 0.05 / YEAR};
  }
  // Play from where the clock stands; from the top if the play is over.
  function play(from) {
    if (reducedMotion()) { render(END); return; }   // reduced motion: straight to the finished chart
    var prev = null;
    if (from !== undefined || clock >= END) { dismissed = {}; hurrying = null; hurry = 0; }
    want = from !== undefined ? from : clock >= END ? 0 : clock;
    played = true;
    setPlaying(true);
    render(want);
    function step(now) {
      if (!playing) return;
      // Advance by wall-clock time (times the chosen speed), capped so a backgrounded tab resumes, not jumps.
      var dt = prev === null ? 0 : Math.min(now - prev, 100) / 1000 * speed, rate = 1;
      prev = now;
      // A box the reader has dismissed: playback eases up to its normal speed and runs on
      // through what is left of the slow stretch, until the schedule is itself back to speed
      // or another box comes up.
      if (hurrying) {
        var pace = paceAt(want), up = STATE.beat;
        if (!pace || (up && up !== hurrying && !dismissed[up.id]) || (want > hurrying.c1 && pace.now >= 0.95 * pace.base)) hurrying = null;
        else rate = clamp(pace.base / Math.max(pace.now, 1e-6), 1, 40);
      }
      hurry = clamp(hurry + (hurrying ? 1 : -1) * dt / speed / 0.3, 0, 1);
      want += dt * (1 + hurry * (rate - 1));
      if (want >= END) { setPlaying(false); render(END); return; }
      if (!busy) render(want);
      raf = requestAnimationFrame(step);
    }
    raf = requestAnimationFrame(step);
  }
  // A click or a tap on a box sends it away. A beat's box: playback eases back to normal speed.
  // The last box: on to its fade, the end of the ending.
  function dismiss() {
    var st = STATE, end = TL.filter(function (s) { return s.kind === "end"; })[0];
    if (st.last > 0) {
      var out = end.c0 + end.marks.boxOut;
      if (playing) want = Math.max(want, out); else render(Math.max(clock, out));
    } else if (st.beat === INTER) {        // the interlude's box: on to the break
      dismissed[INTER.id] = true;
      var gone = INTER.c1 + M.play.card_fade;
      if (playing) want = Math.max(want, gone); else render(Math.max(clock, gone));
    } else if (st.beat) {
      dismissed[st.beat.id] = true;
      if (playing) hurrying = st.beat;
      overlays(st);
      if (!playing) refresh();             // (the recovery's arrow goes with its box; the pill drops the month)
    }
  }
  // Start an act from its title card. (Reduced motion: show where the act starts, and stay there.)
  function jump(k) {
    pause();
    dismissed = {};
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
    var st = L.strip, plotW = w - L.margin.l - L.margin.r, whole = VIEWS.length - 1, ann = gd.layout.annotations;
    var patch = {};
    function A(i, props) { for (var k in props) patch["annotations[" + i + "]." + k] = props[k]; }
    function H(i, props) { for (var k in props) patch["shapes[" + i + "]." + k] = props[k]; }
    function each(fn) { return VIEWS.map(function (V, v) { return fn(v, V); }); }      // one answer per view

    // The two strips: which events are drawn and labelled, in which rows, and in which views each label fits.
    FIT = {top: fitStrip("economy", plotW, w), bottom: fitStrip("stocks", plotW, w)};
    EV.forEach(function (e) {
      e.on = false; e.labelled = false; e.row = 0; e.spot = 0.5; e.ext = [0, 0]; e.stem = 0; e.lift = 3;
      e.fits = each(function () { return false; });
    });
    [FIT.top, FIT.bottom].forEach(function (F) {
      F.events.forEach(function (e, j) {
        e.on = true; e.labelled = F.labels; e.font = F.font; e.say = F.says[j];
        if (!F.placed) return;
        e.row = F.placed[j].row; e.spot = F.placed[j].spot;
        e.stem = 2 + e.row * F.pitch; e.lift = 3 + e.row * F.pitch;      // where its line stops and its label stands, px above the panel
        // How far the label reaches either side of its line, and the views whose axis has room for it.
        e.ext = reachOf(0, textSize(e.say, F.font).w + 2, e.spot);
        e.fits = each(function (v) { return fitsView(v, e.t, e.ext[0], e.ext[1], plotW); });
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
    // The eras: which are drawn, and which are labelled in each view.
    ERAS.forEach(function (e) { e.w = textSize(e.label, st.era_font).w + 2; });
    FIT.eras = fitEras(plotW, w);
    FIT.eraText = each(function (v, V) { return eraLabels(V.r0, V.r1, plotW, FIT.eras.on); });
    ERAS.forEach(function (e, n) {
      e.on = FIT.eras.on[n]; e.labelled = !!FIT.eras.labelled[n];
      e.fits = each(function (v) { return !!FIT.eraText[v][n]; });
    });
    // The leaders: in each view, whether what the view shows of a segment can hold its name (with
    // room to spare, or only just, the name then set nearer the segment's start), and the date
    // by which the segment has grown that long.
    LEADERS.forEach(function (l) {
      l.w = textSize(l.label, st.leader_font).w + 2;
      l.inset = []; l.from = [];
      VIEWS.forEach(function (V, v) {
        var a = Math.max(l.t0, V.r0), b = Math.min(l.t1, T1, V.r1), sc = scaleIn(v, plotW), room = (b - a) * sc - l.w;
        l.inset[v] = room >= 12 ? 5 : Math.max(room / 2, 0);
        l.from[v] = room >= 12 ? a + (l.w + 12) / sc : room >= 4 ? b : null;
      });
      l.labelled = l.from[whole] !== null;
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

    // Each band label's place in each view: the middle of what the view shows of its band (as
    // far as the view's act grows it), in the widest wording that fits there. It shows once its
    // band has grown under it (t).
    BANDS.forEach(function (bd) {
      bd.spots = each(function (v, V) {
        var sc = scaleIn(v, plotW), upTo = Math.min(bd.t1, V.r1, v < ACTS.length ? ACTS[v].t1 : T1);
        var a = (Math.max(bd.t0, V.r0) - V.r0) * sc, b = (upTo - V.r0) * sc, text = null, sz;
        for (var n = 0; n < bd.wraps.length && !text; n++) {
          sz = textSize(bd.wraps[n], L.band_font);
          if (sz.w + 16 <= b - a) text = bd.wraps[n];
        }
        if (!text) return null;
        var mid = (a + b) / 2;
        return {text: text, x: mid / plotW, y: bd.yLabel, a: mid - sz.w / 2, b: mid + sz.w / 2, h: sz.h,
                top: (1 - bd.yLabel) * GEO.botH - sz.h / 2, t: V.r0 + (mid + sz.w / 2 + 8) / sc};
      });
    });

    // The labels either side of the zero lines. Bottom panel: left of where the
    // line starts, on the plain band, in each view where they fit inside what
    // the view shows of that band; on the finished chart, failing that, a line
    // in the key says it. Top panel: right of the anchor, where they fit.
    var COL = columns(plotW), into = BANDS.filter(function (bd) { return bd.t1 === TA; })[0];
    var wb = Math.max(textSize(ann[AN.zero_up].text, L.hint_font).w, textSize(ann[AN.zero_down].text, L.hint_font).w) + 4;
    FIT.hints = {bottomW: wb, top: placeHints(plotW, COL)};
    FIT.hints.bottomFits = each(function (v, V) {
      return !!into && inView(v, TA) && wb <= (TA - Math.max(into.t0, V.r0)) * scaleIn(v, plotW) - 16;
    });
    FIT.hints.bottom = FIT.hints.bottomFits[whole];
    ["zero_up", "zero_down", "gap_up", "gap_down"].forEach(function (r) { A(AN[r], {"font.size": L.hint_font}); });
    if (FIT.hints.top) {
      var ht = FIT.hints.top;
      ht.fits = each(function (v) { return inView(v, ht.t) && pxIn(v, ht.t, plotW) + ht.w <= plotW - 2; });
      ht.show = each(function (v) { return ht.t + (ht.w + 8) / scaleIn(v, plotW); });   // once the playhead has passed them
      ["gap_up", "gap_down"].forEach(function (r) { A(AN[r], {x: iso(ht.t)}); });
    }

    // The arrowed annotations: beside the data if they all fit, in the largest
    // type that lets every one of them show in its arrow's own act (failing
    // that, whichever type waits least); otherwise numbered markers and a key.
    // Then the labels by the fills.
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
      var mx = pxIn(whole, a.t, plotW), my = (M.view.y2[1] - a.y) * GEO.ppb;
      return {a: mx - 9, b: mx + 9, top: my - 9, bottom: my + 9};
    });
    FILLS.forEach(function (F) {
      F.box = placeFill(F, boxes, COL);
      if (!F.box) return;
      boxes.push(F.box);
      F.box.fits = each(function (v) {
        var x = pxIn(v, F.box.at, plotW);
        return inView(v, F.box.at) && x - F.box.w / 2 >= 2 && x + F.box.w / 2 <= plotW - 2;
      });
      A(AN[F.role], {text: F.box.text, x: F.box.x, y: F.box.y, "font.size": L.fill_font});
    });

    // What closes the animation stands right of the last data point: the gap's arrow, and beside
    // it the two rates and the gap's label, in the gutter, each on one line if the gutter is wide
    // enough for that and on two if not. Where there is no gutter (a phone) the three go in the key.
    FIT.ends = L.end.label !== null;
    var gutter = plotW + L.margin.r - 3 - pxIn(whole, T1, plotW) - (L.end.label || 0);
    CHORDS.concat([GAP]).forEach(function (it) {
      var i = it === GAP ? GAP.label : it.annotation;
      if (FIT.ends) A(i, {text: it.wraps[textSize(it.wraps[0], L.rate_font).w + 2 <= gutter ? 0 : 1], xshift: L.end.label, "font.size": L.rate_font});
    });
    A(GAP.arrow, {xshift: L.end.arrow});
    A(CLIMB.arrow, {xshift: L.end.arrow});
    placeEras(plotW, A);
    // Each rate arrow, clear of the line (and of every point between its ends); its rate just above
    // its middle, clear of the arrow's slope.
    BEATS.forEach(function (b) {
      ratesOf(b).forEach(function (R) {
        var g_ = R.geo = rateGeometry(R, b.act, plotW);
        A(R.arrow, {ax: iso(g_.t0), ay: g_.y0 + g_.lift, "arrowwidth": M.play.rate.width});
        A(R.label, {x: iso((g_.t0 + g_.t1) / 2), y: (g_.y0 + g_.y1) / 2 + g_.lift, yshift: g_.yshift, "font.size": L.rate_font});
      });
    });

    // The key under the plot: whatever could not be labelled directly.
    var keyed = false;
    Array.prototype.forEach.call(keyBox.children, function (row) {
      row.hidden = row.hasAttribute("data-zero") ? FIT.hints.bottom : row.hasAttribute("data-era") ? !!ERACHORDS[+row.getAttribute("data-era")].place
        : row.getAttribute("data-end") === "climb" ? !!CLIMB.place : row.hasAttribute("data-end") ? FIT.ends : !!FIT.arrows;
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

    // The boxes of narration (HTML): each is set and measured with its own words, then given its
    // place, the boxes of one act in turn so that each can stay near the one before.
    beatCard.style.visibility = "hidden"; beatCard.style.display = "block";
    var before = null;
    BEATS.concat([FINAL]).forEach(function (b, n, all) {
      if (n && all[n - 1].act !== b.act) before = null;
      b.box = placeBox(b, plotW, b.last ? null : before);
      before = b.box || before;
    });
    beatCard._beat = null;
    beatCard.style.display = "none"; beatCard.style.visibility = "";
    // (Boxes under the plot stand over the key: the key keeps room enough for the tallest of them.)
    var deepest = Math.max.apply(null, BEATS.concat([FINAL]).map(function (b) { return b.box && b.box.below ? b.box.h : 0; }));
    keyBox.style.minHeight = deepest ? (deepest + 10) + "px" : "";

    // The title card, over the middle of the plot, with the scrim over the whole figure; the year
    // pill; and the scrubber's act labels: the acts' titles, or their short forms, or just their
    // numerals -- whichever is the longest form that every act's stretch of the track has room
    // for, so that the three read alike.
    actCard.style.left = (L.margin.l + plotW / 2) + "px";
    actCard.style.top = (GEO.t + GEO.plotH / 2) + "px";
    actCard.style.width = Math.round(Math.min(L.act_card.width * plotW, w - 24)) + "px";
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
            era: tint(nv, al.era), tick: tint(nv, al.tick), tickHot: tint(nv, 1),
            leader: al.leader.map(function (a) { return tint(nv, a); }),
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
      if (e.stalk !== null) H(e.stalk, {"line.color": P.ink});
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
    // The ending: each rate in its series' colour; the gap's arrow and its label in ink.
    CHORDS.forEach(function (ch) { A(ch.annotation, ch.color, P.paper); });
    ERACHORDS.forEach(function (ec) { A(ec.annotation, ec.color, P.paper); });
    A(CLIMB.label, P.text("rate"), P.paper);
    A(CLIMB.arrow, P.text("arrow"), P.paper);
    layout["annotations[" + CLIMB.arrow + "].arrowcolor"] = P.text("arrow");
    A(GAP.label, P.text("rate"), P.paper);
    A(GAP.arrow, P.text("arrow"), P.paper);
    layout["annotations[" + GAP.arrow + "].arrowcolor"] = P.text("arrow");
    // The rate arrows and their rates, and the interlude's arrow: in ink, the page's own in dark mode.
    A(AN.inter_arrow, P.text("arrow"), P.paper);
    layout["annotations[" + AN.inter_arrow + "].arrowcolor"] = P.text("arrow");
    BEATS.forEach(function (b) {
      ratesOf(b).forEach(function (R) {
        A(R.arrow, P.text("arrow"), P.paper); A(R.label, P.text("arrow"), P.paper);
        layout["annotations[" + R.arrow + "].arrowcolor"] = P.text("arrow");
      });
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
  // An event the playhead has not reached says nothing, ghost or not.
  function describe(px, py, cx, cy, xa, ya, y2) {
    var out = [], st = L.strip, done = STATE.done, up = ya._offset - py;          // up: px above the Economy panel
    function shown(t) { return done || clock >= clockOf(t); }
    function tell(parent) {
      out.push(parent.description);
      parent.notes.forEach(function (n) { if (done || n.t <= playhead) out.push({sub: true, text: "**" + n.when + "**: " + n.text}); });
    }
    hovered = [];
    EV.forEach(function (e) {
      if (!e.on || !shown(e.t)) return;
      var ax = e.panel === "economy" ? ya : y2, top = ax._offset - (e.tick ? L.tick.up : e.labelled ? e.stem : 0);
      // (A tick is a short mark: its target is wider, 6 px either side of its date.)
      var onLine = Math.abs(xa.l2p(e.t) - px) <= (e.tick ? 6 : 4) && py >= top - 2 && py <= ax._offset + ax._length;
      var lead = e.tick ? null : e.lead === null ? e : EV[e.lead];       // whose label this event stands under
      if (onLine || (lead && lead.labelled && inside(label(lead.annotation), cx, cy))) { tell(e); hovered.push(e); }
    });
    LEADERS.forEach(function (l) {
      if (l.live && px >= l.a && px <= l.b && up >= GEO.leader - 1 && up <= GEO.topStrip + 1) out.push(l.description);
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
    // A rate, while it is up, says what it measures.
    var rb = STATE.beat;
    if (!done && rb && STATE.beatAlpha > 0 && !dismissed[rb.id]) ratesOf(rb).forEach(function (R) {
      if (inside(label(R.label), cx, cy)) out.push(R.hover);
    });
    // An era's rate, once it is up, says what it was in growth.
    ERACHORDS.forEach(function (ec, n) {
      if (ec.place && STATE.eraRates[n] > 0 && inside(label(ec.annotation), cx, cy)) out.push(ec.hover);
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
    unhot();
  }
  // A line of the hover box. In a mark's own text, **...** is bold: the date that leads it.
  function tipRow(cls, text) {
    var d = document.createElement("div");
    d.className = cls;
    if (cls.indexOf("china-tip-row") === 0) { var k = document.createElement("span"); k.className = "china-tip-key"; d.appendChild(k); }
    String(text).split("**").forEach(function (part, i) {
      if (!part) return;
      if (i % 2) { var b = document.createElement("b"); b.textContent = part; d.appendChild(b); }
      else d.appendChild(document.createTextNode(part));
    });
    return d;
  }
  // ---- Hover highlight: the events the cursor is on ---------------------------------
  // A labelled event's line turns solid, dark and 2 px wide, and its label bold; a tick grows
  // taller and darker. Drawn in HTML over the plot (no Plotly redraw), so it costs a few style
  // writes and moves nothing else; it goes with the hover box (render() clears both).
  var hovered = [], hotEls = [], hotText = [], hotOn = false;
  function hotLine(n, x, y0, y1, w, color) {
    var el = hotEls[n];
    if (!el) { el = hotEls[n] = document.createElement("div"); el.className = "china-hot"; hotBox.appendChild(el); }
    el.style.display = "block"; el.style.width = w + "px"; el.style.height = Math.max(0, y1 - y0) + "px";
    el.style.background = color;
    el.style.transform = "translate(" + (x - w / 2) + "px," + y0 + "px)";
  }
  function unhot() {
    if (!hotOn) return;
    hotOn = false;
    hotEls.forEach(function (el) { el.style.display = "none"; });
    hotText.forEach(function (el) { el.style.fontWeight = ""; });
    hotText = [];
  }
  function hot(xa, ya, y2, ox, oy) {
    unhot();
    var n = 0;
    hovered.forEach(function (e) {
      var ax = e.panel === "economy" ? ya : y2, k = e.panel === "economy" ? 0 : 1, at = xa.l2p(e.t);
      if (at < -0.5 || at > xa._length + 0.5) return;
      var x = ox + xa._offset + at, top = oy + ax._offset;
      hotOn = true;
      if (e.tick) { hotLine(n++, x, top - L.tick.up - 3, top + L.tick.down + 5, L.tick.width + 1, P.tickHot); return; }
      // The line through the panel stops under the panel's name where it would cross it, as the dashed one does.
      var head = GEO.head[k], below = at > head.a - 4 && at < head.b + 4 ? head.h : 0;
      if (e.labelled) hotLine(n++, x, top - e.stem, top, 2, P.ink);
      hotLine(n++, x, top + below, top + ax._length, 2, P.ink);
      var lead = e.lead === null ? e : EV[e.lead], el = lead.labelled ? label(lead.annotation) : null;
      var tx = el && el.querySelector("text");
      if (tx) { tx.style.fontWeight = "700"; hotText.push(tx); }
    });
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
    // The date as a heading (a year for the economy's annual points, a month for the month-ends),
    // then each series' change since its own anchor.
    if (hit.gdp >= 0) {
      tip.appendChild(tipRow("china-tip-when", G.when[hit.gdp]));
      tip.appendChild(tipRow("china-tip-row china-tip-gdp", G.hover[hit.gdp]));
    }
    if (hit.month >= 0) {
      tip.appendChild(tipRow("china-tip-when", S.when[hit.month]));
      tip.appendChild(tipRow("china-tip-row china-tip-stock", S.hoverS[hit.month]));
      tip.appendChild(tipRow("china-tip-row china-tip-economy", S.hoverE[hit.month]));
      // A back-tested month says why it is drawn differently.
      if (S.t[hit.month] < TB) tip.appendChild(tipRow("china-tip-note china-tip-why", M.backtest.note));
    }
    var w = wrap.getBoundingClientRect(), ox = r.left - w.left, oy = r.top - w.top;
    hot(xa, ya, y2, ox, oy);
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
    var full = L.drop_from !== null && lastW >= L.drop_from, whole = VIEWS.length - 1;
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
    // Labels that do not fit the view of the act their line appears in, or the finished chart's.
    out.hiddenSomewhere = EV.filter(function (e) { return e.on && e.labelled && e.annotation !== null && !(e.fits[e.act] && e.fits[whole]); })
      .map(function (e) { return e.label + " (fits views " + e.fits.map(function (f, v) { return f ? v + 1 : ""; }).join("") + ")"; });
    out.fillLabels = FILLS.map(function (f) { return f.role + (f.box ? " at " + f.box.x.slice(0, 7) : " hidden"); });
    out.hints = {bottom: FIT.hints.bottom ? "in plot" : "key", top: FIT.hints.top ? "from " + iso(FIT.hints.top.t).slice(0, 7) : "hidden"};
    out.ends = (FIT.ends ? "in the gutter" : "in the key") + ": " + CHORDS.map(function (ch) { return ch.text; }).concat([GAP.text]).join(" | ");
    out.boxes = BEATS.concat([FINAL]).map(function (b) {
      var q = b.box, V = VIEWS[b.act], sweep = b.last ? null : [pxIn(b.act, b.since, GEO.plotW), pxIn(b.act, b.until, GEO.plotW)];
      var gap = !q ? null : b.last ? pxIn(b.act, T1, GEO.plotW) - q.b : q.a > sweep[1] ? q.a - sweep[1] : sweep[0] - q.b;
      return (b.last ? "last box" : iso(b.t).slice(0, 7)) + " [" + (q ? q.how.kind + (q.how.img ? " " + q.how.img : "") + ", " + Math.round(q.w) + "×" + Math.round(q.h)
        + (q.below ? ", under the plot" : " at " + Math.round(q.a) + "," + Math.round(q.top) + (q.spans ? ", across the panels" : q.k ? ", bottom panel" : ", top panel")
        + (q.fallback ? " (no room in its own)" : "")
        + ", " + Math.round(gap) + " px " + (b.last || q.side < 0 ? "left" : "right") + " of the playhead") : "NO PLACE") + "]"; });
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
    function go(c) { busy = false; pending = null; dismissed = {}; render(c); return frames(3); }
    // An anchor's marker as drawn: a circle with a size, not hidden. Checked wherever its date is in
    // view and has been reached (round 8: the 1978 marker went missing after Part III's view).
    function anchorsDrawn(tag) {
      var xa = gd._fullLayout.xaxis, v0 = xa.r2l(xa.range[0]), v1 = xa.r2l(xa.range[1]);
      ANCHORS.forEach(function (a) {
        if (!(playhead >= a.t && a.t >= v0 && a.t <= v1)) return;
        var g = gd.querySelector(".trace.trace" + gd._fullData[TR[a.trace]].uid), pt = g && g.querySelector("path.point");
        var b = pt && pt.getBoundingClientRect();
        out.anchorChecks = (out.anchorChecks || 0) + 1;
        if (!pt || pt.getAttribute("display") === "none" || !b.width || !b.height)
          fail(tag + ": the " + a.text + " marker is not drawn, though its date is in view");
      });
    }
    // A rate arrow as drawn: the x of its line's two ends, in px from the plot's left edge.
    // (The line and its head together: Plotly stops the line short of the tip, under the head.)
    function arrowEnds(i) {
      var els = gd.querySelectorAll('.annotation[data-index="' + i + '"] .annotation-arrow-g path'), fl_ = gd._fullLayout;
      if (!els.length) return null;
      var r = gd.getBoundingClientRect(), lo = Infinity, hi = -Infinity;
      Array.prototype.forEach.call(els, function (el) { var b = el.getBoundingClientRect(); lo = Math.min(lo, b.left); hi = Math.max(hi, b.right); });
      return [lo - r.left - fl_.xaxis._offset, hi - r.left - fl_.xaxis._offset];
    }
    var BOX_SHARE = Math.max.apply(null, M.play.notes.map(function (n) { return n.share; }));
    function monthOf(T) { var d = new Date(T); return MONTHS[d.getUTCMonth()] + " " + d.getUTCFullYear(); }
    function unbold(text) { return String(text).replace(/\*\*/g, ""); }
    // What each label is. `over`: text inside a panel that may lie over a band,
    // a fill or an event's line, which is what its halo is for.
    var who = {};
    EV.forEach(function (e) {
      if (e.annotation !== null) who[e.annotation] = {name: "event: " + e.label, kind: "event", strip: e.panel};
    });
    ERAS.forEach(function (e) { who[e.annotation] = {name: "era: " + e.label, kind: "era", strip: "economy", bar: e}; });
    LEADERS.forEach(function (l) { who[l.annotation] = {name: "leader: " + l.label, kind: "leader", strip: "economy", bar: l}; });
    BANDS.forEach(function (bd) { who[bd.annotation] = {name: "band: " + plain(bd.wraps[0]), kind: "band", over: true}; });
    ["zero_up", "zero_down", "gap_up", "gap_down"].forEach(function (r) { who[AN[r]] = {name: r, kind: "hint", over: true}; });
    ARROWS.forEach(function (a) { who[AN[a.role]] = {name: a.role, kind: "arrow", over: true}; });
    FILLS.forEach(function (f) { who[AN[f.role]] = {name: f.role, kind: "fill", over: true, infill: f.kind === "behind"}; });
    CHORDS.forEach(function (ch) { who[ch.annotation] = {name: "rate: " + ch.key, kind: "rate", over: true}; });
    // (An era's rate in the plot keeps clear of the event lines, as a label of its own does.)
    ERACHORDS.forEach(function (ec) { who[ec.annotation] = {name: "rate: " + ec.name, kind: "era rate", over: false}; });
    who[CLIMB.label] = {name: "the climb's label", kind: "rate", over: true};
    who[GAP.label] = {name: "the gap's label", kind: "rate", over: true};
    BEATS.forEach(function (b) { ratesOf(b).forEach(function (R) { who[R.label] = {name: "rate: " + R.text, kind: "rate", over: true}; }); });

    // Every visible text box against every other, the bars, the event lines and
    // the data; that each bar's label is still at the bar's start; and how tall
    // the title row and the two strips actually are. A beat's box counts as a
    // text box: it may cover an event's line (it is opaque), nothing else.
    function collisions(tag) {
      var fl = gd._fullLayout, xa = fl.xaxis, ya = fl.yaxis, y2 = fl.yaxis2, r = gd.getBoundingClientRect(), st = L.strip;
      // (Under a reader's zoom, and while the axis is on its way from one view to the next, marks pass under the panels' names.)
      var X = function (t) { return r.left + xa._offset + xa.l2p(t); }, left = r.left + xa._offset, zoomed = tag === "zoomed" || /moving/.test(tag);
      var panels = [{ax: ya, top: r.top + ya._offset}, {ax: y2, top: r.top + y2._offset}];
      var boxes = [], bars = [], minText = 1e9, minData = 1e9, minLine = 1e9, crossed = 0;
      var topMost = panels[0].top, midMost = panels[1].top, chordsOn = gd.layout.shapes[CHORDS[0].shape].visible !== false;
      Array.prototype.forEach.call(gd.querySelectorAll(".annotation"), function (el) {
        var i = +el.getAttribute("data-index"), tg = el.querySelector(".annotation-text-g"), a = fl.annotations[i];
        if (!tg || !a || a.visible === false || a.opacity < 0.05 || !a.text) return;     // (the gap's arrow has no text)
        var b = tg.getBoundingClientRect(), id = who[i] || {name: "#" + i, kind: "?"};
        if (!b.width) return;
        boxes.push({i: i, name: id.name, kind: id.kind, strip: id.strip, over: !!id.over, infill: !!id.infill, bar: id.bar,
                    l: b.left, r: b.right, t: b.top, b: b.bottom});
      });
      var tb = title.getBoundingClientRect();
      boxes.push({i: -9, name: "title", kind: "title", l: tb.left, r: tb.right, t: tb.top, b: tb.bottom});
      heads.forEach(function (h, k) {
        var b = h.getBoundingClientRect();
        boxes.push({i: -1 - k, name: k ? "name: Stocks" : "name: Economy", kind: "head", l: b.left, r: b.right, t: b.top, b: b.bottom});
      });
      if (beatCard.style.display !== "none" && +beatCard.style.opacity > 0.05) {
        // (A box that stands under the plot, on a phone, is clear of everything in it: it must only keep off the controls.)
        var cb = beatCard.getBoundingClientRect();
        if (cb.top < r.bottom) boxes.push({i: -20, name: "the box", kind: "card", over: true, l: cb.left, r: cb.right, t: cb.top, b: cb.bottom});
        else if (cb.bottom > controls.getBoundingClientRect().top + 1 || cb.left < r.left - 1 || cb.right > r.right + 1) fail(tag + ": the box under the plot runs onto the controls or off the figure");
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
            if (a.l < bar.l + 0.5 || a.r > bar.r - 0.5) fail(tag + ": a leader's name runs outside its segment: " + a.name);
            return;
          }
          if (Math.max(bar.l - a.r, a.l - bar.r, bar.t - a.b, a.t - bar.b) < 1) fail(tag + ": text on a bar: " + a.name + " / " + bar.name);
        });
        // A bar's label stays at the bar's start (or at the plot's left edge).
        var inset = a.kind === "leader" ? a.bar.at : 0;
        if (a.bar && Math.abs(a.l - (left + a.bar.a + inset)) > 1.5)
          fail(tag + ": a label has left its bar's start: " + a.name + " by " + (a.l - left - a.bar.a - inset).toFixed(1) + " px");
        // Event lines that are drawn, ghosts included. Haloed text inside a panel may lie over one
        // (they are counted); everything else must stand clear -- the panels' names too, except
        // under a reader's own zoom.
        if (a.kind !== "card") EV.forEach(function (e) {
          var sh = gd.layout.shapes[e.shape], up = e.stalk === null ? null : gd.layout.shapes[e.stalk], x = X(e.t);
          if (e.annotation === a.i || !e.on || sh.visible === false || x < left - 1 || x > left + xa._length + 1) return;
          var pn = panels[e.panel === "economy" ? 0 : 1];
          // The line's two strokes: through the panel (from under the panel's name, if it would cross
          // that), and the stalk from the panel's top up to its label.
          var lineTop = pn.top - (sh.y1 - 1) * pn.ax._length, lineBottom = pn.top + (1 - sh.y0) * pn.ax._length;
          var stalkTop = up && up.visible !== false ? pn.top - (up.y1 - 1) * pn.ax._length : pn.top;
          if ((a.b <= lineTop + 0.5 || a.t >= lineBottom) && (a.b <= stalkTop + 0.5 || a.t >= pn.top)) return;   // neither reaches this box
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
            if (T > playhead || x < left || x > left + xa._length) continue;
            var vals = k === 0 ? [at(G.t, G.y, T)] : [at(S.t, S.s, T), at(S.t, S.e, T)];
            if (vals[0] === null) continue;
            var ys = vals.map(function (v) { return pn.top + pn.ax.l2p(v); }), gap;
            if (a.infill) gap = Math.min.apply(null, ys.map(function (y) { return Math.max(a.t - y, y - a.b); }));
            else gap = Math.max(a.t - Math.max.apply(null, ys), Math.min.apply(null, ys) - a.b);
            minData = Math.min(minData, gap);
            if (gap < 2.5) fail(tag + ": text on the data: " + a.name);
            if (k === 0) ERACHORDS.forEach(function (ec) {
              var esh = fl.shapes[ec.shape];
              if (esh.visible === false || T < ec.t0 || T > toMs(esh.x1)) return;
              var ty = pn.top + pn.ax.l2p(ec.y0 + (ec.y1 - ec.y0) * (T - ec.t0) / (ec.t1 - ec.t0));
              if (Math.max(a.t - ty, ty - a.b) < 2) fail(tag + ": text on a chord: " + a.name + " / " + ec.name);
            });
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
    var framed = false;
    function CLIMB_UP() { return gd._fullLayout.annotations[CLIMB.arrow].visible !== false; }
    function moment(tag, c) {
      return go(c).then(function () {
        var st = STATE, fl = gd._fullLayout, xa = fl.xaxis, r = gd.getBoundingClientRect(), tr = M.play.transition;
        var seg = TL.filter(function (s) { return c >= s.c0; }).pop(), s = c - seg.c0, k = seg.act;
        var cl = collisions(tag), x0 = xa.r2l(xa.range[0]), x1 = xa.r2l(xa.range[1]), held = tr.card_in + tr.hold;
        if (JSON.stringify([fl.yaxis.range, fl.yaxis2.range]) !== yRanges) fail(tag + ": a y-range has changed");
        // The x-range: the act's own, except while a break (or the pull-back) is moving it.
        var moving = (seg.kind === "break" && s > held && s < held + tr.move) || (seg.kind === "pull" && s > 0 && s < seg.dur);
        // (The ending happens in the whole chart's view, after the pull-back.)
        var A = VIEWS[seg.kind === "end" ? whole : seg.kind === "break" && s >= held + tr.move ? k + 1 : k], B = VIEWS[seg.kind === "pull" ? whole : k + 1];
        if (moving) {
          var between = function (v, a, b) { return a === b ? Math.abs(v - a) < 1000 : v > Math.min(a, b) + DAY && v < Math.max(a, b) - DAY; };
          if (!between(x0, VIEWS[k].r0, B.r0) || !between(x1, VIEWS[k].r1, B.r1)) fail(tag + ": the axis is not between two views while it moves");
        } else if (Math.abs(x0 - A.r0) > 1000 || Math.abs(x1 - A.r1) > 1000)
          fail(tag + ": the x-range is not the act's: " + iso(x0).slice(0, 10) + " to " + iso(x1).slice(0, 10) + ", not " + iso(A.r0).slice(0, 10) + " to " + iso(A.r1).slice(0, 10));
        if (Math.abs(scrub.value / scrub.max - (st.T - T0) / (T1 - T0)) > 1 / scrub.max) fail(tag + ": the scrubber is not at the playhead's date");
        // The playhead, with the year under it, until the ending; no axis label crowding the year.
        var head = seg.kind === "open" || seg.kind === "play" || seg.kind === "inter" || seg.kind === "break";
        M.playhead.forEach(function (i) {
          var sh = fl.shapes[i];
          if (head !== (sh.visible !== false)) fail(tag + ": the playhead is " + (head ? "missing" : "still drawn"));
          else if (head && Math.abs(toMs(sh.x0) - st.T) > 1000) fail(tag + ": the playhead is not at the date");
        });
        var pr = pill.getBoundingClientRect(), pillUp = pill.style.display !== "none";
        if (head !== pillUp) fail(tag + ": the year pill is " + (head ? "missing" : "still up"));
        if (pillUp) {
          // The year; while a box is up, the month and the year.
          var boxUp = st.beat && st.beatAlpha > 0 && !dismissed[st.beat.id], yr = String(new Date(st.T).getUTCFullYear());
          if (pill.textContent !== (boxUp ? monthOf(st.T) : yr)) fail(tag + ": the pill says " + pill.textContent + ", not " + (boxUp ? monthOf(st.T) : yr));
          if (pr.left < r.left - 1 || pr.right > r.right + 1 || pr.bottom > r.bottom + 1) fail(tag + ": the year pill is outside the figure");
          Array.prototype.forEach.call(gd.querySelectorAll(".xtick text"), function (el) {
            var b = el.getBoundingClientRect();
            if (el.style.visibility === "hidden") return;
            if (b.left < pr.right + 6 && pr.left < b.right + 6) fail(tag + ": an axis label crowds the year pill");
            if (el.textContent === yr) fail(tag + ": the axis repeats the year in the pill");
          });
        }
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
          if (seg.kind === "break" && s < held + tr.move) fail(tag + ": a ghost is up before the axis has moved: " + e.label);
          if (hoverAt(e).indexOf(e.description) >= 0) fail(tag + ": a ghost answers the cursor: " + e.label);
        });
        // The title card and its scrim.
        var cardUp = actCard.style.display !== "none";
        if (cardUp !== (st.card >= 0 && st.cardAlpha > 0)) fail(tag + ": the act's title card is " + (cardUp ? "up" : "missing"));
        if (cardUp !== (scrim.style.display !== "none")) fail(tag + ": the scrim and the title card are not up together");
        if (cardUp && (actCard.querySelector(".china-act-kicker").textContent !== M.play.acts[st.card].kicker
            || actCard.querySelector(".china-act-name").textContent !== M.play.acts[st.card].card_title)) fail(tag + ": the title card has the wrong words");
        if (seg.kind !== "end" && (gd.layout.shapes[CHORDS[0].shape].visible !== false || CLIMB_UP()
            || ERACHORDS.some(function (ec) { return gd.layout.shapes[ec.shape].visible !== false; }))) fail(tag + ": a chord is drawn before the ending");
        // Every event line at its strength: full during play; a share of it once the view has pulled back (and on the way).
        var share_ = seg.kind === "end" ? M.final_line_share : seg.kind === "pull" ? 1 - (1 - M.final_line_share) * st.vu : 1;
        EV.forEach(function (e, n) {
          var sh = fl.shapes[e.shape];
          // (Those fully drawn, and not picked out by a box.)
          if (e.tick || e.ghost || sh.visible === false || (st.beat && st.beat.event === n) || st.clock - clockOf(e.t) < M.play.reveal) return;
          var want = M.event_line_opacity * share_;
          if (Math.abs(sh.opacity - want) > 0.02) fail(tag + ": an event line is not at its strength: " + e.label + " " + (+sh.opacity).toFixed(3) + " vs " + want.toFixed(3));
        });
        // Nothing moves within an act but the data: every label is where it was.
        if (seg.kind === "play") cl.boxes.forEach(function (b) {
          if (b.i < 0) return;
          var at0 = seen[b.i], now = [b.l - r.left, b.t - r.top];
          if (at0 && at0.act === k && Math.hypot(at0.at[0] - now[0], at0.at[1] - now[1]) > 0.75)
            fail(tag + ": a label moved within the act: " + b.name + " by " + Math.hypot(at0.at[0] - now[0], at0.at[1] - now[1]).toFixed(1) + " px");
          seen[b.i] = {act: k, at: now};
        });
        anchorsDrawn(tag);
        // A rate arrow is up only with its box, and only once the playhead is at its span's last point;
        // the interlude's only at rest at its act's end.
        var ia = fl.annotations[AN.inter_arrow];
        BEATS.forEach(function (b) {
          ratesOf(b).forEach(function (R) {
            var up = fl.annotations[R.arrow].visible !== false;
            var wanted = st.beat === b && st.beatAlpha > 0 && !dismissed[b.id] && (R.reference || st.clock > b.c0);
            if (up !== !!wanted) fail(tag + ": the rate arrow " + R.lead + " is " + (wanted ? "missing" : "up without its box"));
            if (up && !R.reference && st.T < toMs(R.end) - DAY) fail(tag + ": the rate arrow " + R.lead + " is drawn before the playhead reaches its end");
          });
        });
        var interWanted = (seg.kind === "inter" && s > 0) || (seg.kind === "break" && seg.act === M.play.interlude.act && s < tr.card_in);
        if ((ia.visible !== false) !== interWanted) fail(tag + ": the interlude's arrow is " + (interWanted ? "missing" : "up where it should not be"));
        out.frames[tag] = {texts: cl.texts, minGapText: cl.minGapText, minGapData: cl.minGapData,
                           x: iso(x0).slice(0, 7) + " to " + iso(x1).slice(0, 7), ghosts: names(ghosts), pill: pill.style.display !== "none" ? pill.textContent : null};
        return cl;
      });
    }

    var fill0 = [gd.data[TR.fill_behind].y.slice(), gd.data[TR.fill_ahead].y.slice()];
    return frames(3).then(function () {
      var c = collisions("complete");
      delete c.boxes;
      out.frames.complete = c;
      anchorsDrawn("complete");
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
          var want = parent.notes.map(function (n) { return "**" + n.when + "**: " + n.text; });
          if (at0 < 0 || lines.map(function (n) { return typeof n === "string" ? null : n.text; }).join("|") !== want.join("|"))
            fail("a parent's notes are not listed under it in date order: " + parent.label);
          // And the box as drawn says the same: the parent's own text, then one line per note.
          var ax = parent.panel === "economy" ? fl5.yaxis : fl5.yaxis2, hx = fl5.xaxis.l2p(parent.t);
          showTip(r.left + fl5.xaxis._offset + hx, r.top + ax._offset + ax._length * 0.6);
          var drawn = Array.prototype.map.call(tip.querySelectorAll(".china-tip-note"), function (d) { return d.textContent; });
          var from = drawn.indexOf(unbold(parent.description));
          if (from < 0 || drawn.slice(from + 1, from + 1 + want.length).join("|") !== want.map(unbold).join("|"))
            fail("the hover box does not show a parent's text and notes: " + parent.label + " / " + drawn.join(" ; "));
          // Each line leads with its date in bold, then a colon.
          Array.prototype.forEach.call(tip.querySelectorAll(".china-tip-note"), function (d) {
            var b = d.firstChild;
            if (!b || b.nodeName !== "B" || !/^:/.test(b.nextSibling ? b.nextSibling.textContent : ""))
              fail("a line of the hover box does not lead with a bold date and a colon: " + d.textContent.slice(0, 40));
          });
          if (tip.querySelectorAll(".china-tip-sub").length < want.length) fail("notes are not set apart in the hover box: " + parent.label);
          hideTip();
        });
      EV.filter(function (e) { return e.tick; }).forEach(function (e) {
        var ax = e.panel === "economy" ? fl5.yaxis : fl5.yaxis2, hx = fl5.xaxis.l2p(e.t);
        showTip(r.left + fl5.xaxis._offset + hx, r.top + ax._offset + ax._length * 0.6);
        var drawn = Array.prototype.map.call(tip.querySelectorAll(".china-tip-note"), function (d) { return d.textContent; });
        if (drawn.indexOf(unbold(e.description)) < 0) fail("the hover box does not show a tick's text: " + e.label);
        hideTip();
      });
      // Hover highlighting, on the finished chart: a labelled event's line goes solid, dark and 2 px
      // wide and its label bold; a tick taller and darker, its target 6 px either side; all of it
      // gone when the cursor leaves, and nothing else moved. And what a hover costs.
      out.highlight = {};
      function hotNow() {
        return Array.prototype.filter.call(hotBox.querySelectorAll(".china-hot"), function (el) { return el.style.display !== "none"; })
          .map(function (el) { var b = el.getBoundingClientRect(); return {w: +b.width.toFixed(1), h: +b.height.toFixed(1), x: b.left + b.width / 2, color: el.style.background}; });
      }
      // (Each the one furthest from any other event in its panel, so that the cursor is on it alone.)
      function room(e) {
        return Math.min.apply(null, EV.filter(function (o) { return o !== e && o.on && o.panel === e.panel; })
          .map(function (o) { return Math.abs(fl5.xaxis.l2p(o.t) - fl5.xaxis.l2p(e.t)); }));
      }
      function loneliest(list) { return list.sort(function (a, b) { return room(b) - room(a); })[0]; }
      var tickEv = loneliest(EV.filter(function (e) { return e.tick && e.on; }));
      var labEv = loneliest(EV.filter(function (e) { return !e.tick && e.on && e.labelled && e.lead === null; }));
      [labEv, tickEv].forEach(function (e) {
        if (!e) return;
        var ax = e.panel === "economy" ? fl5.yaxis : fl5.yaxis2, hx = r.left + fl5.xaxis._offset + fl5.xaxis.l2p(e.t);
        var before = collisions("before hover").boxes.map(function (b) { return [b.name, Math.round(b.l), Math.round(b.t)].join(); }).join("|");
        showTip(hx + (e.tick ? 5.5 : 3.5), r.top + ax._offset + ax._length * 0.6);
        var lit = hotNow(), tx = e.tick ? null : label(e.annotation).querySelector("text");
        out.highlight[e.tick ? "tick" : "labelled"] = e.label + ": " + lit.map(function (h) { return h.w + "×" + h.h; }).join(", ");
        if (!lit.length) fail("hovering an event does not pick it out: " + e.label);
        // (Faint on the finished chart, a line comes back at full strength while it is hovered: solid ink.)
        lit.forEach(function (h) { if (/rgba\([^)]*,\s*0?\.\d+\)/.test(h.color)) fail("a hovered line is not at full strength: " + e.label + " " + h.color); });
        // (On a narrow plot a neighbour may be under the cursor too: it is picked out as well.)
        var cx_ = hx + (e.tick ? 5.5 : 3.5);
        if (!lit.some(function (h) { return Math.abs(h.x - hx) <= 1.5; })) fail("the highlight is not on the event's line: " + e.label);
        lit.forEach(function (h) { if (Math.abs(h.x - cx_) > (e.tick ? 6 : 4) + 1.5) fail("something not under the cursor is picked out: " + e.label); });
        if (e.tick) {
          var sh = fl5.shapes[e.shape], tall = (sh.y1 - sh.y0) * ax._length;
          var own_ = lit.filter(function (h) { return Math.abs(h.x - hx) <= 1.5; })[0];
          if (!own_ || own_.h < tall + 4 || own_.w <= sh.line.width) fail("a hovered tick does not grow taller: " + e.label);
        } else {
          if (lit.some(function (h) { return Math.abs(h.w - 2) > 0.2; })) fail("a hovered event's line is not 2 px wide: " + e.label);
          if (!tx || getComputedStyle(tx).fontWeight < 600) fail("a hovered event's label is not bold: " + e.label);
        }
        var after = collisions("hovered").boxes.filter(function (b) { return b.kind !== "card"; }).map(function (b) { return [b.name, Math.round(b.l), Math.round(b.t)].join(); }).join("|");
        if (!e.tick && before.split("|").length !== after.split("|").length) fail("hovering changes what is drawn: " + e.label);
        hideTip();
        if (hotNow().length || (tx && getComputedStyle(tx).fontWeight >= 600)) fail("the highlight stays after the cursor leaves: " + e.label);
        // Its cost: one hover, as the browser handles it (the hover box and the highlight).
        var n = 60, t0 = performance.now();
        for (var i = 0; i < n; i++) showTip(hx + (i % 2), r.top + ax._offset + ax._length * 0.6);
        out.highlight[(e.tick ? "tick" : "labelled") + "Ms"] = +((performance.now() - t0) / n).toFixed(2);
        hideTip();
      });
      // Each leader's segment gives that leader's own hover text, and nothing shared.
      LEADERS.forEach(function (l) {
        var mid = (Math.max(l.t0, X0) + Math.min(l.t1, T1)) / 2, hx = fl5.xaxis.l2p(mid), hy = fl5.yaxis._offset - GEO.leader - L.strip.leader / 2;
        var said = describe(hx, hy, r.left + fl5.xaxis._offset + hx, r.top + hy, fl5.xaxis, fl5.yaxis, fl5.yaxis2);
        if (said.length !== 1 || said[0] !== l.description) fail("a leader's segment does not give its own hover text alone: " + l.label + " / " + said.join(" ; "));
      });
      // The finished chart is what the page opens on: both chords, from the anchor to each
      // series' last point; each rate, the final value over the years since the anchor; the gap's
      // arrow between the two ends and what it measures; no playhead, no pill, no card, no box;
      // and a play button that says play, not replay.
      var years = (T1 - TA) / YEAR, ends = [last(S.e), last(S.s)];
      out.end = {years: +years.toFixed(4), chords: []};
      CHORDS.forEach(function (ch, n) {
        var sh = fl5.shapes[ch.shape], lab = fl5.annotations[ch.annotation], finish = ends[n], rate = finish / years;
        var says = (rate >= 0 ? "+" : "−") + Math.abs(rate).toFixed(3) + " bits/yr (×" + Math.pow(2, rate).toFixed(3) + "/yr)";
        out.end.chords.push(ch.key + ": " + finish + " bits / " + years.toFixed(3) + " yr = " + rate.toFixed(5) + " → " + says);
        if (sh.visible === false) fail("a chord is missing from the finished chart: " + ch.key);
        if (toMs(sh.x0) !== TA || sh.y0 !== 0 || toMs(sh.x1) !== last(S.t) || Math.abs(sh.y1 - finish) > 1e-9)
          fail("a chord does not run from the anchor to its series' last point: " + ch.key);
        if (sh.line.dash !== "dash" || sh.line.color !== (n ? M.colors.stock : M.colors.gdp)) fail("a chord is not dashed in its series' colour: " + ch.key);
        if (Math.abs(ch.rate - rate) > 1e-5 || ch.text.indexOf(says) < 0) fail("a rate is not the final value over the years: " + ch.text + " vs " + says);
        if (FIT.ends) {
          if (lab.visible === false || !(lab.opacity > 0.99) || plain(lab.text).replace(" (", "(") !== says.replace(" (", "("))
            fail("a rate is not shown at its chord's end on the finished chart: " + ch.key + " / " + plain(lab.text));
          if (lab.font.color !== ch.color || lab.text.indexOf("<b>") !== 0) fail("a rate is not in its series' colour, in bold: " + ch.key);
          if (toMs(lab.x) !== last(S.t) || Math.abs(lab.y - finish) > 1e-9) fail("a rate is not at its chord's end: " + ch.key);
        } else if (!Array.prototype.some.call(keyBox.children, function (row) { return !row.hidden && row.textContent.indexOf(says) >= 0; }))
          fail("a rate is neither in the plot nor in the key: " + ch.key);
      });
      // The top panel: each era's chord from the line's point at its start to the one at its end; its
      // rate, the change over the years between, near the chord (clear of the event lines) or in the
      // gutter, saying on hover what it was in growth; the climb's arrow from the 1978 level to the
      // line's last point, and its label in the gutter.
      (function () {
        var r5 = gd.getBoundingClientRect(), xa5 = fl5.xaxis, right5 = r5.left + xa5._offset + xa5._length;
        out.end.eras = [];
        ERACHORDS.forEach(function (ec) {
          var sh = fl5.shapes[ec.shape], lab = fl5.annotations[ec.annotation];
          var a = G.t.indexOf(ec.t0), b = G.t.indexOf(ec.t1), rate = (G.y[b] - G.y[a]) / Math.round((ec.t1 - ec.t0) / YEAR);
          var said = ec.name + ", " + ec.span + ": " + (rate >= 0 ? "+" : "−") + Math.abs(rate).toFixed(3) + " bits/yr";
          if (Math.pow(2, rate).toFixed(2) !== "1.00") said += " (×" + Math.pow(2, rate).toFixed(3) + "/yr)";
          if (a < 0 || b < 0) return fail("an era's chord does not start and end on the line's points: " + ec.name);
          if (sh.visible === false || toMs(sh.x0) !== ec.t0 || toMs(sh.x1) !== ec.t1 || sh.y0 !== G.y[a] || sh.y1 !== G.y[b] || sh.yref !== "y")
            fail("an era's chord does not run between its points on the finished chart: " + ec.name);
          if (sh.line.dash !== "dash" || sh.line.color !== M.colors.gdp) fail("an era's chord is not dashed lime: " + ec.name);
          if (Math.abs(ec.rate - rate) > 1e-5 || ec.text !== said) fail("an era's rate is not its change over its years: " + ec.text + " vs " + said);
          if (!ec.place) {
            if (FIT.ends) fail("an era's rate found no place on a chart with a gutter: " + ec.name);
            if (!Array.prototype.some.call(keyBox.children, function (row) { return !row.hidden && row.textContent.indexOf(said) >= 0; }))
              fail("an era's rate is neither in the plot nor in the key: " + ec.name);
            return out.end.eras.push(ec.name + ": in the key");
          }
          var lb = label(ec.annotation).getBoundingClientRect(), cx = (lb.left + lb.right) / 2, cy = (lb.top + lb.bottom) / 2;
          if (lab.visible === false || !(lab.opacity > 0.99) || plain(lab.text) !== said) fail("an era's rate is not shown on the finished chart: " + ec.name);
          if (lab.font.color !== ec.color || lab.text.indexOf("<b>") !== 0) fail("an era's rate is not in lime, in bold: " + ec.name);
          if (ec.place.gutter !== lb.left >= right5) fail("an era's rate is not where it was placed: " + ec.name);
          if (lb.top < r5.top + fl5.yaxis._offset || lb.bottom > r5.top + fl5.yaxis._offset + fl5.yaxis._length) fail("an era's rate is outside the top panel: " + ec.name);
          var said_ = describe(cx - r5.left - xa5._offset, cy - r5.top, cx, cy, xa5, fl5.yaxis, fl5.yaxis2);
          if (said_.indexOf(ec.hover) < 0) fail("an era's rate does not say what it was in growth on hover: " + ec.name);
          var mid = xa5.l2p((ec.t0 + ec.t1) / 2) + r5.left + xa5._offset;
          out.end.eras.push(ec.name + ": " + (ec.place.gutter ? "in the gutter" : "in the plot, " + Math.round(cx - mid) + " px from the chord's middle")
                            + " (" + plain(lab.text).length + " characters, " + lab.text.split("<br>").length + " line(s))");
        });
        var arrow = fl5.annotations[CLIMB.arrow], cl = fl5.annotations[CLIMB.label], gEnd = last(G.y);
        var says = (gEnd >= 0 ? "+" : "−") + Math.abs(gEnd).toFixed(2) + " bits since " + new Date(toMs(M.anchors[0].date)).getUTCFullYear()
          + " (×" + (Math.pow(2, gEnd) >= 10 ? Math.pow(2, gEnd).toFixed(0) : Math.pow(2, gEnd).toFixed(1)) + ")";
        out.end.climb = says;
        if (arrow.visible === false || arrow.arrowside !== "end+start" || toMs(arrow.x) !== last(G.t) || toMs(arrow.ax) !== last(G.t)
            || Math.abs(arrow.y - gEnd) > 1e-9 || arrow.ay !== 0) fail("the climb's arrow does not run from the 1978 level to the line's last point");
        if (arrow.arrowcolor !== P.text("arrow") || arrow.xshift !== L.end.arrow) fail("the climb's arrow is not in ink beside the last point");
        if (CLIMB.text !== says) fail("the climb's label does not say what the arrow measures: " + CLIMB.text + " vs " + says);
        if (FIT.ends) {
          var cb = label(CLIMB.label).getBoundingClientRect();
          if (!CLIMB.place || cl.visible === false || !(cl.opacity > 0.99) || plain(cl.text) !== says) fail("the climb's label is not shown on the finished chart");
          else if (cb.left < right5) fail("the climb's label is not in the gutter");
        } else if (!Array.prototype.some.call(keyBox.children, function (row) { return !row.hidden && row.textContent.indexOf(says) >= 0; }))
          fail("the climb's label is neither in the gutter nor in the key");
        // The event lines, faint: each at a share of its playing strength.
        var faintWant = M.event_line_opacity * M.final_line_share, seen = [];
        EV.forEach(function (e) {
          var s_ = fl5.shapes[e.shape];
          if (e.tick || !e.on || s_.visible === false) return;
          seen.push(+s_.opacity);
          if (Math.abs(s_.opacity - faintWant) > 1e-6) fail("an event line is not faint on the finished chart: " + e.label + " " + s_.opacity);
        });
        out.end.lines = seen.length + " lines at opacity " + faintWant.toFixed(3) + " (" + (100 * M.final_line_share).toFixed(1) + "% of " + M.event_line_opacity + ")";
      })();
      var gapNow = ends[0] - ends[1], arrow = fl5.annotations[GAP.arrow], gapSays = "Gap: " + Math.abs(gapNow).toFixed(2) + " bits (×" + Math.pow(2, Math.abs(gapNow)).toFixed(1) + ")";
      out.end.gap = gapSays;
      if (arrow.visible === false || !arrow.showarrow || arrow.arrowside !== "end+start") fail("the gap's arrow is missing or is not double-headed");
      if (toMs(arrow.x) !== last(S.t) || toMs(arrow.ax) !== last(S.t) || Math.abs(arrow.y - ends[0]) > 1e-9 || Math.abs(arrow.ay - ends[1]) > 1e-9)
        fail("the gap's arrow does not run between the two lines' ends");
      if (arrow.arrowcolor !== P.text("arrow")) fail("the gap's arrow is not in ink");
      if (GAP.text !== gapSays || Math.abs(GAP.value - gapNow) > 1e-5) fail("the gap is not the economy's end less the stocks': " + GAP.text + " vs " + gapSays);
      if (FIT.ends ? plain(fl5.annotations[GAP.label].text).replace(" (", "(") !== gapSays.replace(" (", "(") || fl5.annotations[GAP.label].visible === false
          : !Array.prototype.some.call(keyBox.children, function (row) { return !row.hidden && row.textContent.indexOf(gapSays) >= 0; }))
        fail("the gap's label is neither beside its arrow nor in the key");
      M.playhead.forEach(function (i) { if (fl5.shapes[i].visible !== false) fail("the playhead is drawn on the finished chart"); });
      BEATS.forEach(function (b) { ratesOf(b).forEach(function (R) {
        if (fl5.annotations[R.arrow].visible !== false || fl5.annotations[R.label].visible !== false) fail("a rate arrow is on the finished chart: " + R.lead);
      }); });
      if (pulseRing.style.display !== "none" || pulseDot.style.display !== "none") fail("a pulse is on the finished chart");
      if (pill.style.display !== "none") fail("the year pill is showing on the finished chart");
      if (actCard.style.display !== "none" || beatCard.style.display !== "none" || scrim.style.display !== "none") fail("a card, a box or the scrim is showing on the finished chart");
      if (playBtn.classList.contains("is-done") || playBtn.classList.contains("is-playing")) fail("the play button does not say play when the page opens");
      // The speed toggle, and the labels at the ends of the scrubber.
      // It starts at the default speed, shows the speed it is at, and cycles through the rest.
      var cycle = [speedBtn.textContent];
      if (speed !== M.play.speed || speedBtn.textContent !== M.play.speed + "×") fail("the speed toggle does not start at " + M.play.speed + "×");
      M.play.speeds.forEach(function () { speedBtn.click(); cycle.push(speedBtn.textContent); });
      out.controls = {speeds: cycle.join(" → "), start: startOut.textContent, end: endOut.textContent};
      var at_ = M.play.speeds.indexOf(M.play.speed), want_ = M.play.speeds.slice(at_).concat(M.play.speeds.slice(0, at_), [M.play.speed]);
      if (cycle.join() !== want_.map(function (v) { return v + "×"; }).join()) fail("the speed toggle does not cycle " + want_.join(", "));
      if (speed !== M.play.speed) fail("the speed toggle did not come back round");
      if (startOut.textContent !== String(new Date(T0).getUTCFullYear()) || endOut.textContent !== String(new Date(T1).getUTCFullYear()))
        fail("the scrubber's ends are not labelled with the first and last years");
      // The scrubber's segments: one label per act, in order, each over its own stretch of the track.
      var track = scrubWrap.getBoundingClientRect(), labels = actsBox.querySelectorAll(".china-act-label");
      if (labels.length !== ACTS.length || actsBox.querySelectorAll(".china-act-gap").length !== ACTS.length - 1) fail("the scrubber is not marked off in acts");
      ACTS.forEach(function (A, k) { if (!/^Part [IV]+ · \d{4}–\d{4}$/.test(A.kicker)) fail("a title card's overline is not “Part … · yyyy–yyyy”: " + A.kicker); });
      Array.prototype.forEach.call(labels, function (b, k) {
        var q = b.getBoundingClientRect(), a = track.left + (ACTS[k].t0 - T0) / (T1 - T0) * track.width, e = track.left + (ACTS[k].t1 - T0) / (T1 - T0) * track.width;
        var form = [ACTS[0].title, ACTS[0].short, ACTS[0].numeral].indexOf(labels[0].textContent);
        if (form < 0 || b.textContent !== [ACTS[k].title, ACTS[k].short, ACTS[k].numeral][form]) fail("the acts' labels are not all titles, all short forms or all numerals: " + b.textContent);
        if (form === 0 && b.textContent !== M.play.acts[k].title) fail("a part's label on the scrubber is not its title: " + b.textContent);
        if (form === 0 && k === 1 && !/^“.+”$/.test(b.textContent)) fail("the middle part's title is not in curly quotes on the scrubber");
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
      anchorsDrawn("after a zoom and an autoscale");
      // The whole play, segment by segment. First the opening card over the first frame: one dot.
      var tr = M.play.transition, en = M.play.ending, held = tr.card_in + tr.hold, chain = Promise.resolve();
      function then(tag, c, also) { chain = chain.then(function () { return moment(tag, c); }).then(also || function () {}); }
      function chord(n) { var sh = gd._fullLayout.shapes[CHORDS[n].shape]; return sh.visible === false ? 0 : (toMs(sh.x1) - TA) / (T1 - TA); }
      function shown(i) { var a = gd._fullLayout.annotations[i]; return a.visible === false ? 0 : a.opacity === undefined ? 1 : a.opacity; }
      function eraChord(n) { var ec = ERACHORDS[n], sh = gd._fullLayout.shapes[ec.shape]; return sh.visible === false ? 0 : (toMs(sh.x1) - ec.t0) / (ec.t1 - ec.t0); }
      function climbLength() { var a = gd._fullLayout.annotations[CLIMB.arrow]; return a.visible === false ? 0 : a.y / CLIMB.value; }
      function arrowLength() { var a = gd._fullLayout.annotations[GAP.arrow]; return a.visible === false ? 0 : (a.ay - GAP.top) / (GAP.bottom - GAP.top); }
      TL.forEach(function (seg) {
        var A = ACTS[seg.act], name = "act " + A.numeral;
        if (seg.kind === "open") {
          then("opening: card", seg.c0 + tr.card_in + tr.hold / 2, function () {
            var pts = [gd.data[TR.gdp].x.length, gd.data[TR.gdp_head].x.length, gd.data[TR.stock].x.length];
            if (pts.join() !== "1,1,0") fail("the first frame is not a single dot: " + pts.join());
            if (!(+actCard.style.opacity > 0.99)) fail("the opening title card is not fully up while it holds");
            if (Math.abs(+scrim.style.opacity - M.play.scrim) > 0.01) fail("the figure is not dimmed behind the opening title card");
            var q = actCard.getBoundingClientRect(), fl = gd._fullLayout, r = gd.getBoundingClientRect(), share = q.width / fl.xaxis._length;
            out.titleCard = {width: Math.round(q.width), shareOfPlot: +share.toFixed(2),
                             kicker: getComputedStyle(actCard.querySelector(".china-act-kicker")).fontSize, title: getComputedStyle(actCard.querySelector(".china-act-name")).fontSize};
            if (L.end.label !== null && (share < 0.5 || share > 0.6)) fail("the title card is not 50 to 60% of the plot's width: " + share.toFixed(2));
            if (Math.abs((q.left + q.right) / 2 - (r.left + fl.xaxis._offset + fl.xaxis._length / 2)) > 1.5) fail("the title card is not centred over the plot");
            if (q.left < r.left || q.right > r.right) fail("the title card is wider than the figure");
            if (actCard.querySelector("img")) fail("a title card has an image");
          });
          then("opening: ghost", seg.c0 + held + tr.ghost);
        } else if (seg.kind === "play") {
          [0.004, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.996].forEach(function (f) { then(name + " " + (100 * f).toFixed(1) + "%", seg.c0 + f * seg.dur); });
          // The annotations that are beats: playback slows to a text box's speed, the annotation fades
          // in, its point is marked and pulses once.
          NOTES.filter(function (n) { return n.act === seg.act; }).forEach(function (n) {
            then("annotation beat " + n.role + ": pulse", n.c0 + 0.3 * M.play.note.pulse, function () {
              var pace = paceAt(n.c0 + 0.5), q = pulseRing.getBoundingClientRect(), dt = pulseDot.getBoundingClientRect();
              var fl = gd._fullLayout, r = gd.getBoundingClientRect();
              var px = r.left + fl.xaxis._offset + fl.xaxis.l2p(n.t), py = r.top + fl.yaxis2._offset + fl.yaxis2.l2p(n.y);
              if (!pace || pace.now > 1.05 * BOX_SHARE * pace.base) fail("annotation beat " + n.role + ": playback does not slow to a text box's speed");
              if (pulseRing.style.display === "none" || pulseDot.style.display === "none") fail("annotation beat " + n.role + ": its point does not pulse");
              else if (Math.hypot((q.left + q.right) / 2 - px, (q.top + q.bottom) / 2 - py) > 2 || Math.hypot((dt.left + dt.right) / 2 - px, (dt.top + dt.bottom) / 2 - py) > 2)
                fail("annotation beat " + n.role + ": the pulse is not on its point");
              if (beatCard.style.display !== "none" && STATE.beat && STATE.beatAlpha > 0.5) fail("annotation beat " + n.role + ": a box is up");
              out.notes8 = (out.notes8 || []).concat([n.role + " at " + iso(n.t).slice(0, 10) + ": " + (n.c1 - n.c0 + M.play.card_fade).toFixed(2) + " s slow"]);
            });
            then("annotation beat " + n.role + ": annotation", n.c0 + M.play.reveal + 0.2, function () {
              var a = gd._fullLayout.annotations[AN[n.role]];
              if (FIT.arrows && (a.visible === false || !(a.opacity > 0.9))) fail("annotation beat " + n.role + ": the annotation has not faded in");
            });
            then("annotation beat " + n.role + ": after", n.c1 + M.play.card_fade + 0.05, function () {
              if (pulseRing.style.display !== "none" || pulseDot.style.display !== "none") fail("annotation beat " + n.role + ": the pulse stays");
            });
          });
        } else if (seg.kind === "inter") {
          // At rest at the act's end: the arrow drawn up from the 1978 level to the line, then its box.
          var IL = M.play.interlude;
          then("interlude: arrow", seg.c0 + IL.arrow_seconds / 2, function () {
            var a = gd._fullLayout.annotations[AN.inter_arrow];
            if (a.visible === false || !(a.y > 0.3 * IL.value && a.y < 0.7 * IL.value) || a.ay !== 0) fail("the interlude's arrow is not being drawn up from zero");
            if (beatCard.style.display !== "none") fail("the interlude's box is up before its arrow is drawn");
          });
          then("interlude: box", INTER.c0 + M.play.card_fade + IL.seconds / 2, function () {
            var a = gd._fullLayout.annotations[AN.inter_arrow], g = at(G.t, G.y, ACTS[seg.act].t1), fl = gd._fullLayout;
            if (a.visible === false || a.arrowside !== "end+start" || toMs(a.x) !== ACTS[seg.act].t1 || toMs(a.ax) !== ACTS[seg.act].t1
                || Math.abs(a.y - g) > 1e-4 || a.ay !== 0) fail("the interlude's arrow does not run from the 1978 level to the line at the playhead");
            if (a.arrowcolor !== P.text("arrow")) fail("the interlude's arrow is not in ink");
            if (beatCard.querySelector(".china-beat-lead").textContent !== IL.lead || beatCard.querySelector(".china-beat-text").textContent !== IL.text)
              fail("the interlude's box does not say what it should");
            out.interlude = IL.lead + " " + IL.text;
          });
        } else if (seg.kind === "break") {
          var into = "break after " + name;
          then(into + ": card in", seg.c0 + tr.card_in / 2);
          then(into + ": hold", seg.c0 + tr.card_in + tr.hold / 2, function () {
            if (!(+actCard.style.opacity > 0.99)) fail(into + ": the title card is not fully up while it holds");
            if (Math.abs(+scrim.style.opacity - M.play.scrim) > 0.01) fail(into + ": the figure is not dimmed behind the title card");
            if (EV.some(function (e) { return e.act > seg.act && gd._fullLayout.shapes[e.shape].visible !== false; })) fail(into + ": the next act's events are up before the axis has moved");
          });
          then(into + ": moving", seg.c0 + held + tr.move / 2);
          then(into + ": ghost", seg.c0 + held + tr.move + tr.ghost, function () {
            if (!EV.some(function (e) { return e.ghost && e.act === seg.act + 1; })) fail(into + ": no ghost appears once the axis has moved");
          });
          then(into + ": card out", seg.c0 + seg.dur - tr.card_out / 2);
        } else if (seg.kind === "end") {
          // The ending, step by step, in the whole chart's view: each era's chord alone, then its rate;
          // the climb's arrow, its label, a pause; the lime chord, its rate, a pause; the periwinkle
          // one, its rate, a pause; the gap's arrow, its label; the last box.
          var E = seg.marks;
          out.ending = {era: E.era, eraRate: E.eraRate, climb: E.climb, climbLabel: E.climbLabel, chord: E.chord, rate: E.rate,
                        arrow: E.arrow, gap: E.gap, box: E.box, dur: +seg.dur.toFixed(3)};
          ERACHORDS.forEach(function (ec, n) {
            then("ending: era chord " + (n + 1), seg.c0 + E.era[n] + en.chord / 2, function () {
              var drawn = ERACHORDS.map(function (_, m) { return eraChord(m); });
              if (!(drawn[n] > 0.3 && drawn[n] < 0.7) || drawn.some(function (d, m) { return m < n ? d !== 1 : m > n && d !== 0; }) || shown(ec.annotation)
                  || climbLength() || chord(0)) fail("the eras' chords are not drawn in turn: " + ec.name + " " + drawn.map(function (d) { return d.toFixed(2); }).join(", "));
            });
            then("ending: era rate " + (n + 1), seg.c0 + E.eraRate[n] + en.label + en.pause / 4, function () {
              if (eraChord(n) !== 1 || (ec.place && shown(ec.annotation) < 0.99) || (n + 1 < ERACHORDS.length && eraChord(n + 1)))
                fail("an era's rate does not follow its chord: " + ec.name);
            });
          });
          then("ending: climb arrow", seg.c0 + E.climb + en.arrow / 2, function () {
            if (!(climbLength() > 0.3 && climbLength() < 0.7) || shown(CLIMB.label) || chord(0)) fail("the climb's arrow is not drawn up from the 1978 level, after the eras: " + climbLength().toFixed(2));
          });
          then("ending: climb label", seg.c0 + E.climbLabel + en.label + en.pause / 2, function () {
            if (climbLength() !== 1 || (CLIMB.place && shown(CLIMB.label) < 0.99) || chord(0)) fail("the climb's label does not follow its arrow, with a pause before the bottom panel");
          });
          then("ending: first chord", seg.c0 + E.chord[0] + en.chord / 2, function () {
            if (ERACHORDS.some(function (ec, n) { return eraChord(n) !== 1 || (ec.place && shown(ec.annotation) < 0.99); }) || climbLength() !== 1)
              fail("the top panel's chords and arrow do not stay while the bottom panel's are drawn");
            if (!(chord(0) > 0.3 && chord(0) < 0.7) || chord(1) !== 0 || shown(CHORDS[0].annotation)) fail("the economy's chord is not drawn first, alone: " + chord(0).toFixed(2) + " / " + chord(1).toFixed(2));
          });
          then("ending: first rate", seg.c0 + E.rate[0] + en.label + en.pause / 2, function () {
            if (chord(0) !== 1 || chord(1) !== 0 || (FIT.ends && shown(CHORDS[0].annotation) < 0.99) || shown(CHORDS[1].annotation)) fail("the economy's rate does not follow its chord, before the stocks' chord");
          });
          then("ending: second chord", seg.c0 + E.chord[1] + en.chord / 2, function () {
            if (!(chord(1) > 0.3 && chord(1) < 0.7) || shown(CHORDS[1].annotation) || arrowLength()) fail("the stocks' chord is not drawn second: " + chord(1).toFixed(2));
          });
          then("ending: second rate", seg.c0 + E.rate[1] + en.label + en.pause / 2, function () {
            if (chord(1) !== 1 || (FIT.ends && shown(CHORDS[1].annotation) < 0.99) || arrowLength()) fail("the stocks' rate does not follow its chord, before the gap's arrow");
          });
          then("ending: gap arrow", seg.c0 + E.arrow + en.arrow / 2, function () {
            if (!(arrowLength() > 0.3 && arrowLength() < 0.7) || shown(GAP.label)) fail("the gap's arrow is not drawn between the two ends before its label: " + arrowLength().toFixed(2));
          });
          then("ending: gap label", seg.c0 + E.gap + en.label + 0.1, function () {
            if (arrowLength() !== 1 || (FIT.ends && shown(GAP.label) < 0.99)) fail("the gap's label does not follow its arrow");
            if (beatCard.style.display !== "none") fail("the last box is up before the gap is labelled");
          });
          then("ending: last box", seg.c0 + E.box + M.play.card_fade + M.play.final.seconds / 2, function () {
            var q = beatCard.getBoundingClientRect(), r = gd.getBoundingClientRect();
            if (beatCard.style.display === "none" || !(+beatCard.style.opacity > 0.99)) return fail("the last box is not up while it holds");
            if (beatCard.querySelector(".china-beat-lead").textContent !== M.play.final.lead || beatCard.querySelector(".china-beat-text").textContent !== M.play.final.text)
              fail("the last box does not say what it should");
            if (!FINAL.box.below && (q.left < r.left || q.right > r.right || q.top < r.top || q.bottom > r.bottom)) fail("the last box is outside the figure");
            out.frames["ending: last box"].box = [Math.round(q.left - r.left), Math.round(q.top - r.top), Math.round(q.width), Math.round(q.height)];
          });
          then("ending: box gone", seg.c0 + seg.dur - 0.05, function () {
            if (beatCard.style.display !== "none" && +beatCard.style.opacity > 0.3) fail("the last box has not faded by the end");
          });
        } else if (seg.kind === "pull") {
          // The pull-back comes first, as the data ends: nothing of the ending is drawn yet, and no box is up.
          then("pull-back: moving", seg.c0 + seg.dur / 2, function () {
            if (ERACHORDS.some(function (_, n) { return eraChord(n); }) || climbLength() || chord(0) || chord(1) || arrowLength())
              fail("the ending is drawn before the view has pulled back");
            if (beatCard.style.display !== "none") fail("a box is up in the pull-back");
          });
        }
      });
      // The dates where the strips are busiest.
      [1961.2, 1966.6, 1966.97, 1967.5, 1972.3, 1977.5, 1980.2, 1985, 1989.6, 1992.6, 1994.2, 1999.3, 2002.5, 2005, 2008.4, 2011.2, 2016, 2019, 2023].forEach(function (y) {
        var T = Date.UTC(Math.floor(y), 0, 1) + (y % 1) * YEAR;
        then("date " + y + " (act " + ACTS[actOf(T)].numeral + ")", clockAt(T));
      });
      return chain;
    }).then(function () {
      // Each beat's box, three quarters of the way through its time: its words, inside the figure, off the
      // playhead and its dots; a picture card's picture and credit. (That it is off the data and
      // off every label and annotation is in the collisions.)
      var chain = Promise.resolve();
      out.pictures = [];
      BEATS.forEach(function (b, n) {
        var tag = "box " + (n + 1) + " (" + iso(b.t).slice(0, 7) + ")";
        chain = chain.then(function () { return moment(tag, b.c0 + 0.75 * (b.c1 - b.c0)); }).then(function () {
          var fl = gd._fullLayout, r = gd.getBoundingClientRect(), q = beatCard.getBoundingClientRect();
          if (!b.box) return fail(tag + ": no place was found for the box");
          if (beatCard.style.display === "none" || !(+beatCard.style.opacity > 0.99)) return fail(tag + ": the box is not up");
          if (beatCard.querySelector(".china-beat-lead").textContent !== b.lead || beatCard.querySelector(".china-beat-text").textContent !== b.text)
            fail(tag + ": the box does not say what the beat says");
          if (getComputedStyle(beatCard.querySelector(".china-beat-lead")).fontWeight < 600) fail(tag + ": the box's date is not bold");
          if (!b.box.below && (q.left < r.left || q.right > r.right || q.top < r.top || q.bottom > r.bottom)) fail(tag + ": the box is outside the figure");
          if (!!b.box.below !== (q.top >= r.bottom)) fail(tag + ": the box is not where it was placed");
          // The playhead for as long as the box is up: never on its line, nor on a dot (the current
          // value of each line, in whichever panels the box touches).
          if (!b.box.below) [b.since, playhead, b.until].forEach(function (T) {
            var x = r.left + fl.xaxis._offset + fl.xaxis.l2p(T);
            if (x > q.left - 6 && x < q.right + 6) fail(tag + ": the box is on the playhead");
            [[fl.yaxis, [at(G.t, G.y, T)]], [fl.yaxis2, [at(S.t, S.s, T), at(S.t, S.e, T)]]].forEach(function (pn) {
              pn[1].forEach(function (v) {
                var y = v === null ? null : r.top + pn[0]._offset + pn[0].l2p(v);
                if (y !== null && x > q.left - 6 && x < q.right + 6 && y > q.top - 6 && y < q.bottom + 6) fail(tag + ": the box is on the playhead's dot");
              });
            });
          });
          // A picture card: the picture at full strength, at its size, with its credit; a text box: none.
          var img = beatCard.querySelector(".china-beat-img"), has = getComputedStyle(img).display !== "none", credit = beatCard.querySelector(".china-beat-credit").textContent;
          if (b.kind === "picture") {
            out.pictures.push(tag + ": " + (has ? Math.round(img.getBoundingClientRect().width) + "×" + Math.round(img.getBoundingClientRect().height) + " px, " + b.box.how.kind : "DROPPED") + ", “" + credit + "”");
            if (has && (img.getAttribute("src") !== b.picture.src || credit !== b.picture.credit || +getComputedStyle(img).opacity < 1)) fail(tag + ": the picture or its credit is wrong");
            var side_ = Math.max(img.getBoundingClientRect().width, img.getBoundingClientRect().height);   // its longer side
            var cap_ = b.picture.max_px;
            if (has && !L.card.below && (cap_ ? side_ > cap_ + 1 || side_ < Math.min(165, cap_) - 1 : side_ < 165 || side_ > 285)) fail(tag + ": the picture is not a sensible size");
            if (!has && !L.card.below) out.picturesDropped = (out.picturesDropped || []).concat([tag]);
            // (At the full column, with the figure as published, every picture shows. Rebuilt at another anchor the
            // data stand elsewhere, and a card may fall back to words.)
            if (!has && GEO.plotW + L.margin.l + L.margin.r >= 900 && !M.anchor_moved) fail(tag + ": the picture is not shown at the full column");
          } else if (has || credit) fail(tag + ": a text box shows a picture or a credit");
          if (b.event !== null && gd._fullLayout.shapes[EV[b.event].shape].opacity < 0.8) fail(tag + ": the box's event is not picked out");
          out.frames[tag].box = [Math.round(q.left - r.left), Math.round(q.top - r.top), Math.round(q.width), Math.round(q.height)];
          // In its own panel (economy boxes in the top one, market boxes in the bottom one), unless there is no room there.
          if (!b.box.below && !b.box.fallback && ((b.box.spans && !b.cross) || b.box.k !== (b.panel === "economy" ? 0 : 1)))
            fail(tag + ": the box is not in its own panel");
          if (b.box.fallback) { out.fallbacks = out.fallbacks || []; out.fallbacks.push(iso(b.t).slice(0, 10)); }
          // Up for its reading time, and its fades.
          // (Longer only where playback comes to rest at its part's end meanwhile.)
          var held_ = b.c1 - b.c0 - M.play.card_fade;
          if (held_ < b.seconds - 0.05) fail(tag + ": the box is not up for its reading time");
          if (held_ > b.seconds + 0.05) { out.longer = out.longer || []; out.longer.push(iso(b.t).slice(0, 10) + " +" + (held_ - b.seconds).toFixed(1) + " s"); }
          // On its date: where the playhead is as the box starts to come up, never more than 31 days from it.
          var appear = stateAt(b.c0).T, off = (appear - b.t) / DAY, pre = stateAt(b.c0 - 0.02), post = stateAt(b.c0 + 0.05);
          out.sync = out.sync || [];
          out.sync.push(iso(b.t).slice(0, 10) + ": " + (off >= 0 ? "+" : "") + off.toFixed(1) + " d");
          if (Math.abs(off) > M.play.sync) fail(tag + ": the box comes up " + off.toFixed(1) + " days from its date");
          if (b !== INTER && ((pre.beat === b && pre.beatAlpha > 0) || post.beat !== b || !(post.beatAlpha > 0))) fail(tag + ": the box does not come up at its moment");
          // Its rate arrows: tail and head over the span's two points, parallel to the chord between
          // them, clear above the line, in ink, with its rate and what that measures; the reference faint.
          if (b.rate) {
            out.rateArrows = out.rateArrows || {};
            ratesOf(b).forEach(function (R) {
              var ra = fl.annotations[R.arrow], rl = fl.annotations[R.label], xa = fl.xaxis;
              var slopeA = (ra.y - ra.ay) / (toMs(ra.x) - toMs(ra.ax)), slopeC = (R.y1 - R.y0) / (toMs(R.end) - toMs(R.start));
              if (ra.visible === false || rl.visible === false) return fail(tag + ": the rate arrow " + R.lead + " is not up");
              if (Math.abs(slopeA / slopeC - 1) > 1e-6 || toMs(ra.ax) !== toMs(R.start) || Math.abs(toMs(ra.x) - toMs(R.end)) > 1000)
                fail(tag + ": the rate arrow " + R.lead + " is not parallel to its chord, over its span");
              var ends = arrowEnds(R.arrow), want = [xa.l2p(toMs(R.start)), xa.l2p(toMs(R.end))];
              var off = ends ? Math.max(Math.abs(ends[0] - want[0]), Math.abs(ends[1] - want[1])) : Infinity;
              if (off > 2) fail(tag + ": the rate arrow " + R.lead + "'s ends are " + off.toFixed(1) + " px from its points");
              if (ra.arrowcolor !== P.text("arrow") || rl.font.color !== P.text("arrow") || Math.abs(ra.arrowwidth - M.play.rate.width) > 1e-9)
                fail(tag + ": the rate arrow " + R.lead + " is not in ink, " + M.play.rate.width + " px");
              var clear = Infinity;
              G.t.forEach(function (tt, i) {
                if (tt < toMs(R.start) || tt > toMs(R.end)) return;
                clear = Math.min(clear, (ra.ay + slopeA * (tt - toMs(ra.ax)) - G.y[i]) * GEO.ppb);
              });
              if (clear < 6) fail(tag + ": the rate arrow " + R.lead + " is not clear above the line (" + clear.toFixed(1) + " px)");
              if (rl.text !== R.text) fail(tag + ": the rate arrow " + R.lead + " is labelled " + rl.text);
              if (R.reference && Math.abs(ra.opacity - M.play.rate.reference) > 0.01) fail(tag + ": the reference arrow " + R.lead + " is not faint");
              var lb = label(R.label).getBoundingClientRect();
              if (describe(lb.left + lb.width / 2 - r.left - fl.xaxis._offset, lb.top + lb.height / 2 - r.top, lb.left + lb.width / 2, lb.top + lb.height / 2,
                           fl.xaxis, fl.yaxis, fl.yaxis2).indexOf(R.hover) < 0) fail(tag + ": the rate " + R.lead + " does not say what it measures on hover");
              out.rateArrows[R.lead + (R.reference ? " (reference)" : "")] = rl.text + ", ends within " + off.toFixed(2) + " px of its points, " + clear.toFixed(1) + " px above the line";
            });
            // Drawn tail to head as the box comes up, and not before.
            var R0 = b.rate, ra0 = function () { return gd.layout.annotations[R0.arrow]; };
            busy = false; pending = null; render(b.c0 - 0.02);
            if (ra0().visible !== false) fail(tag + ": the rate arrow " + R0.lead + " is up before its box");
            busy = false; pending = null; render(b.c0 + 0.3 * M.play.rate.draw);
            var part_ = (toMs(ra0().x) - toMs(R0.start)) / (toMs(R0.end) - toMs(R0.start));
            if (ra0().visible === false || !(part_ > 0.15 && part_ < 0.6)) fail(tag + ": the rate arrow " + R0.lead + " is not drawn tail to head (" + part_.toFixed(2) + ")");
            if (stateAt(b.c0).T < toMs(R0.end) - DAY) fail(tag + ": the box with the rate arrow " + R0.lead + " comes up before the playhead reaches its end");
            busy = false; pending = null; render(b.c0 + 0.75 * (b.c1 - b.c0));
            beatCard.click();
            render(clock);
            if (ratesOf(b).some(function (R) { return gd.layout.annotations[R.arrow].visible !== false; })) fail(tag + ": a rate arrow stays when its box is dismissed");
            dismissed = {};
          }
        });
      });
      // A click sends a box away, and it stays away.
      return chain.then(function () { return go((BEATS[0].c0 + BEATS[0].c1) / 2); }).then(function () {
        if (beatCard.style.display === "none") return fail("no box to dismiss");
        beatCard.click();
        if (beatCard.style.display !== "none" || !dismissed[BEATS[0].id]) fail("a click does not dismiss a box");
        render(clock + 0.2);
        if (beatCard.style.display !== "none") fail("a dismissed box comes back");
        dismissed = {};
        // The interlude's box: a click moves on to the break.
        return go(INTER.c0 + M.play.card_fade + 1);
      }).then(function () {
        beatCard.click();
        return frames(2);
      }).then(function () {
        if (clock < INTER.c1 + M.play.card_fade - 1e-6) fail("a click on the interlude's box does not move on");
        // And the last box: a click moves on to its fade.
        var end = TL.filter(function (s) { return s.kind === "end"; })[0];
        return go(end.c0 + end.marks.box + M.play.card_fade + 1).then(function () {
          beatCard.click();
          return frames(2);
        }).then(function () {
          if (clock < end.c0 + end.marks.boxOut - 1e-6) fail("a click on the last box does not move on");
        });
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
          var want2 = T0 + scrub.value / scrub.max * (T1 - T0), xa = gd._fullLayout.xaxis, k = actOf(want2);
          out.scrubber[(+f).toFixed(3)] = iso(playhead).slice(0, 10) + " in act " + ACTS[k].numeral;
          if (Math.abs(playhead - want2) > (T1 - T0) / scrub.max) fail("the scrubber is not linear in the date at " + f);
          if (STATE.kind !== "play" || STATE.act !== k || Math.abs(xa.r2l(xa.range[0]) - VIEWS[k].r0) > 1000 || Math.abs(xa.r2l(xa.range[1]) - VIEWS[k].r1) > 1000)
            fail("scrubbing to " + f + " does not show that date's act at once");
          if (gd._fullLayout.shapes[CHORDS[0].shape].visible !== false || gd._fullLayout.annotations[CHORDS[0].annotation].visible !== false
              || ERACHORDS.some(function (ec) { return gd._fullLayout.shapes[ec.shape].visible !== false || gd._fullLayout.annotations[ec.annotation].visible !== false; })
              || gd._fullLayout.annotations[CLIMB.arrow].visible !== false || gd._fullLayout.annotations[CLIMB.label].visible !== false
              || gd._fullLayout.annotations[GAP.arrow].visible !== false || gd._fullLayout.annotations[GAP.label].visible !== false)
            fail("scrubbing back does not hide the ending");
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
        if (!STATE.done || gd._fullLayout.shapes[CHORDS[1].shape].visible === false || gd._fullLayout.annotations[CLIMB.arrow].visible === false
            || ERACHORDS.some(function (ec) { return gd._fullLayout.shapes[ec.shape].visible === false; })
            || gd._fullLayout.annotations[GAP.arrow].visible === false) fail("the end of the scrubber is not the finished chart");
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
        return new Promise(function (ok) { var got = false; requestAnimationFrame(function () { got = true; }); setTimeout(function () { ok(got); }, 150); });
      }).then(function (frames_) {
        framed = frames_ && !document.hidden;
        play(END - 0.05);
        return new Promise(function (ok) { setTimeout(ok, framed ? 700 : 50); });
      }).then(function () {
        out.replay = !framed ? "not observed: no frames" : (playBtn.classList.contains("is-done") ? "replay" : "play");
        if (framed && (playing || !STATE.done || !playBtn.classList.contains("is-done"))) fail("play does not become replay at the end");
        pause();
        return go(END);
      });
    }).then(function () {
      // Hover at an interpolated playhead: nothing from Plotly, only actual points from us, each
      // under a heading that gives its date.
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
          var when = Array.prototype.map.call(tip.querySelectorAll(".china-tip-when"), function (d) { return d.textContent; });
          var first = tip.querySelector(".china-tip-row");
          out.hover.rows[pn[0]] = when.concat(rows);
          if (!rows.length) fail("no hover box in the " + pn[0] + " panel at the playhead");
          if (when.length !== 1 || !first || first.previousElementSibling.className !== "china-tip-when") fail("the date does not head the data in the hover box of the " + pn[0] + " panel");
          rows.forEach(function (t) {
            if (known.indexOf(t) < 0) fail("hover row is not an actual data point: " + t);
            if (t.indexOf(" bits (×") < 0 || t.indexOf(" compared to ") < 0) fail("hover row does not give the change compared to its anchor, in bits, with its multiple: " + t);
            if (/\(\d{4}\)|\((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) /.test(t)) fail("a hover row still carries its date: " + t);
          });
        });
        var h = probe(xa.p2l(xa.l2p(Tm) - 2), true, true);       // the points nearest the cursor's own date
        if (out.hover.rows.top.length !== 2 || out.hover.rows.top[0] !== G.when[h.gdp]) fail("the top panel should report the year, then the economy alone");
        if (out.hover.rows.bottom.length !== 3 || out.hover.rows.bottom[0] !== S.when[h.month]) fail("the bottom panel should report the month, then the stocks and the economy");
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
        var want2 = gd._fullData.map(function (d) { return "trace" + d.uid; });
        out.traceOrder = Array.prototype.map.call(gd.querySelectorAll(".scatterlayer"), function (layer) {
          return Array.prototype.map.call(layer.querySelectorAll(".trace"), function (t) {
            return want2.indexOf(Array.prototype.filter.call(t.classList, function (c) { return c.length > 5 && c.indexOf("trace") === 0; })[0]); });
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
      out.ghosts = Object.keys(ghostsSeen).length + " of " + EV.filter(function (e) { return !e.tick && e.on; }).length + " labelled events seen as ghosts";
      anchorsDrawn("the finished chart, after the play");
      // What the play adds up to, in seconds at 1x.
      var by = function (kind) { return TL.filter(function (s) { return s.kind === kind; }).map(function (s) { return +s.dur.toFixed(2); }); };
      out.play = {opening: by("open")[0], acts: ACTS.map(function (A) { return A.numeral + ": " + A.total.toFixed(2); }),
                  interlude: by("inter")[0], breaks: by("break"), ending: by("end")[0], pullBack: by("pull")[0], total: +END.toFixed(2),
                  totalAtDefault: +(END / M.play.speed).toFixed(2),
                  totalAtFastest: +(END / last(M.play.speeds)).toFixed(2)};
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
    G = series(TR.gdp); G.hover = M.hover.gdp; G.when = M.hover.year;
    // The stock line is two traces where its early stretch is back-tested; they share the point between them.
    var back = series(TR.stock_back), fore = series(TR.stock);
    S = {x: back.x.slice(0, -1).concat(fore.x), s: back.y.slice(0, -1).concat(fore.y), solid: Math.max(0, back.x.length - 1)};
    S.t = S.x.map(toMs); S.e = gd.data[TR.economy].y.slice();
    S.hoverS = M.hover.stock; S.hoverE = M.hover.economy; S.when = M.hover.month;
    PEERS = TR.peers.map(series);
    T0 = toMs(M.play.start); T1 = toMs(M.play.end); TA = toMs(M.anchor); TG = toMs(M.anchors[0].date);
    TB = M.backtest ? toMs(M.backtest.until) : -Infinity;
    X0 = toMs(M.view.x[0]); X1 = toMs(M.view.x[1]);
    // The acts, each with its own view, then the view of the finished chart; and the timeline they
    // make with the opening card, the breaks, the ending and the pull-back.
    ACTS = M.play.acts.map(function (a) {
      // The schedule: dates, and the seconds into the act at which the playhead reaches each; linear between.
      var t0 = toMs(a.start), x = [0], tau = [0];
      a.grid[0].forEach(function (d) { x.push(last(x) + d); });
      a.grid[1].forEach(function (d) { tau.push(last(tau) + d); });
      return {numeral: a.numeral, title: a.title, cardTitle: a.card_title, short: a.short, kicker: a.kicker, base: a.base,
              t0: t0, t1: toMs(a.end), t: x.map(function (v) { return t0 + v * YEAR; }), tau: tau, total: last(tau),
              c0: 0, b0: 0, i0: 0};
    });
    VIEWS = M.play.acts.map(function (a) { return {r0: toMs(a.range[0]), r1: toMs(a.range[1])}; }).concat([{r0: X0, r1: X1}]);
    var tr = M.play.transition, en = M.play.ending, fade = M.play.card_fade, open = tr.card_in + tr.hold + tr.ghost + tr.card_out, c = open;
    TL = [{kind: "open", act: 0, c0: 0, dur: open}];
    var IL = M.play.interlude, interDur = IL.arrow_seconds + IL.pause + 2 * fade + IL.seconds;
    ACTS.forEach(function (A, k) {
      A.c0 = c; TL.push({kind: "play", act: k, c0: c, dur: A.total}); c += A.total;
      // At the end of one act, before its break, the playhead rests: an arrow up the economy's line, then its box.
      if (k === IL.act) { A.i0 = c; TL.push({kind: "inter", act: k, c0: c, dur: interDur}); c += interDur; }
      if (k === ACTS.length - 1) return;
      A.b0 = c; TL.push({kind: "break", act: k, c0: c, dur: open + tr.move}); c += open + tr.move;
    });
    // As the data ends the view pulls back to the whole chart; the ending follows there, as moments
    // from its start: in the top panel each era's chord and its rate, a short beat after each; the
    // arrow up from the 1978 level and its label, a pause; then each of the bottom panel's chords and
    // its rate, a pause after each; the gap's arrow and its label; the last box coming up, and going.
    var eraStep = en.chord + en.label + en.pause / 2, step = en.chord + en.label + en.pause;
    var marks = {era: M.era_chords.map(function (_, n) { return n * eraStep; }),
                 eraRate: M.era_chords.map(function (_, n) { return n * eraStep + en.chord; })};
    marks.climb = M.era_chords.length * eraStep;
    marks.climbLabel = marks.climb + en.arrow;
    var b0 = marks.climbLabel + en.label + en.pause;
    marks.chord = [b0, b0 + step]; marks.rate = [b0 + en.chord, b0 + step + en.chord];
    marks.arrow = b0 + 2 * step;
    marks.gap = marks.arrow + en.arrow;
    marks.box = marks.gap + en.label + en.pause / 2;
    marks.boxOut = marks.box + fade + M.play.final.seconds;
    TL.push({kind: "pull", act: ACTS.length - 1, c0: c, dur: en.pullback}); c += en.pullback;
    TL.push({kind: "end", act: ACTS.length - 1, c0: c, dur: marks.boxOut + fade + 0.15, marks: marks});
    END = c + marks.boxOut + fade + 0.15;
    EV = M.events.map(function (e) {
      var t = toMs(e.date);
      return {t: t, tier: e.tier, tick: e.tier === "tick", panel: e.panel, label: e.label,
              text: e.text, short: e.short, say: e.text, lead: e.lead, description: e.description, notes: notes(e.notes),
              shape: e.shape, stalk: e.stalk, annotation: e.annotation, on: true, labelled: e.annotation !== null, row: 0, spot: 0.5,
              ext: [0, 0], stem: 0, lift: 3, act: ownAct(t), fits: [], clock: clockOf(t), ghost: false};
    });
    ERAS = M.eras.map(function (e) {
      return {t0: toMs(e.start), t1: toMs(e.end), label: e.label, description: e.description, drop_first: e.drop_first,
              notes: notes(e.notes), bar: e.bar, tip: e.tip, annotation: e.annotation, on: true, labelled: true,
              live: false, text: false, cut: false, a: 0, b: 0, w: 0, fits: []};
    });
    LEADERS = M.leaders.map(function (l) {
      return {t0: toMs(l.start), t1: l.end ? toMs(l.end) : Infinity, label: l.label, description: l.description,
              tint: l.tint, shape: l.shape, tip: l.tip, annotation: l.annotation, labelled: true, live: false,
              text: false, cut: false, a: 0, b: 0, w: 0, at: 5, inset: [], from: []};
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
              text: ch.text, shape: ch.shape, annotation: ch.annotation};
    });
    ERACHORDS = M.era_chords.map(function (ec) {
      return {key: ec.key, name: ec.name, span: ec.span, color: ec.color, rate: ec.rate, t0: toMs(ec.start), t1: toMs(ec.end),
              y0: ec.y0, y1: ec.y1, wraps: ec.wraps, text: ec.text, hover: ec.hover, shape: ec.shape, annotation: ec.annotation,
              place: null};
    });
    CLIMB = {value: M.climb.value, t: toMs(M.climb.date), text: M.climb.text, wraps: M.climb.wraps, arrow: M.climb.arrow,
             label: M.climb.label, place: null};
    GAP = {value: M.gap.value, text: M.gap.text, wraps: M.gap.wraps, top: M.gap.top, bottom: M.gap.bottom, arrow: M.gap.arrow, label: M.gap.label};
    ANCHORS = M.anchors.map(function (a) { return {trace: a.trace, panel: a.panel, date: a.date, t: toMs(a.date), text: a.text, shown: true}; });
    // A beat's box is up between two moments of the clock: those at which the playhead is at its two dates.
    BEATS = M.play.beats.map(function (b, n) {
      var since = toMs(b.since), until = toMs(b.until);
      return {id: "beat" + n, t: toMs(b.date), act: b.act, kind: b.kind, panel: b.panel, lead: b.lead, text: b.text,
              picture: b.picture, share: b.share, event: b.event, rate: b.rate, reference: b.reference, cross: !!b.cross,
              seconds: b.seconds, since: since, until: until, last: false,
              c0: ACTS[b.act].c0 + tauOf(b.act, since), c1: ACTS[b.act].c0 + tauOf(b.act, until), box: null};
    });
    // The interlude's box: after its arrow, while the playhead rests at the end of its act.
    var IA = ACTS[IL.act], ic0 = IA.i0 + IL.arrow_seconds + IL.pause;
    INTER = {id: "inter", t: IA.t1, act: IL.act, kind: "text", panel: "economy", lead: IL.lead, text: IL.text,
             picture: null, event: null, rate: null, reference: null, overlay: "inter", seconds: IL.seconds,
             since: IA.t1, until: IA.t1,
             last: false, c0: ic0, c1: ic0 + fade + IL.seconds, box: null};
    BEATS.push(INTER);
    // The last box, which closes the ending.
    // (It comes up in the whole chart's view, where the ending now happens.)
    FINAL = {id: "last", t: T1, act: ACTS.length - 1, view: VIEWS.length - 1, kind: "text", panel: M.play.final.panel, lead: M.play.final.lead,
             text: M.play.final.text, picture: null, event: null, rate: null, reference: null, since: T1, until: T1,
             last: true, box: null};
    // The annotations that are beats: each slows playback, between two moments, as its point is reached.
    NOTES = M.play.notes.map(function (n) {
      var a = ARROWS.filter(function (x) { return x.role === n.role; })[0], since = toMs(n.since), until = toMs(n.until);
      return {role: n.role, act: n.act, t: a.t, y: a.y, since: since, until: until,
              c0: ACTS[n.act].c0 + tauOf(n.act, since), c1: ACTS[n.act].c0 + tauOf(n.act, until)};
    });
    // The key: a row for the bottom panel's zero line, a numbered row for each arrowed annotation,
    // a row for each closing rate and one for the gap. A row shows only if the plot has no room
    // for what it says.
    function keyRow(sign, text, t, kind, part) {
      var row = document.createElement("div");
      row.className = "china-key-row"; row.setAttribute("data-t", t);
      if (kind) row.setAttribute("data-" + kind, part === undefined ? "" : part);
      row.appendChild(sign);
      row.appendChild(document.createTextNode(text));
      keyBox.appendChild(row);
    }
    function swatch(cls, color) {
      var el = document.createElement("span");
      el.className = cls;
      if (color) el.style.borderTopColor = color;
      return el;
    }
    keyRow(swatch("china-key-line"), M.key.zero, TA, "zero");
    ARROWS.forEach(function (a, n) {
      var num = document.createElement("span");
      num.className = "china-key-n"; num.textContent = n + 1;
      keyRow(num, a.key + ".", a.t, null);
    });
    ERACHORDS.forEach(function (ec, n) { keyRow(swatch("china-key-line china-key-dash", ec.color), ec.text + ".", T1, "era", n); });
    keyRow(swatch("china-key-line china-key-gap"), CLIMB.text + ".", T1, "end", "climb");
    CHORDS.forEach(function (ch, n) { keyRow(swatch("china-key-line china-key-dash", ch.color), ch.text + ".", T1, "end", n); });
    keyRow(swatch("china-key-line china-key-gap"), GAP.text + ".", T1, "end", "gap");
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
    setSpeed(M.play.speed);
    // The page opens on the finished chart.
    clock = want = END; playhead = T1; STATE = stateAt(END);

    playBtn.addEventListener("click", function () { if (playing) pause(); else play(); });
    speedBtn.addEventListener("click", function () {
      setSpeed(M.play.speeds[(M.play.speeds.indexOf(speed) + 1) % M.play.speeds.length]);
    });
    // The scrubber's position is a date. It shows that date as its own act plays it: never a break.
    scrub.addEventListener("input", function () { pause(); dismissed = {}; render(clockAt(T0 + scrub.value / scrub.max * (T1 - T0))); });
    beatCard.addEventListener("click", dismiss);
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
      show: function (c) { pause(); busy = false; pending = null; dismissed = {}; render(c); return STATE; },
      state: function () { return STATE; }, clockAt: clockAt, timeline: TL, acts: ACTS, views: VIEWS, beats: BEATS,
      last: FINAL, inter: INTER, notes: NOTES, end: END, eras: ERACHORDS, climb: CLIMB, hovered: function () { return hovered.slice(); },
      // How many characters of text a picture card can hold and keep its picture at this width (its lead as it is):
      // the card's own words, repeated as needed, cut at a word.
      pictureRoom: function (i) {
        var b = BEATS[i], keep = b.text, words = (keep + " ").repeat(8).split(" ").filter(Boolean);
        function cut(n) { var out = ""; for (var k = 0; k < words.length && (out + " " + words[k]).trim().length <= n; k++) out = (out + " " + words[k]).trim(); return out; }
        function fits(n) { b.text = cut(n); beatCard._beat = null; var q = placeBox(b, GEO.plotW, null, true); return !!(q && q.how && q.how.img); }
        beatCard.style.visibility = "hidden"; beatCard.style.display = "block";
        var lo = 0, hi = 600;
        while (hi - lo > 2) { var mid = (lo + hi) >> 1; if (fits(mid)) lo = mid; else hi = mid; }
        var text = cut(lo);
        b.text = keep; beatCard._beat = null; beatCard.style.display = "none"; beatCard.style.visibility = "";
        return {lead: b.lead, chars: b.lead.length + 1 + text.length, words: (b.lead + " " + text).split(/\s+/).length, text: text};
      },
      // Show a beat with other words (to see a rewrite in place): every box is placed again.
      retext: function (i, text) { BEATS[i].text = text; sizes = {}; fit(true); return BEATS[i].box; }};
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
    scroll-zoom off so the page still scrolls), and in front of it the title,
    each panel's name, the scrim and the title card for an act break, the box
    for a beat's narration, the year pill and the hover overlay, the key used when direct labels
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
    markup = (_MARKUP.replace("__TITLE__", TITLE).replace("__HEAD_TOP__", COPY_TEXT["panel_economy"])
              .replace("__HEAD_BOTTOM__", COPY_TEXT["panel_stocks"]).replace("__FIG__", fig_html))
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
    words = [w.strip(",.:;()“”\"") for w in label.replace("<br>", " ").split()]
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


# --------------------------------------------------------------------------- #
#  The copy: every string a reader sees, for a rewrite
# --------------------------------------------------------------------------- #
COPY_PATH = _HERE / "china_figure_copy.xlsx"
TARGET_SECONDS = 240.0           # the running time at 1x that the word budgets aim at (about 4:00; 2:40 at 1.5x)
# The kinds of string, in the order rows of one date are listed.
COPY_KINDS = ("title card", "scrubber label", "text box", "picture card", "picture credit (card)", "arrow label",
              "arrow hover", "labelled event (label)", "labelled event (hover)", "note", "tick hover",
              "era band (label)", "era band (hover)", "leader (label)", "leader (hover)", "annotation", "fill label",
              "zero-line label", "panel label", "access band", "figure title", "series hover template", "rate label",
              "rate hover", "gap label", "final card")
# Word budgets set by hand, by row id: they take the place of the computed suggestion.
COPY_BUDGETS = {"card-2020-11-03": 14}
# The placeholders each composed string may use, by its key in COPY_TEXT.
_COPY_TEXT_FIELDS = dict(
    panel_economy=(), panel_stocks=(), kicker=("numeral", "start_year", "end_year"),
    hover_economy_1978=("anchor_year", "change"), hover_stocks=("since", "change"), hover_economy=("since", "change"),
    anchor=("anchor",), zero_key=("since",), chord_rate=("rate", "multiple"),
    era_rate=("name", "span", "rate", "multiple"), era_rate_flat=("name", "span", "rate"),
    climb=("bits", "anchor_year", "multiple"), chord_economy=(), chord_stocks=(), gap=("gap_bits", "gap_multiple"))
_COPY_TEXT_KINDS = dict(
    panel_economy="panel label", panel_stocks="panel label", kicker="title card",
    hover_economy_1978="series hover template", hover_stocks="series hover template",
    hover_economy="series hover template", anchor="series hover template", zero_key="zero-line label",
    chord_rate="rate label", era_rate="rate label", era_rate_flat="rate label", climb="arrow label",
    chord_economy="rate label", chord_stocks="rate label", gap="gap label")


def running_time(plan: list[dict], words: dict) -> float:
    """The whole play at 1x, in seconds: the opening card, the parts, the stop at the end of Part II, the
    breaks, the pull-back and the ending (the eras' chords, the climb, the bottom panel's chords, the gap,
    the last box)."""
    opening = sum(TRANSITION[k] for k in ("card_in", "hold", "ghost", "card_out"))
    breaks = (len(ACTS) - 1) * (opening + TRANSITION["move"])
    E = ENDING
    ending = (len(ERA_CHORDS) * (E["chord"] + E["label"] + E["pause"] / 2) + E["arrow"] + E["label"] + E["pause"]
              + 2 * (E["chord"] + E["label"] + E["pause"]) + E["arrow"] + E["label"] + E["pause"] / 2
              + 2 * CARD_FADE_SECONDS + final_seconds(words) + 0.15)
    return (opening + sum(float(part["table"]["tau"][-1]) for part in plan) + interlude_seconds(words) + breaks
            + ending + E["pullback"])


def _placeholders(text: str) -> list[str]:
    """The {names} in a template, in order, each once."""
    import string
    return list(dict.fromkeys(f for _, f, _, _ in string.Formatter().parse(text) if f))


def copy_rows() -> list[dict]:
    """Every string the figure shows a reader, one row each: what china_figure_copy.xlsx lists.

    Each row: ``id`` (stable: built from dates and keys, never from the words),
    ``part`` (I, II, III or "—"), ``date``, ``kind`` (one of ``COPY_KINDS``),
    ``panel``, ``text`` as rendered but with every computed value as a named
    ``{placeholder}``, ``values`` (each placeholder's current value or values),
    ``words``, ``budget`` (for a box: the words it might run to for the play to
    last about ``TARGET_SECONDS`` at 1x, each box cut in proportion; for a
    picture card, no more than its picture leaves room for), and what
    apply_copy.py needs: ``path`` (where the literal is in this module's source:
    a top-level name, then list indices, dict keys and dataclass fields; a
    tuple of fields at the end means the row joins them, as a box's bold lead
    and its text are joined), ``paths`` (for one string kept in several places),
    ``allowed`` (the placeholders it may use), ``room`` and ``picture``.
    """
    plan, marks, words, numbers = default_plan()
    fig = build_china_figure()
    meta = fig.layout.meta
    ends = [pd.Timestamp(part["end"]) for part in plan]
    part_of = lambda when: "—" if when is None else next(
        (a.numeral for a, end in zip(ACTS, ends) if pd.Timestamp(when) <= end), ACTS[-1].numeral)
    narration = tuple(words)                        # what a box's or an event's text may use
    rows = []

    def add(id_, kind, text, path, date=None, panel="—", values=None, allowed=(), budget=None, picture=None,
            room=None, paths=None):
        assert kind in COPY_KINDS, kind
        shown = text.replace("**", "").replace("<br>", " ")
        rows.append(dict(id=id_, part=part_of(date), date=_iso(date) if date is not None else "", kind=kind,
                         panel=panel, text=text, values=values or {}, words=len(shown.split()), budget=budget,
                         path=path, paths=paths or [path], allowed=tuple(allowed), picture=picture, room=room))

    def values_of(text, source):
        return {p: source[p] for p in _placeholders(text) if p in source}

    # The figure's title, the panels' names, and the strings composed with numbers (COPY_TEXT).
    add("figure-title", "figure title", TITLE, ("TITLE",))
    instances = dict(
        kicker=[dict(numeral=a["numeral"], start_year=a["start"][:4], end_year=a["end"][:4]) for a in meta["play"]["acts"]],
        hover_economy_1978=[dict(anchor_year=GDP_ANCHOR_YEAR, change="+2.31 bits (×4.96), for example")],
        hover_stocks=[dict(since=words["since"], change="−0.57 bits (×0.67), for example")],
        hover_economy=[dict(since=words["since"], change="+2.23 bits (×4.69), for example")],
        anchor=[dict(anchor=GDP_ANCHOR_YEAR), dict(anchor=words["since"])],
        zero_key=[dict(since=words["since"])],
        chord_rate=[dict(zip(("rate", "multiple"), re.findall(r"[+−][\d.]+|(?<=×)[\d.]+", c["said"])))
                    for c in meta["chords"]],
        era_rate=[dict(name=c["name"], span=c["span"], rate=f"{'+' if c['rate'] >= 0 else '−'}{abs(c['rate']):.3f}",
                       multiple=f"{2.0 ** c['rate']:.3f}") for c in meta["era_chords"] if "(×" in c["said"]],
        era_rate_flat=[dict(name=c["name"], span=c["span"], rate=f"{'+' if c['rate'] >= 0 else '−'}{abs(c['rate']):.3f}")
                       for c in meta["era_chords"] if "(×" not in c["said"]],
        climb=[dict(bits=re.match(r"[+−][\d.]+", meta["climb"]["text"]).group(), anchor_year=GDP_ANCHOR_YEAR,
                    multiple=re.search(r"×([\d.]+)", meta["climb"]["text"]).group(1))],
        gap=[dict(zip(("gap_bits", "gap_multiple"), re.findall(r"[\d.]+", meta["gap"]["text"])))])
    for key, text in COPY_TEXT.items():
        seen = instances.get(key, [])
        values = {p: ", ".join(dict.fromkeys(str(v[p]) for v in seen if p in v)) for p in _COPY_TEXT_FIELDS[key]}
        panel = "economy" if key in ("panel_economy", "hover_economy_1978", "era_rate", "era_rate_flat", "climb") else (
            "stocks" if key in ("panel_stocks", "hover_stocks", "hover_economy", "zero_key", "chord_economy",
                                "chord_stocks", "gap") else "—")
        add(f"copy-{key.replace('_', '-')}", _COPY_TEXT_KINDS[key], text, ("COPY_TEXT", key), panel=panel,
            values=values, allowed=_COPY_TEXT_FIELDS[key])

    # The parts: each title (its card and the scrubber), and the short form the scrubber falls back on.
    for i, (act, part) in enumerate(zip(ACTS, meta["play"]["acts"])):
        add(f"part-{act.numeral}-title", "title card", PART_TITLES[i], ("PART_TITLES", i), date=part["start"])
        add(f"part-{act.numeral}-short", "scrubber label", act.short, ("ACTS", i, "short"), date=part["start"])

    # The boxes, the stop at the end of Part II and the last box: each with its bold lead.
    total = running_time(plan, words)
    cards = [(b, beat_date(b, numbers["trough"])) for b in BEATS]
    stop, cutoff = pd.Timestamp(ACTS[_INTERLUDE_ACT].end), pd.Timestamp(meta["play"]["end"])
    everything = cards + [(INTERLUDE_BOX, stop), (FINAL_BOX, cutoff)]
    count = lambda b: len(f"{b.lead} {b.text}".format(**words).split())
    reading = sum(box_seconds(b, words) for b, _ in everything)
    base = sum(box_seconds(b, words) - BOX_SECONDS[1] * count(b) for b, _ in everything)
    scale = max(0.2, (reading - (total - TARGET_SECONDS) - base) / (BOX_SECONDS[1] * sum(count(b) for b, _ in everything)))
    # (A budget counts words as "new words" does: as typed, each {placeholder} one word; never more than there are now.)
    typed = lambda b: len(f"{b.lead} {b.text}".split())
    budget_of = lambda b: min(typed(b), max(6, int(typed(b) * scale)))
    for i, (b, when) in enumerate(cards):
        text = f"**{b.lead}** {b.text}"
        pic = PICTURES[b.picture] if b.picture else None
        budget = budget_of(b)
        if pic is not None and pic.room:
            said = f"{b.lead} {b.text}".format(**words)      # (as many of its words as fit in the room, cut at a word)
            budget = min(budget, len(said[:pic.room + 1].rsplit(" ", 1)[0].split()) - (count(b) - typed(b)))
        id_ = "card-after-trough" if b.after else f"card-{b.date}"
        budget = COPY_BUDGETS.get(id_, budget)
        act = ACTS[int(["I", "II", "III"].index(part_of(when)))]
        add(id_, "picture card" if has_picture(b) else "text box", text, ("BEATS", i, ("lead", "text")), date=when,
            panel=b.panel or act.panel, values=values_of(text, words), allowed=narration, budget=budget,
            picture=b.picture if has_picture(b) else None, room=pic.room if pic and has_picture(b) else None)
        if b.picture and has_picture(b):
            add(f"credit-{b.picture.replace('_', '-')}", "picture credit (card)", pic.short,
                ("PICTURES", b.picture, "short"), date=when, panel=b.panel or act.panel)
        if b.rate_note:
            add(f"arrow-note-{b.date}", "arrow hover", b.rate_note, ("BEATS", i, "rate_note"), date=when, panel="economy")
    for box, when, id_, kind in ((INTERLUDE_BOX, stop, "card-interlude", "text box"),
                                 (FINAL_BOX, cutoff, "card-final", "final card")):
        text = f"**{box.lead}** {box.text}"
        add(id_, kind, text, (id_ == "card-final" and "FINAL_BOX" or "INTERLUDE_BOX", ("lead", "text")), date=when,
            panel="economy" if box is INTERLUDE_BOX else "stocks", values=values_of(text, words), allowed=narration,
            budget=budget_of(box))
    # (The fall of each market to the bottom, which the box after the trough quotes as {trough_falls}.)
    wto = next(when for b, when in cards if b.after)
    add("copy-trough-falls", "text box", _TROUGH_FALLS, ("_TROUGH_FALLS",), date=wto, panel="stocks",
        values={"trough_china": f"{numbers['trough_china']:.0f}", "trough_usa": f"{numbers['trough_usa']:.0f}",
                "since": words["since"]}, allowed=("trough_china", "trough_usa", "since"))

    # The ending's top panel: each era's name (its chord's label leads with it) and its hover text.
    gdp_, _ = load_derived()
    usa_, _ = load_narration_data()
    for i, (era, num) in enumerate(zip(ERA_CHORDS, era_numbers(gdp_, usa_))):
        add(f"era-chord-{era.start}-name", "rate label", era.name, ("ERA_CHORDS", i, "name"), date=cutoff,
            panel="economy")
        add(f"era-chord-{era.start}-hover", "rate hover", era.hover, ("ERA_CHORDS", i, "hover"), date=cutoff,
            panel="economy", values=dict(span=num["span"], china=f"{num['china']:.1f}", usa=f"{num['usa']:.1f}"),
            allowed=("span", "china", "usa"))

    # The rate arrows: their labels and hover text (templates, one for every arrow).
    specs = [(b, s) for b in meta["play"]["beats"] for s in (b["rate"], b["reference"]) if s]
    add("template-rate-label", "arrow label", RATE_LABEL, ("RATE_LABEL",), panel="economy",
        values={"rate": ", ".join(f"{re.sub(' bits/yr', '', s['text'])} ({s['lead']})" for b, s in specs if not s["reference"])},
        allowed=("rate",))
    add("template-reference-label", "arrow label", REFERENCE_LABEL, ("REFERENCE_LABEL",), panel="economy",
        values={"rate": ", ".join(f"{s['text'][1:].split(' ')[0]} ({s['lead']})" for b, s in specs if s["reference"])},
        allowed=("rate",))
    add("template-rate-hover", "arrow hover", RATE_HOVER, ("RATE_HOVER",), panel="economy",
        values={"lead": ", ".join(dict.fromkeys(s["lead"] for _, s in specs)),
                "verb": "rose or fell", "change": ", ".join(dict.fromkeys(f"{abs(s['change']):.2f}" for _, s in specs))},
        allowed=("lead", "verb", "change"))

    # The events: labels (and short forms, and group names), hover text, notes.
    first = pd.Timestamp(year=START_YEAR, month=1, day=1)
    groups = {}
    for i, ev in enumerate(EVENTS):
        if ev.tier == "stored" or not first <= pd.Timestamp(ev.date) <= cutoff:
            continue
        key = f"event-{ev.panel}-{ev.date}"
        if ev.tier == "label":
            add(f"{key}-label", "labelled event (label)", ev.label, ("EVENTS", i, "label"), date=ev.date, panel=ev.panel)
            if ev.short:
                add(f"{key}-short", "labelled event (label)", ev.short, ("EVENTS", i, "short"), date=ev.date, panel=ev.panel)
            if ev.group:
                groups.setdefault(ev.group, []).append((i, ev))
        add(f"{key}-hover", "labelled event (hover)" if ev.tier == "label" else "tick hover", ev.description,
            ("EVENTS", i, "description"), date=ev.date, panel=ev.panel, values=values_of(ev.description, words),
            allowed=narration)
        for j, n in enumerate(ev.notes):
            add(f"note-{ev.panel}-{ev.date}-{n.date}", "note", f"**{n.when}**: {n.text}", ("EVENTS", i, "notes", j, ("when", "text")),
                date=n.date, panel=ev.panel)
    for name, members in groups.items():
        add(f"event-group-{name}", "labelled event (label)", name, ("EVENTS", members[0][0], "group"),
            date=members[0][1].date, panel=members[0][1].panel, paths=[("EVENTS", i, "group") for i, _ in members])

    # Eras and leaders, in the strip above the top panel.
    for i, era in enumerate(ERAS):
        add(f"era-{era.start}-label", "era band (label)", era.label, ("ERAS", i, "label"), date=era.start, panel="economy")
        add(f"era-{era.start}-hover", "era band (hover)", era.description, ("ERAS", i, "description"), date=era.start,
            panel="economy")
        for j, n in enumerate(era.notes):
            add(f"note-era-{era.start}-{n.date}", "note", f"**{n.when}**: {n.text}", ("ERAS", i, "notes", j, ("when", "text")),
                date=n.date, panel="economy")
    for i, who in enumerate(LEADERS):
        when = max(pd.Timestamp(who.start), first)
        add(f"leader-{who.start}-label", "leader (label)", who.label, ("LEADERS", i, "label"), date=when, panel="economy")
        add(f"leader-{who.start}-hover", "leader (hover)", who.description, ("LEADERS", i, "description"), date=when,
            panel="economy")

    # The access bands, the annotations, the labels by the fills and the zero lines.
    for i, band in enumerate(BANDS):
        when = pd.Timestamp(band.start) if band.start else first
        for k, wrap in enumerate(band.wraps):
            add(f"band-{band.kind}-wrap-{k}", "access band", wrap, ("BANDS", i, "wraps", k), date=when, panel="stocks")
        add(f"band-{band.kind}-hover", "access band", band.description, ("BANDS", i, "description"), date=when, panel="stocks")
        if band.early_description:
            add(f"band-{band.kind}-early-hover", "access band", band.early_description, ("BANDS", i, "early_description"),
                date=when, panel="stocks")
    arrow_values = dict(trough=meta["arrows"][0]["month"], peak=meta["arrows"][1]["month"], anchor=words["since"],
                        trough_x=re.search(r"×([\d.]+)", meta["arrows"][0]["text"]).group(1),
                        peak_x=re.search(r"×([\d.]+)", meta["arrows"][1]["text"]).group(1))
    for a in meta["arrows"]:
        for k, wrap in enumerate(_ARROWS[a["role"]]["wraps"]):
            add(f"annotation-{a['role'].replace('_', '-')}-wrap-{k}", "annotation", wrap, ("_ARROWS", a["role"], "wraps", k),
                date=pd.Timestamp(a["date"]), panel="stocks", values=values_of(wrap, arrow_values),
                allowed=("trough", "trough_x", "peak", "peak_x", "anchor"))
    for role, spec in _FILL_LABELS.items():
        for k, wrap in enumerate(spec["wraps"]):
            add(f"fill-{role.replace('_', '-')}-wrap-{k}", "fill label", wrap, ("_FILL_LABELS", role, "wraps", k),
                date=spec["start"], panel="stocks")
    for key, text in _HINTS.items():
        add(f"zero-{key.replace('_', '-')}", "zero-line label", text, ("_HINTS", key),
            panel="stocks" if key.startswith("zero") else "economy", values=values_of(text, {"anchor_year": GDP_ANCHOR_YEAR}),
            allowed=("anchor_year",) if "{" in text else ())

    order = {k: n for n, k in enumerate(COPY_KINDS)}
    rows.sort(key=lambda r: (r["date"] == "", r["date"], order[r["kind"]], r["id"]))
    assert len({r["id"] for r in rows}) == len(rows), "two strings share an id"
    return rows


def export_copy(path: str | Path | None = None, force: bool = False) -> Path:
    """Write the copy (:func:`copy_rows`) to a workbook for a rewrite: ``china_figure_copy.xlsx`` by default.

    One sheet of strings, one row each (``new text`` blank, its word count a
    formula), and a sheet of rules. A workbook that already holds new text is
    left alone unless ``force``: a rewrite in progress is never overwritten.
    apply_copy.py reads the new text back into this module.
    """
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    path = Path(COPY_PATH if path is None else path)
    if path.exists() and not force:
        sheet = load_workbook(path)["Copy"]
        head = [c.value for c in sheet[1]]
        at = head.index("new text") + 1
        if any(str(sheet.cell(r, at).value or "").strip() for r in range(2, sheet.max_row + 1)):
            raise FileExistsError(f"{path.name} already holds new text: not overwritten (force=True to replace it)")
    rows = copy_rows()
    book = Workbook()
    sheet = book.active
    sheet.title = "Copy"
    head = ["id", "part", "date", "kind", "panel", "current text", "computed values", "new text", "current words",
            "new words", "word budget", "notes"]
    widths = [30, 6, 11, 20, 9, 70, 40, 70, 9, 9, 9, 30]
    sheet.append(head)
    for r in rows:
        sheet.append([r["id"], r["part"], r["date"], r["kind"], r["panel"], r["text"],
                      "\n".join(f"{k} = {v}" for k, v in r["values"].items()), None, r["words"], None, r["budget"], None])
        n = sheet.max_row
        sheet.cell(n, 10).value = f'=IF(LEN(TRIM(H{n}))=0,0,LEN(TRIM(H{n}))-LEN(SUBSTITUTE(TRIM(H{n})," ",""))+1)'
    bold, shade = Font(bold=True), PatternFill("solid", fgColor="EEF1F6")
    for col, (name, width) in enumerate(zip(head, widths), start=1):
        sheet.column_dimensions[sheet.cell(1, col).column_letter].width = width
        sheet.cell(1, col).font = bold
        sheet.cell(1, col).fill = shade
    for line in sheet.iter_rows(min_row=1):
        for cell in line:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"

    rules = book.create_sheet("Rules")
    rules.column_dimensions["A"].width = 110
    for line in COPY_RULES.format(target=f"{TARGET_SECONDS / 60:.0f}:{TARGET_SECONDS % 60:02.0f}",
                                  at_default=f"{TARGET_SECONDS / DEFAULT_SPEED / 60:.0f}:{TARGET_SECONDS / DEFAULT_SPEED % 60:02.0f}",
                                  default=DEFAULT_SPEED).split("\n"):
        rules.append([line])
        rules.cell(rules.max_row, 1).alignment = Alignment(wrap_text=True, vertical="top")
        if line and not line.startswith(" ") and line.endswith(":"):
            rules.cell(rules.max_row, 1).font = bold
    book.save(path)
    return path


COPY_RULES = """How to rewrite the figure's words:
Write the new words in "new text". A blank "new text" means: keep the current text. Then run apply_copy.py, which puts the new text into china_figure.py (the code stays the one source of every word) and refuses, changing nothing, if a row is wrong.

Placeholders:
{{name}} stands for a number or a word the figure computes from the data. Keep the {{…}} token, anywhere in the sentence, to keep that number computed; "computed values" shows what each stands for now. Use only the placeholders the row already has (some rows may use others: a box or an event's hover text may use any of the narration's; ask if unsure). Write no other braces.
Some placeholders stand for computed words rather than numbers, e.g. {{catch_up_claim}}, {{trough_lag}}, {{xi_change}}: the data choose them.

Typed versus computed facts:
A number that comes from the data (a % change, a rate in bits, a month the data pick out) is always a placeholder, never typed. History the data cannot know (7,000 officials, Deng's age, $40 billion, dates of events) is typed, and is yours to check.

Formatting:
**…** makes bold. A box's text begins with its bold lead: "**1962–65** Liu and Deng …". A note begins with its bold date and a colon: "**Sep 1988**: Friedman …". Keep that shape.
<br> is a line break. Rows whose id ends -wrap-0, -wrap-1, … are the same label broken over lines in different ways; the figure uses the first that fits. Keep their words the same.
Rows whose id starts template- or copy- are used many times (every rate arrow, every hover row); "computed values" lists the uses.
event-group-… is the name that two events share in one label ("2018: …").
House style: American spelling; American dates ("May 16, 1966"; "Dec 1990" in short labels); sentence case for labels; every hover text opens with a bold date and a colon.

Word budgets:
"word budget" (boxes and cards only) is a suggestion: each box's words cut in proportion so that the play lasts about {target} at 1x ({at_default} at the default {default}x), given the reading time of each box (so much a box, plus so much a word). A picture card's budget is also no more than its picture leaves room for at the full 920 px column. A budget set by hand (COPY_BUDGETS in china_figure.py) takes the place of the suggestion: the Jack Ma card's is 14 words, the most that leave its photo room. "new words" counts your words.

Picture cards:
apply_copy.py refuses a picture card's text that would no longer leave its picture room at 920 px (the room, in characters, was measured in the page). The Jack Ma card (2020–21) has room for about 100 characters, its lead included, with its photo at 150 px.
"""

# British spellings that must not reach a reader (house style: American). Words, word endings and
# word stems; checked against every string the page shows.
_BRITISH = re.compile(
    r"\b(?:\w*(?:colo|favo|behavio|labo|hono|harbo|humo|neighbo|rumo|vapo|vigo|savo|endeavo|flavo|armo|parlo|odo|"
    r"valo|tumo|ardo|cando|clamo|glamo|rigo|splendo)urs?(?:ed|ing|ite|ites|able)?|programmes?|\w*(?:cen|thea|met|"
    r"lit|fib|spec|calib|sab)tres?|(?:defen|offen|licen|preten)ces?|(?:travel|cancel|model|label|level|signal|total|"
    r"fuel|channel|counsel|marshal|equal|quarrel|tunnel|funnel)l(?:ed|ing)|grey|tyres?|cheques?|aluminium|moulds?|"
    r"ploughs?|sceptic\w*|whilst|judgement|ageing|manoeuvr\w*|per cent|catalogue|analys(?:e|ed|es|ing)|"
    r"paralys(?:e|ed|es|ing))\b", re.I)
# Words in -ise/-ised/-ising/-isation that are American too (anything else in that form is British).
_ISE_OK = {"rise", "rises", "rising", "otherwise", "malaise", "promise", "promised", "promises", "premise", "premises", "exercise",
           "exercised", "advertise", "advertised", "advertising", "surprise", "surprised", "surprising", "compromise",
           "compromised", "expertise", "enterprise", "enterprises", "franchise", "merchandise", "concise", "precise",
           "wise", "raise", "raised", "raises", "raising", "praise", "praised", "noise", "poise", "cruise", "arise",
           "arises", "arising", "paradise", "treatise", "comprise", "comprised", "comprises", "demise", "devise",
           "devised", "revise", "revised", "supervise", "supervised", "televised", "disguise", "disguised", "guise",
           "apprise", "chastise", "excise", "incise", "despise", "improvise", "improvised", "bruise", "anise", "mise",
           "reprise", "sunrise", "uprise", "uprising", "uprisings", "upraise"}


def _british_spellings(text: str) -> list[str]:
    """The British spellings in a piece of text that a reader would see."""
    found = [m.group(0) for m in _BRITISH.finditer(text)]
    found += [w for w in re.findall(r"\b[A-Za-z]+(?:is|ys)(?:e|ed|es|ing|ation|ations)\b", text)
              if w.lower() not in _ISE_OK and len(w) > 4]
    return found


def _run_checks() -> None:
    def close(a, b, tol=1e-12, msg=""):
        assert abs(a - b) <= tol, f"{msg}: {a} != {b} (tol {tol})"

    def build(**kw):
        """Build the figure, which must not warn: every picture and every number is there."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            built = build_china_figure(**kw)
        others = [str(w.message) for w in caught]
        assert not others, f"the build warned: {others}"
        return built

    gdp, s_file = load_derived()
    g = rebased(gdp, "CHN")
    s_all = stock_since(s_file)
    cutoff = common_cutoff(g, s_all)
    s = s_all[:cutoff]
    e = economy_since_anchor(g, s.index)
    since = _month(STOCK_ANCHOR)                     # how the anchor is named wherever text names it
    usa, returns = load_narration_data()
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)  # every number is there
        words, numbers = narration_numbers(gdp, usa, s, e, STOCK_ANCHOR, cutoff, returns)
    assert anchor_month_end(s_file) == STOCK_ANCHOR == s.index[0], "STOCK_ANCHOR should be a month-end in the derived file"
    fig = build()
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
    arrow_words = dict(trough=_month(trough), trough_x=f"{2 ** s[trough]:.2f}", peak=_month(peak),
                       peak_x=f"{2 ** s[peak]:.1f}", anchor=since)
    for role in ("arrow_peak", "arrow_trough"):
        assert texts[role] == _ARROWS[role]["wraps"][0].format(**arrow_words).replace("<br>", " "), texts[role]
    expected = {"arrow_trough": "2002-01", "arrow_peak": "2007-10", "arrow_economy": "2010-12", "arrow_parity": "2022-07"}

    # (7) Hover: Plotly labels nothing; our box can only report actual points, in bits.
    assert fig.layout.hovermode is False, "Plotly hover must be off"
    assert all(t.hoverinfo == "skip" for t in fig.data), "a trace can still produce a Plotly hover label"
    assert not fig.frames, "no Plotly frames: interpolated points exist only inside the browser's draw call"
    hover = meta["hover"]
    assert len(hover["gdp"]) == len(hover["year"]) == len(gdp_tr.x)
    assert len(hover["stock"]) == len(hover["economy"]) == len(hover["month"]) == len(stock.x)
    read = lambda text: float(text.split(": ")[1].split(" bits")[0].replace("−", "-"))
    times = lambda text: float(text.split("(×")[1].rstrip(")"))
    # Each row: the change since the series' own anchor, in bits, and the multiple; the date is the heading.
    for text, when, x, v in zip(hover["gdp"], hover["year"], gdp_tr.x, gdp_tr.y):
        assert when == x[:4] and text == COPY_TEXT["hover_economy_1978"].format(
            anchor_year=GDP_ANCHOR_YEAR, change=_bits(v, SHOW_MULTIPLE)), "GDP hover names the wrong year"
        close(read(text), round(v, 2), 1e-9, "GDP hover is not g(t)")
        close(times(text), 2.0 ** v, 0.006 if 2.0 ** v < 10 else 0.06, "GDP hover's multiple is not 2 to the bits")
    for d, when, ts, te in zip(s.index, hover["month"], hover["stock"], hover["economy"]):
        assert when == _month(d) and ts == COPY_TEXT["hover_stocks"].format(since=since, change=_bits(s[d], SHOW_MULTIPLE))
        assert te == COPY_TEXT["hover_economy"].format(since=since, change=_bits(e[d], SHOW_MULTIPLE))
        close(read(ts), round(s[d], 2), 1e-9, "stock hover is not s(t)")
        close(read(te), round(e[d], 2), 1e-9, "economy hover is not e(t)")
        close(times(ts), 2.0 ** s[d], 0.006, "stock hover's multiple is not 2 to the bits")
    assert not any(re.search(r"\(\d{4}\)|\([A-Z][a-z]{2} \d{4}\)", row) for key in ("gdp", "stock", "economy") for row in hover[key]), (
        "a hover row still carries its date: that is the heading's job")
    assert _bits(2.239, False) == "+2.24 bits" and _bits(-0.118, False) == "−0.12 bits"
    assert _bits(2.31, True) == "+2.31 bits (×4.96)" and _bits(-0.573, True) == "−0.57 bits (×0.67)"
    assert hover["gdp"][list(hover["year"]).index("1990")].startswith(
        COPY_TEXT["hover_economy_1978"].split("{change}")[0].format(anchor_year=1978) + "+")
    assert _bits(4.019, True) == "+4.02 bits (×16.2)" and SHOW_MULTIPLE
    assert _bits(-0.004, False) == "+0.00 bits", "a rounded zero must not print as minus zero"
    assert [a["text"] for a in meta["anchors"]] == [COPY_TEXT["anchor"].format(anchor=a_) for a_ in (GDP_ANCHOR_YEAR, since)]
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
    assert f'<div class="china-title">{TITLE}</div>' in page
    for word in (COPY_TEXT["panel_economy"], COPY_TEXT["panel_stocks"]):
        assert re.search(rf'<div class="china-head china-head-\w+">{word}</div>', page), f"no panel name: {word}"
    # The zero lines: the same treatment in both panels, a little heavier than a gridline, and no "China = US".
    zero_top, zero_bottom = (fig.layout.shapes[meta["zero"][k]] for k in ("top", "bottom"))
    assert zero_top.line.to_plotly_json() == zero_bottom.line.to_plotly_json() == dict(color=_INK, width=1.2)
    assert zero_top.layer == zero_bottom.layer == "between" and zero_top.y0 == zero_bottom.y0 == 0
    assert (zero_top.yref, zero_bottom.yref, zero_bottom.x0) == ("y", "y2", _iso(STOCK_ANCHOR))
    assert [zero_top.x0, zero_top.x1] == list(fig.layout.xaxis.range) and zero_bottom.x1 == zero_top.x1
    assert "China = US" not in html and not any(axis.zeroline for axis in (fig.layout.yaxis, fig.layout.yaxis2))
    hints = {k: fig.layout.annotations[meta["ann"][k]] for k in _HINTS}
    assert {k: a.text for k, a in hints.items()} == {k: v.format(anchor_year=GDP_ANCHOR_YEAR) for k, v in _HINTS.items()}
    assert "1978" in hints["gap_up"].text and "1978" in hints["gap_down"].text
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
        assert ev.description.endswith((".", ".”")), f"hover text should end with a period: {ev.label}"
    chatgpt = next(ev for ev in EVENTS if "ChatGPT" in ev.label)
    assert not re.search(r"caus|led to|trigger|because|drove|sparked|sent ", chatgpt.description), chatgpt.description
    labelled, ticks, stored = ([ev for ev in EVENTS if ev.tier == tier] for tier in ("label", "tick", "stored"))
    in_time = lambda evs, panel: [ev.label for ev in sorted(evs, key=lambda ev: ev.date) if ev.panel == panel]
    assert in_time(labelled, "economy") == [
        "7,000 Cadres Conference", "May 16 Notification", "“Bombard the Headquarters”", "Nixon in Beijing", "Mao dies",
        "“Reform and opening up”", "Joins World Bank, IMF", "Special economic zones", "Friedman visits", "Tiananmen",
        "Southern Tour", "Currency unification", "Hong Kong handover", "Joins WTO", "¥4 trillion stimulus",
        "Overtakes Japan", "Property crisis"]
    assert in_time(labelled, "stocks") == [
        "Exchanges open", "First B-shares", "First H-shares", "QFII", "Financial crisis", "Stock Connect",
        "Crash", "A-shares join MSCI", "US tariffs", "Chinese tech crackdown", "Stimulus rally"]
    assert in_time(ticks, "economy") == ["Beijing Olympics"]
    assert in_time(ticks, "stocks") == ["Renminbi de-pegged", "ICBC IPO", "Chinese ADRs join MSCI"]
    # The order they are given up in (the round-4 order): from the end of each panel's list.
    kept = lambda panel: [ev.label for ev in labelled if ev.panel == panel]
    assert kept("economy")[::-1][:5] == ["“Bombard the Headquarters”", "Property crisis", "Currency unification",
                                         "Hong Kong handover", "¥4 trillion stimulus"], "Bombard the Headquarters goes first"
    assert kept("stocks")[::-1][:2] == ["Exchanges open", "First H-shares"]
    new = {ev.label: ev.date for ev in labelled if ev.label in (
        "7,000 Cadres Conference", "May 16 Notification", "“Bombard the Headquarters”", "Mao dies", "Exchanges open")}
    assert new == {"7,000 Cadres Conference": "1962-01-11", "May 16 Notification": "1966-05-16",
                   "“Bombard the Headquarters”": "1966-08-05", "Mao dies": "1976-09-09", "Exchanges open": "1990-12-19"}
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
            assert ev["stalk"] is None, f"a tick has a stalk: {ev['label']}"
            assert line.line.dash in (None, "solid") and _rgb(line.line.color).tolist() == _rgb(_CONTEXT).tolist()
            assert line.line.width > 1 and line.opacity in (None, 1), f"a tick should be a firm navy mark: {ev['label']}"
            above, below = (line.y1 - 1) * panel_px[ev["panel"]], (1 - line.y0) * panel_px[ev["panel"]]
            close(above, wide["tick"]["up"], 1e-6, "a tick reaches the wrong height above its panel")
            close(below, wide["tick"]["down"], 1e-6, "a tick reaches the wrong depth into its panel")
            # It costs no height: it stops where the first row of labels starts, 3 px above the panel.
            assert above <= 3 and above + below <= 12, f"a tick should be short: {ev['label']}"
            continue
        # Two strokes: through the panel, and a stalk from the panel's top up to the label.
        stalk = fig.layout.shapes[ev["stalk"]]
        assert line.line.dash == stalk.line.dash == "dash" and line.line.color == stalk.line.color == _INK
        assert (line.y0, line.y1, stalk.y0) == (0, 1, 1) and stalk.y1 > 1 and stalk.x0 == stalk.x1 == ev["date"]
        assert stalk.yref == line.yref and stalk.opacity == line.opacity
        if ev["lead"] is None:
            label = fig.layout.annotations[ev["annotation"]]
            assert label.x == ev["date"] and label.yref == domain[ev["panel"]] and label.text == ev["text"]
        else:                                      # under the label its group shares
            lead = drawn[ev["lead"]]
            assert ev["annotation"] is None and lead["annotation"] is not None and lead["panel"] == ev["panel"]
            assert ev["label"] in lead["text"] and lead["date"] < ev["date"]
            assert stalk.y1 == fig.layout.shapes[lead["stalk"]].y1, f"{ev['label']} does not reach its shared label"
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
    assert sez["date"] == "1980-08-26" and sez["short"] == "SEZs" and "special economic zones (SEZs)" in sez["description"].lower().replace("sezs", "SEZs")
    assert by_label("Chinese tech crackdown", "stocks")["date"] == "2020-11-03"
    # The two stimulus labels, told apart; the yen sign's reading; and the new marks.
    assert "¥4 trillion" in by_label("¥4 trillion stimulus", "economy")["description"] and by_label("¥4 trillion stimulus", "economy")["date"] == "2008-11-09"
    # Every hover text is its template with the narration's words filled in (the Japan share, the exchanges' days).
    for ev in EVENTS:
        if ev.tier != "stored":
            assert by_label(ev.label, ev.panel)["description"] == ev.description.format(**words), ev.label
    assert {"{exchange_day}", "{shenzhen_day}"} <= set(re.findall(r"\{\w+\}", next(
        ev.description for ev in EVENTS if ev.label == "Exchanges open")))
    assert by_label("Overtakes Japan", "economy")["date"][:4] == "2010" and by_label("Beijing Olympics", "economy")["date"][:7] == "2008-08"
    assert by_label("Southern Tour", "economy")["notes"] == []
    friedman = by_label("Friedman visits", "economy")
    assert friedman["tier"] == "label" and friedman["date"][:7] == "1980-09" and friedman["notes"] == []
    both = build(tiers=("label", "tick", "stored"))
    assert len(both.layout.meta["events"]) == len(EVENTS), "a stored event does not pass through the same builder"

    # (10b) Notes: each is attached to a parent that exists in the figure, lies inside the plotted
    #       range, and is listed under its parent in date order. And every acronym is spelled out in
    #       the hover text it appears in.
    era_meta = {era["label"]: era for era in meta["eras"]}
    parents = ([(ev, by_label(ev.label, ev.panel) if ev.tier != "stored" else None) for ev in EVENTS if ev.notes]
               + [(era, era_meta.get(era.label)) for era in ERAS if era.notes])
    assert {p.label: len(p.notes) for p, _ in parents} == {"QFII": 1, "Stock Connect": 2}
    for parent, shown in parents:
        assert shown is not None, f"notes on something that is not drawn: {parent.label}"
        in_order = sorted(parent.notes, key=lambda n: n.date)
        assert [(n["date"], n["when"], n["text"]) for n in shown["notes"]] == [(n.date, n.when, n.text) for n in in_order]
        for n in parent.notes:
            assert x0 <= n.date <= _iso(cutoff), f"a note outside the plotted range: {n.when} ({parent.label})"
            assert n.when and n.text.endswith((".", ".”")), f"{n.when}: {n.text}"
            assert pd.Timestamp(n.date).year == int(re.search(r"(19|20)\d\d", n.when).group()), f"{n.when} is not {n.date}"
    assert sum(len(ev["notes"]) for ev in drawn) + sum(len(era["notes"]) for era in meta["eras"]) == sum(
        len(p.notes) for p, _ in parents), "a note has no parent in the figure"
    hovers = {ev.label: " ".join([ev.description] + [n.text for n in ev.notes]) for ev in EVENTS}
    hovers.update({era.label: " ".join([era.description] + [n.text for n in era.notes]) for era in ERAS})
    hovers.update({who.label: who.description for who in LEADERS})
    hovers.update({band.wraps[0]: band.description + " " + (band.early_description or "") for band in BANDS})
    for name, text in hovers.items():
        assert not _undefined_acronyms(text), f"{name}: {_undefined_acronyms(text)} not spelled out in its hover text"
    assert _undefined_acronyms("The WTO and the IMF (International Monetary Fund).") == ["WTO"]
    # House style. Every hover text (an event's, an era's, a leader's, a band's) leads with a date
    # in bold, then a colon; so does every note (its "when", which the hover box sets in bold).
    leads = ([ev["description"] for ev in meta["events"]] + [era["description"] for era in meta["eras"]]
             + [who["description"] for who in meta["leaders"]]
             + [b["description"] for b in meta["bands"]] + [b["early"]["description"] for b in meta["bands"] if b["early"]]
             + [spec["hover"] for b in meta["play"]["beats"] for spec in (b["rate"], b["reference"]) if spec])
    for text in leads:
        m = re.match(r"\*\*([^*]+)\*\*: \S", text)
        assert m and re.search(r"(19|20)\d\d|present", m.group(1)), f"a hover text does not lead with a bold date: {text[:50]}"
    assert all(n["when"] and re.search(r"(19|20)\d\d", n["when"]) for ev in meta["events"] + meta["eras"] for n in ev["notes"])

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
    # Each leader has a hover text of their own, and no note is shared between them.
    assert "leader_note" not in meta and "LEADER_NOTE" not in globals()
    # Each one's own: its bold lead gives the years of its segment.
    for who in meta["leaders"]:
        lead = re.match(r"\*\*([^*]+)\*\*: ", who["description"])
        assert lead and who["start"][:4] in lead.group(1), f"{who['label']}'s hover text does not lead with its years"
    assert len({who["description"] for who in meta["leaders"]}) == len(meta["leaders"])
    hua = meta["leaders"][1]
    assert (hua["start"][:7], hua["end"][:7]) == ("1976-10", "1978-12"), "Hua's band is Oct 1976 to Dec 1978"
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
    assert era_meta["Retrenchment"]["description"].startswith("**1989–91**: ")
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
    assert plain["early"]["description"].startswith("**Dec 1990 – Feb 1992**: ")
    assert plain["description"].startswith("**From Feb 1992**: ")
    assert "1990" in meta["bands"][0]["description"], "Shanghai's opening belongs in the hover text"
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
    chord_shapes = {chord["shape"] for chord in meta["chords"]} | {chord["shape"] for chord in meta["era_chords"]}
    for i, sh in enumerate(fig.layout.shapes):
        colour = _rgb(sh.fillcolor or sh.line.color).tolist()
        assert colour in (data_colours if i in chord_shapes else (navy, _rgb(_INK).tolist())), "a shape is in a data colour"
    in_colour = {meta["ann"][k] for k in ("fill_ahead", "rate_economy", "rate_stocks", "rate_era0", "rate_era1",
                                          "rate_era2")}                                # rates: each in its line's colour
    for i, a in enumerate(fig.layout.annotations):
        assert (_rgb(a.font.color).tolist() in data_colours) == (i in in_colour), a.text

    # (13) Playback: three acts that tile the data, each with one x-range; what it adds up to.
    play = meta["play"]
    acts, beats = play["acts"], play["beats"]
    assert play["start"] == gdp_tr.x[0] == acts[0]["start"] and play["end"] == _iso(cutoff) == acts[-1]["end"]
    assert play["speeds"] == [1, 1.5, 2] and play["speed"] == DEFAULT_SPEED == 1.5 and 'class="china-speed"' in page
    assert [(a["numeral"], a["title"]) for a in acts] == list(zip(("I", "II", "III"), PART_TITLES))
    # The same on the title card and the scrubber: the middle title in curly quotes on both.
    assert len(PART_TITLES) == 3 and PART_TITLES[1][0] == "“" and PART_TITLES[1][-1] == "”"
    assert [a["card_title"] for a in acts] == PART_TITLES
    assert [a["end"] for a in acts[:-1]] == ["1978-12-18", "1992-02-21"], "the part breaks have moved"
    assert [a["kicker"] for a in acts] == [COPY_TEXT["kicker"].format(numeral=n_, start_year=a_, end_year=z_)
                                           for n_, a_, z_ in (("I", 1960, 1978), ("II", 1978, 1992), ("III", 1992, cutoff.year))]
    assert all(a["kicker"].startswith("Part ") for a in acts)
    assert "text-transform: uppercase" in _STYLE[_STYLE.index(".china-act-kicker"):], "the overline is not in capitals"
    # The acts tile the data: the first starts with it, each starts where the one before ends, the last ends with it.
    for earlier, later in zip(acts, acts[1:]):
        assert earlier["start"] < earlier["end"] == later["start"] < later["end"], "the acts do not tile the data"
    # One x-range per act: from where the act is framed to its end and a little room. The first two
    # are framed from the start of the plot; the last from mid-1990, so that the opening of the
    # Shanghai exchange (the start of the plain band) and the three listings after it are in view.
    for act, spec in zip(acts, ACTS):
        lo, end, hi = (pd.Timestamp(v) for v in (act["range"][0], act["end"], act["range"][1]))
        assert act["range"][0] == (spec.view_from or x0), f"act {act['numeral']} is framed from the wrong date"
        close((hi - end) / (end - lo), WINDOW_MARGIN, 2e-3, f"act {act['numeral']}: the room right of its end")
    assert acts[-1]["range"][0] == "1990-07-01" < _EXCHANGE_OPENS == by_label("Exchanges open", "stocks")["date"] < _SHENZHEN_OPENS
    assert acts[-1]["range"][0] > x0 and acts[-1]["range"][1] <= x1, "the last act is a closer view of the finished chart"
    close((pd.Timestamp(x1) - cutoff) / (cutoff - pd.Timestamp(x0)), WINDOW_MARGIN, 2e-3, "the finished chart's room on the right")
    # The gutter right of the plot holds what closes the animation.
    assert wide["margin"]["r"] >= 80 and wide["end"]["label"] > wide["end"]["arrow"] > 0 and _LAYOUTS["narrow"]["end"]["label"] is None
    # The y-ranges are the same in every act because there is only one of each: nothing changes them.
    assert meta["view"]["y"] == list(fig.layout.yaxis.range) and meta["view"]["y2"] == list(fig.layout.yaxis2.range)
    assert '"yaxis.range' not in script and '"yaxis2.range' not in script, "the script must never set a y-range"
    reform = by_label("“Reform and opening up”", "economy")
    assert reform["date"] == acts[0]["end"] and "Deng's reforms" not in html

    # (13a) The schedule and the tempo rules. Each part lasts what it was given, or (where its boxes'
    #       reading times leave too little) runs over at the fastest base speed allowed; starts from
    #       rest and comes to rest; dips only gently, and briefly, at a labelled event; slows right
    #       down only while a box is up; and is never under 60% of its base speed for more than
    #       1.5 s with no box up to explain it. Every box comes up within SYNC_DAYS of its date, and
    #       stays up for its reading time.
    assert EVENT_SLOWDOWN >= 0.7 and EVENT_WINDOW_YEARS <= 0.25, "a labelled event should slow playback gently and briefly"
    assert BOX_SLOWDOWN == 0.2 and BOX_SECONDS == (1.2, 0.27) and PICTURE_SLOWDOWN == 0.1 and PICTURE_SECONDS == (2.2, 0.27)
    assert LAST_BOX_EXTRA == 0.5 and SYNC_DAYS == 45 and CROWD_SHARE == 0.05 and MIN_SHARE < CROWD_SHARE and MAX_BASE == 1.3
    assert SLOW_LIMIT == (0.6, 1.5) and [spec.seconds for spec in ACTS] == [55.0, 70.0, 73.0]
    assert NOTE_BEAT == dict(seconds=3.0, pulse=0.9) and NOTE_BEATS == ("arrow_economy", "arrow_parity")
    plan, marks, plan_words, _ = default_plan()
    assert plan_words == words and len(marks) == len(labelled)
    durations, bases, slowest, offsets, shares = [], [], [], [], []
    year_ = pd.Timedelta(days=365.25)
    for act, spec, part in zip(acts, ACTS, plan):
        table, name = part["table"], f"part {act['numeral']}"
        start, end = pd.Timestamp(act["start"]), pd.Timestamp(act["end"])
        years = (end - start) / year_
        # The table the page reads: dates and times, linear between them.
        grid_x = np.concatenate([[0.0], np.cumsum(act["grid"][0])])
        tau = np.concatenate([[0.0], np.cumsum(act["grid"][1])])
        assert min(act["grid"][0]) > 0 and min(act["grid"][1]) > 0, f"{name}: playback time does not run forwards"
        assert max(act["grid"][0]) <= _SCHEDULE_STEP_YEARS + 1e-6 and abs(grid_x[-1] - years) < 2e-6
        close(tau[-1], float(table["tau"][-1]), 0.01, f"{name}: the schedule in the figure is not the one built here")
        close(table["base"], act["base"], 1e-3, f"{name}: the base speed in the figure is not the one built here")
        # Read linearly, the page's table is never more than a few hundredths of a second from the schedule.
        edges = np.concatenate([[0.0], np.cumsum(table["dt"])])
        cells = np.concatenate([[0.0], np.cumsum(table["dt"] * table["base"] * table["factor"])])   # the fine grid's dates
        assert np.abs(np.interp(cells, grid_x, tau) - edges).max() < 0.05, f"{name}: the table is coarse"
        if table["base"] < MAX_BASE - 1e-9:
            close(tau[-1], spec.seconds, 0.6, f"{name} does not last what it was given")
        else:
            assert tau[-1] > spec.seconds - 0.6, f"{name}: at the fastest base speed it should run over, not under"
        f, x, dt = table["factor"], table["years"], table["dt"]
        assert f[0] < 0.1 and f[-1] < 0.1 and f.max() > 0.999, f"{name} should start and end at rest, and reach its base speed"
        boxed = np.zeros(len(x), dtype=bool)
        for (lo, hi, share), (opens, reads, _), (when, seconds, nominal), late in zip(
                table["stretches"], table["windows"], part["boxes"], table["late"]):
            up = (x >= lo) & (x <= hi)
            boxed |= (x >= lo - BOX_RAMP_YEARS) & (x <= hi + BOX_RAMP_YEARS)
            assert MIN_SHARE * (1 - 1e-9) <= share <= nominal + 1e-9, f"{name}: a box runs at the wrong speed"
            assert f[up].max() <= share + 1e-9, f"{name}: playback is not slowed throughout the box of {when:%Y-%m}"
            took = float(dt[up].sum())
            assert took >= seconds + 2 * CARD_FADE_SECONDS - 0.02, f"{name}: the box of {when:%Y-%m} is not up long enough to read"
            assert 0 <= lo < hi <= years + 1e-9, f"{name}: the box of {when:%Y-%m} is up outside its part"
            # In sync: the playhead is within SYNC_DAYS of the box's date as the box starts to come up.
            # (On the page the box comes up when the clock reaches the moment the playhead is at `opens`.)
            off = (opens - when) / pd.Timedelta(days=1)
            close(off, late, 1e-6, f"{name}: the box of {when:%Y-%m-%d} is not where the schedule put it")
            assert abs(off) <= SYNC_DAYS, f"{name}: the box of {when:%Y-%m-%d} comes up {off:+.1f} days from its date"
            # It comes up ON its date unless the part starts within a month of it, or the box before it
            # is still up then.
            if abs(off) > 1e-6:
                assert lo < 1e-9 or any(abs(hi_ - lo) < 1e-9 for _, hi_, _ in table["stretches"]), (
                    f"{name}: the box of {when:%Y-%m-%d} is off its date for no reason")
            offsets.append((when, off))
            shares.append((when, share))
        spans = sorted((lo, hi) for lo, hi, _ in table["stretches"])
        assert all(a_hi <= b_lo + 1e-9 for (_, a_hi), (b_lo, _) in zip(spans, spans[1:])), f"{name}: two boxes are up at once"
        # Away from the boxes and the two stops, playback never falls below a labelled event's gentle dip.
        open_road = ~boxed & (x > STOP_YEARS) & (x < years - STOP_YEARS)
        assert f[open_road].min() >= EVENT_SLOWDOWN - 1e-9, f"{name}: a deep slowdown with no box up"
        for d in marks:                               # every labelled event is a (gentle) beat
            at = (d - start).days / 365.25
            if STOP_YEARS < at < years - STOP_YEARS and not boxed[np.abs(x - at).argmin()]:
                close(f[np.abs(x - at).argmin()], EVENT_SLOWDOWN, 0.01, f"{name}: no gentle dip at the event of {d:%Y-%m-%d}")
        broken = unexplained_slow_stretches(table)
        assert not broken, (f"{name}: playback is under {SLOW_LIMIT[0]:.0%} of base speed for more than {SLOW_LIMIT[1]} s "
                            f"with no box up, {[(round(start.year + (start.dayofyear - 1) / 365.25 + at, 1), round(secs, 1)) for at, secs in broken]}")
        # The longest stretch under the threshold with no box up, for the record.
        under = (f < SLOW_LIMIT[0]) & ~boxed
        runs = np.split(dt[under], np.flatnonzero(np.diff(np.flatnonzero(under)) > 1) + 1) if under.any() else [np.zeros(1)]
        slowest.append(max(float(run.sum()) for run in runs))
        jolt = (np.abs(np.diff(f)) / f[:-1])[open_road[:-1] & open_road[1:]].max()
        assert jolt < 0.03, f"{name}: the pace changes abruptly somewhere ({jolt:.1%} in a grid step)"
        durations.append(float(tau[-1]))
        bases.append(table["base"])
    opening = sum(TRANSITION[k] for k in ("card_in", "hold", "ghost", "card_out"))
    transition = opening + TRANSITION["move"]
    last_read = final_seconds(words)
    close(last_read, BOX_SECONDS[0] + BOX_SECONDS[1] * len(f"{play['final']['lead']} {play['final']['text']}".split())
          + LAST_BOX_EXTRA, 1e-9, "the last box's reading time")
    # (After the pull-back: each era's chord, its rate and half a pause; the climb's arrow, its label, a
    # pause; then the bottom panel's two chords, each with its rate and a pause; the gap; the last box.)
    eras_ending = len(ERA_CHORDS) * (ENDING["chord"] + ENDING["label"] + ENDING["pause"] / 2) + ENDING["arrow"] + ENDING["label"]
    ending = (eras_ending + ENDING["pause"] + 2 * (ENDING["chord"] + ENDING["label"] + ENDING["pause"]) + ENDING["arrow"]
              + ENDING["label"] + ENDING["pause"] / 2 + CARD_FADE_SECONDS + last_read + CARD_FADE_SECONDS + 0.15)
    interlude = interlude_seconds(words)
    assert 4 <= transition <= 5.5 and 1.5 <= ENDING["pullback"] <= 2.0 and ENDING["pullback"] > TRANSITION["move"]
    assert ENDING["chord"] == 2 * 0.7 and ENDING["pause"] == 0.8 and "box_hold" not in ENDING, "the ending's timings"
    assert 0.25 <= GHOST_OPACITY <= 0.35 and REVEAL_SECONDS == 0.5 and 0.4 <= SCRIM_OPACITY <= 0.8
    total = opening + sum(durations) + interlude + transition * (len(acts) - 1) + ending + ENDING["pullback"]
    assert play["transition"] == TRANSITION and play["ending"] == ENDING
    close(play["final"]["seconds"], last_read, 1e-3, "the page's last box is not up for its reading time")

    # (13b) The beat script. Every beat lies inside its part; the boxes say what the script says,
    #       with every number in them computed (and each computed number as expected).
    assert len(beats) == len(BEATS) == sum(len(part["beats"]) for part in plan) == 28
    assert [sum(b["act"] == n for b in beats) for n in range(3)] == [7, 10, 11], "the beats are not in the parts they belong to"
    trims = {b.lead: b.trim for b in BEATS if b.trim}
    assert trims == {"Dec 1978": -1.0, "1988": -1.0}, trims
    for b in beats:
        act = acts[b["act"]]
        assert act["start"] < b["date"] <= act["end"], f"the beat of {b['date']} lies outside its part"
        assert act["start"] <= b["since"][:10] < b["until"][:10] <= act["end"], f"the box of {b['date']} is up outside its part"
        assert b["kind"] in ("text", "picture") and (b["picture"] is None) == (b["kind"] == "text")
        assert b["panel"] in ("economy", "stocks") and "{" not in b["lead"] + b["text"], "an unfilled placeholder"
        count = len(f"{b['lead']} {b['text']}".split())
        start_, per_word = PICTURE_SECONDS if b["kind"] == "picture" else BOX_SECONDS
        close(b["seconds"], start_ + per_word * count + trims.get(b["lead"], 0.0), 1e-3, "a box's reading time")
        off = (pd.Timestamp(b["since"]) - pd.Timestamp(b["date"])) / pd.Timedelta(days=1)
        assert abs(off) <= SYNC_DAYS, f"the box of {b['date']} comes up {off:+.1f} days from its date"
    # Economy boxes in the top panel, market boxes in the bottom one.
    assert [b["panel"] for b in beats] == (["economy"] * 15 + ["stocks", "economy"] + ["stocks"] * 2 + ["economy"] * 2
                                           + ["stocks"] * 3 + ["economy", "stocks", "economy", "economy"])
    assert [b.lead for b in BEATS if b.cross] == ["2020–21"], "only the Ma card may cross the panels in its own turn"
    # Every box that quotes a rate has an arrow over its span, and comes up at its span's last point.
    rated = {b["lead"]: (b["rate"]["text"], b["reference"]["text"] if b["reference"] else None) for b in beats if b["rate"]}
    assert rated == {"1962–65": ("+0.11 bits/yr", None), "1966–68": ("−0.15 bits/yr", None),
                     "1968–70": ("+0.19 bits/yr", None), "1989–91": ("+0.01 bits/yr", "(0.09 before)"),
                     "1993–97": ("+0.10 bits/yr", None), "2002–12": ("+0.12 bits/yr", None),
                     "2012–19": ("+0.06 bits/yr", "(0.12 before)")}, rated
    for b in beats:
        assert b["rate"] or "bits a year" not in b["text"], f"the box of {b['date']} quotes a rate without an arrow"
        for spec in filter(None, (b["rate"], b["reference"])):
            a, z = spec["span"]
            assert (spec["start"], spec["end"]) == (f"{a}-07-01", f"{z}-07-01"), "an arrow does not run between July points"
            close(spec["change"], year(g, z) - year(g, a), 1e-6, f"the change over {spec['lead']}")
            close(spec["rate"], (year(g, z) - year(g, a)) / (z - a), 1e-6, f"the rate over {spec['lead']}")
            assert (spec["y0"], spec["y1"]) == (year(g, a), year(g, z)), "an arrow's ends are not its points"
            ra, rl = fig.layout.annotations[spec["arrow"]], fig.layout.annotations[spec["label"]]
            assert (ra.ax, ra.ay, ra.x, ra.y) == (spec["start"], spec["y0"], spec["end"], spec["y1"]) and ra.showarrow
            assert ra.arrowwidth == RATE_ARROW["width"] == 1.5 and ra.arrowside in (None, "end") and not ra.text
            assert _rgb(ra.arrowcolor).tolist() == _rgb(_INK).tolist() == _rgb(rl.font.color).tolist(), "an arrow is not in ink"
            assert ra.visible is False and rl.visible is False and rl.text == spec["text"], "an arrow shows outside its box"
            verb = "rose" if spec["change"] >= 0 else "fell"
            assert spec["hover"].startswith(f"**{spec['lead']}**: Against America, output per person {verb} "
                                            f"{abs(spec['change']):.2f} bits."), spec["hover"]
        if b["rate"]:
            assert b["date"] == b["rate"]["end"], f"the box of {b['date']} does not come up at its span's end"
            # (Within an hour: where a box follows straight on from the one before, the two meet within a
            # fraction of a second of the date.)
            assert pd.Timestamp(b["since"]) >= pd.Timestamp(b["rate"]["end"]) - pd.Timedelta(hours=1), (
                f"the box of {b['date']} comes up before its span's end")
    recovery_ = next(b for b in BEATS if b.lead == "1962–65")
    assert next(b for b in beats if b["lead"] == "1962–65")["rate"]["hover"] == RATE_HOVER.format(
        lead="1962–65", verb="rose", change="0.33") == "**1962–65**: Against America, output per person rose 0.33 bits."
    assert recovery_.rate_note is None and not any(b.rate_note for b in BEATS), "an arrow's hover has a note again"
    # The annotations that are beats: reached at their points, and slow to a text box's speed for 3 s.
    noted = play["notes"]
    assert [n["role"] for n in noted] == list(NOTE_BEATS)
    for n in noted:
        when = points[n["role"]][0]
        assert n["date"] == pd.Timestamp(when).strftime("%Y-%m-%d %H:%M:%S"), f"{n['role']} is not reached at its point"
        assert n["share"] <= BOX_SLOWDOWN + 1e-9 and abs((pd.Timestamp(n["since"]) - when) / pd.Timedelta(days=1)) <= SYNC_DAYS
    # The numbers: each computed from the data, and each as expected. (fdi_rate: the brief had 0.11; it computes 0.10.)
    quoted = dict(famine_fall=31, factions_fall=14, rebound_rise=32, y1976_fall=3, since_reform_rise=75,
                  austerity_growth=2.5, fdi_rate=0.10, trough_china=46,
                  trough_usa=8, hu_rate=0.12, part2_bits=1.1, part2_rate=0.08, part2_own=2.8, economy_end=2.23,
                  stocks_end=-0.57, gap=2.80)
    got = {k: (round(numbers[k]) if isinstance(v, int) else round(numbers[k], len(str(v).split(".")[1]))) for k, v in quoted.items()}
    wrong = {k: (got[k], v) for k, v in quoted.items() if got[k] != v}
    assert not wrong, f"a number in the narration is not what was expected (computed, expected): {wrong}"
    assert words["hu_pct"] == "9" and words["gap_factor"] == "7" and words["trough_lag"] == "A month later"
    assert words["japan_share"] == "a sixth" and words["part2_change"] == "roughly doubled" and words["xi_change"] == "roughly halves"
    assert words["catch_up_claim"] == "the biggest catch-up with America in the World Bank's records"
    assert numbers["trough"] == trough and numbers["peak"] == peak and numbers["trough_months_after_wto"] == 1
    # "Faster than ever": no other leader's years saw the ratio rise as fast. "Roughly halved": since.
    assert max(numbers["era_rates"], key=numbers["era_rates"].get) == "Hu", numbers["era_rates"]
    assert 0.4 <= numbers["xi_share"] <= 0.6, "the catch-up has not roughly halved"
    assert 1.8 <= numbers["part2_multiple"] <= 2.3, "the catch-up to 1992 is not roughly a doubling"
    assert pd.Timestamp(next(b.date for b in BEATS if "{xi_from}" in b.lead)).year == _XI_COMPARED_TO
    # The numbers by another route: straight from the series in the derived file.
    chn, usa_ = gdp["CHN"], usa
    own_level = lambda y: 2.0 ** (year(chn, y) + year(usa_, y))
    close(100 * (1 - own_level(1962) / own_level(1960)), numbers["famine_fall"], 1e-9, "the famine's fall")
    close(100 * (1 - own_level(1968) / own_level(1966)), numbers["factions_fall"], 1e-9, "the fall of 1967-68")
    close(100 * (own_level(1970) / own_level(1968) - 1), numbers["rebound_rise"], 1e-9, "the rebound of 1968-70")
    close(100 * (1 - own_level(1976) / own_level(1975)), numbers["y1976_fall"], 1e-9, "the fall of 1976")
    close(100 * (own_level(1985) / own_level(1978) - 1), numbers["since_reform_rise"], 1e-9, "the rise of 1978-85")
    close(100 * ((own_level(1990) / own_level(1988)) ** 0.5 - 1), numbers["austerity_growth"], 1e-9, "growth in 1989-90")
    close((year(g, 1997) - year(g, 1993)) / 4, numbers["fdi_rate"], 1e-6, "the climb of 1993-97")
    close((year(g, 2012) - year(g, 2002)) / 10, numbers["hu_rate"], 1e-6, "the catch-up under Hu")
    close(2.0 ** (year(gdp["CHN"], 2010) - year(gdp["JPN"], 2010)), numbers["japan_share"], 1e-9, "China against Japan, 2010")
    assert round(1 / numbers["japan_share"]) == 6, "no longer about a sixth of Japan's"
    # The end of Part II, at the playhead there: the economy's line, by hand between its July points.
    stop = pd.Timestamp(ACTS[_INTERLUDE_ACT].end)
    a_, b_ = g[:stop].index[-1], g[stop:].index[0]
    by_hand = g[a_] + (g[b_] - g[a_]) * (stop - a_).days / (b_ - a_).days
    close(numbers["part2_bits"], by_hand, 1e-6, "the arrow at the end of Part II")
    close(numbers["part2_rate"], by_hand / ((stop - g.index[g.index.year == 1978][0]) / year_), 1e-6, "its rate")
    own_ = (gdp["CHN"] + usa).dropna()
    own_stop = own_[a_] + (own_[b_] - own_[a_]) * (stop - a_).days / (b_ - a_).days
    close(numbers["part2_own"], 2.0 ** (own_stop - year(own_, 1978)), 1e-6, "its own-terms multiple")
    # "The biggest catch-up with America in the World Bank's records": every country with data in 1978
    # and in the last year, aggregates aside, ranked by its gain; China first. (From the raw file.)
    aggregates = set(derived_info()["aggregates"].split())
    assert {"WLD", "EAS", "HIC", "OED"} <= aggregates and "CHN" not in aggregates and len(aggregates) > 40
    last_year = gdp["CHN"].dropna().index[-1].year
    raw_gdp = raw[raw["series"] == "gdp"]
    gains = {}
    for code, rows in raw_gdp.groupby("entity"):
        at_ = dict(zip(rows["date"].dt.year, rows["log_ratio"]))
        if code not in aggregates and 1978 in at_ and last_year in at_:
            gains[code] = (at_[last_year] - at_[1978]) / np.log(2)
    ranked = sorted(gains, key=gains.get, reverse=True)
    assert ranked[0] == "CHN" and [c for c, _ in numbers["catch_up_ranking"]] == ranked, "China's catch-up is not the biggest"
    # The bottom: MSCI China's fall is the ratio's fall compounded with MSCI USA's.
    close((1 - numbers["trough_china"] / 100), (1 - numbers["trough_usa"] / 100) * 2.0 ** float(s[trough]), 1e-9, "the two falls")
    assert (STOCK_ANCHOR, trough) in returns, "the derived file has no MSCI USA return for the anchor in use"
    # What the boxes say, word for word (the text as given; numbers and dates filled in).
    # (In date order. Keyed by nothing: a date here would name the anchor's year outside its parameter.)
    # Each box is its template with the narration's numbers filled in (the numbers asserted above), in date order.
    said = [f"{b['lead']} | {b['text']}" for b in beats]
    by_date = sorted(BEATS, key=lambda b: beat_date(b, numbers["trough"]))
    script_ = [f"{b.lead.format(**words)} | {b.text.format(**words)}" for b in by_date]
    assert said == script_, [(a, b) for a, b in zip(said, script_) if a != b]
    assert beats[21]["date"] == _iso(trough + pd.DateOffset(months=1)), "the WTO box follows the computed trough"
    # The merges and the new boxes: no box at the old dates; the new ones in place, picking out their events.
    dates_ = [b["date"] for b in beats]
    assert not {"1963-06-30", "1967-01-13", "1968-03-31", "1969-06-30", "1976-09-09", "1977-12-31", "1990-03-31",
                "2010-06-30", "2019-01-31"} & set(dates_), "a box that was merged or moved is still there"
    for when, label_ in (("2002-12-01", "QFII"), ("2018-06-01", "A-shares join MSCI")):
        b = beats[dates_.index(when)]
        assert b["panel"] == "stocks" and meta["events"][b["event"]]["label"] == label_
    assert play["final"]["lead"] == FINAL_BOX.lead.format(**words) and play["final"]["text"] == FINAL_BOX.text.format(**words)
    assert (words["since"], words["end_month"], words["economy_bits"], words["stocks_bits"], words["gap_bits"],
            words["gap_factor"]) == (since, _month(cutoff), "2.23", "0.57", "2.80", "7")
    # The end of Part II: the arrow up the economy's line from its 1978 level, and its box.
    inter = play["interlude"]
    assert (inter["act"], inter["date"], inter["lead"]) == (1, "1992-02-21", "1978–1992")
    close(inter["value"], by_hand, 2e-6, "the arrow at the end of Part II does not reach the line")
    assert inter["text"] == INTERLUDE_BOX.text.format(**words) and inter["lead"] == INTERLUDE_BOX.lead.format(**words)
    assert (words["part2_bits"], words["part2_rate"], words["part2_own"]) == ("+1.1", "0.08", "2.8")
    close(inter["seconds"], box_seconds(INTERLUDE_BOX, words), 1e-3, "the interlude's box's reading time")
    ia = fig.layout.annotations[inter["arrow"]]
    assert ia.showarrow and ia.arrowside == "end+start" and (ia.x, ia.ax, ia.ay, ia.axref, ia.ayref) == (
        "1992-02-21", "1992-02-21", 0.0, "x", "y") and abs(ia.y - by_hand) < 1e-6 and ia.visible is False and not ia.text
    assert _rgb(ia.arrowcolor).tolist() == _rgb(_INK).tolist(), "the interlude's arrow is not in ink"
    # No box hard-codes a number that is the data's, or a date that is the anchor's or the cutoff's:
    # as written (before the numbers go in), a beat names neither. (Typed history may hold a number:
    # Liu's 30/70, inflation near 20%.)
    for beat in BEATS + [FINAL_BOX, INTERLUDE_BOX]:
        raw_ = f"{beat.lead} {beat.text}"
        assert since not in raw_ and _month(cutoff) not in raw_ and str(cutoff.year) not in raw_, f"typed in: {raw_}"
        assert not re.search(r"\d+(\.\d+)? ?(%|bits)", raw_) or raw_.startswith(("1988", "Jan–Feb 1962")), f"a typed-in statistic: {raw_}"
    for words_ in [b["text"] for b in beats] + [a["card_title"] for a in acts] + [play["final"]["text"], inter["text"]]:
        assert words_ not in script, f"narration is hard-coded in the script: {words_}"

    # House style: American spelling and American dates in everything a reader sees.
    visible = ([ev.label for ev in EVENTS] + [ev["description"] for ev in meta["events"]]
               + [n.text for ev in EVENTS for n in ev.notes] + [n.when for ev in EVENTS for n in ev.notes]
               + [era.label for era in ERAS] + [era["description"] for era in meta["eras"]]
               + [n.text for era in ERAS for n in era.notes] + [who.description for who in LEADERS]
               + [w for band in BANDS for w in band.wraps] + [b["description"] for b in meta["bands"]]
               + [b["early"]["description"] for b in meta["bands"] if b["early"]]
               + [f"{b['lead']} {b['text']}" for b in beats] + [inter["lead"], inter["text"]]
               + [spec[k] for b in beats for spec in (b["rate"], b["reference"]) if spec for k in ("hover", "text")]
               + [play["final"]["lead"], play["final"]["text"]] + PART_TITLES + [a["kicker"] for a in acts]
               + list(_HINTS.values()) + [w for spec in _FILL_LABELS.values() for w in spec["wraps"]]
               + [w for a in meta["arrows"] for w in a["wraps"]] + [a["key"] for a in meta["arrows"]]
               + [c["text"] for c in meta["chords"]] + [meta["gap"]["text"], meta["key"]["zero"], BACKTEST_NOTE]
               + [a["text"] for a in meta["anchors"]] + list(hover["gdp"][:3]) + list(hover["stock"][:3])
               + [p.short for p in PICTURES.values() if p.short] + [TITLE]
               + re.findall(r'(?:title|aria-label|alt)="([^"]*)"', _MARKUP) + re.findall(r">([^<>]*[A-Za-z][^<>]*)<", _MARKUP)
               # What the script itself writes on the page: button titles, labels, aria text.
               + re.findall(r'"([A-Z][a-z]+(?: [^"]*)?)"', script))
    visible += [r["text"] for r in copy_rows()]
    british = sorted({w for text in visible for w in _british_spellings(text)})
    assert not british, f"British spellings a reader would see: {british}"
    assert _british_spellings("a stimulus programme; the colour; centralise; the centre; labelled") == [
        "programme", "colour", "centre", "labelled", "centralise"]
    day_month = re.compile(r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{4}\b")
    assert not [text for text in visible if day_month.search(text)], "a date in day-month-year order"
    assert "Act " not in " ".join(a["kicker"] for a in acts) and not re.search(r"\bAct [IV]", html), "readers see “Part”, not “Act”"

    # (13c) Pictures. Each picture card carries its picture (in the page itself, scaled down) and a
    #       short credit; the full credits are in the data. A missing file means a text box and a warning.
    cards = [b for b in beats if b["kind"] == "picture"]
    shown_pics = [key for key, p in PICTURES.items() if p.credit and (_HERE / p.file).exists()]
    assert [b.picture for b in BEATS if b.picture] == list(PICTURES) == [
        "cr_1966", "deng_carter_1979", "time_1985", "hkex_2007", "jack_ma"]
    assert shown_pics == list(PICTURES) and [b["date"][:4] for b in cards] == ["1966", "1979", "1985", "2006", "2020"]
    for p in PICTURES.values():                      # beside the module, in the post's own folder: no subfolder
        assert "/" not in p.file and Path(p.file).suffix == ".jpg"
    for b, key in zip(cards, shown_pics):
        pic = b["picture"]
        assert pic["src"].startswith("data:image/jpeg;base64,") and pic["credit"] == PICTURES[key].short and 0.3 < pic["aspect"] < 3
        assert len(pic["src"]) < 200_000, f"the picture {key} is embedded too large"
        # Scaled down to PICTURE_MAX_PX on its long side (never up), a JPEG; the file left as it is.
        from PIL import Image
        with Image.open(_HERE / PICTURES[key].file) as original:
            long_side = max(original.size)
        assert max(pic["size"]) == min(PICTURE_MAX_PX, long_side) and PICTURE_MAX_PX == 600 and PICTURE_QUALITY == 82
        sized = picture_data(key)
        close(len(base64.b64decode(pic["src"].split(",", 1)[1])) / 1024, sized["kb"], 0.06, f"the size of {key}")
        assert "kb" not in pic, "a size in KB would read as a stray number in the figure"
        assert PICTURES[key].short and len(PICTURES[key].short) < 40
        # Published by being embedded: the page names no picture file, so Quarto has nothing to copy.
        assert PICTURES[key].file not in html, f"the page refers to {PICTURES[key].file} instead of carrying it"
    assert "IISH, BG E15/699" in PICTURES["cr_1966"].credit and "chineseposters.net" in PICTURES["cr_1966"].credit
    assert PICTURES["time_1985"].credit == "TIME, cover, Jan 6, 1986."
    assert PICTURES["hkex_2007"].short == "Photo: WiNG, CC BY-SA 3.0" and PICTURES["hkex_2007"].credit == (
        "Hong Kong Stock Exchange trading hall, Feb 21, 2007. Photo: WiNG, CC BY-SA 3.0 "
        "(https://creativecommons.org/licenses/by-sa/3.0/), via Wikimedia Commons "
        "(https://commons.wikimedia.org/wiki/File:Hong_Kong_Exchange_Trade_Lobby_2007.jpg)")
    credits = picture_credits()
    assert credits.startswith("Images: ") and all(PICTURES[k].credit.rstrip(".") in credits for k in shown_pics)
    assert "Coca-Cola" not in credits and "coke_1979" not in PICTURES
    assert PICTURES["deng_carter_1979"].short == "Photo: White House / public domain"
    # Each picture card's words leave its picture room at 920 px (measured), the Ma card's included.
    for b in BEATS:
        if b.picture:
            pic, said_ = PICTURES[b.picture], f"{b.lead} {b.text}".format(**words)
            assert pic.room, f"no measured room for {b.picture}"
            assert len(said_) <= pic.room, f"the {b.lead} card's words leave its picture no room at 920 px"
    assert PICTURES["jack_ma"].max_px == 150 and [p for p in PICTURES if PICTURES[p].max_px] == ["jack_ma"]
    ma_words = f"{BEATS[-1].lead} {BEATS[-1].text}".format(**words)
    # The sentence the Ma card gave up closes the crackdown's hover text.
    gave_up = "The crackdown spreads to tech, tutoring and property firms."
    crackdown = by_label("Chinese tech crackdown", "stocks")["description"]
    assert gave_up not in BEATS[-1].text and crackdown.startswith("**Nov 3, 2020**: ") and crackdown.endswith(" " + gave_up)
    assert PICTURES["jack_ma"].short == "Photo: World Economic Forum, CC BY 2.0" and PICTURES["jack_ma"].credit.endswith("; cropped")
    assert all(v >= 160 for v in wide["card"]["pictures"]) and max(wide["card"]["pictures"]) <= 280
    real = dict(PICTURES)
    try:
        PICTURES["cr_1966"] = Picture("no-such-file.jpg", real["cr_1966"].credit, real["cr_1966"].short)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            without = build_china_figure().layout.meta["play"]["beats"]
        assert any("is missing" in str(w.message) and "text box" in str(w.message) for w in caught), "no warning for a missing picture"
        assert [(b["kind"], b["picture"]) for b in without if b["date"][:4] == "1966"] == [("text", None)]
        assert [b["text"] for b in without] == [b["text"] for b in beats], "a missing picture changed the words"
        fallback = next(b for b in without if b["date"][:4] == "1966")
        close(fallback["seconds"], BOX_SECONDS[0] + BOX_SECONDS[1] * len(f"{fallback['lead']} {fallback['text']}".split()), 1e-3,
              "a card without its picture is paced as a text box")
    finally:
        PICTURES.update(real)
    # Without its file, the Carter-Deng picture card is a text box too, saying the same.
    try:
        PICTURES["deng_carter_1979"] = Picture("no-such-file.jpg", real["deng_carter_1979"].credit, "x")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            without = build_china_figure().layout.meta["play"]["beats"]
        assert [b["kind"] for b in without if b["date"] == "1979-02-02"] == ["text"]
        assert [b["text"] for b in without] == [b["text"] for b in beats]
    finally:
        PICTURES.update(real)
    # The page: no year watermark, no ghosted image; a scrim and a title card; a box; the scrubber.
    for cls in ("china-play", "china-ico-replay", "china-scrub", "china-acts", "china-start", "china-end",
                "china-pill", "china-scrim", "china-act-card", "china-act-kicker", "china-act-rule", "china-beat", "china-beat-img"):
        assert cls in page, f"the page has no {cls}"
    assert "china-year-mark" not in html and "china-beat-image" not in html
    assert page.count("<img") == 1 and "<img" not in page[page.index('class="china-act-card"'):page.index('class="china-overlay"')], (
        "the only image slot is the box's: title cards are text")
    playhead = [fig.layout.shapes[i] for i in meta["playhead"]]
    assert [sh.yref for sh in playhead] == ["y domain", "y2 domain"] and all(sh.visible is False for sh in playhead)
    assert all(sh.opacity <= 0.3 and sh.line.width <= 1 and (sh.y0, sh.y1) == (0, 1) for sh in playhead), "a quiet playhead"

    # (13d) The ending, in the bottom panel: a dashed chord from the anchor to each series' last
    #       point and the rate it stands for (the final value over the years since the anchor), in
    #       the series' colour at the chord's end; then the gap between the two ends, with a
    #       double-headed arrow in ink; then the last box.
    span_years = (cutoff - STOCK_ANCHOR).days / 365.25
    close(span_years, numbers["years"], 1e-12, "the years since the anchor")
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
        said_ = COPY_TEXT["chord_rate"].format(rate=f"{'+' if rate >= 0 else '−'}{abs(rate):.3f}", multiple=f"{2 ** rate:.3f}")
        assert chord["said"] == said_ and chord["text"] == f"{chord['name']}: {said_}", f"{chord['text']} != {said_}"
        assert [w.replace("<br>", " ") for w in chord["wraps"]] == [f"<b>{said_}</b>"] * 2, "a rate label's wording, in bold"
        assert (label.x, label.y, label.xref, label.yref) == (chord["date"], finish, "x", "y2"), "a rate is not at its chord's end"
        assert label.font.color == colour and label.xanchor == "left" and not label.textangle
    close(chords[0]["rate"], 0.084, 0.0006, "the economy's rate is not about +0.084 bits a year")
    assert -0.0225 <= chords[1]["rate"] <= -0.0205, f"the stocks' rate is {chords[1]['rate']:+.4f} bits a year"
    assert (chords[0]["said"], chords[1]["said"]) == tuple(COPY_TEXT["chord_rate"].format(rate=r_, multiple=m_)
                                                         for r_, m_ in (("+0.084", "1.060"), ("−0.022", "0.985")))
    # First, in the top panel: a chord across each era, from the line's point at its start to the one at
    # its end; its rate, the change over the years between; on hover, each one's growth; the climb.
    eras_ = era_numbers(gdp, usa)
    point = {d.year: (_iso(d), float(v)) for d, v in g.items()}
    assert [e_["era"].name for e_ in eras_] == ["Mao", "Deng to Hu", "Xi"] and [(e_["start"], e_["end"]) for e_ in eras_] == [
        (1960, 1978), (1978, 2012), (2012, g.index[-1].year)], "the eras are not Mao, Deng to Hu, Xi"
    assert eras_[0]["start"] == START_YEAR and eras_[-1]["end"] == g.index[-1].year, "the eras do not span the line"
    assert all(a_["end"] == b_["start"] for a_, b_ in zip(eras_, eras_[1:])), "the eras do not meet"
    for n_, (era_, chord) in enumerate(zip(eras_, meta["era_chords"])):
        line = fig.layout.shapes[chord["shape"]]
        (x0_, y0_), (x1_, y1_) = point[era_["start"]], point[era_["end"]]
        assert (line.xref, line.yref, line.line.dash, line.line.color) == ("x", "y", "dash", _GDP_COLOR)
        assert (line.x0, line.x1, chord["start"], chord["end"]) == (x0_, x1_, x0_, x1_), f"{chord['name']}'s chord misses its points"
        close(line.y0, y0_, 1e-9, "an era's chord does not start on the line")
        close(line.y1, y1_, 1e-9, "an era's chord does not end on the line")
        rate = (y1_ - y0_) / (era_["end"] - era_["start"])
        close(chord["rate"], rate, 1e-6, f"{chord['name']}'s rate is not its change over its years")
        r_, m_ = f"{'+' if rate >= 0 else '−'}{abs(rate):.3f}", f"{2 ** rate:.3f}"
        flat = f"{2 ** rate:.2f}" == "1.00"
        said_ = COPY_TEXT["era_rate_flat" if flat else "era_rate"].format(name=chord["name"], span=era_["span"], rate=r_, multiple=m_)
        assert chord["said"] == chord["text"] == said_ and chord["wraps"][0] == f"<b>{said_}</b>"
        assert all(w.replace("<br>", " ") == f"<b>{said_}</b>" for w in chord["wraps"]), "a broken label says something else"
        own_ = (gdp["CHN"] + usa).dropna()
        lv = {d.year: float(v) for d, v in own_.items()}
        us_ = {d.year: float(v) for d, v in usa.dropna().items()}
        grow = lambda L_: 100 * (2 ** ((L_[era_["end"]] - L_[era_["start"]]) / (era_["end"] - era_["start"])) - 1)
        close(era_["china"], grow(lv), 1e-9, "China's growth over an era")
        close(era_["usa"], grow(us_), 1e-9, "America's growth over an era")
        assert chord["hover"] == ERA_CHORDS[n_].hover.format(span=era_["span"], china=f"{grow(lv):.1f}", usa=f"{grow(us_):.1f}")
        assert chord["hover"].startswith(f"**{era_['span']}**: "), "an era's hover text does not lead with its years in bold"
    # What the brief expects of them, and the words as they read. (Deng to Hu: 0.09745 bits a year, so
    # "+0.097", where the brief expected "+0.098".)
    expect = [(-0.001, 0.999, 2.6, 2.7), (0.098, 1.070, 8.8, 1.7), (0.054, 1.038, 5.7, 1.8)]
    for era_, (rate_, mult_, china_, usa_) in zip(eras_, expect):
        close(era_["rate"], rate_, 0.0006, f"{era_['era'].name}: the rate")
        close(era_["multiple"], mult_, 0.0006, f"{era_['era'].name}: the multiple")
        close(era_["china"], china_, 0.051, f"{era_['era'].name}: China's growth")
        close(era_["usa"], usa_, 0.051, f"{era_['era'].name}: America's growth")
    assert [c_["said"] for c_ in meta["era_chords"]] == [
        "Mao, 1960–78: −0.001 bits/yr", "Deng to Hu, 1978–2012: +0.097 bits/yr (×1.070/yr)", "Xi, 2012–25: +0.054 bits/yr (×1.038/yr)"]
    assert [c_["hover"] for c_ in meta["era_chords"]] == [
        "**1960–78**: China's output per person grew 2.6% a year, America's 2.7%. Starting far poorer, China did not catch up at all.",
        "**1978–2012**: 8.8% a year against America's 1.7%.", "**2012–25**: 5.7% a year against America's 1.8%."]
    # (The Mao hover's last sentence is typed: China's output per person grew no faster than America's then.)
    assert eras_[0]["china"] <= eras_[0]["usa"] and eras_[0]["rate"] <= 0, "China did catch up under Mao: fix its hover text"
    # The climb: a double-headed arrow from the 1978 level to the line's last point, in ink; its label in the gutter.
    climb_ = meta["climb"]
    arrow_, label_ = fig.layout.annotations[climb_["arrow"]], fig.layout.annotations[climb_["label"]]
    assert (arrow_.x, arrow_.ax, arrow_.ay, arrow_.ayref, arrow_.arrowside) == (gdp_tr.x[-1], gdp_tr.x[-1], 0.0, "y", "end+start")
    close(arrow_.y, gdp_tr.y[-1], 1e-9, "the climb's arrow does not reach the line's last point")
    gap_arrow_, gap_label_ = fig.layout.annotations[meta["gap"]["arrow"]], fig.layout.annotations[meta["gap"]["label"]]
    assert arrow_.arrowcolor == gap_arrow_.arrowcolor and arrow_.arrowwidth == gap_arrow_.arrowwidth and arrow_.xshift == wide["end"]["arrow"] and climb_["value"] == round(gdp_tr.y[-1], 6)
    assert (label_.xanchor, label_.xshift, label_.font.color) == ("left", wide["end"]["label"], gap_label_.font.color),         "the climb's label is not in the gutter, in ink"
    assert climb_["text"] == COPY_TEXT["climb"].format(bits=f"+{gdp_tr.y[-1]:.2f}", anchor_year=GDP_ANCHOR_YEAR,
                                                       multiple=f"{2 ** gdp_tr.y[-1]:.0f}") == "+4.02 bits since 1978 (×16)"
    assert all(w.replace("<br>", " ") == climb_["text"] for w in climb_["wraps"])
    assert "top_chord" not in meta and "rate_economy_top" not in meta["ann"], "the single chord from 1978 is still there"
    # On the finished chart the event lines step back (and come back on hover).
    assert meta["final_line_share"] == FINAL_EVENT_LINE_SHARE and 0.35 <= FINAL_EVENT_LINE_SHARE <= 0.4
    final_line_opacity = _EVENT_LINE_OPACITY * FINAL_EVENT_LINE_SHARE
    end_ = meta["gap"]
    close(end_["value"], float(e.iloc[-1]) - float(s.iloc[-1]), 1e-6, "the gap is not the economy's end less the stocks'")
    assert end_["text"] == COPY_TEXT["gap"].format(gap_bits=f"{abs(end_['value']):.2f}", gap_multiple=f"{2 ** abs(end_['value']):.1f}")
    assert (f"{abs(end_['value']):.2f}", f"{2 ** abs(end_['value']):.1f}") == ("2.80", "7.0")
    arrow, gap_label = fig.layout.annotations[end_["arrow"]], fig.layout.annotations[end_["label"]]
    assert arrow.showarrow and arrow.arrowside == "end+start" and (arrow.axref, arrow.ayref) == ("x", "y2") and not arrow.text
    assert (arrow.x, arrow.y, arrow.ax, arrow.ay) == (stock.x[-1], float(e.iloc[-1]), stock.x[-1], float(s.iloc[-1])), (
        "the gap's arrow does not run between the two lines' ends")
    assert _rgb(arrow.arrowcolor).tolist() == _rgb(_INK).tolist() == _rgb(gap_label.font.color).tolist(), "the gap is in ink, not red"
    close(gap_label.y, (float(e.iloc[-1]) + float(s.iloc[-1])) / 2, 1e-9, "the gap's label is not mid-way along its arrow")

    # (13e) The stock anchor is a parameter. Build the figure with another one, two years on, and
    #       check that everything that depends on the anchor has followed it.
    asked = pd.Timestamp(year=STOCK_ANCHOR.year + 2, month=STOCK_ANCHOR.month, day=STOCK_ANCHOR.day)
    other = anchor_month_end(s_file, asked)          # that month's last trading day, which is what the file holds
    assert other.to_period("M") == asked.to_period("M") and 0 <= (asked - other).days <= 3
    alt = build(stock_anchor=asked)                  # (the derived file carries that anchor's numbers too: no warning)
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
    assert am["anchors"][1]["date"] == _iso(other) and am["anchors"][1]["text"] == COPY_TEXT["anchor"].format(anchor=since2)
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
    # The hover text; the rates and the gap that close the animation; and the boxes that quote the anchor.
    assert am["hover"]["stock"][0] == COPY_TEXT["hover_stocks"].format(since=since2, change=_bits(0.0, SHOW_MULTIPLE))
    assert len(am["hover"]["stock"]) == len(s2)
    assert am["hover"]["economy"][0] == COPY_TEXT["hover_economy"].format(since=since2, change="+0.00 bits (×1.00)")
    span2 = (cutoff - other).days / 365.25
    for chord, series in zip(am["chords"], (e2, s2)):
        line = alt.layout.shapes[chord["shape"]]
        assert (line.x0, line.y0, line.x1, line.y1) == (_iso(other), 0, _iso(cutoff), float(series.iloc[-1]))
        close(chord["rate"], float(series.iloc[-1]) / span2, 1e-6, "a rate did not follow the anchor")
        assert f"{abs(series.iloc[-1] / span2):.3f} bits/yr" in chord["text"]
    gap2 = float(e2.iloc[-1]) - float(s2.iloc[-1])
    close(am["gap"]["value"], gap2, 1e-6, "the gap did not follow the anchor")
    assert am["gap"]["text"] == COPY_TEXT["gap"].format(gap_bits=f"{abs(gap2):.2f}", gap_multiple=f"{2 ** abs(gap2):.1f}") != end_["text"]
    assert (alt.layout.annotations[am["gap"]["arrow"]].y, alt.layout.annotations[am["gap"]["arrow"]].ay) == (float(e2.iloc[-1]), float(s2.iloc[-1]))
    last2, _, numbers2 = am["play"]["final"], None, narration_numbers(gdp, usa, s2, e2, other, cutoff, returns)[1]
    assert last2["lead"] == f"{since2} – {_month(cutoff)}" and f"{abs(gap2):.2f} bits" in last2["text"]
    assert f"gained {abs(float(e2.iloc[-1])):.2f} bits" in last2["text"] and f"lost {abs(float(s2.iloc[-1])):.2f}" in last2["text"]
    after_ = next(b for b in BEATS if b.after)
    bottom2 = next(b for b in am["play"]["beats"] if b["lead"] == after_.lead.format(**words))     # (its lead, the WTO month, is not the anchor's)
    assert f"down {numbers2['trough_china']:.0f}% since {since2}, against {numbers2['trough_usa']:.0f}% for US stocks" in bottom2["text"]
    assert numbers2["trough_china"] != numbers["trough_china"] and numbers2["trough"] == trough2
    # Nothing in that figure, or in the page made from it, still names the default anchor.
    alt_html = china_figure_html(alt)
    for where, text in (("figure JSON", alt.to_json()), ("page", alt_html)):
        assert _iso(STOCK_ANCHOR) not in text and since not in text, f"the {where} still names {since} with the anchor moved"
    assert since2 in alt.to_json() and since in fig.to_json()
    # Nor does the source. Outside the narration's own script (history, which may name any year),
    # the anchor's year is written once, on the line that sets STOCK_ANCHOR (and nowhere in the
    # prep script, which starts wherever its files do); and the narration never names the anchor's
    # month (checked above: no beat, as written, holds it).
    needle = str(STOCK_ANCHOR.year)
    for path, allowed in ((Path(__file__), ["STOCK_ANCHOR = "]), (_HERE / "prepare_china_figure_data.py", [])):
        source = path.read_text(encoding="utf-8")
        if "\nBEATS = [\n" in source:
            source = source[:source.index("\nBEATS = [\n")] + source[source.index("\n]\n", source.index("\nBEATS = [\n")):]
        named = [ln.strip() for ln in source.splitlines() if needle in ln]
        assert len(named) == len(allowed) and all(ln.startswith(a) for ln, a in zip(named, allowed)), (
            f"{path.name} names the anchor's year outside the parameter: {named}")
    # An anchor in a month the derived file does not cover is refused; one it has no MSCI USA
    # return for is built, with a warning, and its box gives the ratio alone.
    for bad in (s_file.index[0] - pd.Timedelta(days=45), s_file.index[-1] + pd.Timedelta(days=45)):
        try:
            build_china_figure(stock_anchor=bad)
            raise RuntimeError(f"an impossible anchor was accepted: {bad:%Y-%m-%d}")
        except AssertionError:
            pass
    odd = next(d for d in s_file.index if d.month == 6 and d > STOCK_ANCHOR)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        unknown = build_china_figure(stock_anchor=odd).layout.meta["play"]["beats"]
    assert any("no MSCI USA return" in str(w.message) for w in caught), "no warning for an anchor without its numbers"
    assert any(f"at ×" in b["text"] and f"of US stocks' value since {_month(odd)}" in b["text"] for b in unknown)

    # (13f) A back-tested stretch, if one is declared: dotted, sharing a point with the solid line,
    #       and saying why in its hover text. None is declared by default.
    assert STOCK_BACKTESTED_UNTIL is None and meta["backtest"] is None and len(fig.data[tr["stock_back"]].x) == 0
    until = s.index[30]
    tested = build_china_figure(backtested_until=until)
    tm, tt = tested.layout.meta, tested.layout.meta["trace"]
    dotted, solid = tested.data[tt["stock_back"]], tested.data[tt["stock"]]
    assert dotted.line.dash == "dot" and solid.line.dash in (None, "solid") and dotted.line.color == solid.line.color
    assert dotted.x[-1] == solid.x[0] == tm["backtest"]["until"] == _iso(until), "the two stretches do not meet"
    assert list(dotted.x[:-1]) + list(solid.x) == list(stock.x) and list(dotted.y[:-1]) + list(solid.y) == list(stock.y)
    assert tm["backtest"]["note"] == BACKTEST_NOTE and "October 31, 1995" in BACKTEST_NOTE and "back-tested" in BACKTEST_NOTE
    flagged = [h.endswith(", back-tested") for h in tm["hover"]["stock"]]
    assert flagged == [d < until for d in s.index], "the hover text flags the wrong months as back-tested"
    assert tt["stock_back"] < tt["stock"] and tested.data[tt["economy"]].x == economy.x

    # (13g) The pacing chart, for reviewing the tempo without watching: exported beside this module.
    chart_path = _HERE / "china_figure_pacing.png"
    pacing_chart(chart_path)
    assert chart_path.stat().st_size > 20_000, "the pacing chart was not written"

    # (16) The copy. Every string a reader sees is a row; each row is a literal in this source the importer
    #      can find and rewrite; the workbook is as described; and the importer refuses what it should.
    import ast
    import importlib.util
    import sys as sys_
    import tempfile
    spec_ = importlib.util.spec_from_file_location("apply_copy", _HERE / "apply_copy.py")
    ac = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(ac)
    this = sys_.modules[__name__]
    rows = copy_rows()
    by_id = {r["id"]: r for r in rows}
    assert len(by_id) == len(rows) and all(r["kind"] in COPY_KINDS for r in rows)
    assert {r["kind"] for r in rows} == set(COPY_KINDS), set(COPY_KINDS) - {r["kind"] for r in rows}
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for r in rows:
        assert set(_placeholders(r["text"])) <= set(r["allowed"]), f"{r['id']} uses a placeholder it may not"
        assert set(r["values"]) <= set(_placeholders(r["text"])) | set(r["allowed"])
        for path in r["paths"]:
            found = [ac.literal_value(source, n) for n in ac.resolve(tree, path, this)]
            if isinstance(path[-1], tuple):
                assert ac._SPLIT[path[-1]].match(r["text"]).groups() == tuple(found), f"{r['id']} is not where it says"
            else:
                assert found == [r["text"]], f"{r['id']} is not where it says: {found[0][:40]!r}"
    # Every string the figure shows is among the rows: the boxes, the hover text, the labels and the templates.
    listed = {r["text"] for r in rows}
    for b in list(BEATS) + [INTERLUDE_BOX, FINAL_BOX]:
        assert f"**{b.lead}** {b.text}" in listed
    for ev in EVENTS:
        if ev.tier != "stored":
            assert ev.description in listed and (ev.tier == "tick" or ev.label in listed)
    for item in [*COPY_TEXT.values(), *_HINTS.values(), *PART_TITLES, TITLE, RATE_LABEL, REFERENCE_LABEL, RATE_HOVER,
                 *(w for spec in _ARROWS.values() for w in spec["wraps"]), *(w for spec in _FILL_LABELS.values() for w in spec["wraps"]),
                 *(w for band in BANDS for w in band.wraps), *(p.short for p in PICTURES.values()),
                 *(x for era in ERAS for x in (era.label, era.description)), *(x for who in LEADERS for x in (who.label, who.description)),
                 *(x for era in ERA_CHORDS for x in (era.name, era.hover))]:
        assert item in listed, f"not in the copy: {item[:50]!r}"
    dates_ = [r["date"] for r in rows if r["date"]]
    assert dates_ == sorted(dates_) and all(r["date"] for r in rows[:len(dates_)]), "rows are not by date, undated last"
    budgeted = [r for r in rows if r["kind"] in ("text box", "picture card", "final card") and not r["id"].startswith("copy-")]
    assert all(r["budget"] and r["budget"] <= r["words"] for r in budgeted), "a box with no word budget"
    ma = by_id["card-2020-11-03"]
    assert ma["budget"] == COPY_BUDGETS["card-2020-11-03"] == 14 == ma["words"] and ma["kind"] == "picture card"
    assert len(ma_words) <= PICTURES["jack_ma"].room
    assert {r["kind"] for r in rows if r["id"].startswith("era-chord-")} == {"rate label", "rate hover"}
    # The workbook: one row a string; a frozen header; a word count that is a formula; a sheet of rules.
    with tempfile.TemporaryDirectory() as tmp:
        from openpyxl import load_workbook
        book_path = export_copy(Path(tmp) / "copy.xlsx")
        book = load_workbook(book_path)
        sheet = book["Copy"]
        head = [c.value for c in sheet[1]]
        assert head == ["id", "part", "date", "kind", "panel", "current text", "computed values", "new text",
                        "current words", "new words", "word budget", "notes"]
        assert sheet.max_row == len(rows) + 1 and sheet.freeze_panes == "A2" and "Rules" in book.sheetnames
        assert str(sheet.cell(2, 10).value).startswith("=IF(LEN(TRIM(H2))") and sheet.cell(2, 6).alignment.wrap_text
        assert [sheet.cell(n, 1).value for n in range(2, sheet.max_row + 1)] == [r["id"] for r in rows]
        sheet.cell(5, 8).value = "a rewrite in progress"
        book.save(book_path)
        try:
            export_copy(book_path)
            raise RuntimeError("the export wrote over new text")
        except FileExistsError:
            pass
        assert ac.read_new_text(book_path) == {sheet.cell(5, 1).value: "a rewrite in progress"}
    # The importer: good edits go in where they belong (a box, a shared group name, a template, an f-string), and
    # the module still parses; bad ones are refused, each with its reason.
    card = by_id["card-1961-06-30"]
    good = {"card-1961-06-30": "**1959–61** The Leap ends in famine: output per person falls {famine_fall}% by 1962.",
            "event-group-2018": "Mid-2018", "template-rate-label": "{rate} bits a year",
            "event-stocks-1990-12-19-hover": "**{exchange_day}**: Shanghai's exchange opens; **{shenzhen_day}**: Shenzhen's.",
            "figure-title": "China ÷ United States, " + "in bits " * 12}
    assert not ac.problems(by_id, good, this), ac.problems(by_id, good, this)
    changed = ac.edits_by_path(by_id, good)
    assert len(changed) == len(good) + 2, "a box's two fields and the group's two places"
    rewritten = ac.rewrite(source, changed, this)
    new_tree = ast.parse(rewritten)
    for path, text_ in changed.items():
        assert [ac.literal_value(rewritten, n) for n in ac.resolve(new_tree, path, this)] == [text_], path
    title_node = ac.resolve(new_tree, ("TITLE",), this)[0]
    assert title_node.end_lineno > title_node.lineno, "a long new text is not broken over lines"
    bad = {"no-such-id": "x", "card-1961-06-30": "**1959–61** Output falls {famine_fal}%.",
           "card-1962-01-30": "**Jan–Feb 1962** a {stray brace", "card-1965-07-01": "1962–65 no bold lead",
           "card-1968-07-01": "**1966–68** falls {factions_fall:.1f}%",
           "card-1979-02-02": "**1979** " + "Deng tours America and dons a cowboy hat at a Texas rodeo. " * 9}
    found = ac.problems(by_id, bad, this)
    for id_, why in (("no-such-id", "no such id"), ("card-1961-06-30", "unknown placeholder {famine_fal}"),
                     ("card-1962-01-30", "malformed placeholder"), ("card-1965-07-01", "bold lead"),
                     ("card-1968-07-01", "malformed placeholder"), ("card-1979-02-02", "no longer leaves its picture room")):
        assert any(p.startswith(id_) and why in p for p in found), (id_, why, found)
    assert card["allowed"] and "famine_fall" in card["allowed"]

    # (14) The top panel takes peer countries without restructuring.
    peers = build_china_figure(peers=("KOR", "JPN"))
    ptr = peers.layout.meta["trace"]
    assert len(ptr["peers"]) == 2 and all(peers.data[i].yaxis in (None, "y") for i in ptr["peers"])
    assert max(ptr["peers"]) < ptr["gdp"] and len(peers.data) == len(fig.data) + 2
    assert all(peers.data[ptr[k]].name == k for k in tr if k != "peers"), "a peer line shifted a named trace"
    assert gdp.shape[1] > 200, "the derived file should keep every World Bank entity"

    # (15) Licensing: no MSCI index level in the figure, the page HTML, the derived file or the copy workbook.
    derived = _DATA_PATH.read_text(encoding="utf-8")
    copy_text = "\n".join(" ".join([r["text"], *map(str, r["values"].values())]) for r in rows)
    published = {"figure JSON": fig.to_json(), "page HTML": html, "derived file": derived, "copy workbook": copy_text}
    assert '"bdata"' not in published["figure JSON"], "an array was binary-encoded; the JSON must stay readable"
    for name in ("figure JSON", "derived file", "copy workbook"):
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
              f"the page HTML, the derived file or the copy workbook.")

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
    both = lambda secs: " / ".join(f"{secs / v:.1f}" for v in SPEEDS)
    print(f"  playback, in seconds at {' / '.join(f'{v}x' for v in SPEEDS)} (the default is {DEFAULT_SPEED}x): "
          f"opening card {both(opening)}; "
          + "; ".join(f"part {a['numeral']} {both(d)} (target {spec.seconds:.0f})" for a, d, spec in zip(acts, durations, ACTS))
          + f"; the stop at the end of Part II {both(interlude)}; each of the {len(acts) - 1} part breaks {both(transition)}; "
          f"the ending {both(ending)}; the pull-back {both(ENDING['pullback'])}; in all {both(total)}.")
    reading = [sum(sec + 2 * CARD_FADE_SECONDS for _, sec, _ in part["boxes"]) for part in plan]
    print("  of which boxes are up (reading time and fades): " + ", ".join(
          f"part {a['numeral']} {r:.1f} s" for a, r in zip(acts, reading)) + f"; base speeds, in years a second: "
          + ", ".join(f"part {a['numeral']} {b:.2f}" for a, b in zip(acts, bases)) + f" (the most allowed is {MAX_BASE}).")
    print(f"  longest stretch under {SLOW_LIMIT[0]:.0%} of base with no box up or about to be (limit {SLOW_LIMIT[1]} s): "
          + ", ".join(f"part {a['numeral']} {v:.2f} s" for a, v in zip(acts, slowest)) + ".")
    print(f"  boxes: {sum(b['kind'] == 'text' for b in beats)} text boxes and {len(cards)} picture cards; up for "
          + ", ".join(f"{b['seconds']:.1f}" for b in beats) + " s to read; at "
          + ", ".join(f"{b['share']:.1%}" for b in beats) + " of base speed.")
    print("  in sync: each box comes up this many days from its date: "
          + ", ".join(f"{w:%Y-%m-%d} {d:+.0f}" for w, d in offsets) + f" (limit ±{SYNC_DAYS}). Under "
          f"{CROWD_SHARE:.0%} of base: " + (", ".join(f"{w:%Y-%m-%d} {sh:.1%}" for w, sh in shares if sh < CROWD_SHARE - 1e-9) or "none") + ".")
    print("  numbers in the boxes, computed (as expected): "
          + "; ".join(f"{k} {numbers[k]:.3f} ({v})" for k, v in quoted.items())
          + f"; Hu's rate as a percentage {100 * (2 ** numbers['hu_rate'] - 1):.2f} (about 9); catch-up since 2012 over Hu's "
          f"{numbers['xi_share']:.2f} (roughly half); to 1992 ×{numbers['part2_multiple']:.2f} (roughly doubled); "
          f"gap factor {2 ** numbers['gap']:.2f} (7); China per person against Japan, 2010: {numbers['japan_share']:.3f} "
          f"(about a sixth); catch-up since 1978: China first of {len(ranked)} countries ({gains['CHN']:.2f} bits; next "
          + ", ".join(f"{c} {gains[c]:.2f}" for c in ranked[1:4]) + ").")
    print("  rate arrows: " + "; ".join(f"{spec['lead']} {spec['text']} ({spec['change']:+.3f} bits)"
                                        for b in beats for spec in (b["rate"], b["reference"]) if spec) + ".")
    print("  the eras' chords: " + "; ".join(
        f"{c_['said']} ({e_['rate']:+.4f} bits/yr, ×{e_['multiple']:.4f}; China {e_['china']:.2f}% a year, America "
        f"{e_['usa']:.2f}%)" for c_, e_ in zip(meta["era_chords"], eras_)) + f"; the climb: {climb_['text']} "
        f"({gdp_tr.y[-1]:.4f} bits, ×{2 ** gdp_tr.y[-1]:.2f}).")
    print(f"  the ending at 1x / 1.5x: the pull-back {ENDING['pullback']:.1f} / {ENDING['pullback'] / 1.5:.1f} s, then "
          f"the eras and the climb {eras_ending + ENDING['pause']:.1f} / {(eras_ending + ENDING['pause']) / 1.5:.1f} s, "
          f"and the rest {ending - eras_ending - ENDING['pause']:.1f} / {(ending - eras_ending - ENDING['pause']) / 1.5:.1f} s.")
    print(f"  event lines: opacity {_EVENT_LINE_OPACITY} in play; {final_line_opacity:.3f} on the finished chart and "
          f"through the ending ({FINAL_EVENT_LINE_SHARE:.1%} of it).")
    print(f"  the Jack Ma card: {len(ma_words)} characters ({len(ma_words.split())} words), room for "
          f"{PICTURES['jack_ma'].room} at 920 px with its photo at {PICTURES['jack_ma'].max_px} px.")
    print(f"  copy: {len(rows)} strings in {COPY_PATH.name} (write it with --export-copy); budgets aim at "
          f"{TARGET_SECONDS:.0f} s at 1x.")
    print(f"  rates since {since} ({span_years:.3f} years): " + "; ".join(c["text"] for c in chords) + f"; {end_['text']}.")
    print(f"  anchor as a parameter: rebuilt at {since2} and every dependent element followed "
          f"(there: {'; '.join(c['text'] for c in am['chords'])}; {am['gap']['text']}; “{bottom2['text'].split(': ', 1)[1]}”).")
    print(f"  pacing chart: {chart_path.name} written beside this module.")
    print(f"  pictures, embedded in the page at {PICTURE_MAX_PX} px on the long side, JPEG {PICTURE_QUALITY}: "
          + "; ".join(f"{PICTURES[k].file} {picture_data(k)['file_kb']:.0f} KB on disk → {b['picture']['size'][0]}×"
                      f"{b['picture']['size'][1]}, {picture_data(k)['kb']:.0f} KB" for b, k in zip(cards, shown_pics))
          + f". Page HTML {len(html) / 1024:.0f} KB; nothing to publish alongside it.")
    print(f"  credits, for the caption:\n    {credits}")
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
    import sys
    if "--export-copy" in sys.argv:              # write china_figure_copy.xlsx (not over a rewrite in progress)
        print(f"wrote {export_copy(force='--force' in sys.argv).name}")
    else:
        _run_checks()
