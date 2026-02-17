# pages/mlb.py
import plotly.express as px
import dash
from dash import html, dcc, Input, Output, callback, dash_table, no_update
import dash_bootstrap_components as dbc

from mlb_data import (
    MLB_IMAGE_BASE,
    df, dfPitchers, dfGameLogs, dfSplits,
    dfpct_reshaped, dfHittersFinal,
    hitter_style
)

dash.register_page(__name__, path="/mlb/matchup", name="MLB Matchup")

# -----------------------------
# Shared table styling helpers
# -----------------------------
BASE_TABLE_STYLE = {
    "style_table": {"overflowX": "auto"},
    "style_cell": {
        "textAlign": "center",
        "padding": "6px",
        "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
        "fontSize": "13px",
        "whiteSpace": "nowrap",
    },
    "style_header": {"fontWeight": "700"},
}

def cols_from_df(dff, drop=None):
    drop = set(drop or [])
    return [{"name": c, "id": c} for c in dff.columns if c not in drop]

# Predefine headers so tables show structure before selection
SEASON_COLS = cols_from_df(df)
GAMELOG_COLS = cols_from_df(dfGameLogs, drop=["Name"])          # you drop Name in callback
SPLITS_COLS = [{"name": c, "id": c} for c in ["vs L", "Statistic", "vs R"]]  # what your pivot returns
HITTER_COLS = cols_from_df(dfHittersFinal, drop=["Pitcher"])    # you drop Pitcher in callback


layout = dbc.Container(
    [
        # Title
        dbc.Row(
            dbc.Col(
                html.H1("MLB Matchup Analysis", className="text-center my-3"),
                width=12,
            )
        ),

        # Top controls + season summary
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="mlb-pitcher-dropdown",
                        options=[
                            {"label": x, "value": x}
                            for x in sorted(dfPitchers["Baseball_Savant_Name"].unique())
                        ],
                        placeholder="Select a pitcher...",
                        clearable=True,
                    ),
                    xs=12, md=4, lg=3,
                ),

                dbc.Col(
                    html.Img(
                        id="mlb-pitcher-picture",
                        src="",
                        alt="pitcher image",
                        style={"display": "none"},
                    ),
                    xs="auto",
                    style={"display": "flex", "alignItems": "center"},
                ),

                dbc.Col(
                    dash_table.DataTable(
                        id="mlb-pitcher-season-table",
                        columns=SEASON_COLS,
                        data=[],  # ✅ empty until selection
                        **BASE_TABLE_STYLE,
                    ),
                    xs=12, md=7, lg=8,
                ),
            ],
            className="g-3 align-items-center mb-3",
        ),

        # Game log table
        dbc.Row(
            dbc.Col(
                dash_table.DataTable(
                    id="mlb-game-log-table",
                    columns=GAMELOG_COLS,
                    data=[],  # ✅ empty until selection
                    page_size=10,
                    **{
                        **BASE_TABLE_STYLE,
                        "style_cell": {
                            **BASE_TABLE_STYLE["style_cell"],
                            "fontWeight": "600",
                            "fontSize": "14px",
                        },
                    },
                ),
                width=12,
            ),
            className="mb-4",
        ),

        # Splits (left) + Percentiles chart (right)
        dbc.Row(
            [
                dbc.Col(
                    dash_table.DataTable(
                        id="mlb-splits-table",
                        columns=SPLITS_COLS,
                        data=[],  # ✅ empty until selection
                        page_size=20,
                        **BASE_TABLE_STYLE,
                    ),
                    xs=12, lg=6,
                ),

                dbc.Col(
                    dcc.Graph(
                        id="mlb-pcts-graph",
                        figure={},
                        style={"display": "none"},
                        config={"displayModeBar": False},
                    ),
                    xs=12, lg=6,
                ),
            ],
            className="g-3 mb-2",
        ),

        dbc.Row(
            dbc.Col(
                html.P(
                    "Splits data are from 2024 and 2025.",
                    id="mlb-splits-note",
                    style={"display": "none", "fontWeight": "700"},
                    className="mb-0",
                ),
                width=12,
            ),
            className="mb-4",
        ),

        # Hitter table
        dbc.Row(
            dbc.Col(
                dash_table.DataTable(
                    id="mlb-hitter-table",
                    columns=HITTER_COLS,
                    data=[],  # ✅ empty until selection
                    page_size=25,
                    style_data_conditional=hitter_style,
                    **BASE_TABLE_STYLE,
                ),
                width=12,
            )
        ),
    ],
    fluid=True,
    className="py-2",
)

