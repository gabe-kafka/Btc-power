from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import gradio as gr
import matplotlib
import numpy as np
import pandas as pd
import requests

matplotlib.use("Agg")

from matplotlib import pyplot as plt
from matplotlib.patches import Wedge


GENESIS = datetime(2009, 1, 3)
A = -17.351
B = 5.84
CSV_PATH = os.path.join(os.path.dirname(__file__), "btc_historical.csv")
CACHE_TTL_SECONDS = 900

BG = "#0A0A0A"
PANEL = "#141414"
INK = "#E5E5E5"
MUTED = "#808080"
GRID = "#2A2A2A"

ZONE_META = [
    {
        "label": "Freezing",
        "summary": "BTC is trading in a cold, fear-heavy zone versus its long-run curve.",
        "detail": "Historically this has been a washed-out part of the cycle where price is subdued relative to trend.",
        "color": "#3B82F6",
    },
    {
        "label": "Cold",
        "summary": "BTC is below its usual cycle heat and still relatively calm.",
        "detail": "This is cooler than average for Bitcoin history, but not a deep capitulation zone.",
        "color": "#60A5FA",
    },
    {
        "label": "Balanced",
        "summary": "BTC is near the middle of its historical temperature range.",
        "detail": "The market is neither especially hot nor especially cold relative to the power curve.",
        "color": "#A3A3A3",
    },
    {
        "label": "Warm",
        "summary": "BTC is trading above trend and sentiment is heating up.",
        "detail": "This zone often appears when momentum is strong but the market is not yet at full euphoria.",
        "color": "#D97706",
    },
    {
        "label": "Overheated",
        "summary": "BTC is running very hot versus its historical power-curve position.",
        "detail": "This is where greed and speculative excess are most likely to dominate.",
        "color": "#DC2626",
    },
]

ZONE_BOUNDS = [20, 40, 60, 80]
PLOT_COLORS = [zone["color"] for zone in ZONE_META]
STATIC_EXPLAINER = """
### How to read this

- The white line is Bitcoin's long-run power curve.
- The color of the BTC line and the gauge reflects how hot or cold price is relative to that curve.
- The Heat Score is a percentile of Bitcoin's full historical deviation from the curve: `0` is among the coldest readings, `100` is among the hottest.
- This is a market-temperature tool. It is not the CNN Fear & Greed index and it does not use social sentiment.
"""

matplotlib.rcParams.update(
    {
        "font.family": ["DejaVu Sans Mono", "monospace"],
        "font.size": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
    }
)

CSS = """
:root {
  --bg: #0a0a0a;
  --panel: #141414;
  --panel-strong: #101010;
  --line: #2a2a2a;
  --ink: #e5e5e5;
  --muted: #808080;
  --accent: #3b82f6;
  --sans: "Neue Haas Grotesk Text Pro", "Univers", "Akzidenz-Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --mono: "Berkeley Mono", "JetBrains Mono", "IBM Plex Mono", "Courier Prime", monospace;
}

body {
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
}

.gradio-container {
  background: var(--bg) !important;
  color: var(--ink) !important;
  max-width: 1440px !important;
  padding: 16px !important;
}

footer {
  display: none !important;
}

.app-shell {
  margin: 0 0 16px;
}

.hero-card,
.narrative-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 0;
  padding: 16px;
  box-shadow: none;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: baseline;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

.eyebrow {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.hero-title {
  font-size: 24px;
  line-height: 1.125;
  font-weight: 700;
  font-family: var(--mono);
  margin: 0;
}

.hero-copy {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
  max-width: 880px;
  margin: 8px 0 0;
}

.stamp {
  border: 1px solid var(--line);
  background: var(--panel-strong);
  color: var(--ink);
  border-radius: 0;
  padding: 8px 12px;
  white-space: nowrap;
  font-size: 12px;
  font-family: var(--mono);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  margin-top: 16px;
  border: 1px solid var(--line);
}

.metric {
  background: transparent;
  border-right: 1px solid var(--line);
  padding: 16px;
}

.metric:last-child {
  border-right: 0;
}

.metric-label {
  color: var(--muted);
  font-size: 12px;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.metric-value {
  color: var(--ink);
  font-size: 24px;
  font-weight: 700;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  margin-top: 8px;
}

.metric-note {
  color: var(--muted);
  font-size: 14px;
  margin-top: 8px;
  line-height: 1.5;
}

.narrative-kicker {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.narrative-title {
  font-size: 20px;
  line-height: 1.2;
  margin: 8px 0 16px;
  font-family: var(--mono);
}

.narrative-copy {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
  margin: 0 0 16px;
}

.signal-list {
  display: grid;
  gap: 0;
  border: 1px solid var(--line);
}

.signal-item {
  display: grid;
  grid-template-columns: 184px 1fr;
  gap: 16px;
  padding: 8px 12px;
  border-top: 1px solid var(--line);
}

.signal-item:first-child {
  border-top: 0;
}

.signal-label {
  color: var(--muted);
  font-size: 12px;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.signal-value {
  color: var(--ink);
  font-size: 14px;
  font-weight: 700;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}

button.primary,
button.secondary {
  border-radius: 0 !important;
  box-shadow: none !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
}

.gr-button-primary {
  background: #1a1a1a !important;
  border: 1px solid var(--accent) !important;
  color: var(--ink) !important;
}

.gr-button-primary:hover {
  background: #111111 !important;
}

.prose,
.prose * {
  font-family: var(--sans) !important;
}

.prose p,
.prose li {
  font-size: 14px !important;
  line-height: 1.5 !important;
}

.prose h3,
.prose code,
.prose pre,
.prose table,
.prose th,
.prose td {
  font-family: var(--mono) !important;
}

.prose code {
  background: transparent !important;
  color: var(--ink) !important;
  border: 1px solid var(--line);
  border-radius: 0 !important;
  padding: 1px 4px;
}

@media (max-width: 980px) {
  .hero-top {
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-bottom: 0;
  }

  .metric {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .signal-item {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
"""


