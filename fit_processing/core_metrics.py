from fitparse import FitFile
import pandas as pd

def extract_core_metrics(filepath, user=None):
    try:
        fitfile = FitFile(filepath)
        records = []

        for record in fitfile.get_messages("record"):
            fields = {f.name: f.value for f in record}
            records.append(fields)

        df = pd.DataFrame(records)
        if df.empty or "timestamp" not in df.columns:
            print(f"⚠️ Keine gültigen Zeitstempel in Datei: {filepath}")
            return None

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Dauer-Berechnung: robustes Median-Intervall
        time_diffs = df["timestamp"].diff().dt.total_seconds().dropna()
        sampling_rate = time_diffs.median() if not time_diffs.empty else 1.0
        duration = round(sampling_rate * len(df), 2)

        # Alternativ: klassische Differenz Start–Ende
        # duration_alt = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds()

        distance = df["distance"].dropna().max() if "distance" in df.columns else None

        return {
            "start_time": df["timestamp"].iloc[0],
            "duration": duration,
            "distance": round(distance / 1000, 2) if distance else None  # in km
        }

    except Exception as e:
        print(f"❌ Fehler beim Verarbeiten von {filepath}: {e}")
        return None