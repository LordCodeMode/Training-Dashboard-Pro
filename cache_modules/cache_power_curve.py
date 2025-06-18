# === Datei: cache_power_curve.py ===

import os
import numpy as np
from fit_processing.power_metrics_complete import compute_alltime_power_curve
from cache_modules.cache_helpers import get_all_file_names
from utils.user_paths import get_user_cache_path
from utils.settings_access import get_setting


def save_power_curve(user: str):
    try:
        print(f"[INFO] Berechne Powerkurve für Benutzer: '{user}'")
        filenames = get_all_file_names(user)
        if not filenames:
            print(f"[WARN] Keine FIT-Dateien für Benutzer '{user}' verfügbar.")
            return

        # 🚫 KEIN Gewicht hier verwenden – sonst ist die gespeicherte .npy dauerhaft gewichtet!
        curve = compute_alltime_power_curve(filenames, user=user)

        if not curve or not isinstance(curve, list):
            print(f"[WARN] Keine gültige Powerkurve für '{user}' berechnet.")
            return

        out_path = get_user_cache_path("power_curve.npy", user=user)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        np.save(out_path, np.array(curve))
        print(f"[OK] Powerkurven-Cache gespeichert für Benutzer '{user}' → {out_path}")

    except Exception as e:
        print(f"[ERROR] Fehler bei Powerkurve für '{user}': {e}")