@dataclass
class Snapshot:
    as_of: datetime
    current_price: float
    curve_price: float
    curve_price_1y: float
    gap_pct: float
    curve_multiple: float
    years_ahead_value: float
    heat_score: float
    zone: dict
    df: pd.DataFrame
    history_years_ahead: np.ndarray
    history_scores: np.ndarray
    source_note: str


_CACHE: dict[str, object] = {"timestamp": 0.0, "snapshot": None}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def days_since_genesis(dt: datetime) -> float:
    return (dt - GENESIS).total_seconds() / 86400


def power_law_price(dt: datetime) -> float:
    days = days_since_genesis(dt)
    if days <= 0:
        return np.nan
    return 10 ** (A + B * np.log10(days))


def years_ahead(price: float, dt: datetime) -> float:
    days = days_since_genesis(dt)
    if days <= 0 or price <= 0:
        return np.nan
    curve_days = 10 ** ((np.log10(price) - A) / B)
    return (curve_days - days) / 365.25


def load_historical_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def fetch_recent_coingecko(days: int = 120) -> pd.DataFrame | None:
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": str(days), "interval": "daily"}
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        prices = response.json().get("prices", [])
        if not prices:
            return None
        df = pd.DataFrame(prices, columns=["ts", "price"])
        df["date"] = pd.to_datetime(df["ts"], unit="ms").dt.normalize()
        return df[["date", "price"]].drop_duplicates("date", keep="last")
    except Exception:
        return None


def fetch_current_price() -> float | None:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        price = response.json()["bitcoin"]["usd"]
        return float(price)
    except Exception:
        return None


def get_full_price_history() -> tuple[pd.DataFrame, str]:
    df = load_historical_csv()
    recent = fetch_recent_coingecko(days=120)
    if recent is not None and not recent.empty:
        merged = pd.concat([df, recent], ignore_index=True)
        merged = merged.drop_duplicates("date", keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)
        return merged, "Bundled history + CoinGecko refresh"
    return df, "Bundled historical CSV"


def heat_score_from_distribution(sorted_years_ahead: np.ndarray, value: float) -> float:
    percentile = np.searchsorted(sorted_years_ahead, value, side="right") / len(sorted_years_ahead)
    return float(np.clip(percentile * 100, 0, 100))


def zone_for_score(score: float) -> dict:
    if score < ZONE_BOUNDS[0]:
        return ZONE_META[0]
    if score < ZONE_BOUNDS[1]:
        return ZONE_META[1]
    if score < ZONE_BOUNDS[2]:
        return ZONE_META[2]
    if score < ZONE_BOUNDS[3]:
        return ZONE_META[3]
    return ZONE_META[4]


