import os
from functools import lru_cache
from pathlib import Path
from io import BytesIO

import pandas as pd
import requests
from dash import html, dcc, register_page, callback, Input, Output

# -------------------------------------------------
# Register Dash Page
# -------------------------------------------------
register_page(
    __name__,
    path="/nfl-game-logs",
    name="NFL Game Log",
    title="NFL Game Log"
)

# -------------------------------------------------
# Data config (DO NOT LOAD AT IMPORT TIME)
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]  # .../src
DEFAULT_STATS_FILE = BASE_DIR / "data" / "Player_Stats_Weekly.parquet"

# Allow override (Render env var). This can be a local path OR a URL.
STATS_FILE = os.getenv("NFL_STATS_FILE", str(DEFAULT_STATS_FILE))

# Optional: for private GitHub repos (or any protected endpoint)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

player_col = "player_display_name"
date_col = "week"
location_col = "location"  # update if your file differs

BASE_STATS = [
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
    "carries", "rushing_yards", "rushing_tds",
    "receptions", "receiving_yards"
]


def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _fetch_bytes(url: str) -> bytes:
    """
    Fetch bytes from a URL. Adds Authorization header if GITHUB_TOKEN is set.
    Works for public URLs and for private GitHub raw URLs when token is required.
    """
    headers = {"User-Agent": "render-dash-app"}
    if GITHUB_TOKEN:
        # For GitHub, PAT usually works with "token <PAT>"
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.content


@lru_cache(maxsize=1)
def get_df_stats():
    """
    Lazy-load + cache NFL stats. Runs only when a callback calls it.
    Supports local path OR URL.
    """
    print(f"[NFL] cwd={os.getcwd()}", flush=True)
    print(f"[NFL] Loading stats from: {STATS_FILE}", flush=True)

    if _is_url(STATS_FILE):
        data = _fetch_bytes(STATS_FILE)
        df = pd.read_parquet(BytesIO(data))
    else:
        df = pd.read_parquet(STATS_FILE)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    print(f"[NFL] Loaded rows={len(df):,} cols={len(df.columns)}", flush=True)
    return df


def invalidate_cache():
    get_df_stats.cache_clear()


def stats_stat_options(df_cols=None):
    # Build from BASE_STATS but only include stats that exist in the file
    if df_cols is None:
        return [{"label": s, "value": s} for s in BASE_STATS]

    available = [s for s in BASE_STATS if s in set(df_cols)]
    return [{"label": s, "value": s} for s in available]


# -------------------------------------------------
# PAGE LAYOUT
# -------------------------------------------------
layout = html.Div([

    # ---------- Sidebar ----------
    html.Div([
        html.H2("Player Stats Filters", style={"marginBottom": "20px"}),

        html.Label("Player"),
        dcc.Dropdown(
            id="nfl-stats-player-dropdown",
            options=[],  # ✅ populated via callback
            placeholder="Select a player",
            persistence=True,
            persistence_type="session",
            style={"marginBottom": "12px"},
        ),

        html.Label("Statistic"),
        dcc.Dropdown(
            id="nfl-stats-stat-dropdown",
            options=[],  # ✅ populated via callback (based on actual columns)
            placeholder="Select a statistic",
            persistence=True,
            persistence_type="session",
            style={"marginBottom": "12px"},
        ),

        html.Label("Threshold (set using the slider)"),

        html.Div(
            id="nfl-threshold-display",
            style={
                "marginBottom": "8px",
                "padding": "6px 12px",
                "border": "1px solid #ccc",
                "borderRadius": "4px",
                "backgroundColor": "#f8f9fa",
                "fontSize": "14px",
                "color": "#333"
            }
        ),

        dcc.Slider(
            id="nfl-stats-threshold-slider",
            min=0,
            max=50,
            step=1,
            value=10,
            tooltip={"placement": "bottom"},
            updatemode="drag",
            persistence=True,
            persistence_type="session",
        ),

        html.Div(
            id="nfl-stats-range-note",
            style={"marginTop": "8px", "fontSize": "12px", "color": "#666"},
        ),

        # ✅ Show load status or errors without crashing app
        html.Div(
            id="nfl-data-load-status",
            style={"marginTop": "12px", "color": "#b00020", "fontSize": "12px"},
        ),

        # hidden trigger to init dropdowns after render
        dcc.Interval(id="nfl-init", interval=500, n_intervals=0, max_intervals=1),

        # optional: a reload button if you want to bust cache without redeploy
        html.Button("Reload data", id="nfl-reload-btn", n_clicks=0, style={"marginTop": "10px"}),
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
        html.H2("Game-by-Game Chart"),

        dcc.Loading(
            dcc.Graph(id="nfl-stats-game-chart"),
            type="default",
        ),

        html.Div(id="nfl-stats-summary-stats", style={"marginTop": "12px"}),

        html.H3("Over Counts (games ≥ threshold)", style={"marginTop": "20px"}),

        html.Div(id="nfl-stats-rates-table"),

        html.Div(
            id="nfl-stats-rates-footnote",
            style={"marginTop": "8px", "fontSize": "12px", "color": "#666"},
        ),
    ],
    style={"marginLeft": "24%", "padding": "20px"}),
])

# -------------------------------------------------
# Callbacks: populate dropdowns (lazy load)
# -------------------------------------------------
@callback(
    Output("nfl-stats-player-dropdown", "options"),
    Output("nfl-stats-stat-dropdown", "options"),
    Output("nfl-data-load-status", "children"),
    Input("nfl-init", "n_intervals"),
    Input("nfl-reload-btn", "n_clicks"),
)
def populate_dropdowns(_init_ticks, reload_clicks):
    if reload_clicks and reload_clicks > 0:
        invalidate_cache()

    try:
        df = get_df_stats()

        # players
        if player_col not in df.columns:
            return [], [], f"Error: player column '{player_col}' not found in file."

        players = sorted(df[player_col].dropna().unique())
        player_opts = [{"label": p, "value": p} for p in players]

        # stats
        stat_opts = stats_stat_options(df.columns)

        return player_opts, stat_opts, f"Loaded {len(df):,} rows from {STATS_FILE}"

    except Exception as e:
        print(f"[NFL] ERROR loading data: {type(e).__name__}: {e}", flush=True)
        return [], [], f"Error loading NFL data: {type(e).__name__}: {e}"
