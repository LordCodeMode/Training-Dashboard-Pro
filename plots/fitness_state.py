import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.user_paths import get_user_cache_path, get_current_user

def fetch_training_load_from_cache(user):
    path = get_user_cache_path("training_load.csv")
    try:
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        return df.rename(columns={"date": "start_time"})
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des Training Load Cache: {e}")
        return pd.DataFrame()

def fetch_recent_activity_metrics(user):
    path = get_user_cache_path("efficiency_factors.csv")
    try:
        df = pd.read_csv(path, parse_dates=["start_time"])
        return df
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des EF-Caches: {e}")
        return pd.DataFrame()

def classify_training_state(tsb, ef_trend, if_recent):
    if tsb > 10 and if_recent < 0.75:
        return "Erholt", "Du bist gut regeneriert – ideal für intensive Einheiten.", "#33A02C"
    elif tsb < -20 and if_recent > 0.85:
        return "Überlastet", "Dein Körper ist stark belastet. Reduziere die Intensität und erhole dich.", "#E31A1C"
    elif -10 <= tsb <= 10:
        return "Belastet", "Du trainierst aktiv, aber bist nicht überfordert. Weiter so.", "#FDBF6F"
    elif ef_trend > 0 and tsb < 0:
        return "Aufbauend", "Deine Effizienz steigt trotz Belastung – du baust Fitness auf.", "#1F78B4"
    elif tsb > 5 and ef_trend > 0.05:
        return "Peakform", "Topform erreicht – du bist leistungsfähig und regeneriert.", "#6A3D9A"
    else:
        return "Neutral", "Keine klare Tendenz erkennbar – halte dein Training ausgewogen.", "#BBBBBB"

def render():
    user = get_current_user()

    st.markdown("""
        <div style='font-size: 1.4rem; font-weight: 600; margin-bottom: 0.5rem;'>
        🔎 Aktueller Trainingszustand
        </div>
    """, unsafe_allow_html=True)

    load_df = fetch_training_load_from_cache(user)
    activity_df = fetch_recent_activity_metrics(user)

    if load_df.empty or activity_df.empty:
        st.warning("Nicht genügend Trainingsdaten verfügbar.")
        return

    latest_tsb = load_df.iloc[-1]["tsb"]

    recent = activity_df[activity_df["start_time"] > datetime.today() - timedelta(days=7)]
    prev = activity_df[(activity_df["start_time"] <= datetime.today() - timedelta(days=7)) &
                       (activity_df["start_time"] > datetime.today() - timedelta(days=28))]

    ef_recent = recent["ef"].mean() if "ef" in recent.columns and not recent.empty else 0
    ef_prev = prev["ef"].mean() if "ef" in prev.columns and not prev.empty else 0
    ef_trend = ef_recent - ef_prev
    if_recent = recent["intensity_factor"].mean() if "intensity_factor" in recent.columns and not recent.empty else 0

    status, status_msg, color = classify_training_state(latest_tsb, ef_trend, if_recent)

    st.markdown(f"""
        <div style='padding: 0.7em; border-radius: 6px; background-color:{color}; color:white; text-align:center; font-size: 1.2rem; font-weight:600;'>
            {status.upper()}
        </div>
        <div style='margin-top: 0.5rem; font-size: 0.95rem; color: #444;'>{status_msg}</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("TSB (Form)", f"{latest_tsb:.1f}")
    col2.metric("EF-Trend (7d)", f"{ef_trend:.2f}")
    col3.metric("Ø IF (7d)", f"{if_recent:.2f}")

    load_plot = load_df.copy().sort_values("start_time")
    load_plot["TSB_Smooth"] = load_plot["tsb"].rolling(3, min_periods=1).mean()
    load_plot["CTL_Smooth"] = load_plot["ctl"].rolling(3, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=load_plot["start_time"],
        y=load_plot["TSB_Smooth"],
        name="TSB (Trend)",
        mode="lines",
        line=dict(color="#1F78B4", width=3),
        hovertemplate="Datum: %{x|%d.%m.%Y}<br>TSB: %{y:.1f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=load_plot["start_time"],
        y=load_plot["CTL_Smooth"],
        name="CTL (Fitness)",
        yaxis="y2",
        mode="lines",
        line=dict(color="#33A02C", dash="dot", width=2),
        hovertemplate="Datum: %{x|%d.%m.%Y}<br>CTL: %{y:.1f}<extra></extra>"
    ))

    fig.update_layout(
        title="📈 Verlauf von Form (TSB) & Fitness (CTL)",
        xaxis_title="Datum",
        yaxis=dict(title="TSB (Form)", side="left"),
        yaxis2=dict(title="Fitness (CTL)", overlaying="y", side="right"),
        template="training_dashboard_light",
        height=420,
        hovermode="x unified",
        margin=dict(t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📘 Bedeutung Trainingszustand"):
        st.markdown("""
        Der Trainingszustand bewertet deine Fitnessqualität basierend auf:
        - **TSB (Form)** – gibt Auskunft über deine momentane Belastung oder Erholung.
        - **EF-Trend** – misst Effizienzveränderung im Training (Normalized Power relativ zur HF).
        - **IF (Intensity Factor)** – wie intensiv du im Verhältnis zu deiner Schwelle trainierst.

        **Bewertungsskala:**
        - **Erholt** – gut erholt, bereit für harte Reize.
        - **Belastet** – Training im Rahmen, ausgewogen.
        - **Überlastet** – erhöhte Ermüdung, Vorsicht.
        - **Aufbauend** – trotz Belastung steigt deine Effizienz.
        - **Peakform** – topfit und ausgeruht – maximale Leistung abrufbar.
        - **Neutral** – kein starker Trend, gleichmäßig trainiert.
        """)