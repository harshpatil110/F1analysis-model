"""Data loading utilities for FastF1 sessions.

Responsible for fetching and caching F1 session data (Race, Quali, Practice),
listing drivers, and providing team colors.
"""
from __future__ import annotations

import fastf1
from fastf1 import utils as ff1_utils
from fastf1.core import Session
import pandas as pd
from typing import List, Dict, Optional

# Enable cache (user's local path). Use environment variable FASTF1_CACHE_DIR if set,
# otherwise default to a local .fastf1_cache directory inside the package folder.
# Create the directory before enabling the cache to avoid NotADirectoryError.
import os

_DEFAULT_CACHE = os.getenv("FASTF1_CACHE_DIR") or os.path.join(os.path.dirname(__file__), "..", ".fastf1_cache")
_DEFAULT_CACHE = os.path.abspath(_DEFAULT_CACHE)
os.makedirs(_DEFAULT_CACHE, exist_ok=True)
fastf1.Cache.enable_cache(_DEFAULT_CACHE)

SESSION_NAME_MAP = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Qualifying": "Qualifying",
    "Race": "Race",
}


def list_events_for_year(year: int) -> pd.DataFrame:
    """Return calendar events for a season using FastF1 schedule.

    Parameters
    ----------
    year: int
        Season year.
    Returns
    -------
    DataFrame with columns: RoundNumber, EventName, Country.
    """
    schedule = fastf1.get_event_schedule(year)
    return schedule[["RoundNumber", "EventName", "Country"]].copy()


def _normalize_session_type(session_type: str) -> str:
    st = session_type.strip().upper()
    if st in SESSION_NAME_MAP:
        return SESSION_NAME_MAP[st]
    # Accept already full names or fallback
    return session_type


def load_session(year: int, grand_prix: str, session_type: str) -> Session:
    """Load a FastF1 session with caching.

    Parameters
    ----------
    year: int
        Season year.
    grand_prix: str
        Grand Prix name (as in schedule EventName).
    session_type: str
        One of FP1, FP2, FP3, Qualifying, Race.
    Returns
    -------
    Loaded FastF1 Session object.
    """
    name = _normalize_session_type(session_type)
    session = fastf1.get_session(year, grand_prix, name)
    session.load(laps=True, telemetry=True, weather=True)
    return session


def get_drivers(session: Session) -> List[str]:
    """Return list of driver abbreviations participating in the session."""
    drivers = session.drivers
    # Return short codes (e.g., VER, LEC)
    return [session.get_driver(d)["Abbreviation"] for d in drivers]


def get_team_colors() -> Dict[str, str]:
    """Return mapping team name -> color hex string."""
    # fastf1's plotting module may expose TEAM_COLORS in some versions.
    # Be defensive: try multiple imports and fall back to an empty dict so plotting
    # uses default colors if TEAM_COLORS is unavailable.
    try:
        from fastf1.plotting import TEAM_COLORS
        return TEAM_COLORS.copy()
    except Exception:
        try:
            # older/newer versions might store colors differently
            import fastf1.plotting as ffplot
            tc = getattr(ffplot, "TEAM_COLORS", None) or getattr(ffplot, "team_colors", None)
            if isinstance(tc, dict):
                return tc.copy()
        except Exception:
            pass
    # Fallback: empty mapping -> plotly will choose default colors
    return {}


def get_driver_team_map(session: Session) -> Dict[str, str]:
    """Return mapping driver code -> team name."""
    mapping = {}
    for drv in session.drivers:
        info = session.get_driver(drv)
        mapping[info["Abbreviation"]] = info["TeamName"]
    return mapping


def safe_laps(session: Session) -> pd.DataFrame:
    """Return laps DataFrame with basic cleaning (dropping invalid laps)."""
    laps = session.laps.pick_quicklaps().copy()
    # Remove laps with NaN LapTime
    laps = laps[laps["LapTime"].notna()]
    return laps


def list_session_types() -> List[str]:
    return list(SESSION_NAME_MAP.keys())
