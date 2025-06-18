import os
import json
import sqlite3
import pandas as pd
import numpy as np
from utils.settings_access import DB_PATH  # ✅ zentrale DB-Konstante
from utils.user_paths import get_user_fit_dir, get_user_cache_path
from fit_processing.power_metrics_complete import estimate_critical_power_model, extract_power_series
from cache_modules.cache_helpers import get_all_file_names, get_activity_id_from_filename

def validate_user(user: str):
    if not user or not isinstance(user, str) or not user.strip():
        raise ValueError(f"[FATAL] Ungültiger Benutzername: {user}")

def save_critical_power(user: str):
    try:
        validate_user(user)
        print(f"[DEBUG] Starte save_critical_power für: '{user}'")
        filenames = get_all_file_names(user)
        model = estimate_critical_power_model(filenames, user=user)
        required = {"durations", "actual", "predicted", "critical_power", "w_prime"}
        if not model or not required.issubset(model):
            print(f"[WARN] Ungültiges CP-Modell für {user} – übersprungen.")
            return

        out_path = get_user_cache_path("critical_power.json", user=user)
        with open(out_path, "w") as f:
            json.dump(model, f, indent=2)
        print(f"[OK] Critical Power Modell für {user} gespeichert.")
    except Exception as e:
        print(f"[ERROR] Fehler bei CP-Modell für {user}: {e}")

def save_critical_power_per_activity(user: str):
    try:
        validate_user(user)
        print(f"[DEBUG] Starte save_critical_power_per_activity für: '{user}'")
        fit_dir = get_user_fit_dir(user)
        filenames = get_all_file_names(user)
        if not filenames:
            print(f"[WARN] Keine FIT-Dateien für {user}.")
            return

        updates = []
        history = []

        for fname in filenames:
            path = os.path.join(fit_dir, fname)
            power = extract_power_series(path)
            if len(power) < 600:
                continue

            s = pd.Series(power)
            cp_estimates = []
            for dur in [180, 300, 1200]:  # 3min, 5min, 20min
                if len(s) >= dur:
                    avg = s.rolling(dur, min_periods=dur).mean().max()
                    if pd.notna(avg):
                        cp_estimates.append(avg)

            if not cp_estimates:
                continue

            cp_estimate = round(np.mean(cp_estimates), 1)
            updates.append((cp_estimate, fname, user))

            with sqlite3.connect(DB_PATH) as conn:
                df = pd.read_sql_query("""
                    SELECT start_time FROM activities
                    WHERE file_name = ? AND user_id = ?
                """, conn, params=(fname, user))
                if not df.empty:
                    timestamp = df.iloc[0]["start_time"]
                    history.append({"timestamp": timestamp, "critical_power": cp_estimate})

        if updates:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.executemany("""
                    UPDATE activities
                    SET critical_power = ?
                    WHERE file_name = ? AND user_id = ?
                """, updates)
                conn.commit()
            print(f"[OK] CP pro Aktivität gespeichert ({len(updates)} für {user}).")
        else:
            print(f"[WARN] Keine CP-Werte für {user} generiert.")

        if history:
            hist_path = get_user_cache_path("critical_power_history.json", user=user)
            os.makedirs(os.path.dirname(hist_path), exist_ok=True)
            with open(hist_path, "w") as f:
                json.dump(history, f, indent=2)
            print(f"[OK] CP-Verlauf für {user} gespeichert.")
    except Exception as e:
        print(f"[ERROR] Fehler bei CP pro Aktivität für {user}: {e}")