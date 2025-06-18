# === Datei: cache_zone_summaries.py ===

import os
import sqlite3
import pandas as pd
from collections import defaultdict
from utils.user_paths import get_user_cache_path
from fit_processing.power_zones import compute_power_zones
from fit_processing.heart_rate_metrics import compute_hr_zones
from cache_modules.cache_helpers import get_all_file_names, get_activity_id_from_filename
from utils.settings_access import DB_PATH  # ⬅️ Neuer Import für DB_PATH

def save_zone_summaries(user: str):
    try:
        print(f"[DEBUG] Starte Zonen-Zusammenfassungen für: '{user}'")
        filenames = get_all_file_names(user)
        pzones_total = defaultdict(int)
        hzones_total = defaultdict(int)
        pzones_detailed = []

        fit_dir = os.path.join(os.path.dirname(DB_PATH), "fit_samples")  # Benutzer-FIT-Verzeichnis

        for fname in filenames:
            path = os.path.join(fit_dir, user, fname)
            activity_id = get_activity_id_from_filename(fname, user_id=user)

            try:
                # ✅ Benutzer mitgeben
                pz = compute_power_zones(path, user=user)
                if isinstance(pz, dict):
                    for label, sec in pz.items():
                        pzones_total[label] += sec
                        pzones_detailed.append({
                            "activity_id": activity_id,
                            "zone_label": label,
                            "seconds_in_zone": sec,
                            "user_id": user
                        })
            except Exception as e:
                print(f"[WARN] Fehler bei Powerzonen ({user} – {fname}): {e}")

            try:
                # ✅ Benutzer mitgeben
                hz = compute_hr_zones(path, user=user)
                if isinstance(hz, dict):
                    for label, sec in hz.items():
                        hzones_total[label] += sec
            except Exception as e:
                print(f"[WARN] Fehler bei HF-Zonen ({user} – {fname}): {e}")

        df_power_summary = pd.DataFrame(pzones_total.items(), columns=["zone", "seconds"])
        df_power_detailed = pd.DataFrame(pzones_detailed)
        df_hr_summary = pd.DataFrame(hzones_total.items(), columns=["zone", "seconds"])
        df_power_summary["user_id"] = user
        df_hr_summary["user_id"] = user

        df_power_summary.to_csv(get_user_cache_path("power_zones_summary.csv", user), index=False)
        df_power_detailed.to_csv(get_user_cache_path("power_zones_detailed.csv", user), index=False)
        df_hr_summary.to_csv(get_user_cache_path("hr_zones_summary.csv", user), index=False)

        print(f"[OK] Zonen-Zusammenfassungen gespeichert für '{user}'.")
    except Exception as e:
        print(f"[ERROR] Fehler bei Zonen-Zusammenfassungen für '{user}': {e}")