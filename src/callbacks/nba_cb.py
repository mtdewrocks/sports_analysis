import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html

# ✅ Import cached loader + constants (safe at import time)
from data_store import get_nba_df, NBA_PLAYER_COL, NBA_DATE_COL, NBA_LOCATION_COL

# Keep names consistent with your existing code
player_col = NBA_PLAYER_COL
date_col = NBA_DATE_COL
location_col = NBA_LOCATION_COL


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def empty_fig(message):
    fig = go.Figure()
    fig.update_layout(title=message)
    return fig, "", "", ""


def clean_numeric(series):
    return pd.to_numeric(series, errors="coerce").dropna()


def over_counts(df, stat_col, threshold):
    if df.empty:
        s = pd.Series([], dtype="float64")
    else:
        s = clean_numeric(df[stat_col])

    return {
        "last5": int((s.tail(5) >= threshold).sum()),
        "last10": int((s.tail(10) >= threshold).sum()),
        "season": int((s >= threshold).sum()),
    }


def build_table(all_counts, home_counts, away_counts):
    header_style = {
        "border": "1px solid #dee2e6",
        "padding": "8px 12px",
        "backgroundColor": "#f8f9fa",
        "fontWeight": "bold",
        "textAlign": "center",
    }

    def cell_style(align="center"):
        return {
            "border": "1px solid #dee2e6",
            "padding": "8px 12px",
            "textAlign": align,
        }

    rows = [
        ("All games", all_counts),
        ("Home games", home_counts),
        ("Away games", away_counts),
    ]

    tbody = [
        html.Tr([
            html.Td(label, style=cell_style("left")),
            html.Td(str(counts["last5"]), style=cell_style()),
            html.Td(str(counts["last10"]), style=cell_style()),
            html.Td(str(counts["season"]), style=cell_style()),
        ])
        for label, counts in rows
    ]

    return html.Table(
        [
            html.Thead(
                html.Tr([
                    html.Th("", style=header_style),
                    html.Th("Last 5", style=header_style),
                    html.Th("Last 10", style=header_style),
                    html.Th("Season", style=header_style),
                ])
            ),
            html.Tbody(tbody),
        ],
        style={
            "borderCollapse": "collapse",
            "width": "60%",
            "minWidth": "360px",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.06)",
            "fontFamily": "Arial, sans-serif",
            "marginTop": "10px",
        },
    )


def apply_schedule_filters(sub: pd.DataFrame, b2b_toggle, three_in_four_toggle) -> pd.DataFrame:
    """
    b2b_toggle comes from id='nba-b2b-toggle' -> [] or ['b2b2']
    three_in_four_toggle comes from id='nba-3in4-toggle' -> [] or ['3in4']
    """
    # Back-to-back filter
    if b2b_toggle and "b2b2" in b2b_toggle:
        if "back_to_back" in sub.columns:
            sub = sub[sub["back_to_back"] == 1]
        else:
            return sub.iloc[0:0]

    # 3rd game in 4 nights filter
    if three_in_four_toggle and "3in4" in three_in_four_toggle:
        if "third_in_four" in sub.columns:
            sub = sub[sub["third_in_four"] == 1]
        else:
            return sub.iloc[0:0]

    return sub


# -------------------------------------------------
# NEW Helpers: Team + WITH/WITHOUT filters
# -------------------------------------------------
def _first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _latest_team_for_player(df: pd.DataFrame, team_col: str, player: str) -> str | None:
    """
    For traded players, pick team from the most recent game_date.
    Prefer rows where played==1 if available.
    """
    if not player or team_col not in df.columns or date_col not in df.columns:
        return None

    tmp = df[df[player_col] == player].copy()
    if tmp.empty:
        return None

    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col, team_col])

    if tmp.empty:
        return None

    if "played" in tmp.columns:
        tmp_played = tmp[tmp["played"] == 1]
        if not tmp_played.empty:
            tmp = tmp_played

    tmp = tmp.sort_values(date_col)
    return str(tmp.iloc[-1][team_col])


