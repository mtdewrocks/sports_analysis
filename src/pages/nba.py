# pages/nba.py
import os
from functools import lru_cache

import pandas as pd
from dash import html, dcc, register_page

# -------------------------------------------------
# Register Dash Page
# -------------------------------------------------
register_page(
    __name__,
    path="/nba",
    name="NBA Game Log",
    title="NBA Game Log",
)

# -------------------------------------------------
# Data config (do NOT load at import time)
# -------------------------------------------------
DEFAULT_STATS_FILE = "https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/NBA_Player_Stats.parquet"
STATS_FILE = os.getenv("NBA_STATS_FILE", DEFAULT_STATS_FILE)

player_col = "player"
date_col = "game_date"
location_col = "location"  # optional

available_stats = {
    "pts": "pts",
    "reb": "reb",
    "ast": "ast",
    "stl": "stl",
    "blk": "blk",
    "tov": "tov",
    "3pm": "3pm",
    "blk_stl": "blk_stl",
    "pra": "pra",
    "reb_ast": "reb_ast",
    "pts_ast": "pts_ast",
    "pts_reb": "pts_reb",
}

# -------------------------------------------------
# Helpers (import these from your callbacks file if desired)
# -------------------------------------------------
def stats_stat_options():
    return [{"label": k.upper(), "value": v} for k, v in available_stats.items()]


def _first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _ensure_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def _get_latest_team_for_player(df: pd.DataFrame, team_col: str, player: str) -> str | None:
    """
    For traded players, choose the most recent team based on latest game_date.
    Prefers rows where played==1 if available.
    """
    if not player or team_col not in df.columns or date_col not in df.columns:
        return None

    tmp = df[df[player_col] == player].copy()
    if tmp.empty:
        return None

    tmp["_dt"] = _ensure_datetime(tmp[date_col])

    if "played" in tmp.columns:
        tmp_played = tmp[tmp["played"] == 1]
        if not tmp_played.empty:
            tmp = tmp_played

    tmp = tmp.dropna(subset=["_dt", team_col])
    if tmp.empty:
        return None

    tmp = tmp.sort_values("_dt")
    return str(tmp.iloc[-1][team_col])


def team_teammates_options(df: pd.DataFrame, selected_player: str) -> list[dict]:
    """
    Returns teammate dropdown options limited to the selected player's (latest) team.
    If no team column exists, falls back to all players (excluding selected).
    """
    if not selected_player:
        return []

    team_col = _first_existing_col(df, ["team", "team_abbreviation", "tm", "team_name", "team_id"])
    if not team_col:
        players = sorted([p for p in df[player_col].dropna().unique() if p != selected_player])
        return [{"label": p, "value": p} for p in players]

    team_val = _get_latest_team_for_player(df, team_col, selected_player)
    if not team_val:
        players = sorted([p for p in df[player_col].dropna().unique() if p != selected_player])
        return [{"label": p, "value": p} for p in players]

    teammates = (
        df.loc[df[team_col].astype(str) == str(team_val), player_col]
        .dropna()
        .unique()
        .tolist()
    )
    teammates = sorted([p for p in teammates if p != selected_player])
    return [{"label": p, "value": p} for p in teammates]


def apply_with_without_filters(
    df: pd.DataFrame,
    main_player: str,
    with_player: str | None,
    without_player: str | None,
) -> tuple[pd.DataFrame, str]:
    """
    Returns:
      - df_main_filtered: MAIN PLAYER rows only, filtered by with/without logic
      - label_suffix: text describing filter applied (for chart title / footnote)

    WITH:
      Keep dates where sum(played) across [main, with_player] == 2,
      then keep only main_player rows for those dates.

    WITHOUT:
      Keep dates where main_player played (played==1) AND without_player did NOT play that date.
      (missing row OR played==0). Practically: exclude dates where without_player played==1.
    """
    if not main_player:
        return df.iloc[0:0].copy(), ""

    if "played" not in df.columns:
        raise ValueError("Missing required column: 'played'")

    df_main = df[df[player_col] == main_player].copy()

    if not with_player and not without_player:
        df_main = df_main[df_main["played"] == 1]
        return df_main, ""

    suffix_parts = []

    if with_player:
        df_pair = df[df[player_col].isin([main_player, with_player])].copy()
        g = df_pair.groupby(date_col, dropna=False)["played"].sum()
        with_dates = set(g[g == 2].index.tolist())

        df_main = df_main[df_main[date_col].isin(with_dates)]
        suffix_parts.append(f"WITH: {with_player}")

    if without_player:
        without_played_dates = set(
            df.loc[
                (df[player_col] == without_player) & (df["played"] == 1),
                date_col
            ].dropna().unique().tolist()
        )

        df_main = df_main[(df_main["played"] == 1) & (~df_main[date_col].isin(without_played_dates))]
        suffix_parts.append(f"WITHOUT: {without_player}")

    suffix = " | " + " & ".join(suffix_parts) if suffix_parts else ""
    return df_main, suffix