# -----------------------------
# CALLBACKS
# -----------------------------
@callback(
    Output("mlb-pitcher-picture", "style"),
    Output("mlb-pcts-graph", "style"),
    Output("mlb-splits-note", "style"),
    Input("mlb-pitcher-dropdown", "value"),
    prevent_initial_call=True,
)
def show_visibility(chosen_value):
    if chosen_value:
        return (
            {"display": "block", "height": "70px", "width": "70px", "borderRadius": "50%"},
            {"display": "block"},
            {"display": "block", "fontWeight": "bold"},
        )
    return {"display": "none"}, {"display": "none"}, {"display": "none"}


@callback(
    Output("mlb-pitcher-picture", "src"),
    Input("mlb-pitcher-dropdown", "value"),
    prevent_initial_call=True,
)
def update_picture(chosen_value):
    if not chosen_value:
        return ""
    dfpicture = df.loc[df["Baseball_Savant_Name"] == chosen_value]
    if dfpicture.empty:
        return ""
    name = str(dfpicture["Name"].values[0])
    filename = "%20".join(name.split()) + ".jpg"
    return f"{MLB_IMAGE_BASE}/{filename}"


@callback(
    Output("mlb-pitcher-season-table", "data"),
    Output("mlb-hitter-table", "data"),
    Input("mlb-pitcher-dropdown", "value"),
    prevent_initial_call=True,
)
def update_pitcher_and_hitters(chosen_value):
    if not chosen_value:
        return [], []

    dff = df.loc[df["Baseball_Savant_Name"] == chosen_value].copy()

    dfh = dfHittersFinal.loc[dfHittersFinal["Baseball Savant Name"] == chosen_value].copy()
    dfh = dfh.drop(columns=["Pitcher"], errors="ignore")

    if "Batting Order" in dfh.columns:
        dfh = dfh.sort_values(by="Batting Order")

    return dff.to_dict("records"), dfh.to_dict("records")


@callback(
    Output("mlb-game-log-table", "data"),
    Input("mlb-pitcher-dropdown", "value"),
    prevent_initial_call=True,
)
def update_game_logs(chosen_value):
    if not chosen_value:
        return []

    # NOTE: if dfGameLogs["Name"] contains the *actual pitcher name* (not Baseball_Savant_Name),
    # you may need to map chosen_value -> Name before filtering.
    dffgame = dfGameLogs.loc[dfGameLogs["Name"] == chosen_value].copy()
    dffgame = dffgame.drop(columns=["Name"], errors="ignore")
    return dffgame.to_dict("records")


@callback(
    Output("mlb-splits-table", "data"),
    Input("mlb-pitcher-dropdown", "value"),
    prevent_initial_call=True,
)
def show_pitcher_splits(chosen_value):
    if not chosen_value:
        return []

    dffSplits = dfSplits.loc[dfSplits["Baseball Savant Name"] == chosen_value].copy()

    try:
        dfPivot = dffSplits.pivot_table("Value", index="Statistic", columns="Split").reset_index()
        cols = ["vs L", "Statistic", "vs R"]
        dfFinal = dfPivot[cols].reset_index(drop=True)

        order = [3, 4, 5, 17, 15, 1, 0, 2, 12, 6, 9, 13, 7, 10, 16, 14, 11, 8, 18]
        dfFinal = dfFinal.reindex(order).reset_index(drop=True)
        return dfFinal.to_dict("records")
    except Exception:
        # fallback to raw filtered splits if pivot fails
        return dffSplits.to_dict("records")


@callback(
    Output("mlb-pcts-graph", "figure"),
    Input("mlb-pitcher-dropdown", "value"),
    prevent_initial_call=True,
)
def show_percentiles(chosen_value):
    if not chosen_value:
        return {}

    dfpcts = dfpct_reshaped.loc[dfpct_reshaped["converted_name"] == chosen_value].copy()
    if dfpcts.empty:
        return {}

    fig = px.bar(
        dfpcts,
        x="Percentile",
        y="Statistic",
        title="2025 MLB Percentile Rankings",
        category_orders={"Statistic": ["Fastball Velo", "Avg Exit Velocity", "Chase %", "Whiff %", "K %", "BB %", "Barrel %", "Hard-Hit %"]},
        color="Percentile",
        orientation="h",
        color_continuous_scale="RdBu_r",
        color_continuous_midpoint=40,
        text="Percentile",
        width=600,
        height=600,
    )
    fig.update_xaxes(range=[0, 100])
    fig.update(layout_coloraxis_showscale=False)
    return fig