def teammates_for_player(df: pd.DataFrame, player: str) -> list[str]:
    """
    Returns other players on the same team as the selected player (based on latest team).
    Falls back to all other players if no team column is available.
    """
    if not player:
        return []

    team_col = _first_existing_col(df, ["team", "team_abbreviation", "tm", "team_name", "team_id"])
    if not team_col:
        # fallback: all other players
        return sorted([p for p in df[player_col].dropna().unique() if p != player])

    team_val = _latest_team_for_player(df, team_col, player)
    if not team_val:
        return sorted([p for p in df[player_col].dropna().unique() if p != player])

    team_mask = df[team_col].astype(str) == str(team_val)
    players = df.loc[team_mask, player_col].dropna().unique().tolist()
    return sorted([p for p in players if p != player])


def apply_with_without_filters(
    df: pd.DataFrame,
    main_player: str,
    with_player: str | None,
    without_player: str | None,
) -> tuple[pd.DataFrame, str]:
    """
    Returns:
      - filtered MAIN PLAYER rows only
      - suffix label for titles/notes

    Requires df to have 'played' column.
    """
    if not main_player:
        return df.iloc[0:0].copy(), ""

    if "played" not in df.columns:
        raise ValueError("Missing required column 'played' in NBA dataset.")

    # main player rows
    sub = df[df[player_col] == main_player].copy()

    # Default: only games where main actually played
    if not with_player and not without_player:
        sub = sub[sub["played"] == 1]
        return sub, ""

    suffix_parts = []

    # WITH: dates where main + with both played -> sum(played)==2 for that date among those 2 players
    if with_player:
        pair = df[df[player_col].isin([main_player, with_player])].copy()
        g = pair.groupby(date_col, dropna=False)["played"].sum()
        with_dates = set(g[g == 2].index.tolist())
        sub = sub[sub[date_col].isin(with_dates)]
        suffix_parts.append(f"WITH: {with_player}")

    # WITHOUT: main played==1 AND without_player did NOT play that date (missing or played==0)
    if without_player:
        without_played_dates = set(
            df.loc[(df[player_col] == without_player) & (df["played"] == 1), date_col]
            .dropna()
            .unique()
            .tolist()
        )
        sub = sub[(sub["played"] == 1) & (~sub[date_col].isin(without_played_dates))]
        suffix_parts.append(f"WITHOUT: {without_player}")

    suffix = " | " + " & ".join(suffix_parts) if suffix_parts else ""
    return sub, suffix


# -------------------------------------------------
# NEW: Populate WITH/WITHOUT dropdown options (same team)
# -------------------------------------------------
@callback(
    Output("nba-stats-with-dropdown", "options"),
    Output("nba-stats-without-dropdown", "options"),
    Output("nba-stats-with-dropdown", "value"),
    Output("nba-stats-without-dropdown", "value"),
    Input("nba-stats-player-dropdown", "value"),
    Input("nba-stats-with-dropdown", "value"),
    Input("nba-stats-without-dropdown", "value"),
)
def update_with_without_dropdowns(main_player, current_with, current_without):
    if not main_player:
        return [], [], None, None

    df = get_nba_df()
    if df is None or df.empty:
        return [], [], None, None

    teammates = teammates_for_player(df, main_player)
    opts = [{"label": p, "value": p} for p in teammates]
    valid = set(teammates)

    # clear invalid selections if player/team changed
    new_with = current_with if current_with in valid else None
    new_without = current_without if current_without in valid else None

    # optional: prevent same player selected in both
    if new_with and new_without and new_with == new_without:
        new_without = None

    return opts, opts, new_with, new_without


