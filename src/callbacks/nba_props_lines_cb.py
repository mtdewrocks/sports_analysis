import pandas as pd

from dash import Input, Output, callback, html, dash_table

# Import dataframe AND helper functions from the page module
from pages.nba_props_lines import (
    df_props,
    props_player_options,
    props_market_options
)

# ------------------------------------------------------------
# DROPDOWN OPTIONS CALLBACK
# ------------------------------------------------------------
@callback(
    Output("props-player-dropdown", "options"),
    Output("props-market-dropdown", "options"),
    Input("main-tabs", "value")
)
def props_update_options(tab):
    return props_player_options(), props_market_options()


# ------------------------------------------------------------
# MAIN TABLE CALLBACK
# ------------------------------------------------------------
@callback(
    Output('props-odds-table', 'children'),
    Input('props-player-dropdown', 'value'),
    Input('props-market-dropdown', 'value'),
    Input('props-side-radio', 'value')
)
def props_update_table(player, market, side):

    if df_props.empty:
        return html.Div("No props data file found.", style={"color": "red"})

    filtered = df_props.copy()

    # Filtering
    if player:
        filtered = filtered[filtered['player'] == player]

    if market:
        filtered = filtered[filtered['market'] == market]

    # Normalized price column names
    price_col = 'over_price' if side == 'over' else 'under_price'

    if filtered.empty or price_col not in filtered.columns:
        return html.Div("No data available for this selection.", style={"color": "red"})

    # Build line_id using normalized column names
    filtered['line_id'] = (
        filtered['player'] + " " +
        filtered['line'].astype(str) + " " +
        filtered['market']
    )

    # Pivot table
    pivot = filtered.pivot_table(
        index='line_id',
        columns='bookmakers',
        values=price_col,
        aggfunc='first'
    )

    # Require at least 4 books
    pivot = pivot[pivot.notnull().sum(axis=1) >= 4]

    if pivot.empty:
        return html.Div("No lines with enough sportsbook coverage.", style={"color": "orange"})

    pivot.reset_index(inplace=True)

    # Implied probability helper
    def implied_prob(odds):
        try:
            odds = float(odds)
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)
        except:
            return None

    # Highlighting logic
    styles = []
    for i, row in pivot.iterrows():
        odds_values = row[1:].dropna()
        if odds_values.empty:
            continue

        probs = odds_values.apply(implied_prob)
        if probs.isnull().all():
            continue

        best_col = probs.idxmin()
        best_prob = probs[best_col]
        other_probs = probs.drop(best_col)

        if len(other_probs) == 0:
            continue

        if all(p > best_prob * 1.05 for p in other_probs):
            styles.append({
                'if': {'row_index': i, 'column_id': best_col},
                'backgroundColor': '#d4edda',
                'fontWeight': 'bold'
            })

    # Build table
    table = dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in pivot.columns],
        data=pivot.to_dict('records'),
        style_table={'overflowX': 'auto', 'border': '1px solid #dee2e6'},
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'border': '1px solid #dee2e6',
            'whiteSpace': 'normal'
        },
        style_header={
            'backgroundColor': '#343a40',
            'color': 'white',
            'fontWeight': 'bold',
            'border': '1px solid #dee2e6'
        },
        style_data_conditional=styles
    )

    return table
