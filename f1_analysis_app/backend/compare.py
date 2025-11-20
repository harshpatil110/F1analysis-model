"""Comparison utilities across drivers.
"""
from __future__ import annotations

import pandas as pd
from .analysis import get_fastest_laps_per_driver, compute_sector_averages, race_pace_metrics
from .telemetry import get_telemetry_comparison, get_fastest_lap_telemetry


def compare_fastest_laps(session) -> pd.DataFrame:
    return get_fastest_laps_per_driver(session)


def compare_sector_times(session, reference_driver: str) -> pd.DataFrame:
    avg = compute_sector_averages(session)
    # Add deltas vs reference
    ref_row = avg.set_index("Driver").loc[reference_driver]
    for sec in ["Sector1", "Sector2", "Sector3"]:
        avg[f"{sec}_Delta_vs_{reference_driver}"] = avg[sec] - ref_row[sec]
    return avg.sort_values(f"Sector1_Delta_vs_{reference_driver}")


def compare_race_pace(session) -> pd.DataFrame:
    return race_pace_metrics(session)


def telemetry_overlay_data(session, driver1: str, driver2: str) -> pd.DataFrame:
    return get_telemetry_comparison(session, driver1, driver2)