def build_snapshot(force: bool = False) -> Snapshot:
    cache_age = time.time() - float(_CACHE["timestamp"])
    if not force and _CACHE["snapshot"] is not None and cache_age < CACHE_TTL_SECONDS:
        return _CACHE["snapshot"]  # type: ignore[return-value]

    df, source_note = get_full_price_history()
    now = utc_now()

    current_price = fetch_current_price()
    if current_price is None:
        current_price = float(df.iloc[-1]["price"])
        now = pd.Timestamp(df.iloc[-1]["date"]).to_pydatetime()
        source_note = f"{source_note} (live spot unavailable, using last close)"

    history_years_ahead = np.array(
        [years_ahead(float(price), date.to_pydatetime()) for price, date in zip(df["price"], df["date"])],
        dtype=float,
    )
    history_years_ahead = history_years_ahead[np.isfinite(history_years_ahead)]
    sorted_years_ahead = np.sort(history_years_ahead)
    history_scores = np.array(
        [heat_score_from_distribution(sorted_years_ahead, value) for value in history_years_ahead],
        dtype=float,
    )

    curve_price = float(power_law_price(now))
    curve_price_1y = float(power_law_price(now + timedelta(days=365)))
    years_ahead_value = float(years_ahead(current_price, now))
    heat_score = heat_score_from_distribution(sorted_years_ahead, years_ahead_value)
    curve_multiple = current_price / curve_price
    gap_pct = (curve_multiple - 1) * 100

    snapshot = Snapshot(
        as_of=now,
        current_price=current_price,
        curve_price=curve_price,
        curve_price_1y=curve_price_1y,
        gap_pct=gap_pct,
        curve_multiple=curve_multiple,
        years_ahead_value=years_ahead_value,
        heat_score=heat_score,
        zone=zone_for_score(heat_score),
        df=df,
        history_years_ahead=history_years_ahead,
        history_scores=history_scores,
        source_note=source_note,
    )

    _CACHE["timestamp"] = time.time()
    _CACHE["snapshot"] = snapshot
    return snapshot


def format_dollar(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}k"
    return f"${value:,.0f}"


def format_gap(gap_pct: float) -> str:
    prefix = "+" if gap_pct >= 0 else ""
    return f"{prefix}{gap_pct:.1f}%"


def relative_sentence(score: float) -> str:
    if score >= 50:
        return f"Hotter than {score:.0f}% of Bitcoin's daily history."
    return f"Colder than {100 - score:.0f}% of Bitcoin's daily history."


def build_hero_html(snapshot: Snapshot) -> str:
    zone = snapshot.zone
    headline = (
        f"STATUS: <span style='color:{zone['color']}'>{zone['label'].upper()}</span> "
        f" | HEAT {snapshot.heat_score:.0f}/100 | GAP {format_gap(snapshot.gap_pct)}"
    )
    return f"""
    <div class="app-shell">
      <div class="hero-card">
        <div class="eyebrow">Bitcoin Power Curve Temperature</div>
        <div class="hero-top">
          <div>
            <h1 class="hero-title">{headline}</h1>
            <p class="hero-copy">{zone['summary']} {relative_sentence(snapshot.heat_score)} {zone['detail']}</p>
            <p class="hero-copy">
              Model fair value is the power-curve value for the current date, not intrinsic value.
              Today the model value is <strong>{format_dollar(snapshot.curve_price)}</strong>.
              One year out on the same curve it is <strong>{format_dollar(snapshot.curve_price_1y)}</strong>.
            </p>
          </div>
          <div class="stamp">Updated {snapshot.as_of.strftime("%b %d, %Y %H:%M UTC")}</div>
        </div>
        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label">Spot Price</div>
            <div class="metric-value">{format_dollar(snapshot.current_price)}</div>
            <div class="metric-note">Live BTC/USD when available.</div>
          </div>
          <div class="metric">
            <div class="metric-label">Model Fair Value</div>
            <div class="metric-value">{format_dollar(snapshot.curve_price)}</div>
            <div class="metric-note">Power-curve value for today, not intrinsic value.</div>
          </div>
          <div class="metric">
            <div class="metric-label">Premium / Discount</div>
            <div class="metric-value" style="color:{zone['color']};">{format_gap(snapshot.gap_pct)}</div>
            <div class="metric-note">Distance from the power-curve value.</div>
          </div>
          <div class="metric">
            <div class="metric-label">Years Ahead</div>
            <div class="metric-value">{snapshot.years_ahead_value:.2f}</div>
            <div class="metric-note">How far ahead of the curve price is trading.</div>
          </div>
          <div class="metric">
            <div class="metric-label">Heat Score</div>
            <div class="metric-value" style="color:{zone['color']};">{snapshot.heat_score:.0f}/100</div>
            <div class="metric-note">Historical percentile of BTC's power-curve deviation.</div>
          </div>
        </div>
      </div>
    </div>
    """


