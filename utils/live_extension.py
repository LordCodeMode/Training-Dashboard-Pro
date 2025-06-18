import pandas as pd
from fitparse import FitFile
from utils.settings_access import get_setting
from fit_processing.core_metrics import extract_core_metrics
from fit_processing.heart_rate_metrics import extract_hr_series
from fit_processing.power_metrics_complete import (
    extract_power_series, calculate_np, calculate_if, calculate_tss, calculate_ef
)


def get_live_extension_rows(paths: list[str], user: str = None) -> pd.DataFrame:
    """Ergänze Aktivitäten-Datenframe mit live berechneten Werten aus neuen FIT-Dateien."""
    if not paths:
        return pd.DataFrame()

    # Benutzer-spezifische Einstellungen laden
    FTP = get_setting("ftp", default=250, user=user)
    WEIGHT = get_setting("weight", default=70, user=user)
    HR_MAX = get_setting("hr_max", default=190, user=user)

    rows = []

    for path in paths:
        try:
            core = extract_core_metrics(path)
            if not core or "start_time" not in core:
                continue

            try:
                fitfile = FitFile(path)
                records = [
                    {field.name: field.value for field in rec if field.value is not None}
                    for rec in fitfile.get_messages("record")
                ]
                df = pd.DataFrame(records)
            except Exception:
                df = None

            power_series = extract_power_series(path)
            duration = core.get("duration")
            distance = core.get("distance")
            start_time = core.get("start_time")

            if not power_series or duration is None or start_time is None:
                continue

            np_val = calculate_np(power_series)
            tss = calculate_tss(np_val, duration, ftp=FTP)
            if_val = calculate_if(np_val, ftp=FTP)
            ef_val = None

            if df is not None and "heart_rate" in df.columns:
                hr_avg = df["heart_rate"].dropna().mean()
                ef_val = calculate_ef(np_val, hr_avg)

            rows.append({
                "start_time": start_time,
                "duration": duration,
                "distance": distance,
                "tss": tss,
                "normalized_power": np_val,
                "intensity_factor": if_val,
                "efficiency_factor": ef_val,
            })

        except Exception as e:
            print(f"[WARN] Fehler bei Live-Analyse von {path}: {e}")
            continue

    return pd.DataFrame(rows)