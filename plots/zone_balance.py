import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import plotly.io as pio
from datetime import timedelta
from utils.user_paths import get_current_user, get_user_cache_path
from utils.settings_access import get_setting

# === Theme ===
pio.templates["training_dashboard_light"] = pio.templates["plotly_white"].update({
    "layout": {
        "font": {"family": "Inter, sans-serif", "size": 14, "color": "#333"},
        "paper_bgcolor": "#fafafa",
        "plot_bgcolor": "#ffffff",
        "xaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "yaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "margin": dict(t=40, b=40, l=40, r=20),
        "hoverlabel": {"bgcolor": "#ffffff", "bordercolor": "#ddd", "font": {"color": "#333"}},
        "colorway": ["#6c9ef2", "#85c88a", "#ffd166", "#f79862", "#eb5757", "#a25ddc", "#7a7a7a"]
    }
})

ZONE_LABELS = [
    "Z1 (Recovery)", "Z2 (Endurance)", "Z3 (Tempo)",
    "Z4 (Schwelle)", "Z5 (VO2max)"
]

ZONE_COLORS = {
    "Z1 (Recovery)": "#c7f6c1",
    "Z2 (Endurance)": "#9ce4a5",
    "Z3 (Tempo)": "#ffe285",
    "Z4 (Schwelle)": "#fab57e",
    "Z5 (VO2max)": "#f1998e"
}

ZONE_TARGETS = {
    "Polarisiert": {"Z1 (Recovery)": 10, "Z2 (Endurance)": 65, "Z3 (Tempo)": 5, "Z4 (Schwelle)": 10, "Z5 (VO2max)": 10},
    "Sweet Spot": {"Z1 (Recovery)": 10, "Z2 (Endurance)": 35, "Z3 (Tempo)": 25, "Z4 (Schwelle)": 25, "Z5 (VO2max)": 5},
    "High Intensity": {"Z1 (Recovery)": 5, "Z2 (Endurance)": 30, "Z3 (Tempo)": 15, "Z4 (Schwelle)": 25, "Z5 (VO2max)": 25}
}

WATT_BEREICHE = {
    "Z1 (Recovery)": (0.0, 0.55),
    "Z2 (Endurance)": (0.55, 0.75),
    "Z3 (Tempo)": (0.75, 0.90),
    "Z4 (Schwelle)": (0.90, 1.05),
    "Z5 (VO2max)": (1.05, 1.20),
}

def render():
    user = get_current_user()
    st.markdown("<h4 style='margin-top: -0.5rem;'>∑ Zonenbalance – Power basiert</h4>", unsafe_allow_html=True)

    model = st.selectbox("Zielverteilung wählen:", list(ZONE_TARGETS.keys()), index=0)
    weeks_back = st.slider("Zeitraum (Wochen)", 1, 12, 4)
    target = ZONE_TARGETS[model]

    ftp = get_setting("ftp", default=250)
    cache_path = get_user_cache_path("activities.csv", user)
    zone_cache_path = get_user_cache_path("power_zones_detailed.csv", user)

    if not os.path.exists(cache_path):
        st.warning("⚠️ Activities-Cache nicht gefunden.")
        return

    try:
        df = pd.read_csv(cache_path, parse_dates=["start_time"])
    except Exception as e:
        st.error(f"Fehler beim Laden des Activities-Caches: {e}")
        return

    since = df["start_time"].max() - timedelta(weeks=weeks_back)
    df_recent = df[df["start_time"] >= since]

    if df_recent.empty:
        st.warning("Keine Aktivitäten im gewählten Zeitraum.")
        return

    ids = df_recent["id"].tolist()

    if not os.path.exists(zone_cache_path):
        st.warning("⚠️ Power-Zonen-Cache nicht gefunden.")
        return

    try:
        df_zones = pd.read_csv(zone_cache_path)
    except Exception as e:
        st.error(f"Fehler beim Laden des Power-Zonen-Caches: {e}")
        return

    df_filtered = df_zones[df_zones["activity_id"].isin(ids)]
    zone_summary = df_filtered.groupby("zone_label")["seconds_in_zone"].sum().to_dict()

    if not zone_summary or sum(zone_summary.values()) == 0:
        st.warning("Keine gültigen Leistungsdaten in diesem Zeitraum.")
        return

    total_time = sum(zone_summary.values())
    ist_pct = {z: zone_summary.get(z, 0) / total_time * 100 for z in ZONE_LABELS}
    delta = {z: ist_pct[z] - target[z] for z in ZONE_LABELS}

    watt_labels = {
        z: f"{int(WATT_BEREICHE[z][0]*ftp)}–{int(WATT_BEREICHE[z][1]*ftp)} W"
        for z in ZONE_LABELS
    }

    df_plot = pd.DataFrame({
        "Zone": ZONE_LABELS,
        "Ist (%)": [round(ist_pct[z], 1) for z in ZONE_LABELS],
        "Ziel (%)": [target[z] for z in ZONE_LABELS],
        "Abweichung": [round(delta[z], 1) for z in ZONE_LABELS],
        "Wattbereich": [watt_labels[z] for z in ZONE_LABELS],
        "Farbe": [ZONE_COLORS[z] for z in ZONE_LABELS]
    })

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_plot["Zone"], y=df_plot["Ist (%)"],
        name="Ist",
        marker_color=df_plot["Farbe"],
        hovertemplate="<b>%{x}</b><br>Watt: %{customdata[0]}<br>Ist: %{y:.1f}%<br>Ziel: %{customdata[1]}%",
        customdata=df_plot[["Wattbereich", "Ziel (%)"]],
    ))
    fig.add_trace(go.Bar(
        x=df_plot["Zone"], y=df_plot["Ziel (%)"],
        name="Ziel",
        marker_color="rgba(200, 200, 200, 0.4)",
        hoverinfo="skip"
    ))

    fig.update_layout(
        barmode="group",
        template="training_dashboard_light",
        title=f"Zonenverteilung (Modell: {model})",
        yaxis_title="Zeitanteil (%)",
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Analyse")
    for zone in ZONE_LABELS:
        abw = delta[zone]
        ziel = target[zone]
        symbol = "✓" if abs(abw) <= 5 else "✘"
        st.markdown(f"**{symbol} {zone}** ({watt_labels[zone]}): {abw:+.1f}% zum Ziel")

    st.caption(f"Zeitraum: Letzte {weeks_back} Wochen · FTP: {ftp} W")