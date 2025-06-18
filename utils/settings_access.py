import os
import json
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from utils.user_paths import get_current_user

# === Benutzerbezogenes Einstellungsverzeichnis ===
SETTINGS_DIR = os.path.join("cache", "user_settings")
os.makedirs(SETTINGS_DIR, exist_ok=True)

# === Absoluter Pfad zur Datenbank ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "trainings.db")  # ⬅️ Wird zentral genutzt in DB-Zugriffen

# === Standardwerte ===
DEFAULTS = {
    "ftp": 250,
    "weight": 70,
    "hr_max": 190,
    "hr_rest": 60,
}

def get_settings_file(user: str = None) -> str:
    """Gibt den Pfad zur Einstellungsdatei eines Benutzers zurück."""
    try:
        if user is None:
            ctx = get_script_run_ctx()
            if ctx is None or "current_user" not in st.session_state:
                raise ValueError("❌ Kein Benutzer eingeloggt.")
            user = st.session_state["current_user"]
        if not user:
            raise ValueError("❌ Kein Benutzername angegeben.")
        return os.path.join(SETTINGS_DIR, f"{user}.json")
    except Exception as e:
        print(f"[WARN] get_settings_file(): {e}")
        return os.path.join(SETTINGS_DIR, "default.json")

def get_setting(key: str, default=None, user: str = None):
    """Liest eine bestimmte Einstellung für einen Benutzer."""
    try:
        path = get_settings_file(user)
        if os.path.exists(path):
            with open(path, "r") as f:
                settings = json.load(f)
                value = settings.get(key)
                if value is not None:
                    return value
    except Exception as e:
        print(f"[WARN] Fehler beim Lesen von Einstellung '{key}' für Benutzer '{user}': {e}")
    return DEFAULTS.get(key, default if default is not None else DEFAULTS.get(key))

def get_all_settings(user: str = None) -> dict:
    """Liefert alle Einstellungen für einen Benutzer, ergänzt um Defaults."""
    settings = DEFAULTS.copy()
    try:
        path = get_settings_file(user)
        if os.path.exists(path):
            with open(path, "r") as f:
                user_settings = json.load(f)
                for key in DEFAULTS:
                    if key in user_settings and user_settings[key] is not None:
                        settings[key] = user_settings[key]
    except Exception as e:
        print(f"[WARN] Fehler beim Laden der Einstellungen für Benutzer '{user}': {e}")
    return settings

def save_settings(user: str = None, new_settings: dict = None):
    """Speichert benutzerdefinierte Einstellungen dauerhaft im Cache."""
    if user is None:
        try:
            user = get_current_user()
        except Exception:
            user = "default"
    if not user:
        user = "default"

    try:
        path = get_settings_file(user)
        settings = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                settings = json.load(f)
        if new_settings:
            settings.update(new_settings)
            with open(path, "w") as f:
                json.dump(settings, f, indent=2)
            print(f"[OK] Einstellungen gespeichert für Benutzer '{user}': {new_settings}")
    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern der Einstellungen für Benutzer '{user}': {e}")