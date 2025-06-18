# Training Dashboard Pro

**Training Dashboard Pro** ist eine leistungsstarke Analyse-App für Radsportler*innen, die auf FIT-Dateien basiert und Trainingsdaten wie Leistung, Herzfrequenz, TSS, VO₂max und mehr auswertet. Sie wurde in Python mit Streamlit entwickelt und unterstützt vollständige Multi-User-Funktionalität.

## Funktionen

- Automatischer FIT-Import mit selektivem Caching
- Leistungsmetriken: NP, IF, TSS, EF, Power Curve, CP-Modell
- Herzfrequenz- und Leistungszonenanalyse
- VO₂max-Schätzung auf Basis intensiver Einheiten
- Übersichtstab mit CTL, ATL, TSB und TSS
- ML-Modul zur automatischen Trainingsklassifikation
- Segmentanalyse und Simulation für GPX-Strecken
- Multi-User-Login mit benutzerspezifischen Verzeichnissen

## Installation

```bash
git clone https://github.com/LordCodeMode/Training-Dashboard-Pro.git
cd Training-Dashboard-Pro
pip install -r requirements.txt
```

## Starten der App

```bash
streamlit run streamlit-app.py
```

## Projektstruktur

- `fit_processing/`: FIT-Import, Feature-Extraktion
- `cache_modules/`: modulare Caching-Komponenten
- `plots/`: alle Visualisierungen (Power Curve, VO₂max, usw.)
- `ml/`: Machine Learning Module
- `utils/`: Hilfsfunktionen, Settings, Auth
- `fit_samples/`: Beispiel-FIT-Dateien
- `cache/`: generierte Cache-Dateien
