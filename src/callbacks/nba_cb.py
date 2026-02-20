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
)
def stats_update_slider_props(player, stat_col):
    print("SLIDER CALLBACK — Player:", player, "Stat:", stat_col, flush=True)

    if not player or not stat_col:
        return 0, 25, {}, 10, "Select a player and stat to begin."

    # ✅ Load cached df inside callback
    df_stats = get_nba_df()

    sub = df_stats[df_stats[player_col] == player]

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

    return vmin, vmax, marks, default_value, f"Range based on selected data: {vmin} to {vmax}."


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
    Input("nba-stats-threshold-slider", "value"),
)
def stats_update_chart_and_counts(player, stat_col, threshold):
    print("CHART CALLBACK — Player:", player, "Stat:", stat_col, "Threshold:", threshold, flush=True)

    if not stat_col:
        return empty_fig("Please select a statistic.")

    # ✅ Load cached df inside callback
    df_stats = get_nba_df()
    if df_stats is None or df_stats.empty:
        return empty_fig("Data file is missing or empty.")

    sub = df_stats.copy()
    if player:
        sub = sub[sub[player_col] == player]

    if sub.empty:
        return empty_fig("No games found for this player.")

    sub[stat_col] = pd.to_numeric(sub[stat_col], errors="coerce")
    sub = sub.dropna(subset=[stat_col])

    if sub.empty:
        return empty_fig("Selected stat has no numeric values.")

    sub = sub.sort_values(date_col)

    threshold_val = float(threshold or 0)
    player_label = player or "All Players"

    x_vals = sub[date_col].astype(str).tolist()
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
        title=f"{player_label} — {stat_col.upper()} by Game",
        xaxis_title="Game",
        yaxis_title=stat_col.upper(),
        template="simple_white",
        margin=dict(l=40, r=20, t=60, b=120),
        xaxis_tickangle=-45,
    )

    total_games = len(y_vals)
    over_count = sum(v >= threshold_val for v in y_vals)
    under_count = total_games - over_count
    over_pct = (100 * over_count / total_games) if total_games else 0

    summary = html.Div([
        html.Strong(f"{player_label} — {stat_col.upper()}"),
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

    footnote = ""
    if total_games < 10:
        footnote = f"Total games for {player_label}: {total_games} (fewer than 10 observations)."

    return fig, summary, table, footnote
