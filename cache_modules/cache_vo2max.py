# === Datei: cache_vo2max_estimate.py ===

import os
import sqlite3
import pandas as pd
from utils.user_paths import get_user_cache_path
from fit_processing.vo2_max_estimate_model import (
    estimate_vo2max_from_dataframe,
    save_vo2max_time_series
)
from utils.settings_access import DB_PATH  # ← neuer zentraler Import

def save_vo2max_peak_estimates_multistage(user: str):
    print(f"[INFO] Starte VO₂max-Hochrechnung für Benutzer: {user}")
    try:
        if not os.path.exists(DB_PATH):
            print(f"[ERROR] Datenbankpfad nicht gefunden: {DB_PATH}")
            return

        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("""
                SELECT start_time, normalized_power, avg_heart_rate, intensity_factor, duration,
                       max_5min_power, max_10min_power
                FROM activities
                WHERE user_id = ?
                  AND normalized_power IS NOT NULL
                  AND avg_heart_rate IS NOT NULL
                  AND intensity_factor IS NOT NULL
                  AND duration >= 300
            """, conn, params=(user,))

        if df.empty:
            print(f"[WARN] Keine Aktivitäten für VO₂max-Berechnung für Benutzer '{user}'")
            return

        results = estimate_vo2max_from_dataframe(df)

        if results:
            out_path = get_user_cache_path("vo2max_time_series.json", user=user)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            save_vo2max_time_series(results, path=out_path)
            print(f"[OK] VO₂max-Zeitreihe gespeichert für '{user}': {len(results)} Einträge → {out_path}")
        else:
            print(f"[WARN] Keine validen VO₂max-Werte für Benutzer '{user}'.")
    except Exception as e:
        print(f"[ERROR] Fehler bei VO₂max-Berechnung für Benutzer '{user}': {e}")