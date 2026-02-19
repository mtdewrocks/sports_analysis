import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import dash
from dash import html, dcc, Input, Output, callback, get_asset_url
import pandas as pd
import requests

# -------------------------------------------------
# REGISTER PAGE
# -------------------------------------------------
dash.register_page(
    __name__,
    path="/nfl-matchups",
    name="NFL Matchups"
)

# -------------------------------------------------
# CONFIG: local defaults + URL override
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # .../src

DEFAULT_TEAM_STATS = BASE_DIR / "data" / "2025_Team_Stats.xlsx"
DEFAULT_SCHEDULE = BASE_DIR / "data" / "schedule.xlsx"

TEAM_STATS_FILE = os.getenv("NFL_TEAM_STATS_FILE", str(DEFAULT_TEAM_STATS))  # path or URL
SCHEDULE_FILE = os.getenv("NFL_SCHEDULE_FILE", str(DEFAULT_SCHEDULE))        # path or URL

# Optional token for private GitHub (or other protected endpoints)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# week cutoff
WEEK_CUTOFF = int(os.getenv("NFL_WEEK_CUTOFF", "18"))

# -------------------------------------------------
# COLUMNS
# -------------------------------------------------
STAT_COLUMNS = [
    "score_offense", "score_defense",
    "Plays Per Game", "pass_share", "run_share",
    "Pass Yards Per Game", "Yards Per Pass Attempt",
    "Rush Yards Per Game", "Yards Per Carry",
    "Defense Plays Per Game", "Defense Pass Share",
    "Defense Rush Share",
    "Defense Pass Yards Per Game",
    "Defense Pass Yards Per Attempt",
    "Defense Rush Yards Per Game",
    "Defense Rush Yards Per Attempt"
]

RANK_ORDER = [
    "Rank - Scoring Offense",
    "Rank - Scoring Defense",
    "Rank - Plays Per Game",
    "Rank - pass_share",
    "Rank - run_share",
    "Rank - Pass Yards Per Game",
    "Rank - Yards Per Pass Attempt",
    "Rank - Rush Yards Per Game",
    "Rank - Yards Per Carry",
    "Rank - Defense Plays Per Game",
    "Rank - Defense Pass Share",
    "Rank - Defense Rush Share",
    "Rank - Defense Pass Yards Per Game",
    "Rank - Defense Pass Yards Per Attempt",
    "Rank - Defense Rush Yards Per Game",
    "Rank - Defense Rush Yards Per Attempt",
]

