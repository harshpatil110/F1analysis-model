"""General helper utilities for formatting and conversions."""
from __future__ import annotations

import pandas as pd
import datetime as dt


def timedelta_to_ms(td) -> float:
    if pd.isna(td):
        return float("nan")
    return td.total_seconds() * 1000.0


def format_lap_time(td) -> str:
    if pd.isna(td):
        return "--"
    total_sec = td.total_seconds()
    minutes = int(total_sec // 60)
    seconds = total_sec % 60
    return f"{minutes}:{seconds:06.3f}"


def safe_get(d: dict, key: str, default=None):
    try:
        return d.get(key, default)
    except Exception:
        return default
