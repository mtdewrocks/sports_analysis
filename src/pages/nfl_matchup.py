import dash
from dash import html, dcc, Input, Output, callback
import pandas as pd
import os
from dash import get_asset_url
# -------------------------------------------------
# REGISTER PAGE
# -------------------------------------------------

dash.register_page(
    __name__,
    path="/nfl-matchups",
    name="NFL Matchups"
)

# -------------------------------------------------
# LOAD DATA (ONCE)
# -------------------------------------------------

df = pd.read_excel("data/2025_Team_Stats.xlsx")
schedule = pd.read_excel("data/schedule.xlsx")

week = 18
schedule = schedule.query("week <= @week")

schedule["Matchup"] = schedule["away_team"] + " @ " + schedule["home_team"]
matchups = schedule["Matchup"].unique()

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

RANK_COLUMNS = [c for c in df.columns if c.startswith("Rank")]

# -------------------------------------------------
# TABLE BUILDER
# -------------------------------------------------

def build_team_table(team):
    stats = (
        df.query("team == @team")[STAT_COLUMNS]
        .T.reset_index()
    )
    stats.columns = ["Stat", "Value"]
    stats["Value"] = stats.Value.round(1)

    ranks = (
        df.query("team == @team")[RANK_COLUMNS]
        .T.reset_index()
    )
    print(ranks)
    ranks.columns = ["Statistic", "Rank"]
    ranks = ranks.set_index("Statistic").reindex(["Rank - Scoring Offense","Rank - Scoring Defense",'Rank - Plays Per Game','Rank - pass_share',
'Rank - run_share','Rank - Pass Yards Per Game','Rank - Yards Per Pass Attempt','Rank - Rush Yards Per Game','Rank - Yards Per Carry','Rank - Defense Plays Per Game','Rank - Defense Pass Share','Rank - Defense Rush Share','Rank - Defense Pass Yards Per Game','Rank - Defense Pass Yards Per Attempt','Rank - Defense Rush Yards Per Game','Rank - Defense Rush Yards Per Attempt']).reset_index()


    final = pd.concat([stats, ranks], axis=1)
    final = final.drop("Statistic", axis=1)
    #final = final.rename(columns={"index":"Stat", 22:"Value"})
    print(f"The columns are: {final.columns}")
    return html.Table(
        [
            html.Thead(
                html.Tr([
                    html.Th("Stat"),
                    html.Th("Value"),
                    html.Th("Rank")
                ])
            ),
            html.Tbody(
                [
                    html.Tr([
                        html.Td(final.iloc[i]["Stat"]),
                        html.Td(final.iloc[i]["Value"]),
                        html.Td(final.iloc[i]["Rank"]),
                    ])
                    for i in range(len(final))
                ]
            )
        ],
        className="team-table"
    )

# -------------------------------------------------
# PAGE LAYOUT
# -------------------------------------------------

layout = html.Div(
    [
        html.H1("NFL Matchup Breakdown", style={"textAlign": "center"}),

        dcc.Dropdown(
            id="matchup-dropdown",
            options=[{"label": m, "value": m} for m in matchups],
            value=matchups[0],
            clearable=False,
            style={"width": "400px", "margin": "auto"}
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
# CALLBACK
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
    away, home = matchup.split(" @ ")
    print(os.getcwd())

    return (
        away,
        home,
        get_asset_url(f"logos/{away}.jpg"),
        get_asset_url(f"logos/{home}.jpg"),
        build_team_table(away),
        build_team_table(home),
    )
