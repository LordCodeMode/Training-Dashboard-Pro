import os
import sqlite3
import pandas as pd
from utils.settings_access import DB_PATH  # ✅ zentrale Definition verwenden
from utils.user_paths import get_user_cache_path

def save_activities_export(user: str):
    """Exportiere alle Aktivitäten eines Benutzers als CSV."""
    try:
        print(f"[DEBUG] Starte Export der Aktivitäten für: '{user}'")

        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("SELECT * FROM activities WHERE user_id = ?", conn, params=(user,))

        if df.empty:
            print(f"[WARN] Keine Aktivitäten für Benutzer '{user}' – Export wird übersprungen.")
            return

        out_path = get_user_cache_path("activities.csv", user=user)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        df.to_csv(out_path, index=False)

        print(f"[OK] Aktivitäten-Export erfolgreich gespeichert für '{user}': {out_path}")
    except Exception as e:
        print(f"[ERROR] Fehler beim Aktivitäten-Export für Benutzer '{user}': {e}")