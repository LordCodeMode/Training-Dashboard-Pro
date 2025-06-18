# === Datei: reset_and_init_db.py ===

import os
import sqlite3
import shutil
import glob
from utils.auth import get_all_users
from utils.user_paths import get_user_cache_dir, get_user_fit_dir
from utils.settings_access import DB_PATH

# === 0. Alle FIT-Dateien je Benutzer löschen ===
print("🧹 Entferne alle FIT-Dateien ...")
for user in get_all_users():
    fit_dir = get_user_fit_dir(user)
    if os.path.exists(fit_dir):
        shutil.rmtree(fit_dir)
        print(f"🗑️ FIT-Verzeichnis gelöscht: {fit_dir}")

# === 1. Cache löschen ===
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
if os.path.exists(CACHE_DIR):
    shutil.rmtree(CACHE_DIR)
    print("🗑️ Alter Cache gelöscht.")
os.makedirs(CACHE_DIR, exist_ok=True)
print("📁 Neues Cache-Verzeichnis erstellt.")

# === 2. Datenbankdatei löschen ===
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"🗑️ Datenbank gelöscht: {DB_PATH}")
else:
    print("ℹ️ Keine alte Datenbank vorhanden.")

# === 3. Tabellenstruktur neu erstellen ===
try:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            start_time TEXT,
            file_name TEXT,
            avg_power REAL,
            avg_heart_rate REAL,
            normalized_power REAL,
            tss REAL,
            intensity_factor REAL,
            efficiency_factor REAL,
            max_5sec_power REAL,
            max_1min_power REAL,
            max_3min_power REAL,
            max_5min_power REAL,
            max_10min_power REAL,
            max_20min_power REAL,
            max_30min_power REAL,
            duration REAL,
            distance REAL,
            file_size INTEGER,
            file_hash TEXT,
            critical_power REAL
        );

        CREATE TABLE IF NOT EXISTS power_zones (
            activity_id INTEGER,
            zone_label TEXT,
            seconds_in_zone INTEGER,
            user_id TEXT NOT NULL,
            FOREIGN KEY(activity_id) REFERENCES activities(id)
        );

        CREATE TABLE IF NOT EXISTS hr_zones (
            activity_id INTEGER,
            zone_label TEXT,
            seconds_in_zone INTEGER,
            user_id TEXT NOT NULL,
            FOREIGN KEY(activity_id) REFERENCES activities(id)
        );

        CREATE TABLE IF NOT EXISTS training_load (
            date TEXT,
            ctl REAL,
            atl REAL,
            tsb REAL,
            user_id TEXT NOT NULL,
            PRIMARY KEY (date, user_id)
        );
        """)
        print("✅ Leere Datenbankstruktur erstellt.")

        # === 4. Entferne Einträge mit NULL-user_id (Fehlerquellen) ===
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM activities WHERE user_id IS NULL;")
                cursor.execute("DELETE FROM power_zones WHERE user_id IS NULL;")
                cursor.execute("DELETE FROM hr_zones WHERE user_id IS NULL;")
                cursor.execute("DELETE FROM training_load WHERE user_id IS NULL;")
                conn.commit()
                print("🧼 NULL-Einträge aus der Datenbank entfernt.")
        except Exception as e:
            print(f"❌ Fehler beim Entfernen von NULL-Einträgen: {e}")

except Exception as e:
    print(f"❌ Fehler beim Erstellen der Tabellen: {e}")

print("🚮 Reset abgeschlossen – System vollständig zurückgesetzt.")