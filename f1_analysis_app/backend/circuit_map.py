"""Circuit map comparison utilities.

Provides function to build a Plotly figure that compares two drivers around the circuit
using their fastest lap telemetry. The function interpolates telemetry on a common
distance axis, computes delta (speed/time), splits the circuit into segments where
one driver is faster than the other, and returns a Plotly figure with separate traces
for each segment.

This module is intentionally independent of Streamlit (no st.* calls here) so it can
be cached on the frontend side using `st.cache_data`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import Tuple, Dict, Any


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _mix_color(hex_color: str, mix_with: Tuple[int, int, int], factor: float = 0.5) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    mr, mg, mb = mix_with
    r2 = int(r * (1 - factor) + mr * factor)
    g2 = int(g * (1 - factor) + mg * factor)
    b2 = int(b * (1 - factor) + mb * factor)
    return _rgb_to_hex((r2, g2, b2))


def _get_team_color_safe(session, driver_code: str) -> str:
    """Try to retrieve a team color for a driver using session metadata.
    Fallback to a default if not found.
    """
    try:
        drv_map = {session.get_driver(d)["Abbreviation"]: session.get_driver(d)["TeamName"] for d in session.drivers}
        team = drv_map.get(driver_code)
        if team:
            try:
                # fastf1.plotting.team_color may or may not exist; try defensively
                from fastf1.plotting import team_color
                return team_color(team)
            except Exception:
                # Some versions expose TEAM_COLORS dict
                try:
                    from fastf1.plotting import TEAM_COLORS
                    tc = TEAM_COLORS.get(team)
                    if tc:
                        return tc
                except Exception:
                    pass
    except Exception:
        pass
    # fallback colors
    return "#1f77b4"  # plotly default blue


def _extract_fastest_telemetry(session, driver_code: str) -> pd.DataFrame:
    """Return telemetry DataFrame for the fastest lap of the driver.
    The returned DataFrame contains at least: Distance, X, Y, Speed, Throttle, Brake, nGear, DRS
    """
    # Map driver_code to internal id
    internal = None
    for d in session.drivers:
        info = session.get_driver(d)
        if info["Abbreviation"] == driver_code:
            internal = d
            break
    if internal is None:
        raise ValueError(f"Driver {driver_code} not found in session")
    laps = session.laps.pick_driver(internal)
    if laps.empty:
        raise ValueError("No laps for driver")
    try:
        lap = laps.pick_fastest()
    except Exception:
        lap = laps.sort_values("LapTime").iloc[0]
    tel = lap.get_telemetry().add_distance()
    # Ensure required columns exist; if not, create with NaNs
    for col in ["X", "Y", "Distance", "Speed", "Throttle", "Brake", "nGear", "DRS"]:
        if col not in tel.columns:
            tel[col] = np.nan
    # Keep only relevant columns and drop NaNs in Distance
    tel = tel[["Distance", "X", "Y", "Speed", "Throttle", "Brake", "nGear", "DRS"]].dropna(subset=["Distance"]) 
    return tel.reset_index(drop=True)


def _interpolate_on_common_distance(t1: pd.DataFrame, t2: pd.DataFrame, n_points: int = 2000) -> Dict[str, np.ndarray]:
    """Interpolate both telemetry traces onto a common distance axis and return a dict of aligned arrays."""
    d1 = t1["Distance"].to_numpy()
    d2 = t2["Distance"].to_numpy()
    # Choose common max as the minimum of both max distances to avoid extrapolation
    max_common = min(d1.max(), d2.max())
    if max_common <= 0 or np.isnan(max_common):
        raise ValueError("Invalid distance in telemetry")
    common = np.linspace(0.0, float(max_common), n_points)

    def interp(arr, src_d):
        # numpy.interp requires increasing src_d; ensure sorted
        idx = np.argsort(src_d)
        src_d_sorted = src_d[idx]
        arr_sorted = arr[idx]
        return np.interp(common, src_d_sorted, arr_sorted)

    aligned = {
        "Distance": common,
        "X1": interp(t1["X"].to_numpy(), d1),
        "Y1": interp(t1["Y"].to_numpy(), d1),
        "Speed1": interp(t1["Speed"].to_numpy(), d1),
        "Throttle1": interp(t1["Throttle"].to_numpy(), d1),
        "Brake1": interp(t1["Brake"].to_numpy(), d1),
        "Gear1": interp(t1["nGear"].to_numpy(), d1),
        "DRS1": interp(t1["DRS"].to_numpy(), d1),
        "X2": interp(t2["X"].to_numpy(), d2),
        "Y2": interp(t2["Y"].to_numpy(), d2),
        "Speed2": interp(t2["Speed"].to_numpy(), d2),
        "Throttle2": interp(t2["Throttle"].to_numpy(), d2),
        "Brake2": interp(t2["Brake"].to_numpy(), d2),
        "Gear2": interp(t2["nGear"].to_numpy(), d2),
        "DRS2": interp(t2["DRS"].to_numpy(), d2),
    }
    return aligned


def _split_segments_by_delta(delta: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """Return an array of segment ids, where segment id increments whenever sign class changes.
    Classes: 1 => driver1 faster (delta>threshold), -1 => driver2 faster (delta<-threshold), 0 => equal
    """
    labels = np.zeros_like(delta, dtype=int)
    labels[delta > threshold] = 1
    labels[delta < -threshold] = -1
    # Now create segment ids
    seg_ids = np.zeros_like(labels)
    seg = 0
    prev = labels[0]
    seg_ids[0] = seg
    for i in range(1, len(labels)):
        if labels[i] != prev:
            seg += 1
            prev = labels[i]
        seg_ids[i] = seg
    return seg_ids, labels


def build_circuit_comparison_map(session, driver1: str, driver2: str) -> go.Figure:
    """Build a Plotly figure that overlays the circuit and colors segments by who is faster.

    Returns a `go.Figure`.
    """
    try:
        t1 = _extract_fastest_telemetry(session, driver1)
        t2 = _extract_fastest_telemetry(session, driver2)
    except Exception as e:
        # Return an empty figure with error text
        fig = go.Figure()
        fig.add_annotation(text=f"Telemetry unavailable: {e}", showarrow=False)
        return fig

    aligned = _interpolate_on_common_distance(t1, t2)
    dist = aligned["Distance"]
    speed1 = aligned["Speed1"]
    speed2 = aligned["Speed2"]

    delta_speed = speed1 - speed2

    seg_ids, labels = _split_segments_by_delta(delta_speed, threshold=0.1)

    # Get colors
    c1 = _get_team_color_safe(session, driver1)
    c2 = _get_team_color_safe(session, driver2)
    # If same color, mix to create two contrasting shades
    if c1.lower() == c2.lower():
        # mix with white/dark to create contrast
        c1 = _mix_color(c1, (40, 40, 40), 0.25)
        c2 = _mix_color(c2, (220, 220, 220), 0.35)

    fig = go.Figure()

    # Build hover labels and traces per segment
    for seg in np.unique(seg_ids):
        idx = np.where(seg_ids == seg)[0]
        if idx.size == 0:
            continue
        seg_x = aligned["X1"][idx]
        seg_y = aligned["Y1"][idx]
        seg_speed1 = speed1[idx]
        seg_speed2 = speed2[idx]
        seg_dist = dist[idx]
        seg_thr1 = aligned["Throttle1"][idx]
        seg_thr2 = aligned["Throttle2"][idx]
        seg_br1 = aligned["Brake1"][idx]
        seg_br2 = aligned["Brake2"][idx]
        seg_gear1 = aligned["Gear1"][idx]
        seg_gear2 = aligned["Gear2"][idx]
        seg_drs1 = aligned["DRS1"][idx]
        seg_drs2 = aligned["DRS2"][idx]
        seg_delta = delta_speed[idx]
        # Determine color based on average delta in segment
        mean_delta = np.nanmean(seg_delta)
        if mean_delta > 0.1:
            color = c1
            label = f"{driver1} faster"
        elif mean_delta < -0.1:
            color = c2
            label = f"{driver2} faster"
        else:
            color = "lightgrey"
            label = "Equal pace"

        hover_texts = []
        for i in range(len(seg_dist)):
            hover_texts.append(
                f"Distance: {seg_dist[i]:.1f} m<br>"
                f"{driver1} Speed: {seg_speed1[i]:.1f} km/h<br>"
                f"{driver2} Speed: {seg_speed2[i]:.1f} km/h<br>"
                f"Delta Speed: {seg_delta[i]:+.2f} km/h<br>"
                f"{driver1} Gear: {int(seg_gear1[i]) if not np.isnan(seg_gear1[i]) else '-'}<br>"
                f"{driver2} Gear: {int(seg_gear2[i]) if not np.isnan(seg_gear2[i]) else '-'}<br>"
                f"{driver1} Throttle: {seg_thr1[i]:.2f}<br>"
                f"{driver2} Throttle: {seg_thr2[i]:.2f}<br>"
                f"{driver1} Brake: {seg_br1[i]:.2f}<br>"
                f"{driver2} Brake: {seg_br2[i]:.2f}<br>"
                f"{driver1} DRS: {int(seg_drs1[i]) if not np.isnan(seg_drs1[i]) else 0}<br>"
                f"{driver2} DRS: {int(seg_drs2[i]) if not np.isnan(seg_drs2[i]) else 0}"
            )

        fig.add_trace(
            go.Scatter(
                x=seg_x,
                y=seg_y,
                mode="lines",
                line=dict(color=color, width=4),
                name=label,
                hoverinfo="text",
                text=hover_texts,
                showlegend=False,
            )
        )

    # Add a thin grey background trace of the circuit (average of both for context)
    avg_x = 0.5 * (aligned["X1"] + aligned["X2"])
    avg_y = 0.5 * (aligned["Y1"] + aligned["Y2"])
    fig.add_trace(
        go.Scatter(
            x=avg_x,
            y=avg_y,
            mode="lines",
            line=dict(color="#444444", width=1),
            name="Circuit",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.update_layout(
        title=f"Circuit Map — {driver1} vs {driver2} Performance Comparison",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        template="plotly_dark",
    )

    return fig
