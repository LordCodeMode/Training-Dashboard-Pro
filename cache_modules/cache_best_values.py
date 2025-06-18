import os
import json
import sqlite3
import pandas as pd
from utils.settings_access import DB_PATH  # ✅ Neue zentrale Konstante
from utils.user_paths import get_user_cache_path

def save_best_power_values(user: str):
    try:
        print(f"[DEBUG] Starte save_best_power_values für: '{user}'")

        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("""
                SELECT 
                    max(max_5sec_power) AS max_5sec_power,
                    max(max_1min_power) AS max_1min_power,
                    max(max_3min_power) AS max_3min_power,
                    max(max_5min_power) AS max_5min_power,
                    max(max_10min_power) AS max_10min_power,
                    max(max_20min_power) AS max_20min_power,
                    max(max_30min_power) AS max_30min_power
                FROM activities
                WHERE user_id = ?
            """, conn, params=(user,))

        if df.empty:
            print(f"[WARN] Keine Bestwerte für Nutzer '{user}' gefunden.")
            return

        result = df.iloc[0].dropna().to_dict()
        if not result:
            print(f"[WARN] Kein gültiger Leistungsdaten-Satz für Nutzer '{user}'.")
            return

        out_path = get_user_cache_path("power_best_values.json", user)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[OK] Power Bestwerte gespeichert für '{user}'.")

    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern der Leistungsbestwerte für '{user}': {e}")

def save_power_bests_time_series(user: str):
    try:
        print(f"[DEBUG] Starte save_power_bests_time_series für: '{user}'")

        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("""
                SELECT start_time,
                       max_1min_power, max_3min_power, max_5min_power,
                       max_10min_power, max_20min_power, max_30min_power
                FROM activities
                WHERE user_id = ? AND start_time IS NOT NULL
            """, conn, params=(user,))

        if df.empty:
            print(f"[WARN] Keine PB-Zeitreihen-Daten für Nutzer '{user}' vorhanden.")
            return

        df["start_time"] = pd.to_datetime(df["start_time"])
        durations = {
            "max_1min_power": "max_1min_power.json",
            "max_3min_power": "max_3min_power.json",
            "max_5min_power": "max_5min_power.json",
            "max_10min_power": "max_10min_power.json",
            "max_20min_power": "max_20min_power.json",
            "max_30min_power": "max_30min_power.json",
        }

        for col, filename in durations.items():
            if col in df.columns:
                out = df[["start_time", col]].dropna()
                out = out.rename(columns={col: "Power"})
                out["start_time"] = out["start_time"].astype(str)
                records = out.to_dict(orient="records")
                with open(get_user_cache_path(filename, user), "w") as f:
                    json.dump(records, f, indent=2)

        print(f"[OK] PB-Zeitreihen gespeichert für '{user}'.")

    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern der PB-Verläufe für '{user}': {e}")