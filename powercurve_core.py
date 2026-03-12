from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

GENESIS = datetime(2009, 1, 3)
A = -17.351
B = 5.84
CSV_PATH = os.path.join(os.path.dirname(__file__), "btc_historical.csv")
CACHE_TTL_SECONDS = 900

ZONE_META = [
    {
        "label": "Extreme Fear",
        "summary": "BTC is trading in an extreme fear zone versus its long-run curve.",
        "detail": "Historically this has been a washed-out part of the cycle where price is subdued relative to trend.",
        "color": "#3B82F6",
    },
    {
        "label": "Fear",
        "summary": "BTC is below its usual cycle pressure and still leaning fearful.",
        "detail": "This is weaker than average for Bitcoin history, but not a full capitulation zone.",
        "color": "#60A5FA",
    },
    {
        "label": "Neutral",
        "summary": "BTC is near the middle of its historical fear-and-greed range.",
        "detail": "The market is neither especially fearful nor especially greedy relative to the power curve.",
        "color": "#A3A3A3",
    },
    {
        "label": "Greed",
        "summary": "BTC is trading above trend and greed is building.",
        "detail": "This zone often appears when momentum is strong but the market is not yet at full euphoria.",
        "color": "#D97706",
    },
    {
        "label": "Extreme Greed",
        "summary": "BTC is in an extreme greed zone versus its historical power-curve position.",
        "detail": "This is where greed and speculative excess are most likely to dominate.",
        "color": "#DC2626",
    },
]

ZONE_BOUNDS = [20, 40, 60, 80]
_CACHE: dict[str, object] = {"timestamp": 0.0, "payload": None}


@dataclass
class Snapshot:
    as_of: datetime
    current_price: float
    curve_price: float
    curve_price_1y: float
    gap_pct: float
    curve_multiple: float
    years_ahead_value: float
    fg_score: float
    zone: dict
    source_note: str
    relative_sentence: str


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


def fetch_current_price() -> float | None:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return float(response.json()["bitcoin"]["usd"])
    except Exception:
        return None


def fg_score_from_distribution(sorted_years_ahead: np.ndarray, value: float) -> float:
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


def relative_sentence(score: float) -> str:
    if score >= 50:
        return f"Greedier than {score:.0f}% of Bitcoin's daily history."
    return f"More fearful than {100 - score:.0f}% of Bitcoin's daily history."


def curve_position_sentence(years_offset: float) -> str:
    magnitude = abs(years_offset)
    if years_offset >= 0:
        return f"{magnitude:.2f} years ahead of the curve."
    return f"{magnitude:.2f} years behind the curve."


def build_snapshot_payload(force: bool = False) -> dict:
    cache_age = time.time() - float(_CACHE["timestamp"])
    if not force and _CACHE["payload"] is not None and cache_age < CACHE_TTL_SECONDS:
        return _CACHE["payload"]  # type: ignore[return-value]

    df = load_historical_csv()
    now = utc_now()
    source_note = "Bundled historical CSV + live CoinGecko spot"

    current_price = fetch_current_price()
    if current_price is None:
        current_price = float(df.iloc[-1]["price"])
        now = pd.Timestamp(df.iloc[-1]["date"]).to_pydatetime()
        source_note = "Bundled historical CSV only (live spot unavailable)"

    history_years_ahead = np.array(
        [years_ahead(float(price), date.to_pydatetime()) for price, date in zip(df["price"], df["date"])],
        dtype=float,
    )
    history_years_ahead = history_years_ahead[np.isfinite(history_years_ahead)]
    sorted_years_ahead = np.sort(history_years_ahead)
    history_scores = np.array(
        [fg_score_from_distribution(sorted_years_ahead, value) for value in history_years_ahead],
        dtype=float,
    )

    curve_price = float(power_law_price(now))
    curve_price_1y = float(power_law_price(now + timedelta(days=365)))
    years_ahead_value = float(years_ahead(current_price, now))
    fg_score = fg_score_from_distribution(sorted_years_ahead, years_ahead_value)
    curve_multiple = current_price / curve_price
    gap_pct = (curve_multiple - 1) * 100
    zone = zone_for_score(fg_score)

    snapshot = Snapshot(
        as_of=now,
        current_price=current_price,
        curve_price=curve_price,
        curve_price_1y=curve_price_1y,
        gap_pct=gap_pct,
        curve_multiple=curve_multiple,
        years_ahead_value=years_ahead_value,
        fg_score=fg_score,
        zone=zone,
        source_note=source_note,
        relative_sentence=relative_sentence(fg_score),
    )

    history_dates = [date.strftime("%Y-%m-%d") for date in df["date"]]
    history_prices = [float(value) for value in df["price"]]
    history_scores_list = [float(value) for value in history_scores]
    curve_dates = pd.date_range("2010-01-01", now + timedelta(days=365), freq="7D")
    curve_series = {
        "dates": [date.strftime("%Y-%m-%d") for date in curve_dates],
        "prices": [float(power_law_price(date.to_pydatetime())) for date in curve_dates],
    }

    payload = {
        "snapshot": {
            **asdict(snapshot),
            "as_of": snapshot.as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "history": {
            "dates": history_dates,
            "prices": history_prices,
            "scores": history_scores_list,
        },
        "curve": curve_series,
        "meta": {
            "generated_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "genesis": GENESIS.strftime("%Y-%m-%d"),
            "model": {"a": A, "b": B},
        },
    }

    _CACHE["timestamp"] = time.time()
    _CACHE["payload"] = payload
    return payload
