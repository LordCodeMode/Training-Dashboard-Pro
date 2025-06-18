import os
import json
import pandas as pd
from utils.settings_access import get_setting
from utils.user_paths import get_user_cache_path, get_current_user


# Garmin/Firstbeat Modellprinzipien (2014): VO₂max-Schätzung basiert auf NP/HR-Ratio während intensiver Einheiten
# Esteve-Lanao et al. (2005): Korrelation von Trainingsintensität (z. B. IF, TRIMP) mit VO₂max-Entwicklung
# Léger & Lambert (1982): Feldschätzungen über 5–10 Minuten Belastungen als Proxy für VO₂max


def get_vo2max_cache_path(user: str = None) -> str:
    return get_user_cache_path("vo2max_time_series.json", user=user or get_current_user())

def validate_vo2max(vo2_rel: float, vo2_abs: float, last_vals: list, hr: float, np_val: float) -> bool:
    if not (40 <= vo2_rel <= 75):
        return False
    if hr < 90 or (np_val / hr > 3.0):
        return False
    if last_vals:
        avg = sum(last_vals[-3:]) / min(3, len(last_vals))
        if abs(vo2_abs - avg) > 400:
            return False
    return True

def estimate_vo2max_from_dataframe(df: pd.DataFrame, user: str = None) -> list:
    weight = get_setting("weight", 70.0, user=user)
    max_hr = get_setting("hr_max", 190, user=user)

    if weight <= 0 or max_hr <= 0:
        raise ValueError("Ungültige Benutzerparameter: Gewicht oder maximale HF nicht gesetzt.")

    df = df.copy()
    df["start_time"] = pd.to_datetime(df["start_time"])
    df = df.sort_values("start_time")

    results = []
    valid_values = []
    factor_peak = 23.0
    drift_per_day = -0.03

    for _, row in df.iterrows():
        ts = row["start_time"]
        np_val = row.get("normalized_power")
        hr = row.get("avg_heart_rate")
        if_val = row.get("intensity_factor")
        dur = row.get("duration")
        p5 = row.get("max_5min_power")
        p10 = row.get("max_10min_power")

        estimation_done = False
# 1. Stufe
        if all(pd.notna([np_val, hr, if_val])) and if_val >= 0.75 and 300 <= dur <= 1500 and hr / max_hr >= 0.75:
            vo2_abs = (np_val / hr) * if_val * weight * factor_peak
            vo2_rel = vo2_abs / weight
            if validate_vo2max(vo2_rel, vo2_abs, valid_values, hr, np_val):
                vo2_abs = (sum(valid_values[-2:] + [vo2_abs]) / min(3, len(valid_values) + 1)) if valid_values else vo2_abs
                results.append({"timestamp": ts, "vo2max": round(vo2_abs, 1)})
                valid_values.append(vo2_abs)
                estimation_done = True
                continue
# 2. Stufe; Midgley et al. (2007): VO₂max ≈ 15 × (maximale 5min-Leistung) / Körpergewicht
        for p_peak in [p5, p10]:
            if pd.notna(p_peak) and p_peak > 0:
                vo2_rel_peak = (15 * p_peak) / weight
                vo2_abs_peak = vo2_rel_peak * weight
                if validate_vo2max(vo2_rel_peak, vo2_abs_peak, valid_values, hr, np_val):
                    vo2_abs_peak = (sum(valid_values[-2:] + [vo2_abs_peak]) / min(3, len(valid_values) + 1)) if valid_values else vo2_abs_peak
                    results.append({"timestamp": ts, "vo2max": round(vo2_abs_peak, 1)})
                    valid_values.append(vo2_abs_peak)
                    estimation_done = True
                    break

        if not estimation_done:
            if all(pd.notna([np_val, hr, if_val])) and if_val >= 0.6 and dur >= 1500 and hr / max_hr >= 0.65:
                if valid_values:
                    decay_days = (ts - pd.to_datetime(results[-1]["timestamp"])).days if results else 0
                    est_vo2 = max(0, valid_values[-1] + (drift_per_day * decay_days))
                    vo2_rel_est = est_vo2 / weight
                    if validate_vo2max(vo2_rel_est, est_vo2, valid_values, hr, np_val):
                        results.append({"timestamp": ts, "vo2max": round(est_vo2, 1)})
                        valid_values.append(est_vo2)

    df_result = pd.DataFrame(results)
    if not df_result.empty:
        df_result["timestamp"] = pd.to_datetime(df_result["timestamp"])
        df_result = df_result.sort_values("timestamp")
        df_result["vo2max"] = df_result["vo2max"].rolling(window=5, center=True, min_periods=1).median()
        results = [{"timestamp": ts.isoformat(), "vo2max": round(vo2, 1)} for ts, vo2 in zip(df_result["timestamp"], df_result["vo2max"])]

    return results

def save_vo2max_time_series(results, user: str = None, path: str = None):
    if not results:
        print("[WARN] Keine VO₂max-Daten zum Speichern übergeben.")
        return

    try:
        if path is None:
            path = get_vo2max_cache_path(user=user)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[OK] VO₂max-Zeitreihe gespeichert: {len(results)} Einträge → {path}")
    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern der VO₂max-Datei: {e}")
