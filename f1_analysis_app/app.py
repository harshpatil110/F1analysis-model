"""Streamlit Frontend for F1 Analysis Dashboard."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import os

import fastf1
# Robust cache initialization: use env FASTF1_CACHE_DIR if set, else local project cache.
# Create directory if missing to avoid NotADirectoryError.
CACHE_DIR = os.getenv("FASTF1_CACHE_DIR", os.path.join(os.path.dirname(__file__), ".fastf1_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


from backend import (
    load_session,
    list_events_for_year,
    get_drivers,
    get_team_colors,
    get_fastest_laps_per_driver,
    get_top_n_fastest_laps,
    compute_sector_averages,
    race_pace_metrics,
    build_degradation_model,
    extract_weather_data,
    telemetry_overlay_data,
    detect_pit_stops,
    identify_stints,
    tyre_compound_usage,
    calculate_undercut_effect,
    stint_pace_table,
)
from utils.plotting import (
    plot_fastest_laps,
    plot_sector_averages,
    plot_race_pace,
    plot_degradation,
    plot_weather,
    plot_telemetry_speed_compare,
    plot_throttle_brake,
    plot_tyre_stints,
    matplotlib_speed_overlay,
)
from utils.helpers import format_lap_time

st.set_page_config(page_title="F1 Analysis Dashboard", layout="wide")

# --- Sidebar Controls ---
st.title("F1 Analysis Dashboard")

with st.sidebar:
    st.header("Session Selector")
    year = st.number_input("Year", min_value=2018, max_value=2030, value=2024, step=1)
    events_df = list_events_for_year(year)
    gp_name = st.selectbox("Grand Prix", options=events_df["EventName"].tolist())
    session_type = st.selectbox("Session Type", options=["FP1", "FP2", "FP3", "Qualifying", "Race"])
    load_btn = st.button("Load Session")

@st.cache_resource(show_spinner=False)
def _cached_session(year: int, gp_name: str, session_type: str):
    return load_session(year, gp_name, session_type)

session = None
if load_btn:
    with st.spinner("Loading session data..."):
        try:
            session = _cached_session(year, gp_name, session_type)
            st.success(f"Loaded {session_type} - {gp_name} {year}")
        except Exception as e:
            st.warning(f"Failed to load session: {e}")

team_colors = get_team_colors()

# Page tabs
pages = st.tabs(["Home", "Driver Analysis", "Telemetry", "Strategy"])

# --- HOME PAGE ---
with pages[0]:
    st.subheader("Welcome")
    st.markdown("""Select a season, Grand Prix, and session from the sidebar and click Load Session.\nUse the tabs above to explore driver performance, telemetry, and race strategy.""")
    if session is not None:
        st.write("Session Info:")
        st.write({"Event": gp_name, "Type": session_type, "Year": year})
        weather_df = extract_weather_data(session)
        if not weather_df.empty:
            st.plotly_chart(plot_weather(weather_df), use_container_width=True)
        else:
            st.info("No weather data available.")

# --- DRIVER ANALYSIS PAGE ---
with pages[1]:
    st.subheader("Driver Analysis")
    if session is None:
        st.info("Load a session first.")
    else:
        drivers = get_drivers(session)
        fastest_df = get_fastest_laps_per_driver(session)
        st.caption("Fastest Lap per Driver")
        st.dataframe(fastest_df.assign(LapTimeStr=fastest_df["LapTime"].apply(format_lap_time)), use_container_width=True)
        st.plotly_chart(plot_fastest_laps(fastest_df, team_colors), use_container_width=True)

        st.markdown("### Sector Analysis")
        sector_avg = compute_sector_averages(session)
        st.dataframe(sector_avg.assign(
            S1=sector_avg["Sector1"].apply(format_lap_time),
            S2=sector_avg["Sector2"].apply(format_lap_time),
            S3=sector_avg["Sector3"].apply(format_lap_time),
        ))
        st.plotly_chart(plot_sector_averages(sector_avg, team_colors), use_container_width=True)

        st.markdown("### Race Pace")
        pace_df = race_pace_metrics(session)
        st.dataframe(pace_df.assign(MedianLapStr=pace_df["MedianLap"].apply(format_lap_time)))
        st.plotly_chart(plot_race_pace(pace_df, team_colors), use_container_width=True)

        st.markdown("### Degradation Model")
        driver_for_model = st.selectbox("Select Driver for Degradation", options=drivers)
        if driver_for_model:
            try:
                model, model_df = build_degradation_model(session, driver_for_model)
                st.plotly_chart(plot_degradation(model_df, driver_for_model), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not build degradation model: {e}")

# --- TELEMETRY PAGE ---
with pages[2]:
    st.subheader("Telemetry Comparison")
    if session is None:
        st.info("Load a session first.")
    else:
        drivers = get_drivers(session)
        col1, col2 = st.columns(2)
        with col1:
            d1 = st.selectbox("Driver 1", options=drivers)
        with col2:
            d2 = st.selectbox("Driver 2", options=drivers, index=min(1, len(drivers)-1))
        if d1 and d2 and d1 != d2:
            try:
                tel_compare = telemetry_overlay_data(session, d1, d2)
                t_tabs = st.tabs(["Speed", "Throttle/Brake", "Matplotlib Overlay"])
                with t_tabs[0]:
                    st.plotly_chart(plot_telemetry_speed_compare(tel_compare, d1, d2), use_container_width=True)
                with t_tabs[1]:
                    st.plotly_chart(plot_throttle_brake(tel_compare, d1, d2), use_container_width=True)
                with t_tabs[2]:
                    st.pyplot(matplotlib_speed_overlay(tel_compare, d1, d2))
            except Exception as e:
                st.warning(f"Telemetry unavailable: {e}")
        else:
            st.info("Select two distinct drivers.")

# --- STRATEGY PAGE ---
with pages[3]:
    st.subheader("Strategy Analysis")
    if session is None or session_type != "Race":
        st.info("Load a Race session for strategy analysis.")
    else:
        st.markdown("### Pit Stops")
        pit_df = detect_pit_stops(session)
        st.dataframe(pit_df)

        st.markdown("### Tyre Stints")
        stints_df = identify_stints(session)
        st.dataframe(stints_df)
        if not stints_df.empty:
            st.plotly_chart(plot_tyre_stints(stints_df), use_container_width=True)

        st.markdown("### Tyre Usage Counts")
        usage_df = tyre_compound_usage(session)
        st.dataframe(usage_df)

        st.markdown("### Stint Pace Table")
        pace_stint_df = stint_pace_table(session)
        st.dataframe(pace_stint_df)

        st.markdown("### Undercut Calculator")
        drivers = get_drivers(session)
        u_col1, u_col2 = st.columns(2)
        with u_col1:
            undercut_driver = st.selectbox("Undercut Driver", options=drivers)
        with u_col2:
            target_driver = st.selectbox("Target Driver", options=drivers, index=min(1, len(drivers)-1))
        if undercut_driver != target_driver:
            effect = calculate_undercut_effect(session, undercut_driver, target_driver)
            if pd.isna(effect):
                st.info("Insufficient data for undercut calculation.")
            else:
                st.metric(label="Estimated Undercut Gain (s)", value=f"{effect:.3f}")
        else:
            st.info("Choose two different drivers for undercut calculation.")

st.caption("Data powered by FastF1. Visualization with Plotly & Matplotlib.")
