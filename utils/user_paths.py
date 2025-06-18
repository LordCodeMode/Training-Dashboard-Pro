import os
import streamlit as st

# Basisverzeichnisse
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
FIT_DIR = os.path.join(BASE_DIR, "fit_samples")

# === Benutzerverwaltung ===
def get_current_user() -> str:
    """Liefert den aktuell eingeloggten Benutzernamen (kleingeschrieben, getrimmt)."""
    user = st.session_state.get("current_user")
    if not user or not isinstance(user, str):
        st.error("❌ Kein Benutzer eingeloggt.")
        st.stop()
    return user.strip().lower()

# === Cache-Verzeichnisse ===
def get_user_cache_dir(user: str = None) -> str:
    """Gibt das Cache-Verzeichnis für einen Benutzer zurück und legt es bei Bedarf an."""
    user = user or get_current_user()
    path = os.path.join(CACHE_DIR, user)
    os.makedirs(path, exist_ok=True)
    return path

def get_user_cache_path(filename: str, user: str = None) -> str:
    """Gibt den vollständigen Pfad zu einer Cache-Datei für einen Benutzer zurück."""
    return os.path.join(get_user_cache_dir(user), filename)

# === FIT-Dateiverzeichnisse ===
def get_user_fit_dir(user: str = None) -> str:
    """Gibt das FIT-Dateiverzeichnis für einen Benutzer zurück und legt es bei Bedarf an."""
    user = user or get_current_user()
    path = os.path.join(FIT_DIR, user)
    os.makedirs(path, exist_ok=True)
    return path

def get_user_fit_path(filename: str, user: str = None) -> str:
    """Gibt den vollständigen Pfad zu einer FIT-Datei für einen Benutzer zurück."""
    return os.path.join(get_user_fit_dir(user), filename)