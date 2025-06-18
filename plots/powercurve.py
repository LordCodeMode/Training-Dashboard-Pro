import streamlit as st
import plotly.graph_objects as go
import numpy as np
import os
import plotly.io as pio
from utils.formatting import format_duration
from utils.settings_access import get_setting
from utils.user_paths import get_current_user, get_user_cache_path
from fit_processing.power_metrics_complete import compute_last_activity_power_curve
from cache_modules.cache_power_curve import save_power_curve

pio.templates.default = "training_dashboard_light"

def build_x_axis_labels(length_seconds: int):
    """
    Generiert log-ticks und Labels für Power-Duration-Achse bis max Dauer
    → Nur sinnvolle Zeitmarker: Sekunden, Minuten, ab 1h nur 1h-Schritte
    """
    ticks = [1, 15, 30, 60, 120, 300, 600, 1200, 1800, 2700, 3600]
    labels = ["1s", "15s", "30s", "1m", "2m", "5m", "10m", "20m", "30m", "45m", "1h"]

    for h in range(2, 13):
        sec = h * 3600
        if sec <= length_seconds:
            ticks.append(sec)
            labels.append(f"{h}h")
    return ticks, labels

def load_power_curve_from_cache(user, weighted=False):
    filepath = get_user_cache_path("power_curve.npy", user=user)
    if not os.path.exists(filepath):
        return None
    try:
        curve = np.load(filepath).tolist()
        if weighted:
            weight = get_setting("weight", default=70, user=user)
            curve = [p / weight for p in curve]
        return curve
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Powerkurve: {e}")
        return None

def render():
    user = get_current_user()
    weight = get_setting("weight", default=70, user=user)
    ftp = get_setting("ftp", default=250, user=user)

    st.markdown("""
        <div style='display: flex; align-items: center; gap: 0.5rem; font-size: 1.5rem; font-weight: 600;'>
        Powerkurve (Allzeit vs. Letzte Einheit)
        </div>
    """, unsafe_allow_html=True)

    unit_mode = st.radio("Einheit wählen:", ["Watt", "W/kg"], horizontal=True)
    show_wkg = unit_mode == "W/kg"
    ftp_line = ftp / weight if show_wkg else ftp
    y_label = "Leistung (W/kg)" if show_wkg else "Leistung (W)"
    ftp_label = f"FTP: {ftp_line:.1f} W/kg" if show_wkg else f"FTP: {ftp_line:.0f} W"

    curve_all = load_power_curve_from_cache(user, weighted=show_wkg)
    if not curve_all:
        st.warning("⚠️ Keine Allzeit-Powerkurve im Cache gefunden.")
        return

    curve_latest = compute_last_activity_power_curve(user=user, weight=weight if show_wkg else None)
    if not curve_latest or len(curve_latest) < 5:
        st.warning("⚠️ Keine gültige Powerkurve der letzten Einheit verfügbar.")
        return

    max_len = max(len(curve_all), len(curve_latest))
    x_vals = list(range(1, max_len + 1))
    x_ticks, x_labels = build_x_axis_labels(max_len)

    # === Hover-Label und Padding vorbereiten ===
    curve_all_padded = curve_all + [None] * (max_len - len(curve_all))
    curve_latest_padded = curve_latest + [None] * (max_len - len(curve_latest))

    hover_labels_all = [
        f"{format_duration(x)}<br>Allzeit: {y:.1f} {y_label.split()[1]}" if y is not None else f"{format_duration(x)}<br>Allzeit: –"
        for x, y in zip(x_vals, curve_all_padded)
    ]
    hover_labels_latest = [
        f"{format_duration(x)}<br>Letzte Einheit: {y:.1f} {y_label.split()[1]}" if y is not None else f"{format_duration(x)}<br>Letzte Einheit: –"
        for x, y in zip(x_vals, curve_latest_padded)
    ]

    # === Plot ===
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=curve_all_padded,
        mode="lines", name="Allzeit",
        line=dict(color="#8e44ad", width=2),
        text=hover_labels_all,
        hoverinfo="text"
    ))
    fig.add_trace(go.Scatter(
        x=x_vals, y=curve_latest_padded,
        mode="lines", name="Letzte Einheit",
        line=dict(color="#5e3370", width=2, dash="dot"),
        text=hover_labels_latest,
        hoverinfo="text"
    ))

    fig.add_hline(
        y=ftp_line,
        line_dash="dash",
        line_color="red",
        line_width=1.5,
        annotation_text=ftp_label,
        annotation_position="top right"
    )

    fig.update_layout(
        title="📈 Power-Dauer-Kurve",
        xaxis=dict(
            title="Dauer",
            tickmode="array",
            tickvals=x_ticks,
            ticktext=x_labels,
            type="log",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikecolor="gray"
        ),
        yaxis=dict(
            title=y_label,
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikecolor="gray"
        ),
        hovermode="x unified",
        height=500,
        margin=dict(t=50, b=50, l=60, r=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # === Rebuild Button ===
    st.markdown("<div style='margin-top: 2rem; text-align: right;'>", unsafe_allow_html=True)
    if st.button("Neuberechnen", key="refresh_power_curve"):
        try:
            save_power_curve(user=user)
            st.success("Powerkurve wurde erfolgreich neu berechnet.")
        except Exception as e:
            st.error(f"Fehler bei Neuberechnung: {e}")
    st.markdown("</div>", unsafe_allow_html=True)