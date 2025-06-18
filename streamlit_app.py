import os
import base64
from pathlib import Path

import streamlit as st
from streamlit_option_menu import option_menu
import plotly.io as pio
import plotly.graph_objects as go

from utils.auth import authenticate_user, register_user
from utils.user_paths import get_current_user
from utils.settings_access import get_all_settings, save_settings

# === Streamlit Page Config ===
st.set_page_config(page_title="Training Dashboard Pro", layout="wide", initial_sidebar_state="expanded")

# === Plotly Template Definition ===
custom_template = go.layout.Template(layout={
    "font": {"family": "Inter, sans-serif", "size": 14, "color": "#333"},
    "paper_bgcolor": "#fafafa",
    "plot_bgcolor": "#ffffff",
    "xaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
    "yaxis": {"gridcolor": "#e5e5e5", "zeroline": False},
    "margin": dict(t=40, b=40, l=40, r=20),
    "hoverlabel": {
        "bgcolor": "#ffffff",
        "bordercolor": "#ddd",
        "font": {"color": "#333"}
    }
})

pio.templates["training_dashboard_light"] = custom_template
pio.templates.default = "training_dashboard_light"

from plots import (
    overview, powercurve, critical_power, vo2max_trend, zone_summary,
    plot_best_values, zone_balance, rider_profile, hrzones, load_trend,
    fitness_state, efficiency, metrics, training_prediction, route_simulator
)
from fit_processing import fit_importer_new
from fit_processing.build_data_cache_new import build_and_save_cache


# === Session State ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = ""
if "mode" not in st.session_state:
    st.session_state.mode = "login"

# === Hintergrundbild vorbereiten (nur für Login-Ansicht verwenden!) ===
bg_path = Path("assets/my_background.jpg")
if bg_path.exists():
    with open(bg_path, "rb") as f:
        bg_bytes = f.read()
        bg_base64 = base64.b64encode(bg_bytes).decode()
        bg_url = f"data:image/jpeg;base64,{bg_base64}"
else:
    bg_url = ""

