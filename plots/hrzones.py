import os
import sqlite3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from utils.settings_access import get_setting, DB_PATH
from utils.user_paths import get_user_cache_path, get_user_fit_path, get_current_user
from fit_processing.heart_rate_metrics import compute_hr_zones

# === HR-Zonen – 5 Zonen Modell (relativ zu Max HR) ===
MAX_HR = get_setting("hr_max", default=190)
HR_ZONES = {
    "Z1 (Erholung)": (0.50, 0.60),
    "Z2 (Grundlage)": (0.60, 0.70),
    "Z3 (GA2)": (0.70, 0.80),
    "Z4 (Schwelle)": (0.80, 0.90),
    "Z5 (VO2max)": (0.90, 1.00),
}
ZONE_ORDER = list(HR_ZONES.keys())
ZONE_COLORS = {
    "Z1 (Erholung)": "#ffe6e6",
    "Z2 (Grundlage)": "#ffb3b3",
    "Z3 (GA2)": "#ff9999",
    "Z4 (Schwelle)": "#ff6666",
    "Z5 (VO2max)": "#cc0000",
}

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"

def bpm_range(z):
    try:
        low, high = HR_ZONES[z]
        return f"{int(low * MAX_HR)}–{int(high * MAX_HR)} bpm"
    except:
        return "?"

def ensure_all_zones(df, value_col="seconds_in_zone"):
    all_zones = pd.DataFrame({"Zone": ZONE_ORDER})
    df = all_zones.merge(df, on="Zone", how="left").fillna({value_col: 0})
    return df

def render():
    user = get_current_user()

    st.subheader("❤ Herzfrequenz-Zonen Analyse")

    tab_selection = option_menu(
        menu_title=None,
        options=["Letztes Training", "Gesamtübersicht"],
        icons=["activity", "bar-chart"],
        orientation="horizontal",
        styles={
            "container": {"margin": "0 0 1.5rem 0", "padding": "0.4rem", "border-radius": "8px", "background-color": "#f2f2f2"},
            "nav-link": {
                "font-size": "14px", "font-weight": "500", "color": "#333", "padding": "8px 12px",
                "border-radius": "6px", "display": "flex", "align-items": "center", "gap": "0.4rem",
                "white-space": "nowrap"
            },
            "nav-link-selected": {
                "background-color": "#ffffff", "color": "#d72638",
                "box-shadow": "inset 0 -2px 0 #d72638"
            }
        }
    )

    if tab_selection == "Letztes Training":
        try:
            with sqlite3.connect(DB_PATH) as conn:
                df = pd.read_sql_query(
                    "SELECT file_name, start_time FROM activities WHERE user_id = ? ORDER BY start_time DESC LIMIT 1",
                    conn, params=(user,)
                )
        except Exception as e:
            st.error(f"Fehler beim Laden der Trainingsdaten: {e}")
            return

        if df.empty or pd.isna(df.at[0, "file_name"]):
            st.warning("Keine gültige Trainingseinheit mit Datei vorhanden.")
            return

        file_name = df.at[0, "file_name"]
        start_time = df.at[0, "start_time"]
        fit_path = get_user_fit_path(file_name, user)

        if not os.path.exists(fit_path):
            st.warning(f"FIT-Datei fehlt: {file_name}")
            return

        try:
            zones = compute_hr_zones(fit_path)
        except Exception as e:
            st.error(f"Fehler bei Berechnung der HF-Zonen: {e}")
            return

        if not zones or sum(zones.values()) == 0:
            st.warning("Keine HF-Zonen-Daten verfügbar.")
            return

        df_zones = pd.DataFrame(list(zones.items()), columns=["Zone", "seconds_in_zone"])
        df_zones = ensure_all_zones(df_zones)
        df_zones["Minuten"] = df_zones["seconds_in_zone"] / 60
        df_zones["Dauer"] = df_zones["seconds_in_zone"].apply(format_time)
        df_zones["Bereich"] = df_zones["Zone"].apply(bpm_range)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_zones["Zone"],
            y=df_zones["Minuten"],
            marker_color=[ZONE_COLORS[z] for z in df_zones["Zone"]],
            customdata=df_zones[["Dauer", "Bereich"]].values,
            hovertemplate="<b>%{x}</b><br>Dauer: %{customdata[0]}<br>Bereich: %{customdata[1]}<extra></extra>"
        ))

        fig.update_layout(
            template="training_dashboard_light",
            showlegend=False,
            height=400,
            xaxis_title="Herzfrequenz-Zone",
            yaxis_title="Zeit in Minuten",
            bargap=0.0,
            bargroupgap=0.0,
            margin=dict(t=50, b=40, l=40, r=20)
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Training: {start_time}")




    elif tab_selection == "Gesamtübersicht":
        cache_path = get_user_cache_path("hr_zones_summary.csv", user)
        if not os.path.exists(cache_path):
            st.warning("⚠️ HF-Zonen-Cachedatei nicht gefunden.")
            return
        try:
            df_total = pd.read_csv(cache_path)
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der HF-Zonen-Cachedaten: {e}")
            return

        if "zone" not in df_total.columns or "seconds" not in df_total.columns:
            st.warning("⚠️ HF-Zonen-Cachedatei enthält keine gültigen Daten.")
            st.text(f"Spalten gefunden: {', '.join(df_total.columns)}")
            return

        if df_total.empty or df_total["seconds"].fillna(0).sum() <= 0:
            st.warning("⚠️ Keine HF-Zonen-Cachedaten verfügbar.")
            return

        df_total.rename(columns={"zone": "Zone", "seconds": "seconds_in_zone"}, inplace=True)
        df_total = ensure_all_zones(df_total)
        df_total["Minuten"] = df_total["seconds_in_zone"] / 60
        df_total["Dauer"] = df_total["seconds_in_zone"].apply(format_time)
        df_total["Bereich"] = df_total["Zone"].apply(bpm_range)
        total_time = int(df_total["seconds_in_zone"].sum())
        st.markdown(f"**Gesamtdauer in HF-Zonen:** {format_time(total_time)}")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_total["Zone"],
            y=df_total["Minuten"],
            marker_color=[ZONE_COLORS[z] for z in df_total["Zone"]],
            customdata=df_total[["Dauer", "Bereich"]].values,
            hovertemplate="<b>%{x}</b><br>Dauer: %{customdata[0]}<br>Bereich: %{customdata[1]}<extra></extra>"
        ))
        fig.update_layout(
            title="Zeit in HF-Zonen (Summiert aus allen Einheiten)",
            template="training_dashboard_light",
            showlegend=False,
            height=400,
            xaxis_title="Herzfrequenz-Zone",
            yaxis_title="Zeit in Minuten",
            bargap=0.0,
            bargroupgap=0.0,
            margin=dict(t=50, b=40, l=40, r=20)
        )
        st.plotly_chart(fig, use_container_width=True)