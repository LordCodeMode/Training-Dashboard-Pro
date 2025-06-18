import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import json
from datetime import timedelta
from utils.settings_access import get_setting, DB_PATH
from utils.user_paths import get_user_cache_path, get_current_user
from fit_processing.metrics_calc_new import get_training_load_df

DURATIONS = {
    "1 Min": "max_1min_power",
    "3 Min": "max_3min_power",
    "5 Min": "max_5min_power",
    "10 Min": "max_10min_power",
    "20 Min": "max_20min_power",
    "30 Min": "max_30min_power"
}

def load_pb_data(user, duration_key):
    filepath = get_user_cache_path(f"{duration_key}.json", user)
    if not os.path.exists(filepath):
        return pd.DataFrame()
    try:
        with open(filepath, "r") as f:
            records = json.load(f)
        df = pd.DataFrame(records)
        df["start_time"] = pd.to_datetime(df["start_time"])
        df["date"] = df["start_time"].dt.normalize()
        df["power"] = pd.to_numeric(df["Power"], errors="coerce")
        weight = get_setting("weight", default=78, user=user)
        df["power_wkg"] = df["power"] / weight
        return df.dropna(subset=["power"])
    except Exception as e:
        st.error(f"Fehler beim Laden der PB-Daten: {e}")
        return pd.DataFrame()

def render():
    user = get_current_user()

    st.markdown("<h3 style='font-weight:600; margin-bottom:1rem'>Persönliche Bestwerte (Power)</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])
    selected = col1.selectbox("⏱ Zeitfenster", list(DURATIONS.keys()))
    duration_key = DURATIONS[selected]
    unit = col2.radio("Einheit", ["Watt", "W/kg"], horizontal=True)
    show_ctl = col3.toggle("Fitness (CTL) anzeigen", value=False)

    start_date = st.date_input("Startdatum", pd.Timestamp.today() - timedelta(weeks=12))
    start_date = pd.to_datetime(start_date)

    df = load_pb_data(user, duration_key)
    if df.empty:
        st.warning("Keine Bestwerte-Daten gefunden.")
        return

    df = df[df["date"] >= start_date]
    if df.empty:
        st.info("Keine Daten im gewählten Zeitraum.")
        return

    ctl_df = get_training_load_df(user)
    ctl_df["date"] = pd.to_datetime(ctl_df["date"])

    merged = pd.merge(df, ctl_df, on="date", how="left").sort_values("date")

    value_col = "power_wkg" if unit == "W/kg" else "power"
    current_pb = merged[value_col].max()
    last = merged.iloc[-1]
    last_val = last[value_col]
    delta_pct = ((last_val - current_pb) / current_pb) * 100 if current_pb else 0

    st.markdown("### Aktuelle Leistung")
    col1, col2, col3 = st.columns(3)
    col1.metric("Letzter Wert", f"{last_val:.1f} {unit}", f"{delta_pct:+.1f}%")
    col2.metric("Datum", last["date"].strftime("%Y-%m-%d"))
    col3.metric(f"PB ({selected})", f"{current_pb:.1f} {unit}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=merged["date"],
        y=merged[value_col],
        mode="lines+markers",
        name="PB Verlauf",
        line=dict(color="#4e79a7")
    ))

    pb_rows = merged[merged[value_col] == current_pb]
    if not pb_rows.empty:
        pb_row = pb_rows.iloc[-1]
        fig.add_trace(go.Scatter(
            x=[pb_row["date"]],
            y=[pb_row[value_col]],
            mode="markers+text",
            name="PB",
            marker=dict(color="#fbbf24", size=10, symbol="star"),
            text=["PB"],
            textposition="top center"
        ))

    if show_ctl and "CTL" in merged.columns:
        fig.add_trace(go.Scatter(
            x=merged["date"],
            y=merged["CTL"],
            name="CTL (Fitness)",
            yaxis="y2",
            mode="lines",
            line=dict(color="#999", dash="dot")
        ))

    fig.update_layout(
        title=f"Verlauf – {selected}",
        xaxis_title="Datum",
        yaxis=dict(title=f"Power ({unit})"),
        yaxis2=dict(title="CTL", overlaying="y", side="right", showgrid=False),
        template="training_dashboard_light",
        height=460,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Top 5 Bestwerte")
    top5 = df.sort_values("power", ascending=False).drop_duplicates(subset=["power"]).head(5)
    top5["Datum"] = top5["date"].dt.strftime("%d.%m.%Y")
    st.dataframe(
        top5[["Datum", "power", "power_wkg"]].rename(columns={
            "power": "Power (W)", "power_wkg": "Power (W/kg)"
        }).round(1),
        use_container_width=True
    )

    with st.expander("ℹ️ Was zeigt dieser Tab?"):
        st.markdown("""
        Du siehst hier deine persönlichen Leistungs-Bestwerte (PBs) für ein gewähltes Zeitintervall.
        Optional kannst du deine Fitness-Entwicklung (CTL) parallel anzeigen lassen.

        Die Tabelle zeigt deine Top-5 Werte unabhängig vom ausgewählten Zeitraum.
        """)