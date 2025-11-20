"""Pit strategy and tyre analysis utilities."""
from __future__ import annotations

import pandas as pd

TYRE_COMPOUNDS_ORDER = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]


def detect_pit_stops(session) -> pd.DataFrame:
    """Detect pit stops from laps (simple heuristic: lap with PitOutTime or PitInTime)."""
    laps = session.laps.copy()
    pit_laps = laps[(laps["PitOutTime"].notna()) | (laps["PitInTime"].notna())]
    pit_laps["DriverCode"] = pit_laps["Driver"].apply(lambda d: session.get_driver(d)["Abbreviation"])
    return pit_laps[["DriverCode", "LapNumber", "PitOutTime", "PitInTime", "Compound"]]


def identify_stints(session) -> pd.DataFrame:
    """Identify stints based on tyre compound changes and pit stops."""
    laps = session.laps.copy()
    rows = []
    for drv in session.drivers:
        dlaps = laps.pick_driver(drv)
        if dlaps.empty:
            continue
        code = session.get_driver(drv)["Abbreviation"]
        current_compound = None
        stint_start = None
        for _, lap in dlaps.iterrows():
            comp = lap.get("Compound")
            if current_compound is None:
                current_compound = comp
                stint_start = lap["LapNumber"]
            elif comp != current_compound:
                rows.append({
                    "Driver": code,
                    "Compound": current_compound,
                    "StintStartLap": stint_start,
                    "StintEndLap": lap["LapNumber"] - 1,
                })
                current_compound = comp
                stint_start = lap["LapNumber"]
        # close last stint
        if current_compound is not None:
            rows.append({
                "Driver": code,
                "Compound": current_compound,
                "StintStartLap": stint_start,
                "StintEndLap": dlaps.iloc[-1]["LapNumber"],
            })
    return pd.DataFrame(rows)


def tyre_compound_usage(session) -> pd.DataFrame:
    """Count usage of compounds per driver."""
    laps = session.laps.copy()
    rows = []
    for drv in session.drivers:
        dlaps = laps.pick_driver(drv)
        code = session.get_driver(drv)["Abbreviation"]
        counts = dlaps["Compound"].value_counts()
        for comp, cnt in counts.items():
            rows.append({"Driver": code, "Compound": comp, "LapCount": cnt})
    return pd.DataFrame(rows)


def calculate_undercut_effect(session, undercut_driver: str, target_driver: str) -> float:
    """Estimate undercut effect as lap time delta after pit vs target driver (simplified)."""
    laps = session.laps.copy()
    # Map codes
    def internal(code):
        for d in session.drivers:
            if session.get_driver(d)["Abbreviation"] == code:
                return d
        return None
    u_int = internal(undercut_driver)
    t_int = internal(target_driver)
    if u_int is None or t_int is None:
        return float("nan")
    ulaps = laps.pick_driver(u_int)
    tlaps = laps.pick_driver(t_int)
    # Find first lap after pit for undercut driver
    pit_laps = ulaps[(ulaps["PitOutTime"].notna()) | (ulaps["PitInTime"].notna())]
    if pit_laps.empty:
        return float("nan")
    pit_lap_num = pit_laps.iloc[-1]["LapNumber"]
    post_lap = ulaps[ulaps["LapNumber"] == pit_lap_num + 1]
    if post_lap.empty:
        return float("nan")
    post_time = post_lap.iloc[0]["LapTime"].total_seconds()
    # Compare with target driver's same lap number if exists
    target_lap = tlaps[tlaps["LapNumber"] == pit_lap_num + 1]
    if target_lap.empty:
        return float("nan")
    target_time = target_lap.iloc[0]["LapTime"].total_seconds()
    return target_time - post_time  # positive means undercut faster


def stint_pace_table(session) -> pd.DataFrame:
    stints = identify_stints(session)
    laps = session.laps.copy()
    pace_rows = []
    for _, row in stints.iterrows():
        drv = row["Driver"]
        internal = None
        for d in session.drivers:
            if session.get_driver(d)["Abbreviation"] == drv:
                internal = d
                break
        if internal is None:
            continue
        dlaps = laps.pick_driver(internal)
        stint_laps = dlaps[(dlaps["LapNumber"] >= row["StintStartLap"]) & (dlaps["LapNumber"] <= row["StintEndLap"])]
        stint_laps = stint_laps[stint_laps["LapTime"].notna()]
        if stint_laps.empty:
            continue
        pace_rows.append({
            "Driver": drv,
            "Compound": row["Compound"],
            "StintStartLap": row["StintStartLap"],
            "StintEndLap": row["StintEndLap"],
            "MedianLapTime_s": stint_laps["LapTime"].dt.total_seconds().median(),
            "LapCount": len(stint_laps),
        })
    return pd.DataFrame(pace_rows)
