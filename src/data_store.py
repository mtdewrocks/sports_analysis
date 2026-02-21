# -----------------------------
# NFL: Game logs dataset (parquet)
# -----------------------------
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import pandas as pd
import requests

# ---------- Helpers ----------
def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def _fetch_bytes_public(url: str) -> bytes:
    headers = {
        "User-Agent": "dash-app",
        "Accept": "application/octet-stream",
        "Cache-Control": "no-cache",
    }
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.content

def _read_parquet_anywhere(path_or_url: str) -> pd.DataFrame:
    if _is_url(path_or_url):
        content = _fetch_bytes_public(path_or_url)
        return pd.read_parquet(BytesIO(content))
    return pd.read_parquet(path_or_url)

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


# -----------------------------
# NBA: Player game logs dataset
# -----------------------------
NBA_STATS_FILE = os.getenv(
    "NBA_STATS_FILE",
    "https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/NBA_Player_Stats.parquet",
)

NBA_PLAYER_COL = "player"
NBA_DATE_COL = "game_date"
NBA_LOCATION_COL = "location"


@lru_cache(maxsize=1)
def get_nba_df() -> pd.DataFrame:
    print(f"[data_store] Loading NBA stats from: {NBA_STATS_FILE}", flush=True)
    df = _read_parquet_anywhere(NBA_STATS_FILE)
    return _normalize_cols(df)


def clear_nba_cache():
    get_nba_df.cache_clear()


# -----------------------------
# NBA: Absence / Impact dataset
# -----------------------------
NBA_IMPACT_FILE = os.getenv(
    "NBA_IMPACT_FILE",
    "https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/NBA_Player_Stats.parquet",
)


@lru_cache(maxsize=1)
def get_nba_impact_df() -> pd.DataFrame:
    print(f"[data_store] Loading NBA impact from: {NBA_IMPACT_FILE}", flush=True)
    df = _read_parquet_anywhere(NBA_IMPACT_FILE)
    df = df.drop(columns=["FGM","FG%","3P%","FTM","FTA","FT%","OREB","DREB","PF","+/-","FP","DBLDBL","TRPLDBL","SEASON"])
    return _normalize_cols(df)


def clear_nba_impact_cache():
    get_nba_impact_df.cache_clear()


def get_nba_impact_stat_cols(df_impact: pd.DataFrame) -> list[str]:
    """
    Builds list of stat columns dynamically for impact charts.
    """
    exclude = {"player", "team", "game_date", "played", "withorwithout"}
    cols = [c for c in df_impact.columns if c not in exclude]

    numeric_cols = []
    for c in cols:
        s = pd.to_numeric(df_impact[c], errors="coerce")
        if s.notna().any():
            numeric_cols.append(c)
    return numeric_cols


# ---------------------------------------------------------
# NFL FILE — ALWAYS LOAD FROM RAW GITHUB URL BY DEFAULT
# ---------------------------------------------------------
NFL_STATS_FILE = os.getenv(
    "NFL_STATS_FILE",
    "https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/Player_Stats_Weekly.parquet",
)

# These MUST match the normalized column names in the parquet file
NFL_PLAYER_COL = "player_display_name"
NFL_DATE_COL = "week"
NFL_LOCATION_COL = "location"


@lru_cache(maxsize=1)
def get_nfl_df() -> pd.DataFrame:
    print(f"[data_store] Loading NFL stats from: {NFL_STATS_FILE}", flush=True)
    df = _read_parquet_anywhere(NFL_STATS_FILE)
    df = _normalize_cols(df)

    # Debug print — remove after confirming
    print("[data_store] NFL columns:", df.columns.tolist(), flush=True)
    print("[data_store] NFL shape:", df.shape, flush=True)

    return df


def clear_nfl_cache():
    get_nfl_df.cache_clear()
