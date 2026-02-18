import pandas as pd
from dash import html, dcc, register_page

# -------------------------------------------------
# Register Dash Page
# -------------------------------------------------
register_page(
    __name__,
    path="/nba_in_out",
    name="NBA In/Out Analysis",
    title="NBA In/Out Analysis"
)

# -------------------------------------------------
# Load data ONCE
# -------------------------------------------------
stats_file = r"https://raw.githubusercontent.com/mtdewrocks/sports_analysis/main/data/NBA_Player_Stats.parquet"
df_stats = pd.read_parquet(stats_file)

df_stats.columns = (
    df_stats.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

df_impact = df_stats.copy()

# -------------------------------------------------
# Columns to exclude from impact stats
# -------------------------------------------------
exclude_stats = {
    "fg%", "3p%", "ft%", "gameid", "fp", "+/-", "ftm", "fta",
    "oreb", "dreb", "date", "dbldbl", "trpldbl", "fgm"
}

impact_stat_cols = [
    c for c in df_impact.columns
    if c not in [
        "player", "team", "match_up", "game_date", "w/l",
        "location", "opponent", "season", "played"
    ]
    and c not in exclude_stats
]

# -------------------------------------------------
# Page Layout
# -------------------------------------------------
layout = html.Div([

    html.H2("Player Absence Impact", style={"marginBottom": "20px"}),

    # Player A selection
    html.Label("Select Player A"),
    dcc.Dropdown(
        id="nba-impact-player-a",
        options=[{"label": p, "value": p} for p in sorted(df_impact["player"].unique())],
        placeholder="Choose Player A",
        style={"marginBottom": "12px"},
        persistence=True,
        persistence_type="session",
    ),

    # Exclude teammates
    html.Label("Exclude up to two teammates"),
    dcc.Dropdown(
        id="nba-impact-exclude-players",
        options=[],  # dynamically updated via callback
        value=[],
        multi=True,
        style={"marginBottom": "20px"},
        persistence=True,
        persistence_type="session",
    ),

    html.Hr(),

    # Buttons for selecting which stat to analyze
    html.Div(
        id="nba-impact-stat-buttons",
        style={"marginBottom": "20px"}
    ),

    html.Hr(),

    # Chart container
    html.Div(id="nba-impact-chart-container"),
])
