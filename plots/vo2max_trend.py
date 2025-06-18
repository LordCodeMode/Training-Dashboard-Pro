import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.io as pio
from cache_modules.cache_vo2max import save_vo2max_peak_estimates_multistage
from utils.user_paths import get_current_user, get_user_cache_path
from utils.settings_access import get_setting

# === Custom Plotly Theme aktivieren ===
pio.templates["training_dashboard_light"] = pio.templates["plotly_white"].update({
    "layout": {
        "font": {"family": "Inter, sans-serif", "size": 14, "color": "#333"},
        "paper_bgcolor": "#fafafa",
        "plot_bgcolor": "#ffffff",
        "xaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "yaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
        "colorway": ["#5b84b1", "#999999"],
        "margin": dict(t=40, b=40, l=40, r=20),
        "hoverlabel": {
            "bgcolor": "#ffffff",
            "bordercolor": "#ddd",
            "font": {"color": "#333"}
        }
    }
})


def load_vo2max_estimates(user):
    path = get_user_cache_path("vo2max_time_series.json", user)
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        with open(path, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if df.empty or "timestamp" not in df or "vo2max" not in df:
            return pd.DataFrame()

        df["Datum"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("Datum")
        df = df[df["vo2max"].notna()]

        weight = get_setting("weight", default=70.0)
        if weight <= 0:
            st.error("❌ Ungültiges Gewicht. Bitte in den Einstellungen prüfen.")
            return pd.DataFrame()

        df["VO₂max"] = (df["vo2max"] / weight).round(1)
        return df[["Datum", "VO₂max"]]
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der VO₂max-Daten: {e}")
        return pd.DataFrame()


def render_vo2max_plot():
    user = get_current_user()
    st.subheader("VO₂max-Verlauf")

    df = load_vo2max_estimates(user)
    if df.empty:
        st.warning("Keine VO₂max-Daten verfügbar.")
        return

    fig = px.line(
        df,
        x="Datum",
        y="VO₂max",
        title="📈 VO₂max Verlauf (ml/min/kg)",
        markers=True,
        labels={"VO₂max": "VO₂max (ml/min/kg)", "Datum": "Datum"},
        template="training_dashboard_light"
    )
    fig.update_traces(line=dict(width=2), marker=dict(size=6))
    fig.update_layout(
        height=420,
        yaxis=dict(
            title="VO₂max (ml/min/kg)",
            range=[max(40, df["VO₂max"].min() - 2), min(85, df["VO₂max"].max() + 2)]
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    latest = df.iloc[-1]
    delta = latest["VO₂max"] - df.iloc[0]["VO₂max"]
    st.metric("Letzter VO₂max-Wert", f"{latest['VO₂max']} ml/min/kg", f"{delta:+.1f}")

    df["KW"] = df["Datum"].dt.isocalendar().week
    df["Jahr"] = df["Datum"].dt.isocalendar().year
    df["KW_Label"] = df["Jahr"].astype(str) + "-KW" + df["KW"].astype(str)
    weekly_avg = df.groupby("KW_Label")["VO₂max"].mean().reset_index()

    fig_week = px.bar(
        weekly_avg,
        x="KW_Label",
        y="VO₂max",
        title="Wöchentlicher Durchschnitt",
        labels={"KW_Label": "Kalenderwoche", "VO₂max": "VO₂max (ml/min/kg)"},
        template="training_dashboard_light",
        color_discrete_sequence=["#5b84b1"]
    )
    st.plotly_chart(fig_week, use_container_width=True)

    df["Trend"] = df.set_index("Datum")["VO₂max"].rolling("21D").mean().values
    trend_df = df[df["Datum"] >= (df["Datum"].max() - pd.Timedelta(days=30))]

    fig2 = px.line(
        trend_df,
        x="Datum",
        y="Trend",
        title="Gleitender Trend der VO₂max (letzte 30 Tage)",
        labels={"Trend": "VO₂max (ml/min/kg)", "Datum": "Datum"},
        template="training_dashboard_light",
        color_discrete_sequence=["#999999"]
    )
    fig2.update_traces(line=dict(width=2, dash="dot"))
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Berechnungsdetails"):
        st.markdown("""
        Die VO₂max-Schätzung basiert auf deinen Trainingsdaten:  
        • Leistung (NP, Peak Power)  
        • Herzfrequenz  
        • Intensität (IF)  
        • Körpergewicht

        Nur plausible und valide Trainings werden einbezogen, um eine belastbare Abschätzung deiner  
        **maximalen Sauerstoffaufnahmefähigkeit (ml/min/kg)** zu ermitteln.
        """)

    st.markdown("<div style='text-align: right; margin-top: 2rem;'>", unsafe_allow_html=True)
    if st.button("Neuberechnen", key="refresh_vo2max", help="Cache für VO₂max neu berechnen"):
        try:
            save_vo2max_peak_estimates_multistage(user=user)
            st.success("✅ VO₂max neu berechnet.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Fehler bei Neuberechnung: {e}")
    st.markdown("</div>", unsafe_allow_html=True)