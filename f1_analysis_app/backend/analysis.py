"""Analytical computations for laps, sectors, pace, and weather.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

# Note: Functions expect a FastF1 Session object with laps loaded.


def get_fastest_laps_per_driver(session) -> pd.DataFrame:
    """Return fastest lap per driver.

    Columns: Driver, LapTime (timedelta), LapNumber
    """
    laps = session.laps.pick_quicklaps()
    fastest_rows = []
    for drv in session.drivers:
        dlaps = laps.pick_driver(drv)
        if len(dlaps) == 0:
            continue
        fastest = dlaps.sort_values("LapTime").iloc[0]
        code = session.get_driver(drv)["Abbreviation"]
        fastest_rows.append({
            "Driver": code,
            "LapTime": fastest["LapTime"],
            "LapNumber": fastest["LapNumber"],
        })
    return pd.DataFrame(fastest_rows).sort_values("LapTime")


def get_top_n_fastest_laps(session, n: int = 10) -> pd.DataFrame:
    """Return top N fastest laps across all drivers."""
    laps = session.laps.pick_quicklaps().copy()
    laps = laps.sort_values("LapTime").head(n)
    laps["Driver"] = laps["Driver"].apply(lambda x: session.get_driver(x)["Abbreviation"])
    return laps[["Driver", "LapNumber", "LapTime"]]


def compute_sector_averages(session) -> pd.DataFrame:
    """Average sector times per driver."""
    laps = session.laps.pick_quicklaps().copy()
    rows = []
    for drv in session.drivers:
        dlaps = laps.pick_driver(drv)
        if len(dlaps) == 0:
            continue
        code = session.get_driver(drv)["Abbreviation"]
        rows.append({
            "Driver": code,
            "Sector1": dlaps["Sector1Time"].mean(),
            "Sector2": dlaps["Sector2Time"].mean(),
            "Sector3": dlaps["Sector3Time"].mean(),
        })
    return pd.DataFrame(rows)


def sector_deltas(avg_sector_df: pd.DataFrame, reference_driver: str) -> pd.DataFrame:
    """Compute delta in sector time vs reference driver."""
    ref = avg_sector_df.set_index("Driver").loc[reference_driver]
    deltas = avg_sector_df.copy()
    for sec in ["Sector1", "Sector2", "Sector3"]:
        deltas[f"{sec}_Delta"] = deltas[sec] - ref[sec]
    return deltas


def rank_sector_performance(avg_sector_df: pd.DataFrame) -> pd.DataFrame:
    """Rank drivers per sector (1 = fastest)."""
    ranked = avg_sector_df.copy()
    for sec in ["Sector1", "Sector2", "Sector3"]:
        ranked[f"{sec}_Rank"] = ranked[sec].rank(method="min")
    return ranked.sort_values("Sector1")


def _filter_race_laps(session) -> pd.DataFrame:
    laps = session.laps.copy()
    # Remove laps with pit events or safety car / yellow flags (approx)
    laps = laps[~laps["PitOutTime"].notna()]
    laps = laps[~laps["PitInTime"].notna()]
    laps = laps[laps["LapTime"].notna()]
    return laps


def race_pace_metrics(session) -> pd.DataFrame:
    """Compute race pace metrics per driver: median lap time and stdev."""
    laps = _filter_race_laps(session)
    rows = []
    for drv in session.drivers:
        dlaps = laps.pick_driver(drv)
        if len(dlaps) < 2:
            continue
        code = session.get_driver(drv)["Abbreviation"]
        rows.append({
            "Driver": code,
            "MedianLap": dlaps["LapTime"].median(),
            "MeanLap": dlaps["LapTime"].mean(),
            "StdLap": dlaps["LapTime"].std(),
            "LapCount": len(dlaps),
        })
    return pd.DataFrame(rows).sort_values("MedianLap")


def build_degradation_model(session, driver_code: str) -> Tuple[LinearRegression, pd.DataFrame]:
    """Linear regression of lap time vs lap number for a driver (stint-based simplification)."""
    laps = _filter_race_laps(session)
    # Map code back to internal driver id
    internal = None
    for d in session.drivers:
        if session.get_driver(d)["Abbreviation"] == driver_code:
            internal = d
            break
    if internal is None:
        raise ValueError("Driver not found in session")
    dlaps = laps.pick_driver(internal)
    if len(dlaps) < 5:
        raise ValueError("Not enough laps for degradation model")
    X = dlaps[["LapNumber"]].values
    y = dlaps["LapTime"].dt.total_seconds().values
    model = LinearRegression()
    model.fit(X, y)
    preds = model.predict(X)
    out = pd.DataFrame({
        "LapNumber": dlaps["LapNumber"],
        "ActualLapTime_s": y,
        "PredictedLapTime_s": preds,
    })
    return model, out


def extract_weather_data(session) -> pd.DataFrame:
    """Return weather telemetry (track temp, air temp, humidity) over time."""
    weather = session.weather_data
    if weather is None or weather.empty:
        return pd.DataFrame(columns=["Time", "AirTemp", "TrackTemp", "Humidity"])
    return weather[["Time", "AirTemp", "TrackTemp", "Humidity"]].copy()
