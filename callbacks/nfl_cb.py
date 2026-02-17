import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html, no_update


# -------------------------------------------------
# Import data directly from the NFL page
# -------------------------------------------------
from pages.nfl import df_stats, player_col, date_col, location_col


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
        s = pd.Series([])
    else:
        s = clean_numeric(df[stat_col])

    return {
        "last5": int((s.tail(5) >= threshold).sum()),
        "last10": int((s.tail(10) >= threshold).sum()),
        "season": int((s >= threshold).sum()),
    }


def build_table(all_counts):
    header_style = {
        "padding": "12px 14px",
        "border": "1px solid #e6e9ee",
        "backgroundColor": "#f8f9fb",
        "fontWeight": "700",
        "textAlign": "center",
    }

    def cell_style():
        return {
            "padding": "10px 14px",
            "border": "1px solid #e6e9ee",
            "textAlign": "center",
            "fontSize": "14px",
        }

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
            html.Tbody([
                html.Tr([
                    html.Td("All games", style=cell_style()),
                    html.Td(str(all_counts["last5"]), style=cell_style()),
                    html.Td(str(all_counts["last10"]), style=cell_style()),
                    html.Td(str(all_counts["season"]), style=cell_style()),
                ])
            ])
        ],
        style={
            "borderCollapse": "collapse",
            "width": "60%",
            "minWidth": "360px",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.06)",
            "fontFamily": "Arial, sans-serif",
        },
    )


# -------------------------------------------------
# Slider update callback
# -------------------------------------------------
@callback(
    Output("nfl-stats-threshold-slider", "min"),
    Output("nfl-stats-threshold-slider", "max"),
    Output("nfl-stats-threshold-slider", "marks"),
    Output("nfl-stats-threshold-slider", "value"),
    Output("nfl-stats-range-note", "children"),
    Input("nfl-stats-player-dropdown", "value"),
    Input("nfl-stats-stat-dropdown", "value"),
)
def nfl_update_slider_props(player, stat_col):
    print("NFL SLIDER CALLBACK — Player:", player, "Stat:", stat_col)

    if not player or not stat_col:
        return 0, 25, {}, 10, "Select a player and stat to begin."

    sub = df_stats[df_stats[player_col] == player]

    if stat_col not in sub.columns:
        return 0, 25, {}, 10, "Selected stat not found in data."

    vals = clean_numeric(sub[stat_col])
    if vals.empty:
        return 0, 25, {}, 10, "No numeric values for selected stat."

    vmin = int(max(0, vals.min() - 1))
    vmax = int(vals.max() + 1)
    step = max(1, int((vmax - vmin) / 5))

    marks = {v: str(v) for v in range(vmin, vmax + 1, step)}
    default_value = int((vmin + vmax) / 2)

    return vmin, vmax, marks, default_value, f"Range based on selected data: {vmin} to {vmax}."


# -------------------------------------------------
# Threshold display (non-editable)
# -------------------------------------------------
@callback(
    Output("nfl-threshold-display", "children"),
    Input("nfl-stats-threshold-slider", "value")
)
def nfl_show_threshold(slider_value):
    print("NFL THRESHOLD DISPLAY — Slider value:", slider_value)
    return f"{slider_value}"


# -------------------------------------------------
# Main chart + summary + table callback
# -------------------------------------------------
@callback(
    Output("nfl-stats-game-chart", "figure"),
    Output("nfl-stats-summary-stats", "children"),
    Output("nfl-stats-rates-table", "children"),
    Output("nfl-stats-rates-footnote", "children"),
    Input("nfl-stats-player-dropdown", "value"),
    Input("nfl-stats-stat-dropdown", "value"),
    Input("nfl-stats-threshold-slider", "value"),
)
def nfl_update_chart_and_counts(player, stat_col, threshold):
    print("NFL CHART CALLBACK — Player:", player, "Stat:", stat_col, "Threshold:", threshold)

    if not stat_col:
        return empty_fig("Please select a statistic.")

    if df_stats is None or df_stats.empty:
        return empty_fig("Data file is missing or empty.")

    sub = df_stats.copy()
    if not player:
        return no_update
    else:
        sub = sub[sub[player_col] == player]

    if sub.empty:
        return empty_fig("No games found for this player.")

    sub[stat_col] = clean_numeric(sub[stat_col])
    sub = sub.dropna(subset=[stat_col])

    if sub.empty:
        return empty_fig("Selected stat has no numeric values.")

    sub = sub.sort_values(date_col)

    threshold_val = float(threshold or 0)
    player_label = player or "All Players"

    x_vals = sub[date_col].astype(str).tolist()
    y_vals = sub[stat_col].astype(float).tolist()

    colors = ["#1f77b4" if v >= threshold_val else "#d62728" for v in y_vals]

    # ---------- Chart ----------
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

    # ---------- Summary ----------
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

    # ---------- Table ----------
    all_counts = over_counts(sub, stat_col, threshold_val)
    table = build_table(all_counts)

    footnote = ""
    if total_games < 10:
        footnote = f"Total games for {player_label}: {total_games} (fewer than 10 observations)."

    return fig, summary, table, footnote
