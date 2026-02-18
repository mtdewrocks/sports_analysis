import os
from functools import lru_cache

import pandas as pd
from dash import html, dcc, register_page, callback, Input, Output

# -------------------------------------------------
# Register Dash Page
# -------------------------------------------------
register_page(
    __name__,
    path="/nba",
    name="NBA Game Log",
    title="NBA Game Log"
)

# -------------------------------------------------
# Data config (do NOT load at import time)
# -------------------------------------------------

# Keep your URL as a default; allow override via Render env var
DEFAULT_STATS_FILE = "https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/NBA_Player_Stats.parquet"
STATS_FILE = os.getenv("NBA_STATS_FILE", DEFAULT_STATS_FILE)

player_col = "player"
date_col = "game_date"
location_col = "location"

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


@lru_cache(maxsize=1)
def get_df_stats():
    """
    Load stats once per process. This is safe on Render because it only runs
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

    # Optional: quick sanity checks in logs
    print(f"[NBA] Loaded rows={len(df):,} cols={len(df.columns)}", flush=True)

    return df


def stats_stat_options():
    return [{"label": k.upper(), "value": v} for k, v in available_stats.items()]


# -------------------------------------------------
# PAGE LAYOUT
# -------------------------------------------------
layout = html.Div([

    # ---------- Sidebar ----------
    html.Div([
        html.H2("Player Stats Filters", style={"marginBottom": "20px"}),

        html.Label("Player"),
        dcc.Dropdown(
            id="nba-stats-player-dropdown",
            options=[],  # ✅ filled by callback below
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

        html.Label("Threshold (set using the slider)"),

        # Display-only threshold box
        html.Div(
            id="nba-threshold-display",
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

        # ✅ Optional: show load errors on the page instead of crashing deploy
        html.Div(
            id="nba-data-load-status",
            style={"marginTop": "12px", "color": "#b00020", "fontSize": "12px"},
        ),

        # hidden trigger to load players after page render
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


# -------------------------------------------------
# Callback: populate player dropdown safely (no import-time load)
# -------------------------------------------------
@callback(
    Output("nba-stats-player-dropdown", "options"),
    Output("nba-data-load-status", "children"),
    Input("nba-init", "n_intervals"),
)
def populate_players(_):
    try:
        df_stats = get_df_stats()
        players = sorted(df_stats[player_col].dropna().unique())
        opts = [{"label": p, "value": p} for p in players]
        return opts, ""  # no error
    except Exception as e:
        # Keep app alive and show error on the page + in logs
        print(f"[NBA] ERROR loading data: {type(e).__name__}: {e}", flush=True)
        return [], f"Error loading NBA data: {type(e).__name__}: {e}"
