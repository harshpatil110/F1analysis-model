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
            # Load session into a cached resource and store in session_state so it
            # is not recreated on every rerun when widgets change.
            session = _cached_session(year, gp_name, session_type)
            st.session_state["f1_session"] = session
            st.session_state["session_info"] = (year, gp_name, session_type)
            # reset telemetry update flag so telemetry won't run until user triggers
            st.session_state["telemetry_updated"] = False
            st.success(f"Loaded {session_type} - {gp_name} {year}")
        except Exception as e:
            st.warning(f"Failed to load session: {e}")

team_colors = get_team_colors()


# Cached loader wrapper for FastF1 session (prevents reloading on widget change)
@st.cache_resource
def load_fastf1_session_cached(year: int, gp_name: str, session_type: str):
    return load_session(year, gp_name, session_type)


# Cached telemetry comparison so it doesn't recompute unless inputs change
@st.cache_data
def cached_telemetry_compare(year: int, gp_name: str, session_type: str, d1: str, d2: str):
    # Use the cached session loader here to ensure consistent session object
    session = load_fastf1_session_cached(year, gp_name, session_type)
    return telemetry_overlay_data(session, d1, d2)

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
    # Use the session stored in st.session_state to avoid reloading on widget change
    session = st.session_state.get("f1_session")
    if session is None:
        st.info("Load a session first from the sidebar and click 'Load Session'.")
    else:
        drivers = get_drivers(session)

        # Initialize session state keys for telemetry drivers and update flag
        if "telemetry_driver_1" not in st.session_state:
            st.session_state.telemetry_driver_1 = drivers[0] if drivers else ""
        if "telemetry_driver_2" not in st.session_state:
            st.session_state.telemetry_driver_2 = drivers[1] if len(drivers) > 1 else st.session_state.telemetry_driver_1
        if "telemetry_updated" not in st.session_state:
            st.session_state.telemetry_updated = False

        # Callbacks set a flag instead of causing heavy computations directly
        def _on_change_driver():
            st.session_state.telemetry_updated = True

        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Driver 1", options=drivers, key="telemetry_driver_1", on_change=_on_change_driver)
        with col2:
            st.selectbox("Driver 2", options=drivers, key="telemetry_driver_2", on_change=_on_change_driver)

        # Only compute telemetry when driver choices are changed and both drivers selected
        d1 = st.session_state.telemetry_driver_1
        d2 = st.session_state.telemetry_driver_2
        if d1 and d2 and d1 != d2 and st.session_state.telemetry_updated:
            with st.spinner("Loading telemetry…"):
                try:
                    # Use cached telemetry compare to avoid repeated heavy computation
                    tel_compare = cached_telemetry_compare(year, gp_name, session_type, d1, d2)
                    t_tabs = st.tabs(["Speed", "Throttle/Brake", "Matplotlib Overlay"])
                    with t_tabs[0]:
                        st.plotly_chart(plot_telemetry_speed_compare(tel_compare, d1, d2), use_container_width=True)
                    with t_tabs[1]:
                        st.plotly_chart(plot_throttle_brake(tel_compare, d1, d2), use_container_width=True)
                    with t_tabs[2]:
                        st.pyplot(matplotlib_speed_overlay(tel_compare, d1, d2))
                except Exception as e:
                    st.warning(f"Telemetry unavailable: {e}")
                finally:
                    # Reset the flag so telemetry doesn't recompute on unrelated reruns
                    st.session_state.telemetry_updated = False
        else:
            st.info("Select two distinct drivers and change a selection to load telemetry.")

        # --- Circuit Map Comparison (added feature) ---
        try:
            # Import the backend builder (kept separate from Streamlit to allow caching)
            from backend.circuit_map import build_circuit_comparison_map

            @st.cache_data
            def load_aligned_telemetry(session_key: str, d1: str, d2: str):
                # This helper simply proxies to the backend builder which returns a figure.
                # Named per requirements; kept small so caching keys are sensible.
                session = st.session_state.get("f1_session")
                if session is None:
                    return None
                # backend returns a full Plotly figure
                return build_circuit_comparison_map(session, d1, d2)

            @st.cache_data
            def circuit_map_cached(session_key: str, driver1: str, driver2: str):
                return load_aligned_telemetry(session_key, driver1, driver2)

            st.subheader("Circuit Map — Driver Performance Split")
            session = st.session_state.get("f1_session")
            if session is not None:
                # Build a stable session_key using the stored session_info when available.
                # Some FastF1 Session objects may not expose attributes like `year`.
                sess_info = st.session_state.get("session_info")
                if sess_info and len(sess_info) == 3:
                    year_val, gp_val, stype_val = sess_info
                    session_key = f"{gp_val}_{year_val}_{stype_val}"
                else:
                    # Fallback: use event name and session name/type safely
                    try:
                        event_name = session.event.get("EventName") if isinstance(session.event, dict) else getattr(session.event, 'EventName', None)
                    except Exception:
                        event_name = None
                    if not event_name:
                        # try other keys
                        try:
                            event_name = session.event.get('Name') if isinstance(session.event, dict) else getattr(session.event, 'Name', None)
                        except Exception:
                            event_name = 'session'
                    sess_type = getattr(session, 'name', None) or getattr(session, 'session_type', None) or 'session'
                    session_key = f"{event_name}_{sess_type}"
                selected_driver_1 = st.session_state.get("telemetry_driver_1", None)
                selected_driver_2 = st.session_state.get("telemetry_driver_2", None)
                if selected_driver_1 and selected_driver_2 and selected_driver_1 != selected_driver_2:
                    with st.spinner("Building circuit comparison map..."):
                        fig = circuit_map_cached(session_key=session_key, driver1=selected_driver_1, driver2=selected_driver_2)
                        if fig is None:
                            st.info("Circuit map unavailable for this session/drivers.")
                        else:
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Choose two distinct drivers to build the circuit comparison map.")
        except Exception as _err:
            # Non-fatal: show a small warning but do not break the page
            st.warning(f"Circuit map feature unavailable: {_err}")

        # --- Additional telemetry comparison plots (speed, throttle/brake, gear) ---
        try:
            from backend.telemetry import get_fastest_lap_telemetry
            import plotly.graph_objects as go

            @st.cache_data
            def cached_full_telemetry(year_: int, gp_: str, stype_: str, d1_: str, d2_: str):
                sess = load_fastf1_session_cached(year_, gp_, stype_)
                # get full telemetry for both drivers (fastest laps)
                t1 = get_fastest_lap_telemetry(sess, d1_)
                t2 = get_fastest_lap_telemetry(sess, d2_)
                # keep relevant columns and drop NaNs on Distance
                cols = ["Distance", "Speed", "Throttle", "Brake", "nGear", "DRS", "X", "Y"]
                for df in (t1, t2):
                    for c in cols:
                        if c not in df.columns:
                            df[c] = pd.NA
                t1s = t1[cols].sort_values("Distance").dropna(subset=["Distance"])
                t2s = t2[cols].sort_values("Distance").dropna(subset=["Distance"])    
                merged = pd.merge_asof(
                    t1s, t2s,
                    on="Distance",
                    direction="nearest",
                    suffixes=(f"_{d1_}", f"_{d2_}"),
                )
                return merged

            # Only show these comparison plots if drivers are selected
            selected_driver_1 = st.session_state.get("telemetry_driver_1")
            selected_driver_2 = st.session_state.get("telemetry_driver_2")
            if selected_driver_1 and selected_driver_2 and selected_driver_1 != selected_driver_2:
                with st.spinner("Loading telemetry comparisons..."):
                    try:
                        tel_full = cached_full_telemetry(year, gp_name, session_type, selected_driver_1, selected_driver_2)
                        if tel_full is None or tel_full.empty:
                            st.info("Telemetry comparison data unavailable.")
                        else:
                            # Speed comparison (reuse plotting helper)
                            try:
                                fig_speed = plot_telemetry_speed_compare(tel_full, selected_driver_1, selected_driver_2)
                                st.plotly_chart(fig_speed, use_container_width=True)
                            except Exception:
                                # fallback: build simple speed trace
                                fig_s = go.Figure()
                                fig_s.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full[f"Speed_{selected_driver_1}"], name=selected_driver_1))
                                fig_s.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full[f"Speed_{selected_driver_2}"], name=selected_driver_2))
                                fig_s.update_layout(title="Speed Comparison", xaxis_title="Distance (m)", yaxis_title="Speed (km/h)", template="plotly_dark")
                                st.plotly_chart(fig_s, use_container_width=True)

                            # Throttle / Brake comparison (reuse helper)
                            try:
                                fig_tb = plot_throttle_brake(tel_full, selected_driver_1, selected_driver_2)
                                st.plotly_chart(fig_tb, use_container_width=True)
                            except Exception:
                                fig_tb2 = go.Figure()
                                fig_tb2.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full[f"Throttle_{selected_driver_1}"], name=f"Throttle {selected_driver_1}"))
                                fig_tb2.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full[f"Brake_{selected_driver_1}"], name=f"Brake {selected_driver_1}"))
                                fig_tb2.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full[f"Throttle_{selected_driver_2}"], name=f"Throttle {selected_driver_2}"))
                                fig_tb2.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full[f"Brake_{selected_driver_2}"], name=f"Brake {selected_driver_2}"))
                                fig_tb2.update_layout(title="Throttle / Brake Comparison", xaxis_title="Distance (m)", template="plotly_dark")
                                st.plotly_chart(fig_tb2, use_container_width=True)

                            # Gear comparison: plot as step lines
                            try:
                                fig_gear = go.Figure()
                                fig_gear.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full.get(f"nGear_{selected_driver_1}", tel_full.get(f"nGear_{selected_driver_1}")), mode='lines', name=f"Gear {selected_driver_1}"))
                                fig_gear.add_trace(go.Scatter(x=tel_full["Distance"], y=tel_full.get(f"nGear_{selected_driver_2}", tel_full.get(f"nGear_{selected_driver_2}")), mode='lines', name=f"Gear {selected_driver_2}"))
                                fig_gear.update_layout(title="Gear Comparison", xaxis_title="Distance (m)", yaxis_title="Gear", template="plotly_dark")
                                st.plotly_chart(fig_gear, use_container_width=True)
                            except Exception:
                                pass
                    except Exception as e:
                        st.warning(f"Failed building comparison plots: {e}")
            else:
                st.info("Choose two distinct drivers to see detailed telemetry comparisons (speed/throttle/brake/gear).")
        except Exception as e:
            st.warning(f"Additional telemetry plots unavailable: {e}")

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
