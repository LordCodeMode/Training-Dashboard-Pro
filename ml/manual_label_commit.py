import os
import pandas as pd
import subprocess

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ML_DIR = os.path.join(BASE_DIR, "ml")

model_script = os.path.join(ML_DIR, "training_ml_model.py")
predict_script = os.path.join(ML_DIR, "predict_training_type.py")

# ✏️ Liste der Benutzer festlegen
users = ["max", "lisa", "paul"]

for user in users:
    user_cache = os.path.join(BASE_DIR, "cache", user)
    manual_labels_path = os.path.join(user_cache, "activities_with_manual_labels.csv")
    labels_output_path = os.path.join(user_cache, "activities_with_labels.csv")

    if os.path.exists(manual_labels_path) and os.path.exists(labels_output_path):
        df_main = pd.read_csv(labels_output_path)
        df_labels = pd.read_csv(manual_labels_path)

        df_main["start_time"] = pd.to_datetime(df_main["start_time"])
        df_labels["start_time"] = pd.to_datetime(df_labels["start_time"])

        df_main = df_main.drop(columns=["training_type"], errors="ignore")
        df = df_main.merge(df_labels, on="start_time", how="left")
        df = df.rename(columns={"manual_label": "training_type"})

        df.to_csv(labels_output_path, index=False)
        print(f"✅ Labels aktualisiert für Benutzer: {user}")

        subprocess.run(["python", model_script, user], check=True)
        subprocess.run(["python", predict_script, user], check=True)
        print(f"✅ Modell & Vorhersage abgeschlossen für Benutzer: {user}")
    else:
        print(f"⚠️ Dateien fehlen für Benutzer: {user}")