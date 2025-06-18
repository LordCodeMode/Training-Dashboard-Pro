import sqlite3
import pandas as pd
from utils.config import settings

DB_PATH = settings["db_path"]

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_best_values():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                MAX(max_1min_power),
                MAX(max_5min_power),
                MAX(max_20min_power),
                MAX(avg_power)
            FROM activities
            WHERE duration >= 5
        """)
        result = cur.fetchone()
        return {
            "5s": result[3] or 0,       # Annäherung über avg_power bei kurzen Fahrten
            "1min": result[0] or 0,
            "5min": result[1] or 0,
            "20min": result[2] or 0,
        }
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Bestwerte: {e}")
        return {
            "5s": 0,
            "1min": 0,
            "5min": 0,
            "20min": 0,
        }
    finally:
        conn.close()

def get_activities_df():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM activities ORDER BY start_time DESC", conn)
    except Exception as e:
        print(f"❌ Fehler beim Laden der Datenbank: {e}")
        df = pd.DataFrame()  # leeres DataFrame bei Fehler
    finally:
        conn.close()
    return df