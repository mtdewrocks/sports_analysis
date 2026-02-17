import math
import numpy as np
import pandas as pd

from dash import html, dcc, register_page
import dash_table
import os

print(os.getcwd())

# ------------------------------------------------------------
# REGISTER PAGE
# ------------------------------------------------------------
register_page(
    __name__,
    path="/nba_props",
    name="NBA Props",
    title="NBA Props"
)

# ------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------
stats_file = r"https://github.com/mtdewrocks/sports_analysis/raw/main/data/NBA_Player_Stats.parquet"
props_file = r"https://github.com/mtdewrocks/sports_analysis/raw/main/data/Basketball_Props.xlsx"

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
df_stats = pd.read_parquet(stats_file)
df_props = pd.read_excel(props_file)

# ------------------------------------------------------------
# NORMALIZE COLUMNS
# ------------------------------------------------------------
df_stats.columns = (
    df_stats.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

df_props.columns = (
    df_props.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

bad_books = {
    "betonlineag", "ballybet", "betrivers", "bovada", "mybookieag",
    "hardrockbet", "prizepicks", "betparx", "rebet", "williamhill_us", "betr_us_dfs"
}

if "bookmakers" in df_props.columns:
    df_props = df_props[~df_props["bookmakers"].str.lower().isin(bad_books)].copy()

# ------------------------------------------------------------
# DROPDOWN OPTION HELPERS
# ------------------------------------------------------------
def props_player_options():
    if "player" in df_props.columns and not df_props.empty:
        players = sorted(df_props["player"].dropna().unique())
        return [{"label": p, "value": p} for p in players]
    return []

def props_market_options():
    if "market" in df_props.columns and not df_props.empty:
        markets = sorted(df_props["market"].dropna().unique())
        return [{"label": m, "value": m} for m in markets]
    return []

# ------------------------------------------------------------
# PAGE LAYOUT
# ------------------------------------------------------------
layout = html.Div([
    # ---------------- LEFT SIDEBAR ----------------
    html.Div([
        html.H2("Prop Odds Filters", style={"marginBottom": "20px"}),

        html.Label("Select Player"),
        dcc.Dropdown(
            id="props-player-dropdown",
            options=props_player_options(),
            placeholder="Choose a player",
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session"
        ),

        html.Label("Select Market"),
        dcc.Dropdown(
            id="props-market-dropdown",
            options=props_market_options(),
            placeholder="Choose a market",
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session"
        ),

        html.Label("Over or Under"),
        dcc.RadioItems(
            id="props-side-radio",
            options=[
                {'label': 'Over', 'value': 'over'},
                {'label': 'Under', 'value': 'under'}
            ],
            value='over',
            inline=True,
            style={"marginBottom": "12px"},
            persistence=True,
            persistence_type="session"
        )
    ],
    style={
        'width': '20%',
        'padding': '20px',
        'backgroundColor': '#f8f9fa',
        'borderRight': '2px solid #dee2e6',
        'height': '100vh',
        'position': 'fixed',
        'overflowY': 'auto'
    }),

    # ---------------- RIGHT CONTENT ----------------
    html.Div([
        html.H2("Odds Table", style={"marginTop": "20px"}),
        html.Div(id='props-odds-table', style={"padding": "20px"})
    ],
    style={'marginLeft': '22%', 'padding': '20px'})
])
