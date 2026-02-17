# pages/mlb_hot_hitters.py
import dash
from dash import html
import dash_bootstrap_components as dbc
from dash import dash_table

from mlb_data import dfHot

dash.register_page(__name__, path="/mlb/hot-hitters", name="MLB Hot Hitters")

layout = dbc.Container(
    [
        dbc.Row([html.H1("Hot Hitters", style={"color": "red", "fontSize": 40, "textAlign": "center"})]),
        dbc.Row(html.H6("Statistics over the last week", style={"fontSize": 20, "textAlign": "center"})),
        dbc.Row(
            dash_table.DataTable(
                id="mlb-hot-hitters",
                data=dfHot.to_dict("records"),
                style_cell={"textAlign": "center"},
                sort_action="native",
                page_size=25,
            )
        ),
    ],
    fluid=True,
)
