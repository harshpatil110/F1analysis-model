"""Simple predictive models using scikit-learn.
"""
from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from typing import Tuple


def _driver_internal_id(session, driver_code: str):
    for d in session.drivers:
        if session.get_driver(d)["Abbreviation"] == driver_code:
            return d
    return None


def predict_tyre_degradation(session, driver_code: str) -> Tuple[LinearRegression, pd.DataFrame]:
    """Predict lap time increase over stint using linear regression."""
    internal = _driver_internal_id(session, driver_code)
    if internal is None:
        raise ValueError("Driver not found")
    laps = session.laps.pick_driver(internal)
    laps = laps[laps["LapTime"].notna()]
    if len(laps) < 5:
        raise ValueError("Insufficient laps for model")
    X = laps[["LapNumber"]].values
    y = laps["LapTime"].dt.total_seconds().values
    model = LinearRegression().fit(X, y)
    preds = model.predict(X)
    df = pd.DataFrame({"LapNumber": laps["LapNumber"], "Actual": y, "Predicted": preds})
    return model, df


def predict_qualifying_gap(session) -> Tuple[RandomForestRegressor, pd.DataFrame]:
    """Predict relative gap between drivers in qualifying using simple features (Sector sums)."""
    laps = session.laps.pick_quicklaps().copy()
    if laps.empty:
        raise ValueError("No laps loaded")
    # Build feature per lap
    laps["TotalSector"] = laps["Sector1Time"].dt.total_seconds() + laps["Sector2Time"].dt.total_seconds() + laps["Sector3Time"].dt.total_seconds()
    X = laps[["LapNumber", "TotalSector"]].values
    y = laps["LapTime"].dt.total_seconds().values
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    laps["PredLapTime_s"] = model.predict(X)
    return model, laps[["Driver", "LapNumber", "LapTime", "PredLapTime_s"]]


def predict_pit_window(session, driver_code: str) -> Tuple[LinearRegression, pd.DataFrame]:
    """Naive pit window prediction: model lap time vs lap number; infer lap when projected lap time exceeds threshold.
    Threshold heuristic: +2.0s over median of first 5 laps.
    """
    internal = _driver_internal_id(session, driver_code)
    laps = session.laps.pick_driver(internal)
    laps = laps[laps["LapTime"].notna()]
    if len(laps) < 8:
        raise ValueError("Not enough laps for pit window model")
    base = laps.head(5)["LapTime"].dt.total_seconds().median()
    threshold = base + 2.0
    X = laps[["LapNumber"]].values
    y = laps["LapTime"].dt.total_seconds().values
    model = LinearRegression().fit(X, y)
    projected = model.predict(X)
    laps["ProjectedLapTime_s"] = projected
    pit_lap_candidates = laps[laps["ProjectedLapTime_s"] >= threshold]
    pit_lap = pit_lap_candidates["LapNumber"].min() if not pit_lap_candidates.empty else None
    result = laps[["LapNumber", "LapTime", "ProjectedLapTime_s"]].copy()
    result["PitLapEstimate"] = pit_lap
    return model, result
