import os
import numpy as np
import pandas as pd
import sqlite3
from fitparse import FitFile
import streamlit as st
from typing import List, Dict, Optional
from utils.settings_access import get_setting, DB_PATH
from fit_processing.power_zones import compute_power_zones
from utils.user_paths import get_user_fit_dir

# Coggan, A. R., & Allen, H. (2010). Training and Racing with a Power Meter (2nd ed.). VeloPress.
def calculate_np(power_series: List[float]) -> Optional[float]:
    s = pd.Series(power_series, dtype='float64')
    if len(s) < 180:
        return None
    rolled = s.rolling(window=30, min_periods=30).mean()
    mean_4th = (rolled.dropna() ** 4).mean()
    return round(mean_4th ** 0.25, 2) if pd.notna(mean_4th) else None

def calculate_tss(np: Optional[float], duration_s: float, ftp: Optional[float] = None, user: Optional[str] = None) -> Optional[float]:
    ftp = ftp or get_setting("ftp", 250, user=user)
    if not np or not duration_s or ftp <= 0:
        return None

    return round(((duration_s / 3600) * (np / ftp) ** 2) * 100, 2)


def calculate_if(np: Optional[float], ftp: Optional[float] = None, user: Optional[str] = None) -> Optional[float]:
    ftp = ftp or get_setting("ftp", 250, user=user)
    if not np or ftp <= 0:
        return None
    val = np / ftp
    return round(val, 3) if val < 1.5 else None

def calculate_ef(np: Optional[float], hr_avg: Optional[float]) -> Optional[float]:
    if np and hr_avg and hr_avg > 60:
        val = np / hr_avg
        return round(val, 3) if val < 3.0 else None
    return None

def rolling_best_powers(power_series: List[float]) -> Dict[str, Optional[float]]:
    s = pd.Series(power_series)
    windows = {
        "max_1min_power": 60,
        "max_3min_power": 180,
        "max_5min_power": 300,
        "max_10min_power": 600,
        "max_20min_power": 1200,
        "max_30min_power": 1800,
    }
    return {
        key: round(s.rolling(w, min_periods=w).mean().max(), 2) if len(s) >= w else None
        for key, w in windows.items()
    }

@st.cache_data(show_spinner=False)
def extract_power_series(filepath: str) -> List[float]:
    try:
        fitfile = FitFile(filepath)
        power_values = []

        for rec in fitfile.get_messages("record"):
            row = {f.name: f.value for f in rec}
            val = row.get("power")

            if isinstance(val, (int, float)) and pd.notna(val):
                val = float(val)
                if val >= 0:  # 0-Watt-Daten mit aufnehmen, aber nicht negativ
                    power_values.append(val)

        if not power_values or len(power_values) < 30:
            print(f"[DEBUG] ⚠️ Ungültig oder zu wenig Powerdaten in: {filepath} (n={len(power_values)})")
            return []

        avg = round(np.mean(power_values), 2)
        max_p = round(np.max(power_values), 2)
        print(f"[DEBUG] Powerdaten in {filepath}: Einträge={len(power_values)}, Ø={avg} W, Max={max_p} W")

        return power_values

    except Exception as e:
        print(f"⚠️ Fehler bei Powerextraktion von {filepath}: {e}")
        return []


def compute_power_curve(power_series: List[float]) -> Optional[List[float]]:
    if not power_series or len(power_series) < 3:
        return None

    s = pd.Series(power_series, dtype="float64").dropna()
    if s.empty:
        return None

    curve = [
        round(s.rolling(window=i, min_periods=i).mean().max(), 2)
        for i in range(1, len(s) + 1)
    ]
    return curve if any(pd.notna(v) for v in curve) else None

@st.cache_data(show_spinner=True)
def compute_alltime_power_curve(
    filenames: List[str],
    weight: Optional[float] = None,
    user: Optional[str] = None
) -> List[float]:

    from fit_processing.power_metrics_complete import extract_power_series, compute_power_curve
    from utils.user_paths import get_user_fit_dir

    all_curves = []
    fit_dir = get_user_fit_dir(user)

    for fname in filenames:
        fit_path = os.path.join(fit_dir, fname)
        power = extract_power_series(fit_path)

        if not power or len(power) < 30:
            continue

        if weight:
            power = [p / weight for p in power]

        curve = compute_power_curve(power)
        if not curve or all(v is None for v in curve):
            continue

        all_curves.append(curve)

    if not all_curves:
        return []

    max_len = max(len(c) for c in all_curves)
    padded = [np.pad(c, (0, max_len - len(c)), constant_values=np.nan) for c in all_curves]
    return np.nanmax(padded, axis=0).tolist()

