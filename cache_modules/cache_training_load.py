# === Datei: cache_training_load.py ===

import os
import sqlite3
import pandas as pd
from fit_processing.metrics_calc_new import calculate_training_load
from utils.user_paths import get_user_cache_path
from utils.settings_access import get_setting
from utils.settings_access import DB_PATH  # ⬅️ Direkt aus settings_access importieren

def save_training_load(user: str):
    """
    Berechnet CTL, ATL und TSB für einen bestimmten Benutzer
    und speichert das Ergebnis als CSV im benutzerspezifischen Cache.
    """
    try:
        print(f"[INFO] Berechne Training Load für Benutzer: '{user}'")

        # === Datenbankverfügbarkeit prüfen ===
        if not os.path.exists(DB_PATH):
            print(f"[ERROR] Datenbankpfad nicht gefunden: {DB_PATH}")
            return

        # === TSS-Daten für Benutzer laden ===
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(
                """
                SELECT start_time, tss
                FROM activities
                WHERE user_id = ?
                  AND tss IS NOT NULL
                  AND start_time IS NOT NULL
                """,
                conn,
                params=(user,)
            )

        if df.empty:
            print(f"[WARN] Keine gültigen TSS-Daten für Benutzer '{user}' – übersprungen.")
            return

        # === Trainingsbelastung berechnen ===
        df_load = calculate_training_load(df)
        if df_load.empty:
            print(f"[WARN] Ergebnis-DataFrame leer für Benutzer '{user}'.")
            return

        # === Cache-Datei schreiben ===
        out_path = get_user_cache_path("training_load.csv", user=user)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        df_load.to_csv(out_path, index=False)

        print(f"[OK] Training Load gespeichert für Benutzer '{user}' → {out_path}")

    except Exception as e:
        print(f"[ERROR] Fehler beim Training Load für Benutzer '{user}': {e}")