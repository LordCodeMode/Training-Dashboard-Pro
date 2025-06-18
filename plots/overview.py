import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.formatting import format_duration
from fit_processing.metrics_calc_new import update_training_load_table, get_training_load_df
from utils.live_extension import get_live_extension_rows
from utils.user_paths import get_current_user, get_user_cache_path

def render():
    user = get_current_user()
    activities_path = get_user_cache_path("activities.csv")

    st.markdown("""
        <h2 style='display: flex; align-items: center; gap: 0.5rem;'>
            ▣ Aktuelle Trainingsübersicht
        </h2>
    """, unsafe_allow_html=True)

    if not os.path.exists(activities_path):
        st.error("❗️ Aktivitäten-Cache nicht gefunden.")
        return

    try:
        df = pd.read_csv(activities_path, parse_dates=["start_time"])
    except Exception as e:
        st.error(f"❗️ Fehler beim Laden des Aktivitäten-Caches: {e}")
        return

    if df.empty:
        st.warning("Keine Aktivitäten vorhanden.")
        return

    df = df[df["start_time"].notna()]

    live_key = "live_fit_paths_for_user_" + user
    if live_key in st.session_state:
        try:
            changed_paths = st.session_state[live_key]
            if changed_paths:
                live_rows = get_live_extension_rows(changed_paths, user=user)
                if not live_rows.empty:
                    df = pd.concat([df, live_rows], ignore_index=True)
                    df = df[df["start_time"].notna()]
                    df = df.drop_duplicates(subset=["file_hash", "user_id"], keep="last")
                    df = df.sort_values("start_time")
        except Exception as e:
            st.error(f"⚠️ Fehler bei Live-Ergänzung: {e}")

    start_of_week = pd.Timestamp.today().normalize() - pd.to_timedelta(pd.Timestamp.today().weekday(), unit='d')
    weekly = df[df["start_time"] >= start_of_week].copy()

    dur_sec = pd.to_numeric(weekly["duration"], errors="coerce").sum()
    tss_sum = pd.to_numeric(weekly["tss"], errors="coerce").sum()
    dist_sum = pd.to_numeric(weekly["distance"], errors="coerce").sum()
    count = len(weekly)
    dur_str = format_duration(dur_sec) if pd.notna(dur_sec) and dur_sec > 0 else "–"

    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🗓 Trainings", count)
        col2.metric("⏲ Gesamtzeit", dur_str)
        col3.metric("∑ TSS", round(tss_sum, 1) if pd.notna(tss_sum) else "–")
        col4.metric("→ Distanz (km)", round(dist_sum, 1) if pd.notna(dist_sum) else "–")

    try:
        update_training_load_table(user)
        df_load = get_training_load_df(user)
        df_load = df_load[df_load[["CTL", "ATL", "TSB"]].notna().all(axis=1)]

        if not df_load.empty:
            latest = df_load.iloc[-1]
            ctl, atl, tsb = latest["CTL"], latest["ATL"], latest["TSB"]

            st.markdown("<h4 style='margin-top: 2rem;'>⚙ Trainingszustand</h4>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("Fitness (CTL)", f"{ctl:.1f}")
            col2.metric("Fatigue (ATL)", f"{atl:.1f}")

            if tsb > 0:
                status, color = "Erholt", "#27ae60"
            elif tsb < -20:
                status, color = "Überlastet", "#e74c3c"
            else:
                status, color = "Belastet", "#f39c12"

            col3.markdown(f"""
                <div style='text-align: center; background: {color}; padding: 0.5rem 0.8rem; border-radius: 8px; color: white;'>
                    <strong>Form (TSB)</strong><br>{tsb:.1f} – {status}
                </div>
            """, unsafe_allow_html=True)

            st.caption("**CTL:** Fitness · **ATL:** kurzfristige Ermüdung · **TSB:** aktueller Zustand")
    except Exception as e:
        st.error(f"❗️ Fehler bei Trainingszustand-Berechnung: {e}")

    try:
        df["week"] = df["start_time"].dt.isocalendar().week
        df["year"] = df["start_time"].dt.isocalendar().year
        df["label"] = df["year"].astype(str) + "-W" + df["week"].astype(str).str.zfill(2)

        tss_df = df.groupby("label")["tss"].sum(min_count=1).reset_index().rename(columns={"tss": "TSS"})
        dist_df = df.groupby("label")["distance"].sum(min_count=1).reset_index().rename(columns={"distance": "Distanz"})
        trend = pd.merge(tss_df, dist_df, on="label", how="outer").fillna(0)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=trend["label"],
            y=trend["TSS"],
            name="TSS",
            marker_color="#6c9ef2",
            yaxis="y"
        ))
        fig.add_trace(go.Scatter(
            x=trend["label"],
            y=trend["Distanz"],
            name="Distanz (km)",
            mode="lines+markers",
            line=dict(color="#f79862"),
            yaxis="y2"
        ))

        fig.update_layout(
            title=f"↯ Leistungstrend ({len(trend)} Wochen)",
            xaxis=dict(title="Kalenderwoche", tickangle=45),
            yaxis=dict(title="TSS", titlefont=dict(color="#6c9ef2"), tickfont=dict(color="#6c9ef2")),
            yaxis2=dict(title="Distanz (km)", overlaying="y", side="right",
                        titlefont=dict(color="#f79862"), tickfont=dict(color="#f79862"), showgrid=False),
            template="training_dashboard_light",
            margin=dict(t=60, b=40, l=40, r=40),
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Fehler beim Zeichnen des Trends: {e}")

    st.markdown("### ⎛ Letzte Aktivitäten")
    df_table = df.sort_values("start_time", ascending=False).copy()
    df_table["Dauer"] = df_table["duration"].apply(format_duration)
    df_table = df_table.drop(columns=["duration"], errors="ignore").fillna("–")

    for _, row in df_table.head(10).iterrows():
        st.markdown(f"""
            <div style='border-radius: 12px; background: #f9f9f9; padding: 1rem; margin: 0.5rem 0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
                <div style='font-weight: 600; font-size: 1.1rem;'>🟢 {row.get('sport_type', 'Aktivität')} – {row['start_time'].strftime('%d.%m.%Y')}</div>
                <div style='margin-top: 0.3rem; font-size: 0.9rem;'>
                    Dauer: <strong>{row['Dauer']}</strong> · Distanz: <strong>{row.get('distance', '–')} km</strong> · TSS: <strong>{row.get('tss', '–')}</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("Alle Details anzeigen"):
        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            height=400
        )

    st.markdown("<div style='margin-top: 2rem; text-align: right;'>", unsafe_allow_html=True)
    if st.button("Neu berechnen", key="refresh_overview_tab"):
        try:
            from cache_modules.cache_export import save_activities_export
            from cache_modules.cache_training_load import save_training_load
            save_activities_export(user=user)
            save_training_load(user=user)
            st.success("Overview-Daten wurden erfolgreich neu berechnet.")
        except Exception as e:
            st.error(f"Fehler bei Neuberechnung: {e}")
    st.markdown("</div>", unsafe_allow_html=True)