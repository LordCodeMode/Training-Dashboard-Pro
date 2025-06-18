import os
import pandas as pd
import sqlite3

from utils.auth import get_all_users
from utils.user_paths import get_current_user  # Fallback in der App
from utils.settings_access import DB_PATH

from cache_modules.cache_training_load import save_training_load
from cache_modules.cache_power_curve import save_power_curve
from cache_modules.cache_critical_power import save_critical_power_per_activity, save_critical_power
from cache_modules.cache_vo2max import save_vo2max_peak_estimates_multistage
from cache_modules.cache_efficiency import save_efficiency_factors
from cache_modules.cache_zones import save_zone_summaries
from cache_modules.cache_export import save_activities_export
from cache_modules.cache_best_values import save_best_power_values, save_power_bests_time_series
from cache_modules.cache_helpers import get_changed_files, migrate_add_critical_power_column

# === Mapping: Modulname → user-fähige Funktion ===
MODULES = {
    "training_load": lambda user: save_training_load(user=user),
    "power_curve": lambda user: save_power_curve(user=user),
    "cp_per_activity": lambda user: save_critical_power_per_activity(user=user),
    "cp_model": lambda user: save_critical_power(user=user),
    "vo2max": lambda user: save_vo2max_peak_estimates_multistage(user=user),
    "efficiency": lambda user: save_efficiency_factors(user=user),
    "zones": lambda user: save_zone_summaries(user=user),
    "export": lambda user: save_activities_export(user=user),
    "power_bests": lambda user: save_best_power_values(user=user),
    "power_time_series": lambda user: save_power_bests_time_series(user=user),
}

def remove_duplicate_activities(user):
    """
    Entfernt doppelte FIT-Dateien (gleiche Hashes) sowie Einträge ohne gültigen Benutzer.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("""
                SELECT id, start_time, file_name, file_size, file_hash
                FROM activities
                WHERE user_id = ?
            """, conn, params=(user,))

            before = len(df)
            df["key"] = df["file_hash"]
            keep_ids = df.drop_duplicates("key", keep="first")["id"]
            drop_ids = df.loc[~df["id"].isin(keep_ids), "id"]

            if not drop_ids.empty:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM power_zones WHERE activity_id IN ({','.join('?' for _ in drop_ids)})", drop_ids.tolist())
                cursor.execute(f"DELETE FROM hr_zones WHERE activity_id IN ({','.join('?' for _ in drop_ids)})", drop_ids.tolist())
                cursor.execute(f"DELETE FROM activities WHERE id IN ({','.join('?' for _ in drop_ids)})", drop_ids.tolist())
                conn.commit()
                print(f"🧹 {len(drop_ids)} doppelte Aktivitäten für '{user}' entfernt.")
            else:
                print(f"✅ Keine Duplikate für '{user}' gefunden.")

            # --- Bereinigung ungültiger Benutzer-Einträge ---
            cursor = conn.cursor()
            cursor.execute("DELETE FROM activities WHERE user_id IS NULL OR TRIM(user_id) = ''")
            cursor.execute("DELETE FROM power_zones WHERE user_id IS NULL OR TRIM(user_id) = ''")
            cursor.execute("DELETE FROM hr_zones WHERE user_id IS NULL OR TRIM(user_id) = ''")
            cursor.execute("DELETE FROM training_load WHERE user_id IS NULL OR TRIM(user_id) = ''")
            conn.commit()
            print("🧹 Ungültige Benutzer-Einträge entfernt.")

    except Exception as e:
        print(f"[ERROR] Fehler beim Entfernen von Duplikaten für '{user}': {e}")

def build_and_save_cache(user: str = None, modules: list[str] = None, selective: bool = True):
    """
    Baut alle oder ausgewählte Cache-Komponenten für einen oder mehrere Nutzer neu auf.
    """
    if user is None:
        try:
            user = get_current_user()
        except Exception:
            pass

    users = [user] if user else get_all_users()

    for u in users:
        if not u:
            print("[WARN] Benutzername ist leer – übersprungen.")
            continue

        print(f"\n🔁 Cache-Aufbau für Nutzer: {u}")

        remove_duplicate_activities(u)

        if selective:
            changed = get_changed_files(user_id=u)
            if not changed:
                print("[OK] Keine Dateiänderungen erkannt – Cache bleibt bestehen.")
                continue
            else:
                print(f"[INFO] {len(changed)} Datei(en) geändert – selektiver Cache-Rebuild...")

        active = modules or list(MODULES.keys())
        for key in active:
            try:
                print(f"[MODUL] {key} ...")
                MODULES[key](user=u)
            except Exception as e:
                print(f"[ERROR] Modul '{key}' für Nutzer '{u}' fehlgeschlagen: {e}")

def rebuild_single_cache(user: str = None, module_key: str = None):
    """
    Baut gezielt ein einzelnes Cache-Modul für einen Benutzer neu auf.
    """
    if module_key not in MODULES:
        print(f"[WARN] Modul '{module_key}' nicht bekannt.")
        print(f"🔎 Verfügbare: {', '.join(MODULES.keys())}")
        return

    if user is None:
        try:
            user = get_current_user()
        except Exception:
            raise ValueError("Kein Benutzer angegeben und kein aktueller Benutzer ermittelbar.")

    try:
        print(f"🔄 Starte gezielten Cache-Rebuild: {module_key} für {user}")
        MODULES[module_key](user=user)
        print(f"[OK] Modul '{module_key}' für '{user}' erfolgreich.")
    except Exception as e:
        print(f"[ERROR] Fehler im Modul '{module_key}' für '{user}': {e}")

if __name__ == "__main__":
    migrate_add_critical_power_column()
    build_and_save_cache(selective=False)