# -------------------------------------------------
# Slider update callback
# -------------------------------------------------
@callback(
    Output("nba-stats-threshold-slider", "min"),
    Output("nba-stats-threshold-slider", "max"),
    Output("nba-stats-threshold-slider", "marks"),
    Output("nba-stats-threshold-slider", "value"),
    Output("nba-stats-range-note", "children"),
    Input("nba-stats-player-dropdown", "value"),
    Input("nba-stats-stat-dropdown", "value"),
    Input("nba-stats-with-dropdown", "value"),      # ✅ NEW
    Input("nba-stats-without-dropdown", "value"),   # ✅ NEW
    Input("nba-b2b-toggle", "value"),
    Input("nba-3in4-toggle", "value"),
)
def stats_update_slider_props(player, stat_col, with_player, without_player, b2b_toggle, three_in_four_toggle):
    print(
        "SLIDER CALLBACK — Player:", player, "Stat:", stat_col,
        "WITH:", with_player, "WITHOUT:", without_player,
        "B2B:", b2b_toggle, "3in4:", three_in_four_toggle,
        flush=True
    )

    if not player or not stat_col:
        return 0, 25, {}, 10, "Select a player and stat to begin."

    df_stats = get_nba_df()
    if df_stats is None or df_stats.empty:
        return 0, 25, {}, 10, "Data file is missing or empty."

    # Apply WITH/WITHOUT first (then schedule)
    sub, suffix = apply_with_without_filters(df_stats, player, with_player, without_player)
    sub = apply_schedule_filters(sub, b2b_toggle, three_in_four_toggle)

    if sub.empty:
        msg = f"No games found for this player with the selected filters.{suffix}"
        return 0, 25, {}, 10, msg

    if stat_col not in sub.columns:
        return 0, 25, {}, 10, "Selected stat not found in data."

    vals = clean_numeric(sub[stat_col])
    if vals.empty:
        return 0, 25, {}, 10, "No numeric values for selected stat."

    vmin = int(max(0, vals.min() - 5))
    vmax = int(vals.max() + 5)
    step = max(1, int((vmax - vmin) / 5))

    marks = {v: str(v) for v in range(vmin, vmax + 1, step)}
    default_value = int((vmin + vmax) / 2)

    return vmin, vmax, marks, default_value, f"Range based on selected data: {vmin} to {vmax}.{suffix}"


# -------------------------------------------------
# Threshold display (non-editable)
# -------------------------------------------------
@callback(
    Output("nba-threshold-display", "children"),
    Input("nba-stats-threshold-slider", "value")
)
def show_threshold(slider_value):
    print("THRESHOLD DISPLAY — Slider value:", slider_value, flush=True)
    return f"{slider_value}"


