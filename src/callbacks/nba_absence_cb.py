from dash import Input, Output, callback, html, dcc, callback_context
from dash.dependencies import ALL
import pandas as pd

from data_store import get_nba_impact_df, get_nba_impact_stat_cols
import json


# -------------------------------------------------
# Update teammate exclusion dropdown
# -------------------------------------------------
@callback(
    Output("nba-impact-exclude-players", "options"),
    Output("nba-impact-exclude-players", "value"),
    Input("nba-impact-player-a", "value")
)
def update_exclude_dropdown(player_a):
    if not player_a:
        return [], []

    df_impact = get_nba_impact_df()

    team_series = df_impact.loc[df_impact["player"] == player_a, "team"]
    if team_series.empty:
        return [], []

    team = team_series.mode()[0]

    teammates = sorted(df_impact[df_impact["team"] == team]["player"].dropna().unique())
    teammates = [p for p in teammates if p != player_a]

    return [{"label": p, "value": p} for p in teammates], []


# -------------------------------------------------
# Build stat buttons dynamically
# -------------------------------------------------
@callback(
    Output("nba-impact-stat-buttons", "children"),
    Input("nba-impact-player-a", "value")
)
def build_stat_buttons(player_a):
    if not player_a:
        return html.Div("Select Player A above.")

    df_impact = get_nba_impact_df()
    impact_stat_cols = get_nba_impact_stat_cols(df_impact)

    buttons = []
    for stat in impact_stat_cols:
        buttons.append(
            html.Button(
                stat.upper(),
                id={"type": "nba-impact-stat-button", "index": stat},
                n_clicks=0,
                style={
                    "margin": "4px",
                    "padding": "10px",
                    "width": "90px",
                    "height": "40px",
                    "border": "1px solid #888",
                    "borderRadius": "6px",
                    "cursor": "pointer",
                },
            )
        )

    return html.Div(buttons)


# -------------------------------------------------
# Update impact chart
# -------------------------------------------------
@callback(
    Output("nba-impact-chart-container", "children"),
    Input({"type": "nba-impact-stat-button", "index": ALL}, "n_clicks"),
    Input("nba-impact-player-a", "value"),
    Input("nba-impact-exclude-players", "value"),
)
def update_impact_chart(n_clicks_list, player_a, exclude_players):
    ctx = callback_context
    if not ctx.triggered:
        return html.Div("Select a stat above.")

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    try:
        stat_clicked = json.loads(trigger)["index"]
    except Exception:
        return html.Div("Select a stat above.")

    if not player_a:
        return html.Div("Select Player A above.")

    df_impact = get_nba_impact_df()

    # Basic validation for expected columns
    required_cols = {"player", "team", "game_date", "played"}
    missing = required_cols - set(df_impact.columns)
    if missing:
        return html.Div(f"Impact dataset missing columns: {', '.join(sorted(missing))}")

    team_series = df_impact.loc[df_impact["player"] == player_a, "team"]
    if team_series.empty:
        return html.Div(f"No team found for {player_a}.")
    team = team_series.mode()[0]

    team_games = df_impact[df_impact["team"] == team]["game_date"].dropna().unique()
    team_rows = df_impact[df_impact["team"] == team][["player", "game_date", "played"]].copy()

    excluded = exclude_players[:2] if exclude_players else []

    game_status = {}
    for game in team_games:
        a_played = bool(
            team_rows[
                (team_rows["player"] == player_a) &
                (team_rows["game_date"] == game)
            ]["played"].sum()
        )

        excluded_played = []
        for p in excluded:
            played = bool(
                team_rows[
                    (team_rows["player"] == p) &
                    (team_rows["game_date"] == game)
                ]["played"].sum()
            )
            excluded_played.append(played)

        if a_played and all(excluded_played):
            game_status[game] = "With"
        elif (not a_played) and all(not x for x in excluded_played):
            game_status[game] = "Without"
        else:
            game_status[game] = "Exclude"

    df_team = df_impact[df_impact["team"] == team].copy()
    df_team["WithOrWithout"] = df_team["game_date"].map(game_status)
    df_team = df_team[df_team["WithOrWithout"].isin(["With", "Without"])]
    df_team = df_team[df_team["player"] != player_a]

    if df_team.empty:
        return html.Div("No teammate data available after filtering games.")

    if stat_clicked not in df_team.columns:
        return html.Div(f"Stat '{stat_clicked}' not found in dataset.")

    df_team[stat_clicked] = pd.to_numeric(df_team[stat_clicked], errors="coerce")
    df_team = df_team.dropna(subset=[stat_clicked])

    if df_team.empty:
        return html.Div("No valid values for this stat after cleaning.")

    df_grouped = (
        df_team.groupby(["player", "WithOrWithout"])[stat_clicked]
        .mean()
        .reset_index()
    )

    if df_grouped.empty:
        return html.Div("No grouped data available.")

    df_pivot = df_grouped.pivot(
        index="player",
        columns="WithOrWithout",
        values=stat_clicked
    ).reset_index()

    if "With" not in df_pivot.columns or "Without" not in df_pivot.columns:
        return html.Div("Insufficient With/Without data to compute differences.")

    df_pivot = df_pivot.dropna(subset=["With", "Without"])
    if df_pivot.empty:
        return html.Div("No players have both With and Without data.")

    df_pivot["Difference"] = df_pivot["Without"] - df_pivot["With"]
    df_pivot = df_pivot.sort_values("Difference", ascending=False)

    df_pivot["With_avg"] = df_pivot["With"]
    df_pivot["Without_avg"] = df_pivot["Without"]

    if excluded:
        excluded_str = " & ".join(excluded)
        title_text = f"{stat_clicked.upper()}: Impact When {player_a} AND {excluded_str} Are OUT"
    else:
        title_text = f"{stat_clicked.upper()}: Impact When {player_a} Is OUT"

    import plotly.express as px

    fig = px.bar(
        df_pivot,
        x="player",
        y="Difference",
        title=title_text,
        custom_data=["With_avg", "Without_avg"],
        color=df_pivot["Difference"] >= 0,
        color_discrete_map={True: "#2ca02c", False: "#d62728"},
    )

    hovertemplate = (
        "<b>%{x}</b><br>"
        + stat_clicked.upper() + " Difference: %{y:.2f}<br>"
        "With Avg: %{customdata[0]:.2f}<br>"
        "Without Avg: %{customdata[1]:.2f}<br>"
        "<extra></extra>"
    )

    fig.update_traces(hovertemplate=hovertemplate)
    fig.update_layout(
        height=500,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Teammate",
        yaxis_title=f"{stat_clicked.upper()} Difference (Without − With)",
    )

    return dcc.Graph(figure=fig)
