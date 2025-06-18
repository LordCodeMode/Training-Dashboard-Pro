import pandas as pd
from fitparse import FitFile
from utils.settings_access import get_setting  # Holt FTP aus Benutzereinstellungen

# Coggan A. (2003): “Power Training Levels”
# Definierte Zonenbereiche als Faktor vom FTP
ZONE_RANGES = {
    "Z1 (Recovery)": (0.0, 0.55),
    "Z2 (Endurance)": (0.55, 0.75),
    "Z3 (Tempo)": (0.75, 0.90),
    "Z4 (Schwelle)": (0.90, 1.05),
    "Z5 (VO2max)": (1.05, 1.20),
    "Z6 (Anaerob)": (1.20, 1.50),
    "Z7 (Sprint)": (1.50, 10.0)
}

def compute_power_zones(filepath: str, ftp: float = None, user: str = None) -> dict:
    """
    Berechnet die Zeit (in Sekunden), die in jeder Power-Zone verbracht wurde,
    basierend auf dem FTP-Wert. Nutzt den FTP-Wert aus Benutzereinstellungen,
    falls kein Wert übergeben wurde.

    Args:
        filepath: Pfad zur FIT-Datei
        ftp: Functional Threshold Power (optional)
        user: Benutzerkennung (für Multi-User-System)

    Returns:
        Dictionary mit Zone als Key und Zeit in Sekunden als Value
    """
    try:
        ftp = ftp or get_setting("ftp", 250, user=user)

        fitfile = FitFile(filepath)
        records = [{field.name: field.value for field in rec} for rec in fitfile.get_messages('record')]
        df = pd.DataFrame(records)

        if df.empty or "power" not in df.columns:
            print(f"⚠️ Keine Leistungsdaten in {filepath}")
            return {}

        df = df.dropna(subset=["power"])
        df["power"] = df["power"].astype(float)

        zone_seconds = {}
        for label, (low_factor, high_factor) in ZONE_RANGES.items():
            low_watt = low_factor * ftp
            high_watt = high_factor * ftp
            in_zone = df["power"].between(low_watt, high_watt, inclusive="left")
            zone_seconds[label] = int(in_zone.sum())

        return zone_seconds

    except Exception as e:
        print(f"❌ Fehler bei compute_power_zones({filepath}): {e}")
        return {}