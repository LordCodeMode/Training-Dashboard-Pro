import pandas as pd
from fitparse import FitFile
from utils.settings_access import get_setting

# Seiler S. (2010). What is best practice for training intensity and duration distribution in endurance athletes?. International Journal of Sports Physiology and Performance.
# Herzfrequenz-Zonen relativ zum Maximalwert
HR_ZONES = {
    "Z1 (Erholung)": (0.50, 0.60),
    "Z2 (Grundlage)": (0.60, 0.70),
    "Z3 (GA2)": (0.70, 0.80),
    "Z4 (Schwelle)": (0.80, 0.90),
    "Z5 (VO2max)": (0.90, 1.00),
}

def extract_hr_series(df):
    try:
        if not isinstance(df, pd.DataFrame):
            print(f"❌ extract_hr_series: Ungültiger Typ: {type(df)}")
            return None

        if df.empty or "heart_rate" not in df.columns:
            return None

        df = df.dropna(subset=["heart_rate"])
        return df["heart_rate"].astype(int)
    except Exception as e:
        print(f"❌ Fehler beim Extrahieren der HF-Serie: {e}")
        return None

def compute_hr_zones(source, user=None):
    try:
        # Datenquelle interpretieren
        if isinstance(source, str):
            fitfile = FitFile(source)
            records = [
                {field.name: field.value for field in record if field.value is not None}
                for record in fitfile.get_messages("record")
            ]
            df = pd.DataFrame(records)

        elif isinstance(source, FitFile):
            records = [
                {field.name: field.value for field in record if field.value is not None}
                for record in source.get_messages("record")
            ]
            df = pd.DataFrame(records)

        elif isinstance(source, pd.DataFrame):
            df = source

        else:
            print(f"❌ compute_hr_zones: Ungültiger Eingabetyp: {type(source)}")
            return None

        # HF-Serie extrahieren
        hr_series = extract_hr_series(df)
        if hr_series is None or hr_series.empty:
            return None

        # Maximale HF laden (user-spezifisch!)
        max_hr = get_setting("hr_max", 190, user=user)
        if not isinstance(max_hr, (int, float)) or max_hr <= 0:
            print(f"❌ Ungültiger Maximalpuls: {max_hr}")
            return None

        # Zeit in Zonen berechnen
        zone_times = {}
        for label, (low, high) in HR_ZONES.items():
            lower = int(low * max_hr)
            upper = int(high * max_hr)
            in_zone = (hr_series >= lower) & (hr_series < upper)
            zone_times[label] = int(in_zone.sum())

        return zone_times

    except Exception as e:
        print(f"❌ Fehler in compute_hr_zones: {e}")
        return None

def compute_avg_hr(hr_series):
    return round(hr_series.mean(), 2) if hr_series is not None and not hr_series.empty else None

def compute_max_hr(hr_series):
    return int(hr_series.max()) if hr_series is not None and not hr_series.empty else None