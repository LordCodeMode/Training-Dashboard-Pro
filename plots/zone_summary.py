import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.io as pio
from utils.settings_access import get_setting, DB_PATH
from utils.user_paths import get_current_user, get_user_cache_path
from plotly import graph_objects as go
from fit_processing.power_zones import compute_power_zones
from fit_processing.core_metrics import extract_core_metrics
from utils.user_paths import get_user_fit_dir


# === Custom Plotly Theme ===
pio.templates["training_dashboard_light"] = pio.templates["plotly_white"].update({
    "layout": {
        "font": {"family": "Inter, sans-serif", "size": 14, "color": "#333"},
        "paper_bgcolor": "#fafafa",
        "plot_bgcolor": "#ffffff",
        "xaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "yaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "colorway": ["#6c9ef2", "#85c88a", "#ffd166", "#f79862", "#eb5757", "#a25ddc", "#7a7a7a"],
        "margin": dict(t=40, b=40, l=40, r=20),
        "hoverlabel": {
            "bgcolor": "#ffffff",
            "bordercolor": "#ddd",
            "font": {"color": "#333", "family": "Inter, sans-serif", "size": 13}
        }
    }
})

ZONE_ORDER = [
    "Z1 (Recovery)", "Z2 (Endurance)", "Z3 (Tempo)",
    "Z4 (Schwelle)", "Z5 (VO2max)", "Z6 (Anaerob)", "Z7 (Sprint)"
]

ZONE_WATTS = {
    "Z1 (Recovery)": (0.0, 0.55),
    "Z2 (Endurance)": (0.55, 0.75),
    "Z3 (Tempo)": (0.75, 0.90),
    "Z4 (Schwelle)": (0.90, 1.05),
    "Z5 (VO2max)": (1.05, 1.20),
    "Z6 (Anaerob)": (1.20, 1.50),
    "Z7 (Sprint)": (1.50, 10.0),
}

ZONE_COLORS = {
    "Z1 (Recovery)": "#c7f6c1",
    "Z2 (Endurance)": "#9ce4a5",
    "Z3 (Tempo)": "#ffe285",
    "Z4 (Schwelle)": "#fab57e",
    "Z5 (VO2max)": "#f1998e",
    "Z6 (Anaerob)": "#d67777",
    "Z7 (Sprint)": "#c9a0db",
}

def format_duration(seconds):
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except:
        return "–"

def load_last_training_zones(user):
    """
    Holt die Power-Zonen des letzten Trainings live aus der letzten FIT-Datei des Nutzers.
    Kein Cachezugriff notwendig, vollständig Multi-User-fähig.
    """
    fit_dir = get_user_fit_dir(user)
    files = sorted(os.listdir(fit_dir))
    if not files:
        return None, None, None

    last_file = files[-1]
    path = os.path.join(fit_dir, last_file)

    try:
        ftp = get_setting("ftp", default=250, user=user)
        zones = compute_power_zones(path, ftp=ftp, user=user)
        if not zones:
            return None, None, None

        df_zones = pd.DataFrame(list(zones.items()), columns=["zone_label", "seconds_in_zone"])

        core = extract_core_metrics(path)
        start_time = core.get("start_time")  # z. B. datetime
        duration = core.get("duration")      # Sekunden

        return df_zones, start_time, duration

    except Exception as e:
        st.error(f"❌ Fehler beim Live-Laden der Zonenverteilung: {e}")
        return None, None, None

def load_total_zone_distribution(user):
    path = get_user_cache_path("power_zones_summary.csv", user)
    if not os.path.exists(path):
        st.warning("⚠️ Power-Zonen-Cache nicht gefunden.")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df.columns = ["zone_label", "total_sec"] + (["user_id"] if "user_id" in df.columns else [])
        return df
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des Power-Zonen-Caches: {e}")
        return pd.DataFrame()

def render():
    user = get_current_user()
    ftp = get_setting("ftp", default=250)

    st.subheader("Zonenanalyse")
    tab1, tab2 = st.tabs(["⚡ Letztes Training", "∑ Gesamtverteilung"])

    with tab1:
        df_last, name, dur = load_last_training_zones(user)

        if df_last is None or df_last.empty or df_last["seconds_in_zone"].sum() == 0:
            st.info("Keine Leistungszonen-Daten für das letzte Training vorhanden.")
        else:
            df_last["Zone"] = df_last["zone_label"]
            df_last["Wattbereich"] = df_last["Zone"].apply(
                lambda z: f"{int(ZONE_WATTS[z][0] * ftp)}–{int(ZONE_WATTS[z][1] * ftp)} W"
            )
            df_last["Minuten"] = df_last["seconds_in_zone"] / 60
            df_last["Dauer"] = df_last["seconds_in_zone"].apply(format_duration)
            df_last = df_last[df_last["Zone"].isin(ZONE_ORDER)]
            df_last["Zone"] = pd.Categorical(df_last["Zone"], categories=ZONE_ORDER, ordered=True)
            df_last = df_last.sort_values("Zone")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_last["Zone"],
                y=df_last["Minuten"],
                marker_color=[ZONE_COLORS[z] for z in df_last["Zone"]],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Dauer: %{customdata[0]}<br>"
                    "Wattbereich: %{customdata[1]}<extra></extra>"
                ),
                customdata=df_last[["Dauer", "Wattbereich"]].values,
            ))

            fig.update_layout(
                template="training_dashboard_light",
                showlegend=False,
                height=400,
                xaxis_title="Leistungszone",
                yaxis_title="Zeit in Minuten",
                bargap=0.0,
                bargroupgap=0.0,
                margin=dict(t=40, b=40, l=40, r=20),
            )

            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Training: {name} – Dauer: {format_duration(dur)}")

    with tab2:
        df_total = load_total_zone_distribution(user)

        if df_total.empty or df_total["total_sec"].sum() == 0:
            st.info("Noch keine Leistungszonen-Zeit erfasst.")
        else:
            df_total["Zone"] = df_total["zone_label"]
            df_total["Wattbereich"] = df_total["Zone"].apply(
                lambda z: f"{int(ZONE_WATTS[z][0] * ftp)}–{int(ZONE_WATTS[z][1] * ftp)} W"
            )
            df_total["Minuten"] = df_total["total_sec"] / 60
            df_total["Dauer"] = df_total["total_sec"].apply(format_duration)
            df_total = df_total[df_total["Zone"].isin(ZONE_ORDER)]
            df_total["Zone"] = pd.Categorical(df_total["Zone"], categories=ZONE_ORDER, ordered=True)
            df_total = df_total.sort_values("Zone")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_total["Zone"],
                y=df_total["Minuten"],
                marker_color=[ZONE_COLORS[z] for z in df_total["Zone"]],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Dauer: %{customdata[0]}<br>"
                    "Wattbereich: %{customdata[1]}<extra></extra>"
                ),
                customdata=df_total[["Dauer", "Wattbereich"]].values,
            ))

            fig.update_layout(
                template="training_dashboard_light",
                showlegend=False,
                height=400,
                xaxis_title="Leistungszone",
                yaxis_title="Gesamtzeit in Minuten",
                bargap=0.0,  # keine Lücke zwischen Balken
                bargroupgap=0.0,
                margin=dict(t=40, b=40, l=40, r=20),
            )

            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Gesamte Trainingszeit: {format_duration(df_total['total_sec'].sum())}")