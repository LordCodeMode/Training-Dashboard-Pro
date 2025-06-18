import os
import sys
import json
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

# === Pfad setzen, damit utils importierbar ist (bei CLI-Aufruf)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.user_paths import get_user_cache_path, get_user_cache_dir

def train_model_for_user(user: str):
    # === Benutzerpfade
    cache_dir = get_user_cache_dir(user)
    ml_dir = os.path.join(cache_dir, "ml")
    os.makedirs(ml_dir, exist_ok=True)

    # === Pfade zu Input- und Output-Dateien
    activities_path = get_user_cache_path("activities_with_manual_labels.csv", user)
    eff_path = get_user_cache_path("efficiency_factors.csv", user)
    max_paths = {
        "max_5min_power": get_user_cache_path("max_5min_power.json", user),
        "max_10min_power": get_user_cache_path("max_10min_power.json", user),
        "max_20min_power": get_user_cache_path("max_20min_power.json", user),
    }
    model_path = os.path.join(ml_dir, "saved_model.pkl")
    scaler_path = os.path.join(ml_dir, "saved_scaler.pkl")
    features_path = os.path.join(ml_dir, "feature_names.json")

    def load_power_json(path, col_name):
        try:
            df = pd.read_json(path)
            for tcol in ["timestamp", "start_time", "date", "time"]:
                if tcol in df.columns:
                    df["start_time"] = pd.to_datetime(df[tcol])
                    break
            else:
                print(f"⚠️ Keine Zeitspalte in {os.path.basename(path)} erkannt.")
                return pd.DataFrame()
            df = df.rename(columns={"Power": col_name})
            return df[["start_time", col_name]]
        except Exception as e:
            print(f"❌ Fehler beim Laden von {path}: {e}")
            return pd.DataFrame()

    if not os.path.exists(activities_path):
        raise FileNotFoundError(f"❌ Gelabelte Aktivitäten nicht gefunden: {activities_path}")
    df = pd.read_csv(activities_path)
    df["start_time"] = pd.to_datetime(df["start_time"])

    # === Effizienzfaktoren (optional)
    eff = pd.read_csv(eff_path) if os.path.exists(eff_path) else pd.DataFrame()
    if not eff.empty and "start_time" in eff.columns:
        eff["start_time"] = pd.to_datetime(eff["start_time"])
        df = pd.merge_asof(df.sort_values("start_time"), eff.sort_values("start_time"), on="start_time", direction="nearest")

    # === Power-Zusatzdaten (optional)
    for label, path in max_paths.items():
        addon = load_power_json(path, col_name=label)
        if not addon.empty:
            df = pd.merge_asof(df.sort_values("start_time"), addon.sort_values("start_time"), on="start_time", direction="nearest")

    # === Nur gelabelte Einträge verwenden
    df = df[df["manual_label"].notna() & (df["manual_label"] != "unclassified")]
    y = df["manual_label"]

    # === Feature-Auswahl
    all_possible_features = [
        "duration", "intensity_factor", "normalized_power", "tss",
        "avg_power", "avg_heart_rate", "efficiency_factor", "distance",
        "max_5sec_power", "max_1min_power", "max_5min_power",
        "max_10min_power", "max_20min_power"
    ]
    features = [f for f in all_possible_features if f in df.columns]
    if len(features) < 3:
        raise ValueError("❌ Zu wenige gültige Merkmale für das Modelltraining.")

    # === Training vorbereiten
    X = df[features].fillna(0)

    scaler = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=features)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # === Evaluation
    y_pred = model.predict(X_test)
    print(f"\n=== Klassifikationsbericht ({user}) ===")
    print(classification_report(y_test, y_pred))
    print("=== Konfusionsmatrix ===")
    print(confusion_matrix(y_test, y_pred))

    # === Speichern
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    with open(features_path, "w") as f:
        json.dump(features, f)
    print(f"\n✅ Modell, Skalierer & Featureliste gespeichert in '{ml_dir}' für Benutzer '{user}'.")


# === CLI-Einstieg
if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("❌ Kein Benutzer angegeben.\nBeispiel: python training_ml_model.py max")
    train_model_for_user(sys.argv[1])