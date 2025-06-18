import os
import sqlite3
import hashlib
import pandas as pd
from typing import List, Dict, Tuple
from utils.settings_access import DB_PATH  # ✅ neue zentrale Quelle für den DB-Pfad
from utils.user_paths import get_user_fit_dir

def migrate_add_critical_power_column():
    """Fügt der Tabelle 'activities' die Spalte 'critical_power' hinzu, falls sie nicht existiert."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(activities)")
            columns = [col[1] for col in cursor.fetchall()]
            if "critical_power" not in columns:
                cursor.execute("ALTER TABLE activities ADD COLUMN critical_power REAL")
                conn.commit()
                print("[MIGRATION] Spalte 'critical_power' zur Tabelle 'activities' hinzugefügt.")
            else:
                print("[INFO] Spalte 'critical_power' ist bereits vorhanden.")
    except Exception as e:
        print(f"[ERROR] Fehler bei Migration (critical_power): {e}")

def get_all_file_names(user_id: str) -> List[str]:
    """Gibt alle FIT-Dateinamen eines Benutzers aus der Datenbank zurück."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(
                "SELECT file_name FROM activities WHERE user_id = ?",
                conn, params=(user_id,)
            )
        return df["file_name"].dropna().tolist() if not df.empty else []
    except Exception as e:
        print(f"[ERROR] Fehler beim Abruf der Dateinamen für '{user_id}': {e}")
        return []

def get_file_metadata(user_id: str) -> Dict[str, Tuple[int, str]]:
    """Gibt ein Dictionary zurück: Dateiname → (Dateigröße, MD5-Hash) aus der Datenbank."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("""
                SELECT file_name, file_size, file_hash
                FROM activities
                WHERE user_id = ?
            """, conn, params=(user_id,))
        return {
            row["file_name"]: (row["file_size"], row["file_hash"])
            for _, row in df.iterrows()
        }
    except Exception as e:
        print(f"[ERROR] Fehler beim Abruf der Datei-Metadaten für '{user_id}': {e}")
        return {}

def get_changed_files(user_id: str) -> List[str]:
    """
    Vergleicht gespeicherte Metadaten mit Dateisystem.
    Gibt geänderte oder neue FIT-Dateien zurück.
    """
    changed_files = []
    metadata = get_file_metadata(user_id)
    fit_dir = get_user_fit_dir(user_id)

    if not os.path.isdir(fit_dir):
        return []

    for fname in os.listdir(fit_dir):
        path = os.path.join(fit_dir, fname)
        if not os.path.isfile(path):
            continue

        try:
            current_size = os.path.getsize(path)
            with open(path, "rb") as f:
                current_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"[WARN] Fehler beim Lesen von '{fname}': {e}")
            continue

        if fname not in metadata:
            changed_files.append(fname)
        else:
            old_size, old_hash = metadata[fname]
            if current_size != old_size or current_hash != old_hash:
                changed_files.append(fname)

    return changed_files

def get_activity_id_from_filename(filename: str, user_id: str) -> int:
    """Gibt die ID der Aktivität zu einer bestimmten FIT-Datei für einen Benutzer zurück."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            result = pd.read_sql_query("""
                SELECT id FROM activities
                WHERE file_name = ? AND user_id = ?
            """, conn, params=(filename, user_id))
        if not result.empty:
            return int(result.iloc[0]["id"])
    except Exception as e:
        print(f"[ERROR] Fehler beim Abrufen der activity_id für '{filename}' ({user_id}): {e}")
    return -1