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
