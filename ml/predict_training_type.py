import os
import sys
import json
import pandas as pd
import joblib

# === Projektverzeichnis zur sys.path hinzufügen (für utils etc.) ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.user_paths import get_user_cache_path

# === ML-Verzeichnisse ===
ML_DIR = os.path.join(BASE_DIR, "ml")
MODEL_PATH = os.path.join(ML_DIR, "saved_model.pkl")
SCALER_PATH = os.path.join(ML_DIR, "saved_scaler.pkl")
FEATURES_PATH = os.path.join(ML_DIR, "feature_names.json")


def run_prediction(user: str):
    activities_path = get_user_cache_path("activities.csv", user)
    output_path = get_user_cache_path("activities_with_predictions.csv", user)

    # === Existenz prüfen ===
    for path, label in [
        (activities_path, "Aktivitäten-Datei"),
        (MODEL_PATH, "Modell"),
        (SCALER_PATH, "Scaler"),
        (FEATURES_PATH, "Feature-Liste")
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ {label} nicht gefunden: {path}")

    # === Laden
    df = pd.read_csv(activities_path)
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    with open(FEATURES_PATH, "r") as f:
        trained_features = json.load(f)

    # === Feature-Vorauswahl
    missing = [f for f in trained_features if f not in df.columns]
    if missing:
        raise ValueError(f"❌ Fehlende Spalten in activities.csv: {missing}")

    X = df[trained_features].fillna(0)

    # === Skalieren & Vorhersage
    X_scaled = scaler.transform(X)
    df["predicted_training_type"] = model.predict(X_scaled)

    # === Speichern
    df.to_csv(output_path, index=False)
    print(f"✅ Vorhersagen gespeichert unter: {output_path}")


# === CLI-Einstiegspunkt
if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("❌ Kein Benutzer angegeben.\nBeispiel: python predict_training_type.py max")

    user_arg = sys.argv[1]
    run_prediction(user_arg)