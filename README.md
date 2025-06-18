# Training Dashboard Pro

**Training Dashboard Pro** ist eine leistungsstarke Analyse-App für Radsportler*innen, die auf FIT-Dateien basiert und Trainingsdaten wie Leistung, Herzfrequenz, TSS, VO₂max und mehr auswertet. Sie wurde in Python mit Streamlit entwickelt und unterstützt vollständige Multi-User-Funktionalität.

##  Funktionen

- Automatischer FIT-Import mit selektivem Caching
- Leistungsmetriken: NP, IF, TSS, EF, Power Curve, CP-Modell
- Herzfrequenz- und Leistungszonenanalyse
- VO₂max-Schätzung auf Basis intensiver Einheiten
- Übersichtstab mit CTL, ATL, TSB und TSS
- ML-Modul zur automatischen Trainingsklassifikation
- Segmentanalyse und Simulation für GPX-Strecken
- Multi-User-Login mit benutzerspezifischen Verzeichnissen

---

##  Installation

### 1. Repository klonen und Abhängigkeiten installieren

```bash
git clone https://github.com/LordCodeMode/Training-Dashboard-Pro.git
cd Training-Dashboard-Pro
pip install -r requirements.txt
```

### 2. Lokale Datenbank initialisieren

Beim ersten Start muss eine leere SQLite-Datenbank mit der passenden Tabellenstruktur angelegt werden:

```bash
python reset_and_init_db.py
```

Dadurch wird die Datei `trainings.db` erstellt. Sie enthält die Tabellen für Aktivitäten, Metriken, Nutzer, Zonen, Trainingslast u. v. m.

---

## ▶ App starten

```bash
streamlit run streamlit_app.py
```

Danach öffnet sich die Anwendung automatisch im Browser. Du kannst dich registrieren, einloggen und deine FIT-Dateien importieren.

---

##  Erste Schritte nach dem Start

1. Registriere einen neuen Benutzer direkt in der App.
2. Importiere deine eigenen FIT-Dateien über die Upload-Funktion.
3. Die App erstellt automatisch benutzerspezifische Unterordner:
   - `fit_samples/<username>/`
   - `cache/<username>/`
   - `cache/<username>/ml/`
   - `cache/<username>/user_settings.json`
4. Sämtliche Metriken werden beim Import automatisch berechnet und in den Cache geschrieben.
5. Alle Analysen und Plots stehen danach sofort zur Verfügung.

---

##  Projektstruktur

| Ordner / Datei          | Beschreibung                                                   |
|-------------------------|----------------------------------------------------------------|
| `fit_processing/`       | Import- und Extraktionslogik für FIT-Dateien                   |
| `cache_modules/`        | Module für die Cache-Berechnung aller Metriken                 |
| `plots/`                | Visualisierungen (Powerkurve, TSB, Zonen, ML, GPX)             |
| `ml/`                   | Machine-Learning-Modell und Trainingsklassifikation            |
| `utils/`                | Hilfsfunktionen (Auth, Settings, Formatierung)                 |
| `fit_samples/`          | Benutzer-FIT-Dateien (initial leer, wird automatisch erstellt) |
| `cache/`                | Zwischengespeicherte Analysedaten (initial leer)               |
| `streamlit_app.py`      | Haupt-Streamlit-Datei zum Starten der App                      |
| `reset_and_init_db.py`  | Initialisiert die SQLite-Datenbank mit Grundstruktur           |

---

## ⚠️ Hinweise

- **Keine FIT-Dateien oder persönlichen Daten** sind im Repository enthalten. Jeder Nutzer importiert seine eigenen Einheiten lokal.
- Die `.gitignore` schließt `.fit`-Dateien, `.db`, Cache und nutzerspezifische Daten zuverlässig aus.
- Alle erforderlichen Unterordner werden beim ersten Login oder Import automatisch erzeugt.
- Diese App ist primär für die **lokale Nutzung** konzipiert und speichert alle Daten lokal.

---

##  Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Details siehe [LICENSE](./LICENSE).
