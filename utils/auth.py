# === Datei: utils/auth.py ===

import json
import os
import streamlit as st

# Pfad zur Benutzerdatei
USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "users.json")

# === Nutzerverwaltung ===
def load_users():
    if not os.path.exists(USERS_PATH):
        return {}
    try:
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Fehler beim Laden der Nutzerdatei: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_PATH, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern der Nutzerdatei: {e}")

def get_all_users():
    """Gibt alle registrierten Benutzernamen als Liste zurück."""
    return list(load_users().keys())

# === Authentifizierung ===
def authenticate_user(username, password):
    users = load_users()
    return username in users and users[username].get("password") == password

def register_user(username, password):
    users = load_users()
    if username in users:
        return False  # Benutzer existiert bereits
    users[username] = {"password": password}
    save_users(users)
    return True

def require_login():
    if "current_user" not in st.session_state or not st.session_state["current_user"]:
        st.error("❌ Du musst eingeloggt sein, um diese Seite zu nutzen.")
        st.stop()