def apply_schedule_filters(df_main: pd.DataFrame, b2b_values: list, in3in4_values: list) -> pd.DataFrame:
    """
    Applies optional schedule toggles if corresponding columns exist.
    """
    df_out = df_main.copy()

    if "b2b2" in (b2b_values or []):
        b2b_col = _first_existing_col(df_out, ["back_to_back", "b2b", "b2b_2nd", "b2b2"])
        if b2b_col:
            df_out = df_out[df_out[b2b_col] == 1]
        else:
            return df_out.iloc[0:0]

    if "3in4" in (in3in4_values or []):
        in3in4_col = _first_existing_col(df_out, ["third_in_four", "third_in_4", "three_in_four", "3in4"])
        if in3in4_col:
            df_out = df_out[df_out[in3in4_col] == 1]
        else:
            return df_out.iloc[0:0]

    return df_out


# -------------------------------------------------
# Data loader (safe: runs only when called)
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_df_stats() -> pd.DataFrame:
    """
    Load stats once per process. Safe on Render because it only runs
    when a callback needs it, not during module import.
    """
    print(f"[NBA] cwd={os.getcwd()}", flush=True)
    print(f"[NBA] Loading parquet from: {STATS_FILE}", flush=True)

    df = pd.read_parquet(STATS_FILE)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    print(f"[NBA] Loaded rows={len(df):,} cols={len(df.columns)}", flush=True)

    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    return df


# -------------------------------------------------
# PAGE LAYOUT (UPDATED ORDER)
# - WITH/WITHOUT dropdowns are AFTER slider and range note
#   but BEFORE the schedule options block.
# -------------------------------------------------
layout = html.Div([

    # ---------- Sidebar ----------
    html.Div([
        html.H2("Player Stats Filters", style={"marginBottom": "20px"}),

        html.Label("Player"),
        dcc.Dropdown(
            id="nba-stats-player-dropdown",
            options=[],  # populated by callback in callbacks file
            placeholder="Select a player",
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session",
        ),

        html.Label("Statistic"),
        dcc.Dropdown(
            id="nba-stats-stat-dropdown",
            options=stats_stat_options(),
            placeholder="Select a statistic",
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session",
        ),

        # Threshold block
        html.Label("Threshold (set using the slider)"),

        html.Div(
            id="nba-threshold-display",
            style={
                "marginBottom": "8px",
                "padding": "6px 12px",
                "border": "1px solid #ccc",
                "borderRadius": "4px",
                "backgroundColor": "#f8f9fa",
                "fontSize": "14px",
                "color": "#333",
            }
        ),

        dcc.Slider(
            id="nba-stats-threshold-slider",
            min=0,
            max=50,
            step=1,
            value=10,
            tooltip={"placement": "bottom"},
            updatemode="drag",
            marks=None,
            persistence=True,
            persistence_type="session",
        ),

        html.Div(
            id="nba-stats-range-note",
            style={"marginTop": "8px", "color": "#666", "fontSize": "12px"},
        ),

        # ✅ NEW DROPDOWNS (moved here)
        html.Label("WITH (same team)"),
        dcc.Dropdown(
            id="nba-stats-with-dropdown",
            options=[],  # populated by callback
            value=None,
            placeholder="Select a teammate (filters dates where both played)",
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session",
            clearable=True,
        ),

        html.Label("WITHOUT (same team)"),
        dcc.Dropdown(
            id="nba-stats-without-dropdown",
            options=[],  # populated by callback
            value=None,
            placeholder="Select a teammate (filters dates where teammate did NOT play)",
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session",
            clearable=True,
        ),

        # Schedule block (below WITH/WITHOUT)
        html.Div(
            [
                html.Label("Schedule Filters", style={"marginTop": "10px"}),

                dcc.Checklist(
                    id="nba-b2b-toggle",
                    options=[{"label": "2nd night of back-to-back only", "value": "b2b2"}],
                    value=[],
                    style={"marginBottom": "8px"},
                    inputStyle={"marginRight": "8px"},
                    persistence=True,
                    persistence_type="session",
                ),

                dcc.Checklist(
                    id="nba-3in4-toggle",
                    options=[{"label": "3rd game in 4 nights only", "value": "3in4"}],
                    value=[],
                    style={"marginBottom": "12px"},
                    inputStyle={"marginRight": "8px"},
                    persistence=True,
                    persistence_type="session",
                ),
            ],
            style={"marginTop": "6px"},
        ),

        # Status / errors
        html.Div(
            id="nba-data-load-status",
            style={"marginTop": "12px", "color": "#b00020", "fontSize": "12px"},
        ),

        # Initial load trigger (used by callbacks file)
        dcc.Interval(id="nba-init", interval=500, n_intervals=0, max_intervals=1),
    ],
    style={
        "width": "22%",
        "padding": "20px",
        "backgroundColor": "#f8f9fa",
        "borderRight": "2px solid #dee2e6",
        "height": "100vh",
        "position": "fixed",
        "overflowY": "auto",
    }),

    # ---------- Main Content ----------
    html.Div([
        html.H2("Game-by-Game Chart", style={"marginTop": "20px"}),

        dcc.Loading(
            dcc.Graph(id="nba-stats-game-chart", config={"displayModeBar": True}),
            type="default",
        ),

        html.Div(id="nba-stats-summary-stats", style={"marginTop": "12px"}),

        html.H3("Over Counts (counts of games ≥ threshold)", style={"marginTop": "20px"}),

        html.Div(id="nba-stats-rates-table", style={"marginTop": "8px"}),

        html.Div(
            id="nba-stats-rates-footnote",
            style={"marginTop": "8px", "color": "#666", "fontSize": "12px"},
        ),
    ],
    style={"marginLeft": "24%", "padding": "20px"}),
])