# === Nur anzeigen, wenn NICHT eingeloggt ===
if not st.session_state.logged_in:
    # === CSS Styling + Hintergrundbild ===
    st.markdown(f"""
        <style>
            html, body, .stApp {{
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: auto;
                font-family: 'Inter', sans-serif;
                background: none !important;
            }}

            .fullscreen-bg {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-image: url('{bg_url}');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                z-index: -999;
            }}

            .login-container {{
                position: relative;
                margin: 0 auto;
                margin-top: 8vh;
                background: rgba(255, 255, 255, 0.96);
                padding: 2.5rem 2rem;
                width: 360px;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
                text-align: center;
            }}

            .tabs {{
                display: flex;
                justify-content: space-between;
                gap: 0.5rem;
                margin-bottom: 1.5rem;
            }}

            .tab-button {{
                flex: 1;
                padding: 0.6rem 1rem;
                font-weight: 600;
                font-size: 1rem;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}

            .active-tab {{
                background-color: #419aff;
                color: white;
            }}

            .inactive-tab {{
                background-color: #e0e0e0;
                color: #333;
            }}

            .stTextInput {{
                margin-bottom: 1rem;
            }}

            .stTextInput input {{
                font-size: 1rem;
                padding: 0.5rem;
            }}

            .stButton > button {{
                background-color: #419aff;
                color: white;
                font-weight: 600;
                font-size: 1rem;
                padding: 0.6rem 1rem;
                width: 100%;
                border: none;
                border-radius: 6px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            }}
        </style>
        <div class="fullscreen-bg"></div>
    """, unsafe_allow_html=True)

    # === Titelbox zentriert über den Tabs ===
    st.markdown(f"""
        <div style='
            position: relative;
            margin: 0 auto;
            margin-top: 6vh;
            width: 320px;
            padding: 1rem 1.5rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
            text-align: center;
            font-size: 1.5rem;
            font-weight: 700;
            color: #222;
            z-index: 5;
        '>
            Training Dashboard Pro
        </div>
        <div style='height: 3rem;'></div>
    """, unsafe_allow_html=True)

    # === Login-Box ===
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown('<div class="tabs">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔐 Login"):
            st.session_state.mode = "login"
    with col2:
        if st.button("🆕 Registrieren"):
            st.session_state.mode = "register"
    st.markdown('</div>', unsafe_allow_html=True)

    # === Formular Inhalt ===
    if st.session_state.mode == "login":
        st.markdown("<h3>Login</h3>", unsafe_allow_html=True)
        username = st.text_input("Benutzername", key="login_user", placeholder="Benutzername", label_visibility="collapsed")
        password = st.text_input("Passwort", type="password", key="login_pw", placeholder="Passwort", label_visibility="collapsed")
        if st.button("Login senden"):
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("❌ Benutzername oder Passwort falsch.")

    elif st.session_state.mode == "register":
        st.markdown("<h3>Registrieren</h3>", unsafe_allow_html=True)
        new_username = st.text_input("Benutzername", key="reg_user", placeholder="Benutzername", label_visibility="collapsed")
        new_password = st.text_input("Passwort", type="password", key="reg_pw", placeholder="Passwort", label_visibility="collapsed")
        if st.button("Registrieren senden"):
            if register_user(new_username, new_password):
                st.success("✅ Registrierung erfolgreich. Bitte einloggen.")
                st.session_state.mode = "login"
            else:
                st.error("❌ Benutzername bereits vergeben.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# === Sidebar Navigation ===
with st.sidebar:
    user = get_current_user()
    st.markdown(f"**👤 Eingeloggt als:** `{user}`")

    selected_section = option_menu(
        menu_title=None,
        options=[
            "Übersicht", "Leistungsanalyse", "Herzfrequenz", "Trainingsbelastung",
            "Trainingsanalyse", "Streckensimulator", "Import", "Einstellungen"
        ],
        icons=[
            "grid", "battery-charging", "heart", "activity", "pie-chart", "map", "upload", "sliders"
        ],
        default_index=0
    )

    st.markdown("---")

    if st.button("↻ Neu berechnen"):
        with st.spinner("Baue Cache neu auf..."):
            build_and_save_cache(user=user, selective=False)
            st.success("Cache wurde vollständig neu berechnet.")
            st.cache_data.clear()
            st.info("Cache neu gebaut. Bitte Seite manuell neu laden.")

# === Seitenlogik ===
if selected_section == "Übersicht":
    overview.render()

elif selected_section == "Leistungsanalyse":
    tab_selection = option_menu(
        menu_title=None,
        options=[
            "Powerkurve", "Critical Power", "VO₂max", "Leistungszonen",
            "Bestwerte", "Zonenbalance", "Fahrertyp"
        ],
        icons=[
            "activity", "power", "wind", "sliders", "award", "layers", "person"
        ],
        orientation="horizontal",
        styles={
            "container": {"margin": "0 0 1.5rem 0", "padding": "0.4rem", "border-radius": "8px", "background-color": "#f2f2f2"},
            "nav-link": {
                "font-size": "14px", "font-weight": "500", "color": "#333", "padding": "8px 12px",
                "border-radius": "6px", "display": "flex", "align-items": "center", "gap": "0.4rem",
                "white-space": "nowrap"
            },
            "nav-link-selected": {
                "background-color": "#ffffff", "color": "#d72638",
                "box-shadow": "inset 0 -2px 0 #d72638"
            }
        }
    )

    if tab_selection == "Powerkurve":
        powercurve.render()
    elif tab_selection == "Critical Power":
        critical_power.render()
    elif tab_selection == "VO₂max":
        vo2max_trend.render_vo2max_plot()
    elif tab_selection == "Leistungszonen":
        zone_summary.render()
    elif tab_selection == "Bestwerte":
        plot_best_values.render()
    elif tab_selection == "Zonenbalance":
        zone_balance.render()
    elif tab_selection == "Fahrertyp":
        rider_profile.show_rider_profile()

elif selected_section == "Herzfrequenz":
    hrzones.render()

elif selected_section == "Trainingsbelastung":
    tab_selection = option_menu(
        menu_title=None,
        options=["TSB Verlauf", "Trainingszustand"],
        icons=["activity", "heart"],
        orientation="horizontal",
        styles={
            "container": {"margin": "0 0 1.5rem 0", "padding": "0.4rem", "border-radius": "8px", "background-color": "#f2f2f2"},
            "nav-link": {
                "font-size": "14px", "font-weight": "500", "color": "#333", "padding": "8px 12px",
                "border-radius": "6px", "display": "flex", "align-items": "center", "gap": "0.4rem",
                "white-space": "nowrap"
            },
            "nav-link-selected": {
                "background-color": "#ffffff", "color": "#d72638",
                "box-shadow": "inset 0 -2px 0 #d72638"
            }
        }
    )
    if tab_selection == "TSB Verlauf":
        load_trend.render()
    elif tab_selection == "Trainingszustand":
        fitness_state.render()

elif selected_section == "Trainingsanalyse":
    tab_selection = option_menu(
        menu_title=None,
        options=["Effizienz", "Einzeltrainings", "Trainingsklassifikation"],
        icons=["power", "activity", "list-check"],
        orientation="horizontal",
        styles={
            "container": {"margin": "0 0 1.5rem 0", "padding": "0.4rem", "border-radius": "8px", "background-color": "#f2f2f2"},
            "nav-link": {
                "font-size": "14px", "font-weight": "500", "color": "#333", "padding": "8px 12px",
                "border-radius": "6px", "display": "flex", "align-items": "center", "gap": "0.4rem",
                "white-space": "nowrap"
            },
            "nav-link-selected": {
                "background-color": "#ffffff", "color": "#d72638",
                "box-shadow": "inset 0 -2px 0 #d72638"
            }
        }
    )
    if tab_selection == "Effizienz":
        efficiency.render()
    elif tab_selection == "Einzeltrainings":
        metrics.render()
    elif tab_selection == "Trainingsklassifikation":
        training_prediction.render()

elif selected_section == "Streckensimulator":
    route_simulator.render()

elif selected_section == "Import":
    st.markdown("### 📂 FIT-Dateien importieren")

    st.markdown("""
        <div style='font-size: 0.95rem; color: #555; margin-bottom: 1rem;'>
            Ziehe deine <strong>.fit-Dateien</strong> hier hinein oder wähle sie manuell aus.
        </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "FIT-Dateien auswählen oder hierhin ziehen",
        type="fit",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        save_dir = os.path.join("fit_samples", user)
        os.makedirs(save_dir, exist_ok=True)
        file_paths = []

        with st.spinner("Importiere Dateien..."):
            for file in uploaded_files:
                path = os.path.join(save_dir, file.name)
                with open(path, "wb") as f:
                    f.write(file.getbuffer())
                file_paths.append(path)

            results = fit_importer_new.import_fit_files(file_paths)
            st.cache_data.clear()

        st.success(f"{len(results)} Datei(en) erfolgreich importiert.")
        st.markdown("<ul style='padding-left: 1rem;'>", unsafe_allow_html=True)
        for name, msg in results:
            st.markdown(f"<li><strong>{name}</strong> – {msg}</li>", unsafe_allow_html=True)
        st.markdown("</ul>", unsafe_allow_html=True)

elif selected_section == "Einstellungen":
    st.markdown("### ⚙️ Einstellungen")

    user = get_current_user()
    current_settings = get_all_settings(user=user)

    # Eingabefelder
    ftp = st.number_input("FTP (Watt)", min_value=100, max_value=600, value=current_settings.get("ftp", 250), step=1)
    weight = st.number_input("Körpergewicht (kg)", min_value=40.0, max_value=150.0,
                             value=float(current_settings.get("weight", 70)), step=0.1)
    hr_max = st.number_input("Maximale Herzfrequenz (bpm)", min_value=120, max_value=220, value=current_settings.get("hr_max", 190), step=1)
    hr_rest = st.number_input("Ruhepuls (bpm)", min_value=30, max_value=100, value=current_settings.get("hr_rest", 60), step=1)

    if st.button("💾 Einstellungen speichern"):
        save_settings(user, {
            "ftp": ftp,
            "weight": weight,
            "hr_max": hr_max,
            "hr_rest": hr_rest
        })
        st.success("✅ Einstellungen gespeichert.")
        st.rerun()  # ⬅️ wichtig für sofortige Anzeige der neuen Werte

    # Optional: Debuganzeige
    with st.expander("📋 Aktuelle gespeicherte Werte"):
        st.json(current_settings)

# === Footer ===
st.markdown("---")
st.markdown("<center><sub>Made with ♥ by Training Dashboard Pro</sub></center>", unsafe_allow_html=True)