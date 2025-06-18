import os
import streamlit as st
import numpy as np
import json
import plotly.graph_objects as go
import plotly.io as pio

from utils.user_paths import get_user_cache_path, get_current_user
from cache_modules.cache_critical_power import save_critical_power

# === Custom Plotly Theme laden ===
pio.templates.default = "training_dashboard_light"

def format_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s}s"
    else:
        h, rem = divmod(seconds, 3600)
        m = rem // 60
        return f"{h}h {m}m"

def render():
    user = get_current_user()
    cp_path = get_user_cache_path("critical_power.json")

    st.markdown("""
        <div style='display: flex; align-items: center; gap: 0.5rem; font-size: 1.5rem; font-weight: 600;'>
        ⚡ Critical Power Analyse
        </div>
    """, unsafe_allow_html=True)

    if not os.path.exists(cp_path):
        st.warning("Keine Critical Power Daten im Cache gefunden.")
        return

    try:
        with open(cp_path, "r") as f:
            model = json.load(f)
    except Exception as e:
        st.error(f"Fehler beim Laden der CP-Daten: {e}")
        return

    cp = model.get("critical_power")
    w_prime = model.get("w_prime")
    durations = np.array(model.get("durations", []))
    predicted = np.array(model.get("predicted", []))
    actual = np.array(model.get("actual", []))

    if cp is None or w_prime is None or len(durations) == 0:
        st.warning("Unvollständige CP-Modell-Daten.")
        return

    st.markdown(f"""
    <div style='margin-top: 0.5rem; margin-bottom: 1rem; font-size: 1.1rem;'>
        <strong>CP:</strong> {cp:.0f} W &nbsp;&nbsp;|&nbsp;&nbsp; <strong>W′:</strong> {w_prime:.0f} J
    </div>
    """, unsafe_allow_html=True)

    hover_texts = [
        f"{format_duration(d)} ({d}s)<br><b>Powerkurve:</b> {a:.1f} W<br><b>Modell:</b> {p:.1f} W"
        for d, a, p in zip(durations, actual, predicted)
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=durations, y=actual,
        mode="lines",
        name="Powerkurve",
        line=dict(color="#6c9ef2", width=2),
        hovertext=hover_texts,
        hoverinfo="text"
    ))
    fig.add_trace(go.Scatter(
        x=durations, y=predicted,
        mode="lines",
        name="CP-Modell",
        line=dict(color="#f79862", width=2, dash="dot"),
        hoverinfo="skip"
    ))
    fig.add_hline(
        y=cp,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"CP = {cp:.0f} W · W′ = {w_prime:.0f} J",
        annotation_position="top right"
    )

    fig.update_layout(
        title="Vergleich: Powerkurve vs. CP-Modell",
        xaxis=dict(
            title="Dauer",
            type="log",
            tickvals=[5, 15, 60, 180, 300, 600, 1200, 1800, 2400, 3000, 3600],
            ticktext=[format_duration(t) for t in [5, 15, 60, 180, 300, 600, 1200, 1800, 2400, 3000, 3600]]
        ),
        yaxis=dict(title="Leistung (W)"),
        hovermode="x unified",
        height=520,
        margin=dict(t=50, b=50, l=60, r=40),
        legend=dict(x=0.99, y=0.99, xanchor="right", yanchor="top")
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
        ### Interpretation
        - **Critical Power (CP):** {cp:.0f} W  
        - **W′ (anaerobe Kapazität):** {w_prime:.0f} J  

        Die Kurve zeigt deine reale Leistung (Powerkurve) im Vergleich zum theoretischen CP-Modell.
    """)

    with st.expander("Was ist Critical Power?"):
        st.markdown(r"""
        **Critical Power (CP)** ist die maximale Dauerleistung, die du ohne kontinuierliche Ermüdung aufrechterhalten kannst.  
        **W′** steht für die anaerobe Reserve, die du oberhalb der CP kurzfristig abrufen kannst.

        Das Modell basiert auf folgender Formel:

        \[ P(t) = \frac{W'}{t} + CP \]

        - \(P(t)\): Leistung bei Dauer \(t\)  
        - \(CP\): Dauerleistungs-Schwelle (in Watt)  
        - \(W'\): anaerobe Kapazität (in Joule)
        """)

    st.markdown("<div style='text-align: right; margin-top: 2rem;'>", unsafe_allow_html=True)
    if st.button("Neuberechnen", key="refresh_cp", help="Cache für Critical Power neu berechnen"):
        try:
            save_critical_power(user)
            st.success("✅ CP-Modell erfolgreich neu berechnet.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"❌ Fehler bei Neuberechnung: {e}")
    st.markdown("</div>", unsafe_allow_html=True)