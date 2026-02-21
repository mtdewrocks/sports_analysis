import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import (
    html,
    dcc,
    register_page,
    callback,
    Input,
    Output,
    dash_table,
)

# -------------------------------------------------
# Register Dash Page
# -------------------------------------------------
register_page(
    __name__,
    path="/nfl-game-logs",
    name="NFL Game Log",
    title="NFL Game Log",
)

# -------------------------------------------------
# Data config (lazy loaded)
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATS_FILE = PROJECT_ROOT / "data" / "Player_Stats_Weekly.parquet"

STATS_FILE = os.getenv("NFL_STATS_FILE", str(DEFAULT_STATS_FILE))

player_col = "player_display_name"
date_col = "week"
location_col = "location"

BASE_STATS = [
    "completions", "attempts", "passing_yards", "passing_tds",
    "passing_interceptions", "carries", "rushing_yards",
    "rushing_tds", "receptions", "receiving_yards"
]


@lru_cache(maxsize=1)
def get_df_stats():
    print(f"[NFL] Loading stats from: {STATS_FILE}", flush=True)

    df = pd.read_parquet(STATS_FILE)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    print(f"[NFL] Loaded rows={len(df):,} cols={len(df.columns)}", flush=True)
    return df


def stats_stat_options(df_cols):
    available = [s for s in BASE_STATS if s in set(df_cols)]
    return [{"label": s, "value": s} for s in available]


# -------------------------------------------------
# Layout
# -------------------------------------------------

layout = html.Div([

    # Sidebar
    html.Div([
        html.H2("Player Stats Filters"),

        html.Label("Player"),
        dcc.Dropdown(
            id="nfl-stats-player-dropdown",
            options=[],
            placeholder="Select a player",
            persistence=True,
            persistence_type="session",
        ),

        html.Label("Statistic"),
        dcc.Dropdown(
            id="nfl-stats-stat-dropdown",
            options=[],
            placeholder="Select a statistic",
            persistence=True,
            persistence_type="session",
        ),

        html.Label("Threshold (set using the slider)"),

        html.Div(id="nfl-threshold-display"),

        dcc.Slider(
            id="nfl-stats-threshold-slider",
            min=0,
            max=50,
            step=1,
            value=10,
            updatemode="drag",
        ),

        html.Div(id="nfl-stats-range-note"),

        html.Div(
            id="nfl-data-load-status",
            style={"color": "crimson"}
        ),

        dcc.Interval(id="nfl-init", interval=500, n_intervals=0, max_intervals=1),

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

    # Main Content
    html.Div([
        html.H2("Game-by-Game Chart"),

        dcc.Graph(id="nfl-stats-game-chart"),

        html.Div(id="nfl-stats-summary-stats"),

        html.H3("Over Counts (games ≥ threshold)"),

        html.Div(id="nfl-stats-rates-table"),

        html.Div(id="nfl-stats-rates-footnote"),

    ],
    style={"marginLeft": "24%", "padding": "20px"}),

])


# -------------------------------------------------
# Populate dropdowns
# -------------------------------------------------

@callback(
    Output("nfl-stats-player-dropdown", "options"),
    Output("nfl-stats-stat-dropdown", "options"),
    Output("nfl-data-load-status", "children"),
    Input("nfl-init", "n_intervals"),
)
def populate_dropdowns(_):
    try:
        df = get_df_stats()

        if player_col not in df.columns:
            return [], [], f"Missing column: {player_col}"

        players = sorted(df[player_col].dropna().unique())
        player_opts = [{"label": p, "value": p} for p in players]

        stat_opts = stats_stat_options(df.columns)

        return player_opts, stat_opts, f"Loaded {len(df):,} rows / {len(df.columns)} cols."

    except Exception as e:
        return [], [], f"Error loading data: {type(e).__name__}: {e}"


# -------------------------------------------------
# Threshold display
# -------------------------------------------------

@callback(
    Output("nfl-threshold-display", "children"),
    Input("nfl-stats-threshold-slider", "value"),
)
def show_threshold(v):
    return str(v)


# -------------------------------------------------
# Main chart callback
# -------------------------------------------------

@callback(
    Output("nfl-stats-game-chart", "figure"),
    Output("nfl-stats-summary-stats", "children"),
    Output("nfl-stats-rates-table", "children"),
    Output("nfl-stats-rates-footnote", "children"),
    Output("nfl-stats-range-note", "children"),
    Input("nfl-stats-player-dropdown", "value"),
    Input("nfl-stats-stat-dropdown", "value"),
    Input("nfl-stats-threshold-slider", "value"),
)
def update_chart(player, stat_col, threshold):

    df = get_df_stats()

    if not player or not stat_col:
        fig = px.line(title="Please select a statistic.")
        return fig, "", "", "", ""

    sub = df.loc[df[player_col] == player].copy()

    if sub.empty:
        fig = px.line(title="No data for selected player.")
        return fig, "", "", "", ""

    sub[stat_col] = pd.to_numeric(sub[stat_col], errors="coerce")
    sub = sub.dropna(subset=[stat_col])
    sub = sub.sort_values(date_col)

    fig = px.line(
        sub,
        x=date_col,
        y=stat_col,
        markers=True,
        title=f"{player} — {stat_col} by {date_col}",
    )

    fig.add_hline(y=threshold, line_dash="dash")

    n_games = len(sub)
    avg_val = sub[stat_col].mean()
    over_n = (sub[stat_col] >= threshold).sum()
    over_rate = over_n / n_games if n_games else 0

    summary = html.Div([
        html.Div(f"Games: {n_games}"),
        html.Div(f"Average: {avg_val:.2f}"),
        html.Div(f"Overs: {over_n} ({over_rate:.1%})"),
    ])

    grp = (
        sub.assign(over=(sub[stat_col] >= threshold))
        .groupby(location_col)
        .agg(games=("over", "size"), overs=("over", "sum"))
        .reset_index()
    )
    grp["over_rate"] = grp["overs"] / grp["games"]

    table = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in grp.columns],
        data=grp.to_dict("records"),
        style_cell={"padding": "6px"},
    )

    footnote = f"Over = {stat_col} ≥ {threshold}"
    range_note = f"{n_games} games included."

    return fig, summary, table, footnote, range_note
