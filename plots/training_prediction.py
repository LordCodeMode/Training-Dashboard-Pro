import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import subprocess
import plotly.io as pio
from utils.user_paths import get_current_user, get_user_cache_path
from utils.settings_access import get_setting

# === Plot-Theme aktivieren ===
pio.templates.default = "training_dashboard_light"

# === Farben pro Klasse ===
COLOR_MAP = {
    "Grundlage": "#aec7e8",
    "Tempo": "#ffbb78",
    "Schwelle": "#98df8a",
    "VO2max": "#ff9896",
    "unclassified": "#c7c7c7"
}

# === Skriptpfade ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_SCRIPT = os.path.join(BASE_DIR, "ml", "training_ml_model.py")
PREDICT_SCRIPT = os.path.join(BASE_DIR, "ml", "predict_training_type.py")

def render():
    user = get_current_user()
    st.title("Trainingsklassifikation")

    # === Nutzerpfade
    activities_path = get_user_cache_path("activities.csv", user=user)
    predictions_path = get_user_cache_path("activities_with_predictions.csv", user=user)
    manual_label_path = get_user_cache_path("activities_with_manual_labels.csv", user=user)

    # === Vorhersage notwendig?
    needs_prediction = (
        not os.path.exists(predictions_path) or
        os.path.getmtime(predictions_path) < os.path.getmtime(activities_path)
    )

    if needs_prediction:
        st.warning("⚠️ Vorhersagen veraltet oder fehlen – führe Klassifikation durch...")
        try:
            subprocess.run(["python", PREDICT_SCRIPT, user], check=True)
            st.success("✅ Vorhersagen neu generiert.")
            df = pd.read_csv(predictions_path)
        except Exception as e:
            st.error("❌ Fehler bei Vorhersage:")
            st.code(str(e))
            return
    else:
        df = pd.read_csv(predictions_path)

    if "predicted_training_type" not in df.columns:
        st.error("❌ 'predicted_training_type' fehlt in den Daten.")
        return

    # === Manuelle Labels einlesen
    if os.path.exists(manual_label_path):
        manual_df = pd.read_csv(manual_label_path)
        if "manual_label" not in manual_df.columns:
            manual_df["manual_label"] = None
        df = df.merge(manual_df, on="start_time", how="left")
    else:
        df["manual_label"] = None

    # === Balkendiagramm anzeigen
    st.subheader("Verteilung der Trainingsarten")
    label_counts = df["manual_label"].fillna(df["predicted_training_type"])
    summary = label_counts.value_counts().reset_index()
    summary.columns = ["Klasse", "Anzahl"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["Klasse"],
        y=summary["Anzahl"],
        marker_color=[COLOR_MAP.get(k, "gray") for k in summary["Klasse"]],
        text=summary["Anzahl"],
        textposition="outside"
    ))
    fig.update_layout(
        template="training_dashboard_light",
        height=400,
        xaxis_title="Trainingsart",
        yaxis_title="Anzahl",
        bargap=0.2,
        margin=dict(t=40, b=40, l=40, r=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # === Editierbare Labels
    st.subheader("Letzte Einheiten manuell überprüfen")
    df["start_time"] = pd.to_datetime(df["start_time"])
    editable = df.sort_values("start_time", ascending=False).head(5).copy()

    label_options = list(COLOR_MAP.keys())
    for i in editable.index:
        row = editable.loc[i]
        default = row["manual_label"] if pd.notna(row["manual_label"]) else row["predicted_training_type"]
        selection = st.selectbox(
            f"{row['start_time'].strftime('%Y-%m-%d %H:%M')} | {int(row['duration'])}s | IF: {row['intensity_factor']:.2f}",
            label_options,
            index=label_options.index(default) if default in label_options else 0,
            key=f"label_{i}"
        )
        df.loc[df["start_time"] == row["start_time"], "manual_label"] = selection

    # === Speichern & Modell
    if st.button("💾 Speichern & Modell trainieren"):
        save_df = df[["start_time", "manual_label"]].dropna().drop_duplicates(subset=["start_time"])
        if save_df.empty:
            st.error("❌ Keine gültigen Labels zum Speichern gefunden.")
            return

        save_df.to_csv(manual_label_path, index=False)
        st.success("✅ Manuelle Labels gespeichert.")

        with st.spinner("Trainiere Modell..."):
            train_result = subprocess.run(["python", MODEL_SCRIPT, user], capture_output=True, text=True)
            if train_result.returncode == 0:
                st.success("✅ Modell erfolgreich trainiert.")
            else:
                st.error("❌ Fehler beim Training:")
                st.code(train_result.stderr)

        with st.spinner("Generiere neue Vorhersagen..."):
            predict_result = subprocess.run(["python", PREDICT_SCRIPT, user], capture_output=True, text=True)
            if predict_result.returncode == 0:
                st.success("✅ Vorhersagen aktualisiert.")
            else:
                st.error("❌ Fehler bei Vorhersagen:")
                st.code(predict_result.stderr)

    # === Vorschautabelle
    st.subheader("Vorschau: Aktivitäten")
    cols = [
        "start_time", "duration", "intensity_factor", "normalized_power", "tss",
        "avg_power", "efficiency_factor", "avg_heart_rate", "distance",
        "predicted_training_type", "manual_label"
    ]
    st.dataframe(df[[c for c in cols if c in df.columns]])