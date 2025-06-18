import streamlit as st
import pandas as pd
import gpxpy
import numpy as np
import folium
import plotly.graph_objects as go
from datetime import timedelta
from streamlit_folium import st_folium
import os
import uuid
from scipy.ndimage import uniform_filter1d
from utils.user_paths import get_current_user

# === Datei speichern ===
def save_uploaded_file(user, uploaded_file):
    gpx_dir = os.path.join("fit_samples", user, "gpx")
    os.makedirs(gpx_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.gpx"
    path = os.path.join(gpx_dir, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

# === GPX-Datei einlesen ===
def parse_gpx(file):
    gpx = gpxpy.parse(file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append({
                    "lat": p.latitude,
                    "lon": p.longitude,
                    "elevation": p.elevation or 0.0
                })
    df = pd.DataFrame(points)
    return df.dropna().reset_index(drop=True)

# === Distanzberechnung (Haversine) ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = phi2 - phi1
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# === Strecke und Höhenmeter berechnen ===
def calculate_segments(df):
    distances = [0]
    for i in range(1, len(df)):
        d = haversine(df.lat[i - 1], df.lon[i - 1], df.lat[i], df.lon[i])
        distances.append(d)
    df["distance"] = distances
    df["cum_dist_km"] = np.cumsum(df["distance"]) / 1000

    # Glättung der Höhe zur Reduktion von Ausreißern
    df["elevation"] = uniform_filter1d(df["elevation"], size=25)
    df["delta_h"] = df["elevation"].diff().fillna(0)
    return df

def estimate_total_time(df, power, total_weight):
    total_km = df["cum_dist_km"].iloc[-1]
    total_hm = df["delta_h"].clip(lower=0).sum()

    # === Referenzfahrt
    ref_power = 236
    ref_time_sec = 3 * 3600 + 43 * 60
    ref_km = 110.5
    ref_hm = 2015
    ref_weight = 85

    power_ratio = ref_power / power
    weight_penalty = total_weight / ref_weight
    dist_ratio = total_km / ref_km
    hm_ratio = total_hm / ref_hm

    # === Final angepasst:
    time_sec = ref_time_sec * power_ratio**1.05 * weight_penalty**1.1 * dist_ratio**1.0 * hm_ratio**1.1
    return time_sec


# === Streamlit UI ===
def render():
    user = get_current_user()
    st.title("🗻 Streckensimulator")

    uploaded_file = st.file_uploader("GPX-Datei hochladen", type="gpx")
    if not uploaded_file:
        return

    file_path = save_uploaded_file(user, uploaded_file)
    df = calculate_segments(parse_gpx(open(file_path, "r")))
    total_km = df["cum_dist_km"].iloc[-1]
    total_hm = df["delta_h"].clip(lower=0).sum()

    st.success(f"{total_km:.1f} km – {total_hm:.0f} Höhenmeter")

    c1, c2 = st.columns(2)
    weight = c1.number_input("Fahrergewicht (kg)", 40, 120, 75)
    bike_weight = c2.number_input("Radgewicht (kg)", 5, 20, 8)
    total_weight = weight + bike_weight

    power = st.slider("Durchschnittsleistung (Watt)", 100, 400, 220, step=5)

    total_time = estimate_total_time(df, power, total_weight)
    avg_speed = total_km / (total_time / 3600)

    st.success(f"Geschätzte Fahrzeit: {timedelta(seconds=int(total_time))}")
    st.info(f"Ø Geschwindigkeit: {avg_speed:.1f} km/h")

    # === Höhenprofil-Plot ===
    st.subheader("Höhenprofil")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["cum_dist_km"], y=df["elevation"],
        mode="lines", line=dict(color="royalblue")
    ))
    fig.update_layout(
        xaxis_title="Distanz (km)", yaxis_title="Höhe (m)", height=300
    )
    st.plotly_chart(fig, use_container_width=True)

    # === Streckenkarte ===
    st.subheader("Streckenkarte")
    midpoint = df.iloc[len(df)//2]
    m = folium.Map(location=[midpoint.lat, midpoint.lon], zoom_start=12)
    folium.PolyLine(list(zip(df.lat, df.lon)), color="blue").add_to(m)
    st_folium(m, height=360, use_container_width=True)