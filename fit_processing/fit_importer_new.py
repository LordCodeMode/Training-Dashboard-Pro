import os
import sqlite3
import math
import hashlib
import traceback
import subprocess
from threading import Thread

import pandas as pd
from fitparse import FitFile
import streamlit as st

from fit_processing.core_metrics import extract_core_metrics
from fit_processing.power_metrics_complete import extract_power_metrics
from fit_processing.power_zones import compute_power_zones
from fit_processing.heart_rate_metrics import extract_hr_series, compute_hr_zones
from fit_processing.metrics_calc_new import update_training_load_table
from fit_processing.build_data_cache_new import build_and_save_cache
from utils.settings_access import get_setting, DB_PATH
from utils.user_paths import get_current_user

MIN_DURATION = 60        # Sekunden
MAX_DURATION = 8 * 3600  # 8 Stunden

def is_valid_number(value):
    return isinstance(value, (int, float)) and not math.isnan(value)

def compute_file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def fitfile_to_df(fitfile):
    records = []
    for record in fitfile.get_messages("record"):
        data = {field.name: field.value for field in record if field.value is not None}
        records.append(data)
    return pd.DataFrame(records)

def safe(source, key):
    if isinstance(source, dict):
        val = source.get(key)
        return val if is_valid_number(val) else None
    return None

def trigger_background_cache_rebuild(user: str, imported_paths: list[str] = None):
    def run():
        try:
            print(f"[INFO] Hintergrundprozess: Starte vollständigen Cache-Rebuild für Benutzer: {user} ...")
            if imported_paths:
                st.session_state[f"live_fit_paths_for_user_{user}"] = imported_paths
            build_and_save_cache(user=user, selective=False)
            if imported_paths:
                del st.session_state[f"live_fit_paths_for_user_{user}"]
            print(f"[INFO] Hintergrundprozess: Cache-Rebuild abgeschlossen für {user}.")
        except Exception as e:
            print(f"❌ Fehler im Hintergrund-Cache-Rebuild für {user}: {e}")

    Thread(target=run, daemon=True).start()

