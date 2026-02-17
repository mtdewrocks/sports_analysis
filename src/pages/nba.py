import pandas as pd
from dash import html, dcc, register_page

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
# Load data ONCE
# -------------------------------------------------
stats_file = r"C:\Users\shawn\Python\sports_dash_app\data\NBA Player Stats.parquet"

df_stats = pd.read_parquet(stats_file)
df_stats.columns = (
    df_stats.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

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

def stats_player_options():
    players = sorted(df_stats[player_col].dropna().unique())
    return [{"label": p, "value": p} for p in players]

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
            options=stats_player_options(),
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