# -------------------------------------------------
# Main chart + summary + table callback
# -------------------------------------------------
@callback(
    Output("nba-stats-game-chart", "figure"),
    Output("nba-stats-summary-stats", "children"),
    Output("nba-stats-rates-table", "children"),
    Output("nba-stats-rates-footnote", "children"),
    Input("nba-stats-player-dropdown", "value"),
    Input("nba-stats-stat-dropdown", "value"),
    Input("nba-stats-with-dropdown", "value"),      # ✅ NEW
    Input("nba-stats-without-dropdown", "value"),   # ✅ NEW
    Input("nba-stats-threshold-slider", "value"),
    Input("nba-b2b-toggle", "value"),
    Input("nba-3in4-toggle", "value"),
)
def stats_update_chart_and_counts(player, stat_col, with_player, without_player, threshold, b2b_toggle, three_in_four_toggle):
    print(
        "CHART CALLBACK — Player:", player, "Stat:", stat_col, "Threshold:", threshold,
        "WITH:", with_player, "WITHOUT:", without_player,
        "B2B:", b2b_toggle, "3in4:", three_in_four_toggle,
        flush=True
    )

    if not stat_col:
        return empty_fig("Please select a statistic.")

    df_stats = get_nba_df()
    if df_stats is None or df_stats.empty:
        return empty_fig("Data file is missing or empty.")

    if not player:
        return empty_fig("Select a player to view game-by-game stats.")

    # Apply WITH/WITHOUT first (then schedule)
    sub, suffix = apply_with_without_filters(df_stats, player, with_player, without_player)
    sub = apply_schedule_filters(sub, b2b_toggle, three_in_four_toggle)

    if sub.empty:
        return empty_fig(f"No games found for this player with the selected filter(s).{suffix}")

    if stat_col not in sub.columns:
        return empty_fig("Selected stat not found in data.")

    # Ensure numeric stat
    sub[stat_col] = pd.to_numeric(sub[stat_col], errors="coerce")
    sub = sub.dropna(subset=[stat_col])
    if sub.empty:
        return empty_fig("Selected stat has no numeric values.")

    # Ensure date column is datetime for sorting/formatting
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub = sub.dropna(subset=[date_col])
    if sub.empty:
        return empty_fig("No valid game dates after filtering.")

    # --- DATE HANDLING ---
    sub = sub.sort_values(date_col)
    sub["date_str"] = sub[date_col].dt.strftime("%m/%d/%Y")

    threshold_val = float(threshold or 0)
    player_label = player

    x_vals = sub["date_str"]
    y_vals = sub[stat_col].astype(float).tolist()

    colors = ["#1f77b4" if v >= threshold_val else "#d62728" for v in y_vals]

    fig = go.Figure()
    fig.add_bar(
        x=x_vals,
        y=y_vals,
        marker_color=colors,
        hovertemplate=(
            f"{player_col}: {player_label}<br>"
            f"{date_col}: %{{x}}<br>"
            f"{stat_col.upper()}: %{{y}}<extra></extra>"
        ),
    )

    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="paper",
        y0=threshold_val, y1=threshold_val, yref="y",
        line=dict(color="black", width=2, dash="dash"),
    )

    fig.add_annotation(
        xref="paper",
        x=0.01,
        y=threshold_val,
        yref="y",
        yshift=8,
        text=f"Threshold: {threshold_val}",
        showarrow=False,
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="black",
        font=dict(size=11),
    )

    fig.update_layout(
        title=f"{player_label} — {stat_col.upper()} by Game{suffix}",
        xaxis_title="Game",
        yaxis_title=stat_col.upper(),
        template="simple_white",
        margin=dict(l=40, r=20, t=60, b=120),
        xaxis_tickangle=-45,
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=sub["date_str"].tolist(),
        ),
    )

    total_games = len(y_vals)
    over_count = sum(v >= threshold_val for v in y_vals)
    under_count = total_games - over_count
    over_pct = (100 * over_count / total_games) if total_games else 0

    summary = html.Div([
        html.Strong(f"{player_label} — {stat_col.upper()}{suffix}"),
        html.Div(f"Games shown: {total_games}"),
        html.Div(f"Over threshold: {over_count} ({over_pct:.1f}%)", style={"color": "#1f77b4"}),
        html.Div(f"Below threshold: {under_count}", style={"color": "#d62728"}),
    ])

    if location_col in sub.columns:
        home_games = sub[sub[location_col].astype(str).str.lower() == "home"]
        away_games = sub[sub[location_col].astype(str).str.lower() == "away"]
    else:
        home_games = pd.DataFrame()
        away_games = pd.DataFrame()

    all_counts = over_counts(sub, stat_col, threshold_val)
    home_counts = over_counts(home_games, stat_col, threshold_val)
    away_counts = over_counts(away_games, stat_col, threshold_val)

    table = build_table(all_counts, home_counts, away_counts)

    footnote_parts = []
    if total_games < 10:
        footnote_parts.append(f"Total games for {player_label}: {total_games} (fewer than 10 observations).")

    if with_player:
        footnote_parts.append("WITH filter: dates where both players played (sum(played)=2 for that date across the two players).")
    if without_player:
        footnote_parts.append("WITHOUT filter: dates where main player played and the other player did not (missing row or played==0).")

    footnote = " ".join(footnote_parts)

    return fig, summary, table, footnote
