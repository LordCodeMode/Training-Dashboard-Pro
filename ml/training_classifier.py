import os
import streamlit as st
import pandas as pd
from utils.user_paths import get_user_cache_path, get_current_user

# === Aktueller Benutzer
user = get_current_user()

# === Pfade korrekt setzen ===
CACHE_PATH = get_user_cache_path("activities.csv", user)
OUTPUT_PATH = get_user_cache_path("activities_with_labels.csv", user)

# === Daten laden ===
@st.cache_data
def load_activities(path):
    if not os.path.exists(path):
        st.error(f"❌ Datei nicht gefunden: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)

# === App-Start ===
st.title("Trainingsklassifikation – Heuristik")

df = load_activities(CACHE_PATH)

if df.empty:
    st.warning("Keine Daten geladen.")
    st.stop()

# === Interaktive Schwellwerte festlegen ===
st.sidebar.header("Klassifikationsregeln")
min_duration = st.sidebar.number_input("Min. Dauer für Grundlage (Sekunden)", value=3600)
if_z1 = st.sidebar.slider("IF-Grenze für Grundlage", 0.5, 0.95, (0.5, 0.75))
if_z2 = st.sidebar.slider("IF-Grenze für Tempo", 0.5, 1.1, (0.75, 0.85))
if_z3 = st.sidebar.slider("IF-Grenze für Schwelle", 0.5, 1.2, (0.85, 0.95))
if_z4 = st.sidebar.slider("IF-Grenze für VO₂max", 0.5, 1.5, 0.95)

# === Klassifikationslogik ===
def classify(row):
    if pd.isna(row.get("intensity_factor")) or row.get("duration", 0) < 300:
        return "unclassified"
    if row["intensity_factor"] < if_z1[1] and row["duration"] > min_duration:
        return "Grundlage"
    elif if_z2[0] <= row["intensity_factor"] < if_z2[1]:
        return "Tempo"
    elif if_z3[0] <= row["intensity_factor"] < if_z3[1]:
        return "Schwelle"
    elif row["intensity_factor"] >= if_z4:
        return "VO2max"
    return "unclassified"

# === Klassifikation anwenden
df["training_type"] = df.apply(classify, axis=1)

# === Tabelle anzeigen
columns_to_show = [col for col in ["start_time", "duration", "intensity_factor", "normalized_power", "tss", "training_type"] if col in df.columns]
st.dataframe(df[columns_to_show])

# === Speichern & Download
df.to_csv(OUTPUT_PATH, index=False)
st.download_button("📥 Download als CSV", df.to_csv(index=False), file_name="activities_with_labels.csv")