# -------------------------------------------------
# Helpers: URL download
# -------------------------------------------------
def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def _fetch_bytes(url: str) -> bytes:
    headers = {"User-Agent": "render-dash-app"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.content

def _read_excel_anywhere(path_or_url: str) -> pd.DataFrame:
    """
    Read Excel from local path or URL (public/private).
    Uses requests+BytesIO for URL for reliability.
    """
    if _is_url(path_or_url):
        content = _fetch_bytes(path_or_url)
        return pd.read_excel(BytesIO(content), engine="openpyxl")
    return pd.read_excel(path_or_url, engine="openpyxl")

# -------------------------------------------------
# Cached loader
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_data():
    """
    Loads team stats + schedule once per process.
    """
    print(f"[NFL-MATCHUPS] cwd={os.getcwd()}", flush=True)
    print(f"[NFL-MATCHUPS] TEAM_STATS_FILE={TEAM_STATS_FILE}", flush=True)
    print(f"[NFL-MATCHUPS] SCHEDULE_FILE={SCHEDULE_FILE}", flush=True)

    df = _read_excel_anywhere(TEAM_STATS_FILE)
    schedule = _read_excel_anywhere(SCHEDULE_FILE)

    # Rank columns depend on df
    rank_columns = [c for c in df.columns if str(c).startswith("Rank")]

    # Build matchups safely
    sch = schedule.copy()
    if "week" in sch.columns:
        sch = sch.query("week <= @WEEK_CUTOFF")

    # Ensure expected columns exist
    if "away_team" not in sch.columns or "home_team" not in sch.columns:
        raise KeyError("schedule.xlsx must include 'away_team' and 'home_team' columns.")

    sch["Matchup"] = sch["away_team"].astype(str) + " @ " + sch["home_team"].astype(str)
    matchups = sch["Matchup"].dropna().unique().tolist()

    print(f"[NFL-MATCHUPS] Loaded df rows={len(df):,}, schedule rows={len(schedule):,}, matchups={len(matchups)}", flush=True)
    return df, sch, matchups, rank_columns

def invalidate_cache():
    get_data.cache_clear()

# -------------------------------------------------
# TABLE BUILDER
# -------------------------------------------------
def build_team_table(df: pd.DataFrame, rank_cols: list[str], team: str):
    # Stats table
    sub = df.query("team == @team")
    stats = sub[STAT_COLUMNS].T.reset_index()
    stats.columns = ["Stat", "Value"]
    stats["Value"] = pd.to_numeric(stats["Value"], errors="coerce").round(1)

    # Ranks table
    ranks = sub[rank_cols].T.reset_index()
    ranks.columns = ["Statistic", "Rank"]
    ranks = (
        ranks.set_index("Statistic")
        .reindex(RANK_ORDER)
        .reset_index()
    )

    final = pd.concat([stats, ranks], axis=1).drop("Statistic", axis=1)

    return html.Table(
        [
            html.Thead(html.Tr([html.Th("Stat"), html.Th("Value"), html.Th("Rank")])),
            html.Tbody(
                [
                    html.Tr([
                        html.Td(final.iloc[i]["Stat"]),
                        html.Td(final.iloc[i]["Value"]),
                        html.Td(final.iloc[i]["Rank"]),
                    ])
                    for i in range(len(final))
                ]
            ),
        ],
        className="team-table",
    )

# -------------------------------------------------
# PAGE LAYOUT
# -------------------------------------------------
layout = html.Div(
    [
        html.H1("NFL Matchup Breakdown", style={"textAlign": "center"}),

        # init trigger to populate dropdown after page renders
        dcc.Interval(id="nfl-matchups-init", interval=300, n_intervals=0, max_intervals=1),

        # optional reload button
        html.Div(
            html.Button("Reload data", id="nfl-matchups-reload", n_clicks=0),
            style={"textAlign": "center", "marginBottom": "8px"},
        ),

        # status/errors shown here
        html.Div(
            id="nfl-matchups-status",
            style={"textAlign": "center", "fontSize": "12px", "color": "#b00020", "marginBottom": "8px"},
        ),

        dcc.Dropdown(
            id="matchup-dropdown",
            options=[],      # ✅ populated by callback
            value=None,      # ✅ set by callback
            clearable=False,
            style={"width": "400px", "margin": "auto"},
        ),

        html.Br(),

        html.Div(
            [
                html.Div(
                    [
                        html.Img(id="away-logo", className="team-logo"),
                        html.H3(id="away-team"),
                        html.Div(id="away-table"),
                    ],
                    className="team-panel",
                ),
                html.Div(
                    [
                        html.Img(id="home-logo", className="team-logo"),
                        html.H3(id="home-team"),
                        html.Div(id="home-table"),
                    ],
                    className="team-panel",
                ),
            ],
            className="matchup-container",
        ),
    ]
)

# -------------------------------------------------
# INIT: populate dropdown options + default value
# -------------------------------------------------
@callback(
    Output("matchup-dropdown", "options"),
    Output("matchup-dropdown", "value"),
    Output("nfl-matchups-status", "children"),
    Input("nfl-matchups-init", "n_intervals"),
    Input("nfl-matchups-reload", "n_clicks"),
)
def init_matchup_dropdown(_ticks, reload_clicks):
    if reload_clicks and reload_clicks > 0:
        invalidate_cache()

    try:
        _df, _sch, matchups, _rank_cols = get_data()
        opts = [{"label": m, "value": m} for m in matchups]
        default_val = matchups[0] if matchups else None
        status = "" if matchups else "No matchups found (check schedule week / columns)."
        return opts, default_val, status
    except Exception as e:
        print(f"[NFL-MATCHUPS] ERROR: {type(e).__name__}: {e}", flush=True)
        return [], None, f"Error loading matchup data: {type(e).__name__}: {e}"

# -------------------------------------------------
# MATCHUP CALLBACK
# -------------------------------------------------
@callback(
    Output("away-team", "children"),
    Output("home-team", "children"),
    Output("away-logo", "src"),
    Output("home-logo", "src"),
    Output("away-table", "children"),
    Output("home-table", "children"),
    Input("matchup-dropdown", "value"),
)
def update_matchup(matchup):
    if not matchup:
        return "", "", "", "", "", ""

    df, _sch, _matchups, rank_cols = get_data()
    away, home = matchup.split(" @ ")

    return (
        away,
        home,
        get_asset_url(f"logos/{away}.jpg"),
        get_asset_url(f"logos/{home}.jpg"),
        build_team_table(df, rank_cols, away),
        build_team_table(df, rank_cols, home),
    )
