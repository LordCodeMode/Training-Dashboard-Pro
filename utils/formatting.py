
# 📦 Zusatz: Dauer schön formatieren (z. B. "4m 12s")
def format_duration(seconds: float | int | None) -> str:
    """
    Formatiert Sekunden als Minuten + Sekunden-String (z. B. "4m 12s").
    Gibt "–" zurück, wenn Umrechnung nicht möglich ist.
    """
    try:
        seconds = float(seconds)
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    except:
        return "–"