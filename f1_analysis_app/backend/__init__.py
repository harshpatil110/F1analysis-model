"""Backend package for F1 Analysis App.

Provides data loading, analysis, telemetry, comparison, strategy, and ML utilities.
"""

from .data_loader import load_session, get_drivers, get_team_colors, list_events_for_year
from .analysis import (
    get_fastest_laps_per_driver,
    get_top_n_fastest_laps,
    compute_sector_averages,
    sector_deltas,
    rank_sector_performance,
    race_pace_metrics,
    build_degradation_model,
    extract_weather_data,
)
from .telemetry import (
    get_fastest_lap_telemetry,
    get_telemetry_comparison,
    get_speed_trace,
    get_brake_trace,
)
from .compare import (
    compare_fastest_laps,
    compare_sector_times,
    compare_race_pace,
    telemetry_overlay_data,
)
from .strategy import (
    detect_pit_stops,
    identify_stints,
    tyre_compound_usage,
    calculate_undercut_effect,
    stint_pace_table,
)
from .ml_model import predict_tyre_degradation, predict_qualifying_gap, predict_pit_window
