import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.user_paths import get_user_cache_path, get_current_user

def render():
    user = get_current_user()
    cache_path = get_user_cache_path("efficiency_factors.csv", user)

    st.markdown("""
        <div style='font-size: 1.4rem; font-weight: 600; margin-bottom: 0.5rem;'>
        Efficiency Factor (EF) Analyse
        </div>
    """, unsafe_allow_html=True)

    try:
        df = pd.read_csv(cache_path, parse_dates=["start_time"])
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des EF-Caches: {e}")
        return

    if df.empty or "ef" not in df.columns:
        st.warning("⚠️ Keine validen EF-Daten im Cache vorhanden.")
        return

    df = df.rename(columns={"ef": "EF"})
    df = df[df["EF"] > 0]  # Filtere ungültige Werte
    df = df.sort_values("start_time")
    df["EF_smooth"] = df["EF"].rolling(window=7, min_periods=1).mean()

    # Filterbereich
    with st.expander("⚙️ Filteroptionen", expanded=False):
        ga1_filter = st.checkbox("Nur GA1-Einheiten anzeigen (IF < 0.75)", value=True)
        if ga1_filter and "intensity_factor" in df.columns:
            df = df[df["intensity_factor"] < 0.75]

    if df.empty:
        st.warning("⚠️ Keine passenden Einheiten im ausgewählten Zeitraum.")
        return

    # Zeitfenster: letzte 4 Monate
    four_months_ago = pd.Timestamp.today() - pd.DateOffset(months=4)
    df = df[df["start_time"] >= four_months_ago]

    # Fortschritts-Logik
    last_ef = df["EF"].iloc[-1]
    first_ef = df[df["start_time"] <= df["start_time"].min() + pd.Timedelta(days=14)]["EF"].mean()
    delta_pct = ((last_ef - first_ef) / first_ef) * 100 if first_ef else 0

    if delta_pct > 5:
        trend = "🔼 Verbesserte Effizienz"
        color = "#4CAF50"
        text_color = "white"
    elif delta_pct < -5:
        trend = "🔽 Rückgang der Effizienz"
        color = "#E31A1C"
        text_color = "white"
    else:
        trend = "➖ Stabiler Wert"
        color = "#FDBF6F"
        text_color = "black"

    # Metriken
    st.markdown("### Übersicht")
    col1, col2, col3 = st.columns(3)
    col1.metric("Ø EF (alle)", f"{df['EF'].mean():.2f}")
    col2.metric("Letzter EF", f"{last_ef:.2f}")
    col3.markdown(
        f"""<div style='padding: 1em; border-radius: 8px;
                    background-color:{color}; color:{text_color};
                    text-align:center; font-weight:600; font-size:1.1rem'>
                📈 Fortschritt<br><span style='font-size:1.2rem'>{trend}</span>
            </div>""",
        unsafe_allow_html=True
    )

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["start_time"],
        y=df["EF_smooth"],
        mode="lines+markers",
        name="EF (geglättet)",
        line=dict(color="#1F78B4", width=2),
        marker=dict(size=6),
        hovertemplate="📅 %{x|%d.%m.%Y}<br>EF: %{y:.2f}<extra></extra>"
    ))
    fig.update_layout(
        title="📈 EF-Verlauf (letzte 4 Monate)",
        xaxis_title="Datum",
        yaxis_title="Efficiency Factor",
        template="training_dashboard_light",
        height=420,
        margin=dict(t=40, b=30),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabelle
    st.markdown("### 📋 Aktivitäten mit EF")
    df_table = df[["start_time", "normalized_power", "avg_heart_rate", "intensity_factor", "EF"]].copy()
    df_table["start_time"] = df_table["start_time"].dt.strftime("%d.%m.%Y")
    df_table = df_table.rename(columns={
        "start_time": "Datum",
        "normalized_power": "NP",
        "avg_heart_rate": "HFavg",
        "intensity_factor": "IF"
    }).round(2)
    st.dataframe(df_table.sort_values("Datum", ascending=False), use_container_width=True)

    # Erklärung
    with st.expander("ℹ️ Was bedeutet der Efficiency Factor?", expanded=False):
        st.markdown("""
        <div style='font-size: 0.94rem; line-height: 1.6;'>
        Der <strong>Efficiency Factor (EF)</strong> ist das Verhältnis von <em>Normalized Power (NP)</em> zur <em>durchschnittlichen Herzfrequenz (HFavg)</em>:

        <div style='text-align: center; padding: 0.5em 0; font-size: 1.05rem;'><strong>EF = NP / HFavg</strong></div>

        Ein hoher EF bedeutet, dass du mehr Leistung mit weniger Herzfrequenzaufwand erzeugst – ein guter Indikator für deine <strong>aerobe Effizienz</strong>.

        <strong>Wann nützlich?</strong> Vor allem bei <code>IF &lt; 0.75</code> (Grundlagenfahrten)

        <strong>Typische Interpretation:</strong>
        <ul style='margin-top: 0.5em;'>
            ✅ <strong>Höherer EF:</strong> Bessere aerobe Fitness<br>
            🔁 <strong>Stabiler EF:</strong> Gleichbleibende Form<br>
            ⚠️ <strong>Niedriger EF:</strong> Ermüdung oder Ineffizienz
        </ul>
        </div>
        """, unsafe_allow_html=True)