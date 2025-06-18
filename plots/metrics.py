import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from utils.settings_access import DB_PATH
from fitparse import FitFile
from fit_processing.power_zones import compute_power_zones
from fit_processing.heart_rate_metrics import compute_hr_zones
from utils.formatting import format_duration
from utils.user_paths import get_current_user, get_user_fit_path

def render():
    user = get_current_user()

    st.markdown("""
        <div style='display: flex; align-items: center; gap: 0.5rem; font-size: 1.5rem; font-weight: 600;'>
        ⬍ Trainingsanalyse – Wochenmetriken
        </div>
    """, unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT id, file_name, date(start_time) as date,
               strftime('%Y-%W', start_time) as week,
               tss,
               normalized_power,
               avg_power,
               intensity_factor
        FROM activities
        WHERE user_id = ?
        ORDER BY start_time
    """, conn, params=(user,))
    conn.close()

    if df.empty:
        st.warning("Keine Metriken verfügbar.")
        return

    df["date"] = pd.to_datetime(df["date"])
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    df["week_end"] = df["week_start"] + pd.Timedelta(days=6)
    df["week_label"] = df["week_start"].dt.strftime("%Y-%m-%d") + " – " + df["week_end"].dt.strftime("%m-%d")

    weekly = df.groupby(["week_start", "week_label"]).agg(
        total_tss=("tss", "sum"),
        avg_np=("normalized_power", "mean"),
        avg_power=("avg_power", "mean"),
        avg_if=("intensity_factor", "mean")
    ).reset_index().sort_values("week_start")

    st.markdown("### Analyse auswählen")
    view_option = st.radio("", ["TSS-Verlauf", "Leistung", "IF & TSS"], horizontal=True)

    if view_option == "TSS-Verlauf":
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=weekly["week_label"],
            y=weekly["total_tss"],
            name="Wöchentlicher TSS",
            marker_color="#1F78B4"
        ))
        fig.add_hline(
            y=weekly["total_tss"].mean(),
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Ø TSS: {round(weekly['total_tss'].mean(), 1)}",
            annotation_position="top left"
        )
        fig.update_layout(
            title="Wöchentlicher TSS-Verlauf",
            xaxis_title="Kalenderwoche",
            yaxis_title="TSS",
            xaxis_tickangle=45,
            template="training_dashboard_light",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    elif view_option == "Leistung":
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=weekly["week_label"],
            y=weekly["avg_np"],
            mode="lines+markers",
            name="Normalized Power",
            line=dict(color="#33A02C", width=3),
            marker=dict(symbol="circle", size=8)
        ))
        fig2.add_trace(go.Scatter(
            x=weekly["week_label"],
            y=weekly["avg_power"],
            mode="lines+markers",
            name="Ø Leistung",
            line=dict(color="#888888", width=2, dash="dot"),
            marker=dict(symbol="x", size=7)
        ))
        mean_all = weekly[["avg_np", "avg_power"]].stack().mean()
        fig2.add_hline(
            y=mean_all,
            line_dash="dot",
            line_color="red",
            annotation_text=f"Gesamtmittelwert: {round(mean_all)} W",
            annotation_position="top left"
        )
        fig2.update_layout(
            title="Normalisierte Leistung vs. Ø Leistung",
            xaxis_title="Kalenderwoche",
            yaxis_title="Watt",
            xaxis_tickangle=45,
            template="training_dashboard_light",
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)

    elif view_option == "IF & TSS":
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=weekly["week_label"],
            y=weekly["avg_if"],
            mode="lines+markers",
            name="Intensity Factor",
            marker=dict(symbol="diamond", size=8, color="#E31A1C"),
            line=dict(color="#E31A1C", width=3),
            yaxis="y1"
        ))
        fig3.add_trace(go.Scatter(
            x=weekly["week_label"],
            y=weekly["total_tss"],
            mode="lines+markers",
            name="TSS",
            marker=dict(symbol="circle", size=7, color="#1F78B4"),
            line=dict(color="#1F78B4", width=2),
            yaxis="y2"
        ))
        fig3.update_layout(
            title="Intensity Factor & TSS kombiniert",
            xaxis=dict(title="Kalenderwoche", tickangle=45),
            yaxis=dict(title="Intensity Factor", range=[0, 1.5]),
            yaxis2=dict(title="TSS", overlaying="y", side="right", showgrid=False),
            template="training_dashboard_light",
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig3, use_container_width=True)

    selected_week = st.selectbox("Woche auswählen", weekly["week_label"])
    selected_start = weekly.loc[weekly["week_label"] == selected_week, "week_start"].values[0]
    selected_end = pd.to_datetime(selected_start) + pd.Timedelta(days=6)
    week_df = df[(df["date"] >= pd.to_datetime(selected_start)) & (df["date"] <= selected_end)]

    st.markdown(f"### Aktivitäten in der Woche {selected_week}")

    for _, row in week_df.iterrows():
        with st.expander(f"{row['date'].date()} | NP: {row['normalized_power']} W | IF: {row['intensity_factor']:.2f}"):
            st.markdown(f"**TSS**: {row['tss']:.1f}")
            st.markdown(f"**Ø Leistung**: {row['avg_power']} W")
            st.markdown(f"**IF (Intensity Factor)**: {row['intensity_factor']:.2f}")

            try:
                fitfile = FitFile(get_user_fit_path(row["file_name"]))
                records = [r.get_values() for r in fitfile.get_messages("record") if "power" in r.get_values() or "heart_rate" in r.get_values()]
                df_rec = pd.DataFrame(records).dropna(subset=["power", "heart_rate"], how="all")

                if not df_rec.empty:
                    df_rec = df_rec.reset_index(drop=True)
                    df_rec["seconds"] = df_rec.index
                    df_rec["time_str"] = pd.to_datetime(df_rec["seconds"], unit="s").dt.strftime("%H:%M:%S")
                    df_rec["power_smooth"] = df_rec["power"].rolling(window=30, min_periods=1).mean()
                    df_rec["hr_smooth"] = df_rec["heart_rate"].rolling(window=15, min_periods=1).mean()

                    fig_pwr = go.Figure()
                    fig_pwr.add_trace(go.Scatter(
                        x=df_rec["time_str"],
                        y=df_rec["power_smooth"],
                        mode='lines',
                        name='30s Glättung (Watt)',
                        line=dict(color="#555555", width=2)
                    ))
                    fig_pwr.update_layout(
                        title="Powerverlauf (30s Mittelwert)",
                        xaxis_title="Zeit (hh:mm:ss)",
                        yaxis_title="Leistung (W)",
                        template="training_dashboard_light",
                        height=300
                    )
                    st.plotly_chart(fig_pwr, use_container_width=True)

                    fig_hr = go.Figure()
                    fig_hr.add_trace(go.Scatter(
                        x=df_rec["time_str"],
                        y=df_rec["hr_smooth"],
                        mode='lines',
                        name='Herzfrequenz (Ø)',
                        line=dict(color="#D72638", width=2)
                    ))
                    fig_hr.update_layout(
                        title="Herzfrequenzverlauf",
                        xaxis_title="Zeit (hh:mm:ss)",
                        yaxis_title="HF (bpm)",
                        template="training_dashboard_light",
                        height=300
                    )
                    st.plotly_chart(fig_hr, use_container_width=True)
                else:
                    st.info("Keine Power- oder Herzfrequenzdaten verfügbar.")
            except Exception as e:
                st.warning(f"Verläufe konnten nicht geladen werden: {e}")

            try:
                zones = compute_power_zones(get_user_fit_path(row["file_name"]))
                labels = [f"{z} ({format_duration(s)})" for z, s in zones.items()]
                fig_zones = go.Figure(data=[go.Pie(labels=labels, values=list(zones.values()), hole=.4)])
                fig_zones.update_layout(
                    title="Zeit in Leistungszonen",
                    template="training_dashboard_light",
                    legend_title="Zonen"
                )
                st.plotly_chart(fig_zones, use_container_width=True)
            except Exception as e:
                st.warning(f"Leistungszonen konnten nicht geladen werden: {e}")

            try:
                hr_zones = compute_hr_zones(get_user_fit_path(row["file_name"]))
                if hr_zones:
                    labels = [f"{z} ({format_duration(s)})" for z, s in hr_zones.items()]
                    fig_hrz = go.Figure(data=[go.Pie(labels=labels, values=list(hr_zones.values()), hole=.4)])
                    fig_hrz.update_layout(
                        title="Zeit in HF-Zonen",
                        template="training_dashboard_light",
                        legend_title="Zonen"
                    )
                    st.plotly_chart(fig_hrz, use_container_width=True)
            except Exception as e:
                st.warning(f"HF-Zonen konnten nicht geladen werden: {e}")
