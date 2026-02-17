# pages/mlb_props.py
import dash
from dash import html, dcc, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

from mlb_data import df_daily_props, df_props_matchup

dash.register_page(__name__, path="/mlb/props", name="MLB Player Props")


layout = dbc.Container(
    [
        html.Div(html.H1("Player Props Analysis", style={"textAlign": "center"}), className="row"),
        html.Br(),

        html.Div(
            [
                html.Div(
                    dcc.Dropdown(
                        id="mlb-team-dropdown",
                        multi=False,
                        options=[{"label": x, "value": x} for x in sorted(df_daily_props["mlb_team_long"].unique())],
                        placeholder="Team..."
                    ),
                    className="three columns",
                ),

                html.Div(
                    dcc.Dropdown(
                        id="mlb-player-dropdown",
                        multi=False,
                        options=[{"label": x, "value": x} for x in sorted(df_daily_props["Player"].unique())],
                        placeholder="Player..."
                    ),
                    className="three columns",
                ),

                html.Div(
                    dcc.Dropdown(
                        id="mlb-market-dropdown",
                        multi=False,
                        options=[{"label": x, "value": x} for x in sorted(df_daily_props["market"].unique())],
                        placeholder="Market..."
                    ),
                    className="two columns",
                ),

                html.Div(
                    dcc.Dropdown(
                        id="mlb-bookmaker-dropdown",
                        multi=False,
                        options=[{"label": x, "value": x} for x in sorted(df_daily_props["bookmakers"].unique())],
                        placeholder="Book..."
                    ),
                    className="two columns",
                ),

                html.Div(html.Button("Apply Filters", id="mlb-props-filter-button"), className="two columns"),
            ],
            className="row",
        ),

        html.Div(
            dash_table.DataTable(
                id="mlb-props-data-table",
                data=df_daily_props.to_dict("records"),
                style_table={"marginTop": "15px"},
                style_cell={"textAlign": "center"},
                sort_action="native",
                page_size=25,
            ),
            className="row",
        ),
    ],
    fluid=True,
)

# -----------------------------
# CALLBACKS (props page only)
# -----------------------------
@callback(
    Output("mlb-props-data-table", "data"),
    Input("mlb-props-filter-button", "n_clicks"),
    State("mlb-team-dropdown", "value"),
    State("mlb-player-dropdown", "value"),
    State("mlb-market-dropdown", "value"),
    State("mlb-bookmaker-dropdown", "value"),
)
def update_props_table(n_clicks, chosen_team, chosen_player, chosen_market, chosen_bookmaker):
    if not n_clicks:
        return df_daily_props.to_dict("records")

    dff_props = df_props_matchup.copy()

    drop_cols = [
        "commence_time", "Props Name", "home_team", "away_team", "fg_name", "Savant Name",
        "Split Hitter", "HR Hitter", "SB", "CS", "Bats", "GB%", "Fly Ball %", "wOBA",
        "Weighted OBP", "Weighted Slugging", "Weighted OBPS", "Team", "Handedness",
        "Opposing Team", "Baseball Savant Name", "Split Pitcher", "Weighted FIP",
        "Weighted GB% Pitcher", "Weighted FB% Pitcher", "Weighted HR/FB",
        "player_name_hitter", "player_name_pitcher", "player_id_pitcher"
    ]
    dff_props = dff_props.drop(columns=drop_cols, errors="ignore")

    if chosen_team:
        dff_props = dff_props.loc[dff_props["mlb_team_long"] == chosen_team]
    if chosen_player:
        dff_props = dff_props.loc[dff_props["Player"] == chosen_player]
    if chosen_market:
        dff_props = dff_props.loc[dff_props["market"] == chosen_market]

        if chosen_market == "hits":
            keep = ["Player", "market", "bookmakers", "Line", "Over Price", "Under Price",
                    "Batting Order", "Average", "K%", "BB%", "Pitcher Average", "Pitcher K%",
                    "Weighted BB% Pitcher", "Expected Batting Avg_hitter", "Expected Batting Avg_pitcher"]
            dff_props = dff_props[[c for c in keep if c in dff_props.columns]]

        elif chosen_market == "strikeouts":
            keep = ["Player", "market", "bookmakers", "Line", "Over Price", "Under Price",
                    "Batting Order", "Average", "K%", "BB%", "Whiff %_hitter", "Chase %_hitter",
                    "Pitcher K%", "Weighted BB% Pitcher", "Whiff %_pitcher", "Chase %_pitcher"]
            dff_props = dff_props[[c for c in keep if c in dff_props.columns]]

    if chosen_bookmaker:
        dff_props = dff_props.loc[dff_props["bookmakers"] == chosen_bookmaker]

    return dff_props.to_dict("records")