def build_narrative_html(snapshot: Snapshot) -> str:
    premium_text = "above" if snapshot.gap_pct >= 0 else "below"
    return f"""
    <div class="narrative-card">
      <div class="narrative-kicker">Interpretation</div>
      <div class="narrative-title">Market Readout</div>
      <p class="narrative-copy">
        Bitcoin is trading {abs(snapshot.gap_pct):.1f}% {premium_text} the model curve.
        The current reading is <span style="color:{snapshot.zone['color']}; font-weight:700;">{snapshot.zone['label'].upper()}</span>.
      </p>
      <div class="signal-list">
        <div class="signal-item">
          <div class="signal-label">Summary</div>
          <div class="signal-value">{snapshot.zone['summary']}</div>
        </div>
        <div class="signal-item">
          <div class="signal-label">Historical Position</div>
          <div class="signal-value">{relative_sentence(snapshot.heat_score)} {snapshot.years_ahead_value:.2f} years ahead of the curve.</div>
        </div>
        <div class="signal-item">
          <div class="signal-label">Fair Value Assumption</div>
          <div class="signal-value">The site treats the power-curve price as model fair value: {format_dollar(snapshot.curve_price)} today and {format_dollar(snapshot.curve_price_1y)} one year out.</div>
        </div>
        <div class="signal-item">
          <div class="signal-label">Data Source</div>
          <div class="signal-value">{snapshot.source_note}</div>
        </div>
      </div>
    </div>
    """


def score_to_color(score: float) -> str:
    if score < 20:
        return PLOT_COLORS[0]
    if score < 40:
        return PLOT_COLORS[1]
    if score < 60:
        return PLOT_COLORS[2]
    if score < 80:
        return PLOT_COLORS[3]
    return PLOT_COLORS[4]


def build_gauge(snapshot: Snapshot):
    fig, ax = plt.subplots(figsize=(5.4, 4.6), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-0.35, 1.25)
    ax.set_aspect("equal")
    ax.axis("off")

    radius = 1.0
    width = 0.24
    segment_edges = [0, 20, 40, 60, 80, 100]

    for left, right, zone in zip(segment_edges[:-1], segment_edges[1:], ZONE_META):
        theta1 = 180 - right * 1.8
        theta2 = 180 - left * 1.8
        wedge = Wedge((0, 0), radius, theta1, theta2, width=width, facecolor=zone["color"], edgecolor=BG, lw=3)
        ax.add_patch(wedge)

    for tick in [0, 20, 40, 60, 80, 100]:
        angle = np.radians(180 - tick * 1.8)
        label_radius = 1.12
        ax.text(
            label_radius * np.cos(angle),
            label_radius * np.sin(angle),
            str(tick),
            ha="center",
            va="center",
            fontsize=10,
            color=MUTED,
        )

    needle_angle = np.radians(180 - snapshot.heat_score * 1.8)
    ax.annotate(
        "",
        xy=(0.76 * np.cos(needle_angle), 0.76 * np.sin(needle_angle)),
        xytext=(0, 0),
        arrowprops=dict(arrowstyle="-|>", lw=2.6, color=INK, mutation_scale=18),
        zorder=6,
    )
    ax.add_artist(plt.Circle((0, 0), 0.08, color=INK, zorder=7))

    ax.text(0, 0.36, "Heat Score", ha="center", color=MUTED, fontsize=11, fontweight="bold")
    ax.text(0, 0.17, f"{snapshot.heat_score:.0f}", ha="center", color=snapshot.zone["color"], fontsize=34, fontweight="bold")
    ax.text(0, -0.05, snapshot.zone["label"], ha="center", color=INK, fontsize=18, fontweight="bold")
    ax.text(0, -0.18, relative_sentence(snapshot.heat_score), ha="center", color=MUTED, fontsize=10)
    ax.text(0, -0.29, f"Curve value today: {format_dollar(snapshot.curve_price)}", ha="center", color=MUTED, fontsize=9)

    fig.tight_layout(pad=0)
    return fig


def add_colored_price_line(ax, dates, values, scores, linewidth: float) -> None:
    for idx in range(1, len(dates)):
        ax.semilogy(
            [dates[idx - 1], dates[idx]],
            [values[idx - 1], values[idx]],
            color=score_to_color(float(scores[idx])),
            lw=linewidth,
            alpha=0.95,
            zorder=4,
        )


