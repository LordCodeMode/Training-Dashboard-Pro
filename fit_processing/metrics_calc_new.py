import os
import sqlite3
import pandas as pd
from utils.settings_access import get_setting
from utils.user_paths import get_current_user, get_user_cache_path

def calculate_training_load(tss_df: pd.DataFrame, ctl_constant: int = 42, atl_constant: int = 7) -> pd.DataFrame:
    """
    Berechnet CTL, ATL, TSB nach Performance-Management-Chart-Methode (Coggan).
    """
    df = tss_df.copy()
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df["tss"] = pd.to_numeric(df["tss"], errors="coerce")
    df = df[df["start_time"].notna() & df["tss"].notna() & (df["tss"] > 0)]

    if df.empty:
        return pd.DataFrame(columns=["date", "tss", "ctl", "atl", "tsb"])

    df = df.groupby(df["start_time"].dt.date)["tss"].sum().reset_index()
    df.rename(columns={"start_time": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])

    full_range = pd.date_range(df["date"].min(), pd.Timestamp.today(), freq="D")
    df = df.set_index("date").reindex(full_range, fill_value=0).rename_axis("date").reset_index()

    ctl, atl = [], []
    ctl_prev, atl_prev = 0.0, 0.0

    for tss in df["tss"]:
        ctl_today = ctl_prev + (tss - ctl_prev) * (1 / ctl_constant)
        atl_today = atl_prev + (tss - atl_prev) * (1 / atl_constant)
        ctl.append(ctl_today)
        atl.append(atl_today)
        ctl_prev = ctl_today
        atl_prev = atl_today

    df["ctl"] = ctl
    df["atl"] = atl
    df["tsb"] = df["ctl"] - df["atl"]

    return df[["date", "tss", "ctl", "atl", "tsb"]]

def update_training_load_table(user: str = None):
    """
    Holt TSS-Werte aus der Datenbank und aktualisiert die Tabelle 'training_load' im DB-System.
    """
    user = user or get_current_user()
    db_path = get_setting("db_path", default="trainings.db", user=user)

    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(
                """
                SELECT start_time, tss
                FROM activities
                WHERE user_id = ?
                  AND start_time IS NOT NULL
                  AND tss IS NOT NULL
                """,
                conn, params=(user,)
            )

        df_load = calculate_training_load(df)
        if df_load.empty:
            print(f"[WARN] Keine gültigen TSS-Werte für '{user}' – Abbruch.")
            return

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM training_load WHERE user_id = ?", (user,))
            cursor.executemany(
                """
                INSERT INTO training_load (date, ctl, atl, tsb, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (row["date"].strftime("%Y-%m-%d"), row["ctl"], row["atl"], row["tsb"], user)
                    for _, row in df_load.iterrows()
                ]
            )
            conn.commit()
        print(f"[OK] Training Load erfolgreich aktualisiert für '{user}'")

    except Exception as e:
        print(f"❌ Fehler beim Training Load Update für '{user}': {e}")

def get_training_load_df(user: str = None) -> pd.DataFrame:
    """
    Läd die gecachte Training-Load-Zeitreihe für einen Nutzer.
    """
    user = user or get_current_user()
    path = get_user_cache_path("training_load.csv", user=user)

    if not os.path.exists(path):
        print(f"[WARN] Kein Cache gefunden: {path}")
        return pd.DataFrame(columns=["date", "CTL", "ATL", "TSB"])

    try:
        df = pd.read_csv(path, parse_dates=["date"])
        df = df.dropna(subset=["ctl", "atl", "tsb"])
        df.rename(columns={"ctl": "CTL", "atl": "ATL", "tsb": "TSB"}, inplace=True)
        return df
    except Exception as e:
        print(f"[ERROR] Fehler beim Laden des Training Load Caches: {e}")
        return pd.DataFrame(columns=["date", "CTL", "ATL", "TSB"])