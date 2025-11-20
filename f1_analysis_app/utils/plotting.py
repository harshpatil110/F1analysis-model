"""Unified plotting helpers using Plotly and Matplotlib.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from typing import List, Dict


# Plotly Helpers

def plot_fastest_laps(df_fast: pd.DataFrame, team_colors: Dict[str, str]):
    fig = px.bar(
        df_fast,
        x="Driver",
        y=df_fast["LapTime"].dt.total_seconds(),
        color="Driver",
        title="Fastest Lap per Driver",
        color_discrete_map=team_colors,
        labels={"y": "Lap Time (s)"},
    )
    return fig


def plot_sector_averages(avg_df: pd.DataFrame, team_colors: Dict[str, str]):
    melted = avg_df.melt(id_vars="Driver", value_vars=["Sector1", "Sector2", "Sector3"], var_name="Sector", value_name="Time")
    melted["Time_s"] = melted["Time"].dt.total_seconds()
    fig = px.bar(
        melted,
        x="Driver",
        y="Time_s",
        color="Sector",
        barmode="group",
        title="Average Sector Times",
        labels={"Time_s": "Time (s)"},
    )
    return fig


def plot_race_pace(pace_df: pd.DataFrame, team_colors: Dict[str, str]):
    tmp = pace_df.copy()
    tmp["MedianLap_s"] = tmp["MedianLap"].dt.total_seconds()
    fig = px.scatter(
        tmp,
        x="Driver",
        y="MedianLap_s",
        color="Driver",
        color_discrete_map=team_colors,
        size="LapCount",
        title="Race Pace (Median Lap Time)",
        labels={"MedianLap_s": "Median Lap (s)"},
    )
    return fig


def plot_degradation(model_df: pd.DataFrame, driver_code: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=model_df["LapNumber"], y=model_df["ActualLapTime_s"], mode="markers", name="Actual"))
    fig.add_trace(go.Scatter(x=model_df["LapNumber"], y=model_df["PredictedLapTime_s"], mode="lines", name="Predicted"))
    fig.update_layout(title=f"Lap Time Degradation - {driver_code}", xaxis_title="Lap", yaxis_title="Lap Time (s)")
    return fig


def plot_weather(weather_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weather_df["Time"], y=weather_df["TrackTemp"], name="TrackTemp"))
    fig.add_trace(go.Scatter(x=weather_df["Time"], y=weather_df["AirTemp"], name="AirTemp"))
    fig.add_trace(go.Scatter(x=weather_df["Time"], y=weather_df["Humidity"], name="Humidity"))
    fig.update_layout(title="Weather Over Time")
    return fig


def plot_telemetry_speed_compare(tel_compare: pd.DataFrame, d1: str, d2: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tel_compare["Distance"], y=tel_compare[f"Speed_{d1}"], name=f"Speed {d1}"))
    fig.add_trace(go.Scatter(x=tel_compare["Distance"], y=tel_compare[f"Speed_{d2}"], name=f"Speed {d2}"))
    fig.update_layout(title="Speed Trace Comparison", xaxis_title="Distance (m)", yaxis_title="Speed (km/h)")
    return fig


def plot_throttle_brake(tel_compare: pd.DataFrame, d1: str, d2: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tel_compare["Distance"], y=tel_compare[f"Throttle_{d1}"], name=f"Throttle {d1}"))
    fig.add_trace(go.Scatter(x=tel_compare["Distance"], y=tel_compare[f"Brake_{d1}"], name=f"Brake {d1}"))
    fig.add_trace(go.Scatter(x=tel_compare["Distance"], y=tel_compare[f"Throttle_{d2}"], name=f"Throttle {d2}"))
    fig.add_trace(go.Scatter(x=tel_compare["Distance"], y=tel_compare[f"Brake_{d2}"], name=f"Brake {d2}"))
    fig.update_layout(title="Throttle/Brake Comparison")
    return fig


def plot_tyre_stints(stints_df: pd.DataFrame):
    fig = go.Figure()
    for _, row in stints_df.iterrows():
        fig.add_trace(go.Bar(
            x=[row["StintEndLap"] - row["StintStartLap"] + 1],
            y=[row["Driver"]],
            name=f"{row['Driver']} {row['Compound']}",
            orientation="h",
            hovertext=f"{row['Compound']} Laps {row['StintStartLap']}-{row['StintEndLap']}",
        ))
    fig.update_layout(title="Tyre Stints", barmode="stack", xaxis_title="Lap Count")
    return fig

# Matplotlib overlay example

def matplotlib_speed_overlay(tel_compare: pd.DataFrame, d1: str, d2: str):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(tel_compare["Distance"], tel_compare[f"Speed_{d1}"], label=d1)
    ax.plot(tel_compare["Distance"], tel_compare[f"Speed_{d2}"], label=d2)
    ax.set_title("Speed Overlay")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.legend()
    fig.tight_layout()
    return fig