@st.cache_data(show_spinner=True)
def compute_last_activity_power_curve(user: str, weight: Optional[float] = None) -> List[float]:
    from fit_processing.power_metrics_complete import extract_power_series, compute_power_curve
    from utils.user_paths import get_user_fit_dir

    fit_dir = get_user_fit_dir(user)
    files = sorted(os.listdir(fit_dir), reverse=True)

    for fname in files:
        path = os.path.join(fit_dir, fname)
        power = extract_power_series(path)

        if power and len(power) >= 30:
            if weight:
                power = [p / weight for p in power]

            curve = compute_power_curve(power)
            if curve and any(pd.notna(v) for v in curve):
                return curve

    print("[WARN] Keine gültige Powerkurve in den letzten Dateien gefunden.")
    return []

def get_best_power_data(column_name: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(f"""
            SELECT start_time, {column_name} AS Power
            FROM activities
            WHERE {column_name} IS NOT NULL
            ORDER BY start_time
        """, conn)

def compute_power_zones_for_files(file_names: List[str], ftp: Optional[float] = None, user: Optional[str] = None) -> Dict[str, int]:
    from collections import defaultdict
    ftp = ftp or get_setting("ftp", 250, user=user)
    zone_totals = defaultdict(int)
    fit_dir = get_user_fit_dir(user)
    for fname in file_names:
        try:
            path = os.path.join(fit_dir, fname)
            zones = compute_power_zones(path, ftp=ftp, user=user)
            for label, seconds in zones.items():
                zone_totals[label] += seconds
        except Exception as e:
            print(f"⚠️ Fehler bei {fname}: {e}")
    return dict(zone_totals)

def extract_power_metrics(df: pd.DataFrame, hr_avg: Optional[float] = None, user: Optional[str] = None, return_stream=False) -> Dict:
    if "power" not in df.columns or df["power"].dropna().empty:
        return {}
    if "timestamp" not in df.columns:
        return {}

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # === Bewegungszeit berechnen statt Gesamtzeit
        if "speed" in df.columns:
            moving_mask = df["speed"].fillna(0) > 0.5  # Schwellenwert für Bewegung
            duration_s = moving_mask.sum()  # 1 Hz: 1 Sekunde pro Zeile mit Bewegung
        else:
            duration_s = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds()
    except Exception as e:
        print(f"❌ Fehler bei Zeitberechnung: {e}")
        return {}

    power_series = df["power"].dropna().astype(float).tolist()
    np_val = calculate_np(power_series)

    if user is None:
        print("⚠️ Kein Benutzer angegeben – Standardwerte für FTP & Co. werden verwendet.")

    ftp_val = get_setting("ftp", 250, user=user)
    print(f"🔍 extract_power_metrics(): user={user}, ftp={ftp_val}, np={np_val}, duration={duration_s}")

    result = {
        "avg_power": round(np.mean(power_series), 2),
        "normalized_power": np_val,
        "tss": calculate_tss(np_val, duration_s, ftp=ftp_val, user=user),
        "intensity_factor": calculate_if(np_val, ftp=ftp_val, user=user),
        "efficiency_factor": calculate_ef(np_val, hr_avg),
        "duration": duration_s,
        **rolling_best_powers(power_series)
    }

    if return_stream:
        result["power_stream"] = power_series

    return result

# Skiba, P. F. (2006). Analysis of critical power and W′. University of Toledo.
def estimate_critical_power_model(filenames: List[str], user: Optional[str] = None) -> dict:
    if not filenames or not isinstance(filenames, list) or all(f is None or not isinstance(f, str) for f in filenames):
        print(f"[WARN] Leere oder ungültige Dateiliste – CP-Modell wird nicht berechnet.")
        return {}

    power_curve = compute_alltime_power_curve(filenames, user=user)

    if not power_curve or not isinstance(power_curve, list) or len(power_curve) < 300:
        print("⚠️ Ungültige oder unvollständige Powerkurve – mindestens 5 min erforderlich.")
        return {}

    try:
        min_sec = 5
        max_sec = min(len(power_curve), 3600)
        durations = np.arange(min_sec, max_sec + 1)
        curve_section = power_curve[min_sec - 1:max_sec]

        if len(durations) != len(curve_section):
            print("❌ Dauer und Kurvenlänge stimmen nicht überein.")
            return {}

        inv_t = 1 / durations
        A = np.vstack([inv_t, np.ones_like(inv_t)]).T
        result = np.linalg.lstsq(A, curve_section, rcond=None)[0]
        w_prime, cp = result[0], result[1]
        predicted = w_prime / durations + cp

        return {
            "durations": durations.tolist(),
            "actual": [round(v, 1) for v in curve_section],
            "predicted": [round(v, 1) for v in predicted],
            "critical_power": round(cp, 1),
            "w_prime": round(w_prime, 1),
            "min_sec": int(min_sec),
            "max_sec": int(max_sec),
            "source": "power_curve"
        }

    except Exception as e:
        print(f"[ERROR] Fehler bei CP-Modellschätzung: {e}")
        return {}