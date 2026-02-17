print("NFL PAGE LOADED")

import pandas as pd
from dash import html, dcc, register_page

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
# Load data ONCE
# -------------------------------------------------
stats_file = r"C:\Users\shawn\Python\Football\2025\Player_Stats_Weekly.parquet"

df_stats = pd.read_parquet(stats_file)
df_stats.columns = (
    df_stats.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

player_col = "player_display_name"
date_col = "week"
location_col = "location"   # If your NFL file has home/away, update this

# -------------------------------------------------
# Available stats
# -------------------------------------------------
BASE_STATS = ["completions", "attempts", "passing_yards","passing_tds","passing_interceptions","carries",
              "rushing_yards","rushing_tds","receptions","receiving_yards"]

available_stats = {
    stat: stat for stat in BASE_STATS if stat in df_stats.columns
}

def stats_player_options():
    players = sorted(df_stats[player_col].dropna().unique())
    return [{"label": p, "value": p} for p in players]

def stats_stat_options():
    return [{"label": k, "value": v} for k, v in available_stats.items()]

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
            options=stats_player_options(),
            placeholder="Select a player",
            persistence=True,
            persistence_type="session",
            style={"marginBottom": "12px"},
        ),

        html.Label("Statistic"),
        dcc.Dropdown(
            id="nfl-stats-stat-dropdown",
            options=stats_stat_options(),
            placeholder="Select a statistic",
            persistence=True,
            persistence_type="session",
            style={"marginBottom": "12px"},
        ),

        html.Label("Threshold (set using the slider)"),

        # Display-only threshold box
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
