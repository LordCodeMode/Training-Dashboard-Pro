import os
import sqlite3
import pandas as pd
from utils.settings_access import DB_PATH  # ✅ zentraler DB-Pfad
from utils.user_paths import get_user_cache_path

def save_efficiency_factors(user: str):
    try:
        print(f"[INFO] Berechne EF für Nutzer: {user}")
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("""
                SELECT start_time, normalized_power, avg_heart_rate, intensity_factor
                FROM activities
                WHERE user_id = ?
                  AND normalized_power IS NOT NULL
                  AND avg_heart_rate IS NOT NULL
                  AND intensity_factor IS NOT NULL
            """, conn, params=(user,))

        if df.empty:
            print(f"[WARN] Keine validen EF-Daten für {user}.")
            return

        df["start_time"] = pd.to_datetime(df["start_time"])
        df["ef"] = df["normalized_power"] / df["avg_heart_rate"]
        df = df.dropna(subset=["ef", "intensity_factor"])
        df = df.sort_values("start_time")

        out_path = get_user_cache_path("efficiency_factors.csv", user=user)
        df.to_csv(out_path, index=False)
        print(f"[OK] EF-Cache für {user} gespeichert.")
    except Exception as e:
        print(f"[ERROR] Fehler bei EF-Berechnung für {user}: {e}")