def build_market_chart(snapshot: Snapshot):
    fig = plt.figure(figsize=(12.6, 8.2), facecolor=BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.18)
    ax_price = fig.add_subplot(gs[0])
    ax_temp = fig.add_subplot(gs[1], sharex=ax_price)

    for ax in (ax_price, ax_temp):
        ax.set_facecolor(PANEL)
        for spine in ax.spines.values():
            spine.set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.grid(True, color=GRID, alpha=0.35, linewidth=0.6)

    df = snapshot.df.copy()
    dates = df["date"].tolist()
    prices = df["price"].astype(float).tolist()
    history_scores = snapshot.history_scores

    curve_dates = pd.date_range("2010-01-01", snapshot.as_of + timedelta(days=365), freq="7D")
    curve_prices = [power_law_price(date.to_pydatetime()) for date in curve_dates]

    ax_price.semilogy(curve_dates, curve_prices, color=INK, lw=1.8, alpha=0.9, zorder=2)
    add_colored_price_line(ax_price, dates, prices, history_scores, linewidth=1.15)
    ax_price.semilogy([snapshot.as_of], [snapshot.current_price], "o", color=snapshot.zone["color"], ms=7, zorder=6)

    ax_price.annotate(
        f"Spot {format_dollar(snapshot.current_price)}\nCurve {format_dollar(snapshot.curve_price)}",
        xy=(snapshot.as_of, snapshot.current_price),
        xytext=(-120, 30),
        textcoords="offset points",
        color=INK,
        fontsize=9,
        bbox=dict(boxstyle="square,pad=0.45", facecolor=BG, edgecolor=GRID, alpha=1.0),
        arrowprops=dict(arrowstyle="-", color=GRID),
    )

    ax_price.set_title("BTC price against the power curve", color=INK, fontsize=13, loc="left", pad=12)
    ax_price.set_ylabel("BTC / USD", color=MUTED, fontsize=10)
    ax_price.set_xlim(pd.Timestamp("2010-01-01"), pd.Timestamp(snapshot.as_of) + timedelta(days=150))
    ax_price.set_ylim(0.08, max(snapshot.current_price * 1.55, 200_000))
    ax_price.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda value, _: f"${value:,.0f}" if value >= 1 else f"${value:.2f}")
    )
    ax_price.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
    ax_price.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))

    for lower, upper, zone in zip([0, 20, 40, 60, 80], [20, 40, 60, 80, 100], ZONE_META):
        ax_temp.axhspan(lower, upper, color=zone["color"], alpha=0.18, zorder=1)

    ax_temp.plot(dates[-len(history_scores):], history_scores, color=INK, lw=1.4, zorder=3)
    ax_temp.plot([snapshot.as_of], [snapshot.heat_score], "o", color=snapshot.zone["color"], ms=7, zorder=4)
    ax_temp.axhline(50, color="#d5b36a", lw=1.0, alpha=0.8, linestyle="--", zorder=2)
    ax_temp.set_ylim(0, 100)
    ax_temp.set_ylabel("Heat Score", color=MUTED, fontsize=10)
    ax_temp.set_title("Historical market temperature", color=INK, fontsize=13, loc="left", pad=10)
    ax_temp.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
    ax_temp.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))

    fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.08, hspace=0.2)
    return fig


def render_dashboard(force_refresh: bool = False):
    snapshot = build_snapshot(force=force_refresh)
    hero_html = build_hero_html(snapshot)
    gauge_fig = build_gauge(snapshot)
    market_fig = build_market_chart(snapshot)
    narrative_html = build_narrative_html(snapshot)
    footer_md = (
        f"{STATIC_EXPLAINER}\n\n"
        f"`As of {snapshot.as_of.strftime('%Y-%m-%d %H:%M UTC')} | Data: {snapshot.source_note}`"
    )
    return hero_html, gauge_fig, market_fig, narrative_html, footer_md


def create_demo() -> gr.Blocks:
    with gr.Blocks(css=CSS, title="BTC Power Curve Temperature") as demo:
        hero = gr.HTML()

        with gr.Row(equal_height=True):
            gauge = gr.Plot(show_label=False, container=True)
            narrative = gr.HTML()

        with gr.Row():
            refresh_btn = gr.Button("Refresh Data", variant="primary")

        market_chart = gr.Plot(show_label=False, container=True)
        explainer = gr.Markdown()

        demo.load(fn=render_dashboard, outputs=[hero, gauge, market_chart, narrative, explainer])
        refresh_btn.click(
            fn=lambda: render_dashboard(force_refresh=True),
            outputs=[hero, gauge, market_chart, narrative, explainer],
        )

    return demo


demo = create_demo()


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
