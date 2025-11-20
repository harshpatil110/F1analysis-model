"""Telemetry extraction utilities.

Provides speed, throttle, brake, gear, RPM traces and comparisons.
"""
from __future__ import annotations

import pandas as pd


def get_fastest_lap_telemetry(session, driver_code: str) -> pd.DataFrame:
    """Return telemetry for fastest lap of specified driver code."""
    internal = None
    for d in session.drivers:
        if session.get_driver(d)["Abbreviation"] == driver_code:
            internal = d
            break
    if internal is None:
        raise ValueError("Driver code not found")
    laps = session.laps.pick_driver(internal).pick_fastest()
    tel = laps.get_telemetry().add_distance()
    return tel


def get_speed_trace(lap) -> pd.DataFrame:
    """Return distance vs speed for given lap object."""
    tel = lap.get_telemetry().add_distance()
    return tel[["Distance", "Speed"]].copy()


def get_brake_trace(lap) -> pd.DataFrame:
    tel = lap.get_telemetry().add_distance()
    return tel[["Distance", "Brake", "Throttle"]].copy()


def get_telemetry_comparison(session, driver1: str, driver2: str) -> pd.DataFrame:
    """Return merged telemetry for fastest laps of two drivers.

    Columns: Distance, Speed_driver1, Speed_driver2, Throttle_driver1, Throttle_driver2, Brake_driver1, Brake_driver2
    """
    tel1 = get_fastest_lap_telemetry(session, driver1)
    tel2 = get_fastest_lap_telemetry(session, driver2)
    # Merge on Distance with interpolation.
    merged = pd.merge_asof(
        tel1.sort_values("Distance"),
        tel2.sort_values("Distance"),
        on="Distance",
        direction="nearest",
        suffixes=(f"_{driver1}", f"_{driver2}"),
    )
    cols = ["Distance",
            f"Speed_{driver1}", f"Speed_{driver2}",
            f"Throttle_{driver1}", f"Throttle_{driver2}",
            f"Brake_{driver1}", f"Brake_{driver2}"]
    return merged[cols]
