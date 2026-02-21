# src/data_store.py
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

# -----------------------------
# Utilities
# -----------------------------
def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _fetch_bytes_public(url: str) -> bytes:
    """
    Fetch bytes from a public URL (no auth).
    Raises a helpful error message on failure.
    """
    headers = {
        "User-Agent": "render-dash-app",
        "Accept": "application/octet-stream",
        "Cache-Control": "no-cache",
    }
    try:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        return r.content
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        body = ""
        try:
            body = (e.response.text or "")[:300]
        except Exception:
            body = ""
        raise RuntimeError(f"Failed to download {url} (HTTP {status}). {body}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download {url}: {type(e).__name__}: {e}") from e


def _read_parquet_anywhere(path_or_url: str) -> pd.DataFrame:
    """
    Read parquet from a local path or public URL.
    """
    if _is_url(path_or_url):
        content = _fetch_bytes_public(path_or_url)
        return pd.read_parquet(BytesIO(content))
    return pd.read_parquet(path_or_url)


def _read_excel_anywhere(path_or_url: str) -> pd.DataFrame:
    """
    Read Excel from a local path or public URL.
    Requires openpyxl in requirements.txt.
    """
    if _is_url(path_or_url):
        content = _fetch_bytes_public(path_or_url)
        return pd.read_excel(BytesIO(content), engine="openpyxl")
    return pd.read_excel(path_or_url, engine="openpyxl")


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
    "https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/nba_absence_impact.parquet",
)


@lru_cache(maxsize=1)
def get_nba_impact_df() -> pd.DataFrame:
    print(f"[data_store] Loading NBA impact from: {NBA_IMPACT_FILE}", flush=True)
    df = _read_parquet_anywhere(NBA_IMPACT_FILE)
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


# -----------------------------
# NFL: Game logs dataset (parquet)
# -----------------------------
# Project root (this file is at project/src/data_store.py)
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # project/
DEFAULT_NFL_STATS_FILE = PROJECT_ROOT / "data" / "Player_Stats_Weekly.parquet"

# ✅ Allow override via env var, but default to local repo file
NFL_STATS_FILE = os.getenv(
    "NFL_STATS_FILE",
    str(DEFAULT_NFL_STATS_FILE),
)

NFL_PLAYER_COL = os.getenv("NFL_PLAYER_COL", "player_display_name")
NFL_DATE_COL = os.getenv("NFL_DATE_COL", "week")
NFL_LOCATION_COL = os.getenv("NFL_LOCATION_COL", "location")


@lru_cache(maxsize=1)
def get_nfl_df() -> pd.DataFrame:
    print(f"[data_store] Loading NFL stats from: {NFL_STATS_FILE}", flush=True)
    df = _read_parquet_anywhere(NFL_STATS_FILE)
    return _normalize_cols(df)


def clear_nfl_cache():
    get_nfl_df.cache_clear()


# -----------------------------
# NFL: Matchups datasets (Excel)
# -----------------------------
NFL_TEAM_STATS_FILE = os.getenv("NFL_TEAM_STATS_FILE", "")
NFL_SCHEDULE_FILE = os.getenv("NFL_SCHEDULE_FILE", "")


@lru_cache(maxsize=1)
def get_nfl_matchup_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not NFL_TEAM_STATS_FILE or not NFL_SCHEDULE_FILE:
        raise RuntimeError(
            "NFL_TEAM_STATS_FILE and NFL_SCHEDULE_FILE must be set (local path or public URL)."
        )
    print(f"[data_store] Loading NFL team stats from: {NFL_TEAM_STATS_FILE}", flush=True)
    print(f"[data_store] Loading NFL schedule from: {NFL_SCHEDULE_FILE}", flush=True)

    df_team = _read_excel_anywhere(NFL_TEAM_STATS_FILE)
    df_sched = _read_excel_anywhere(NFL_SCHEDULE_FILE)
    return df_team, df_sched


def clear_nfl_matchup_cache():
    get_nfl_matchup_data.cache_clear()
