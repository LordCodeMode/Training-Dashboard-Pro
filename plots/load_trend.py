import streamlit as st
import plotly.graph_objects as go
from fit_processing.metrics_calc_new import get_training_load_df

def render():
    df = get_training_load_df()  # ✅ Kein Argument übergeben!

    st.markdown("""
        <div style='display: flex; align-items: center; gap: 0.5rem; font-size: 1.4rem; font-weight: 600;'>
        ▼ Training Load Entwicklung
        </div>
    """, unsafe_allow_html=True)

    if df.empty or df[["CTL", "ATL", "TSB"]].dropna().empty:
        st.warning("Keine validen Trainingsdaten mit TSS im Cache gefunden.")
        return

    latest = df.dropna().iloc[-1]
    ctl, atl, tsb = latest['CTL'], latest['ATL'], latest['TSB']

    st.markdown("### Tagesstatus")

    col1, col2, col3 = st.columns(3)
    col1.metric("Fitness (CTL)", f"{ctl:.1f}")
    col2.metric("Fatigue (ATL)", f"{atl:.1f}")

    if tsb > 0:
        status = "Erholt"
        color = "#4CAF50"
        text_color = "white"
    elif tsb < -20:
        status = "Überlastet"
        color = "#E31A1C"
        text_color = "white"
    else:
        status = "Belastet"
        color = "#FDBF6F"
        text_color = "black"

    col3.markdown(
        f"""
        <div style='padding: 1em; border-radius: 8px;
                    background-color:{color}; color:{text_color};
                    text-align:center; font-weight:600; font-size:1.1rem'>
            Form (TSB)<br>
            <span style='font-size:1.4rem'>{tsb:.1f} – {status}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("CTL = langfristige Fitness · ATL = kurzfristige Ermüdung · TSB = aktuelle Form (CTL - ATL)")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=df['CTL'],
        mode='lines', name='Fitness (CTL)',
        line=dict(color="#1F78B4", width=2.2),
        hovertemplate='Datum: %{x|%d.%m.%Y}<br>CTL: %{y:.1f}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df["date"], y=df['ATL'],
        mode='lines', name='Fatigue (ATL)',
        line=dict(color="#FF7F00", width=1.6, dash="dot"),
        hovertemplate='Datum: %{x|%d.%m.%Y}<br>ATL: %{y:.1f}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df["date"], y=df['TSB'],
        mode='lines', name='Form (TSB)',
        line=dict(color="#33A02C", width=1.8),
        hovertemplate='Datum: %{x|%d.%m.%Y}<br>TSB: %{y:.1f}<extra></extra>'
    ))

    fig.update_layout(
        title="Trainingslastentwicklung (CTL / ATL / TSB)",
        xaxis_title="Datum",
        yaxis_title="TSS-Werte",
        template="training_dashboard_light",
        hovermode="x unified",
        margin=dict(t=50, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)