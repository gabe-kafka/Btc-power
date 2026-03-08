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
from matplotlib import pyplot as plt
from matplotlib.patches import Wedge

matplotlib.use("Agg")


GENESIS = datetime(2009, 1, 3)
A = -17.351
B = 5.84
CSV_PATH = os.path.join(os.path.dirname(__file__), "btc_historical.csv")
CACHE_TTL_SECONDS = 900

BG = "#07131c"
PANEL = "#0e2231"
INK = "#f5efe3"
MUTED = "#9db2c3"
GRID = "#204056"

ZONE_META = [
    {
        "label": "Freezing",
        "summary": "BTC is trading in a cold, fear-heavy zone versus its long-run curve.",
        "detail": "Historically this has been a washed-out part of the cycle where price is subdued relative to trend.",
        "color": "#6ec5ff",
    },
    {
        "label": "Cold",
        "summary": "BTC is below its usual cycle heat and still relatively calm.",
        "detail": "This is cooler than average for Bitcoin history, but not a deep capitulation zone.",
        "color": "#42a4d9",
    },
    {
        "label": "Balanced",
        "summary": "BTC is near the middle of its historical temperature range.",
        "detail": "The market is neither especially hot nor especially cold relative to the power curve.",
        "color": "#f0c36c",
    },
    {
        "label": "Warm",
        "summary": "BTC is trading above trend and sentiment is heating up.",
        "detail": "This zone often appears when momentum is strong but the market is not yet at full euphoria.",
        "color": "#ef8d49",
    },
    {
        "label": "Overheated",
        "summary": "BTC is running very hot versus its historical power-curve position.",
        "detail": "This is where greed and speculative excess are most likely to dominate.",
        "color": "#ff5d4d",
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

CSS = """
:root {
  --bg: #07131c;
  --panel: rgba(14, 34, 49, 0.86);
  --panel-strong: rgba(8, 20, 29, 0.94);
  --line: rgba(121, 164, 191, 0.22);
  --ink: #f5efe3;
  --muted: #9db2c3;
}

body {
  background:
    radial-gradient(circle at top left, rgba(110, 197, 255, 0.14), transparent 28%),
    radial-gradient(circle at top right, rgba(255, 93, 77, 0.14), transparent 25%),
    linear-gradient(180deg, #07131c 0%, #081723 100%);
}

.gradio-container {
  background: transparent !important;
  color: var(--ink) !important;
  max-width: 1220px !important;
}

footer {
  display: none !important;
}

.app-shell {
  margin: 16px 0 8px;
}

.hero-card,
.narrative-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 26px;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(16px);
}

.hero-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.eyebrow {
  color: #8ec7ea;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.hero-title {
  font-size: clamp(34px, 5vw, 54px);
  line-height: 0.98;
  font-weight: 700;
  max-width: 760px;
  margin: 0;
}

.hero-copy {
  color: var(--muted);
  font-size: 16px;
  line-height: 1.55;
  max-width: 760px;
  margin: 14px 0 0;
}

.stamp {
  border: 1px solid var(--line);
  background: var(--panel-strong);
  color: var(--ink);
  border-radius: 999px;
  padding: 10px 14px;
  white-space: nowrap;
  font-size: 12px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-top: 22px;
}

.metric {
  background: rgba(5, 14, 21, 0.62);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 16px;
}

.metric-label {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.metric-value {
  color: var(--ink);
  font-size: 26px;
  font-weight: 700;
  margin-top: 10px;
}

.metric-note {
  color: var(--muted);
  font-size: 13px;
  margin-top: 8px;
  line-height: 1.45;
}

.narrative-kicker {
  color: #8ec7ea;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.narrative-title {
  font-size: 30px;
  line-height: 1.04;
  margin: 10px 0 14px;
}

.narrative-copy {
  color: var(--muted);
  font-size: 15px;
  line-height: 1.6;
  margin: 0 0 18px;
}

.signal-list {
  display: grid;
  gap: 12px;
}

.signal-item {
  display: grid;
  gap: 4px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}

.signal-label {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.signal-value {
  color: var(--ink);
  font-size: 18px;
  font-weight: 700;
}

@media (max-width: 980px) {
  .hero-top {
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
"""


@dataclass
class Snapshot:
    as_of: datetime
    current_price: float
    curve_price: float
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
    years_ahead_value = float(years_ahead(current_price, now))
    heat_score = heat_score_from_distribution(sorted_years_ahead, years_ahead_value)
    curve_multiple = current_price / curve_price
    gap_pct = (curve_multiple - 1) * 100

    snapshot = Snapshot(
        as_of=now,
        current_price=current_price,
        curve_price=curve_price,
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
    headline = f"BTC is <span style='color:{zone['color']}'>{zone['label']}</span> versus its power curve."
    return f"""
    <div class="app-shell">
      <div class="hero-card">
        <div class="eyebrow">Bitcoin Power Curve Temperature</div>
        <div class="hero-top">
          <div>
            <h1 class="hero-title">{headline}</h1>
            <p class="hero-copy">{zone['summary']} {relative_sentence(snapshot.heat_score)} {zone['detail']}</p>
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
            <div class="metric-label">Curve Value</div>
            <div class="metric-value">{format_dollar(snapshot.curve_price)}</div>
            <div class="metric-note">Model price on the long-run power curve.</div>
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
      <div class="narrative-kicker">What This Means</div>
      <div class="narrative-title">A simple answer for visitors: is the market hot or cold?</div>
      <p class="narrative-copy">
        Bitcoin is currently trading {abs(snapshot.gap_pct):.1f}% {premium_text} the model curve.
        That places the market in the <span style="color:{snapshot.zone['color']}; font-weight:700;">{snapshot.zone['label']}</span> zone
        and makes today's reading {relative_sentence(snapshot.heat_score).lower()}
      </p>
      <div class="signal-list">
        <div class="signal-item">
          <div class="signal-label">For normal users</div>
          <div class="signal-value">{snapshot.zone['summary']}</div>
        </div>
        <div class="signal-item">
          <div class="signal-label">Model read</div>
          <div class="signal-value">{snapshot.years_ahead_value:.2f} years ahead of the curve</div>
        </div>
        <div class="signal-item">
          <div class="signal-label">Data source</div>
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
        bbox=dict(boxstyle="round,pad=0.5", facecolor=BG, edgecolor=GRID, alpha=0.9),
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
            refresh_btn = gr.Button("Refresh market data", variant="primary")

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