def trigger_prediction_after_import():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    prediction_script = os.path.join(BASE_DIR, "ml", "predict_training_type.py")
    if os.path.exists(prediction_script):
        try:
            result = subprocess.run(["python", prediction_script], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Vorhersagen erfolgreich aktualisiert.")
            else:
                print("❌ Fehler beim Ausführen des Prediction-Skripts:")
                print(result.stderr)
        except Exception as e:
            print(f"❌ Ausnahme beim Vorhersage-Trigger: {e}")
    else:
        print(f"❌ Vorhersage-Skript nicht gefunden: {prediction_script}")

def import_fit_files(paths):
    current_user = get_current_user()
    if not current_user:
        raise ValueError("❗️ Kein Benutzer gesetzt beim Import – Abbruch.")

    FTP = get_setting("ftp", default=250, user=current_user)
    WEIGHT = get_setting("weight", default=70, user=current_user)
    HR_MAX = get_setting("hr_max", default=190, user=current_user)

    # Öffnet Datenbankverbindung und bereitet Ergebnislisten vor
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    results = []
    imported_paths = []

    # Verhindert Doppelimporte auf Basis des Hashs + Benutzer-ID
    for path in paths:
        file_name = os.path.basename(path)
        file_hash = compute_file_hash(path)

        cursor.execute("""
            SELECT 1 FROM activities
            WHERE file_hash = ? AND user_id = ?
        """, (file_hash, current_user))
        if cursor.fetchone():
            results.append((file_name, "⚠️ Bereits vorhanden – übersprungen"))
            continue
    # Extrahiert alle record-Nachrichten.
    # Sortiert sie chronologisch.
        try:
            fitfile = FitFile(path)
            df = fitfile_to_df(fitfile)
            if "timestamp" not in df.columns:
                raise ValueError("Keine Timestamp-Spalte gefunden.")

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

    # Metriken extrahieren und berechnen
            core = extract_core_metrics(path)
            if core is None:
                raise ValueError("Konnte keine Kerndaten extrahieren.")

            hr_series = extract_hr_series(df)
            avg_hr = round(hr_series.mean(), 2) if isinstance(hr_series, pd.Series) and not hr_series.empty else None
            power = extract_power_metrics(df, hr_avg=avg_hr, user=current_user)

    # Fallback für unrealistische TSS Werte

            if power.get("tss") and power["tss"] > 500:
                power["tss"] = None
            if power.get("intensity_factor") and power["intensity_factor"] > 1.4:
                power["intensity_factor"] = None

            # === Bewegungszeit berechnen (inkl. Pausen bei Stillstand)
            try:
                if "speed" in df.columns and "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values("timestamp").reset_index(drop=True)

                    moving_mask = df["speed"].fillna(0) > 0.5
                    df["is_moving"] = moving_mask.astype(int)

                    # Bewegungszeit = Anzahl Sekunden mit Bewegung
                    duration_s = int(df["is_moving"].sum())
                    moving_duration = duration_s
                else:
                    # Fallback: Gesamtdifferenz der Zeitstempel
                    moving_duration = int((df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds())
            except Exception as e:
                print(f"❗️ Fehler bei Zeitberechnung im Importprozess: {e}")
                moving_duration = None

            # Dauer validieren aber nicht abbrechen
            if not is_valid_number(moving_duration) or moving_duration < MIN_DURATION or moving_duration > MAX_DURATION:
                print(f"⚠️ Warnung: Ungültige Dauer ({moving_duration}) – setze auf None")
                moving_duration = None

            start_time = core.get("start_time")
            if isinstance(start_time, pd.Timestamp):
                start_time = start_time.isoformat()

            file_size = os.path.getsize(path)

    # zentrale Metriken in der Activities Tabelle eingetragen
            data = (
                start_time, file_name,
                safe(power, "avg_power"), avg_hr,
                safe(power, "normalized_power"),
                safe(power, "tss"),
                safe(power, "intensity_factor"),
                safe(power, "efficiency_factor"),
                safe(power, "max_5sec_power"),
                safe(power, "max_1min_power"),
                safe(power, "max_3min_power"),
                safe(power, "max_5min_power"),
                safe(power, "max_10min_power"),
                safe(power, "max_20min_power"),
                safe(power, "max_30min_power"),
                moving_duration,
                safe(core, "distance"),
                file_size, file_hash,
                current_user
            )
    # Schreibt zentrale Metriken zur Aktivität in die activities-Tabelle.

            cursor.execute("""
                INSERT INTO activities (
                    start_time, file_name, avg_power, avg_heart_rate,
                    normalized_power, tss, intensity_factor, efficiency_factor,
                    max_5sec_power, max_1min_power, max_3min_power, max_5min_power,
                    max_10min_power, max_20min_power, max_30min_power,
                    duration, distance, file_size, file_hash, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            activity_id = cursor.lastrowid
        # wenn is_valid_number dann optionale Power und HF-Zonen Berechnung
            if is_valid_number(data[2]):
                try:
                    pzones = compute_power_zones(path, ftp=FTP, user=current_user)
                    for label, seconds in pzones.items():
                        if seconds > 0:
                            cursor.execute("""
                                INSERT INTO power_zones (activity_id, zone_label, seconds_in_zone, user_id)
                                VALUES (?, ?, ?, ?)
                            """, (activity_id, label, seconds, current_user))
                except Exception as e:
                    print(f"⚠️ Power-Zonen-Fehler für {file_name}: {e}")

            if is_valid_number(avg_hr):
                try:
                    hzones = compute_hr_zones(df, user=current_user)
                    for label, seconds in hzones.items():
                        if seconds > 0:
                            cursor.execute("""
                                INSERT INTO hr_zones (activity_id, zone_label, seconds_in_zone, user_id)
                                VALUES (?, ?, ?, ?)
                            """, (activity_id, label, seconds, current_user))
                except Exception as e:
                    print(f"⚠️ HF-Zonen-Fehler für {file_name}: {e}")

        # erfolgreich importierte Dateien werden festgehalten und in den Ergebnislisten geschrieben.

            conn.commit()
            imported_paths.append(path)

            msg = "✅ Erfolgreich importiert"
            if not is_valid_number(data[2]) and not is_valid_number(avg_hr):
                msg += " – ⚠️ keine Leistung & HF"
            elif not is_valid_number(data[2]):
                msg += " – ⚠️ keine Leistung"
            elif not is_valid_number(avg_hr):
                msg += " – ⚠️ keine HF"

            results.append((file_name, msg))

        # Rückgängig machen falls ein Fehler beim Import aufgetreten ist.

        except Exception as e:
            conn.rollback()
            print(f"❌ Fehler beim Import von {file_name}: {e}")
            traceback.print_exc()
            results.append((file_name, f"❌ Fehler: {str(e)}"))

    conn.close()

    # Hintergrundprozess starten, falls neue Dateien importiert wurden.
    if imported_paths:
        print(f"[INFO] Neue FIT-Dateien importiert: {len(imported_paths)}")
        try:
            update_training_load_table(user=current_user)
        except Exception as e:
            print(f"⚠️ Fehler bei Training Load Update: {e}")
        try:
            st.session_state["imported_fit_paths"] = imported_paths
            st.session_state["pending_rebuild"] = True
        except Exception as e:
            print(f"[WARN] Konnte Session-State nicht setzen: {e}")
        try:
            trigger_background_cache_rebuild(current_user)
        except Exception as e:
            print(f"❌ Fehler beim Cache-Rebuild: {e}")
        try:
            trigger_prediction_after_import()
        except Exception as e:
            print(f"❌ Fehler bei Trainingsklassifikation: {e}")

    return results
