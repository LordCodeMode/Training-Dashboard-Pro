import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import json
import os
import plotly.io as pio
from utils.settings_access import get_setting
from utils.user_paths import get_user_cache_path, get_current_user

# === Theme
pio.templates["training_dashboard_light"] = pio.templates["plotly_white"].update({
    "layout": {
        "font": {"family": "Inter, sans-serif", "size": 14, "color": "#333"},
        "paper_bgcolor": "#fafafa",
        "plot_bgcolor": "#ffffff",
        "xaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "yaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "margin": dict(t=40, b=40, l=40, r=20),
        "hoverlabel": {
            "bgcolor": "#ffffff",
            "bordercolor": "#ddd",
            "font": {"color": "#333"}
        }
    }
})

TYP_ERKLAERUNGEN = {
    "Sprinter": "Explosive Leistung über wenige Sekunden, ideal für Endspurts.",
    "Puncheur": "Kurze, intensive Antritte – z. B. bei steilen Anstiegen oder auf welligem Terrain.",
    "Kletterer": "Starke Leistung über längere Zeit bei hohem Watt-pro-Kilo – ideal für lange Anstiege.",
    "Zeitfahrer": "Konstante Leistung über längere Zeit – ideal für flache Zeitfahrten.",
    "Allrounder": "Ausgeglichene Fähigkeiten in allen Bereichen ohne klare Schwäche.",
}

def save_rider_profile(user, rider_type, profile_data):
    try:
        db_path = get_setting("db_path", user=user)
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rider_profiles (
                    user TEXT,
                    timestamp TEXT,
                    rider_type TEXT,
                    profile_json TEXT
                )
            """)
            cur.execute("INSERT INTO rider_profiles VALUES (?, datetime('now'), ?, ?)",
                        (user, rider_type, json.dumps(profile_data)))
            conn.commit()
    except Exception as e:
        st.warning(f"Profil konnte nicht gespeichert werden: {e}")

def show_rider_profile():
    user = get_current_user()

    st.markdown("<h2 style='display: flex; align-items: center; gap: 0.5rem;'>▣ Fahrertyp-Profil</h2>", unsafe_allow_html=True)
    st.markdown("""
    Dieses Modul analysiert deine besten Leistungswerte und zeigt dir, welchem Fahrertyp du am ehesten entsprichst.
    Die Analyse basiert auf dem Verhältnis deiner kurzfristigen und mittelfristigen Leistungswerte zur 20-Minuten-Leistung (als FTP-Proxy).
    """)

    cache_file = get_user_cache_path("power_best_values.json", user)
    if not os.path.exists(cache_file):
        st.error("❌ Leistungsdaten-Cache nicht gefunden.")
        return

    try:
        with open(cache_file, "r") as f:
            best_values = json.load(f)
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des Caches: {e}")
        return

    best_5s = best_values.get("max_5sec_power", 0)
    best_1min = best_values.get("max_1min_power", 0)
    best_5min = best_values.get("max_5min_power", 0)
    best_20min = best_values.get("max_20min_power", 0)

    if not best_20min or best_20min == 0:
        st.warning("Nicht genügend Leistungsdaten für die Analyse.")
        return

    profile = {
        "Sprint (5s)": round(best_5s / best_20min, 2),
        "Anaerob (1min)": round(best_1min / best_20min, 2),
        "VO2max (5min)": round(best_5min / best_20min, 2),
        "FTP (20min)": 1.00
    }

    df_profile = pd.DataFrame({
        "Leistungsbereich": list(profile.keys()),
        "Verhältnis zu FTP": list(profile.values())
    })

    color_map = {
        "Sprint (5s)": "#eb5757",
        "Anaerob (1min)": "#f79862",
        "VO2max (5min)": "#ffd166",
        "FTP (20min)": "#85c88a"
    }

    fig = px.bar(
        df_profile,
        x="Leistungsbereich",
        y="Verhältnis zu FTP",
        text="Verhältnis zu FTP"
    )
    fig.update_traces(
        marker_color=[color_map[x] for x in df_profile["Leistungsbereich"]],
        marker_line_width=0,
        texttemplate="%{text:.2f}",
        textposition="outside"
    )
    fig.update_layout(
        template="training_dashboard_light",
        title=dict(text="Dein Leistungsprofil", x=0.5),
        yaxis=dict(title="Leistung / FTP", tickformat=".1f"),
        xaxis=dict(title=""),
        height=480
    )

    st.plotly_chart(fig, use_container_width=True)

    if profile["Sprint (5s)"] > 1.6 and profile["VO2max (5min)"] < 1.2:
        typ = "Sprinter"
        farbe = "#f79862"
    elif profile["VO2max (5min)"] > 1.4 and profile["Sprint (5s)"] < 1.4:
        typ = "Kletterer"
        farbe = "#85c88a"
    elif profile["Anaerob (1min)"] > 1.3 and profile["VO2max (5min)"] > 1.3:
        typ = "Puncheur"
        farbe = "#eb5757"
    else:
        typ = "Allrounder"
        farbe = "#5b84b1"

    st.markdown("### ⤷ Vermuteter Fahrertyp")
    st.markdown(f"<h2 style='color:{farbe}; margin-top: -0.2em'>{typ}</h2>", unsafe_allow_html=True)
    st.caption(TYP_ERKLAERUNGEN.get(typ, ""))

    if st.button("⭳ Profil speichern"):
        save_rider_profile(user, typ, profile)
        st.success("Profil gespeichert!")

    if st.checkbox("⟲ Mit Profi-Fahrertypen vergleichen"):
        vergleichsprofile = {
            "Sprinter": [1.8, 1.5, 1.2, 1.0],
            "Puncheur": [1.4, 1.6, 1.4, 1.0],
            "Kletterer": [1.2, 1.3, 1.6, 1.0],
            "Zeitfahrer": [1.0, 1.1, 1.2, 1.0],
            "Allrounder": [1.4, 1.4, 1.4, 1.0],
            "Du": list(profile.values())
        }

        theta = list(profile.keys()) + [list(profile.keys())[0]]

        fig_radar = go.Figure()
        for name, werte in vergleichsprofile.items():
            fig_radar.add_trace(go.Scatterpolar(
                r=werte + [werte[0]],
                theta=theta,
                fill='toself' if name == "Du" else None,
                name=name,
                opacity=1.0 if name == "Du" else 0.5,
                line=dict(width=2 if name == "Du" else 1, dash="solid" if name == "Du" else "dot")
            ))

        fig_radar.update_layout(
            template="training_dashboard_light",
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 2], tickfont_size=11)
            ),
            title="Vergleich mit Profi-Fahrertypen (nach Allen & Coggan, 2010)",
            showlegend=True,
            height=600,
            margin=dict(t=80, b=60),
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.15)
        )

        st.plotly_chart(fig_radar, use_container_width=True)

        with st.expander("ℹ Erklärung der Profi-Typen"):
            for k, v in TYP_ERKLAERUNGEN.items():
                st.markdown(f"**{k}**: {v}")