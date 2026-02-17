from flask import Flask, render_template
import dash
from dash import Dash
import dash_bootstrap_components as dbc
import os
from dash import html, dcc

# -------------------------------------------------
# Create Flask server
# -------------------------------------------------
server = Flask(__name__)

# -------------------------------------------------
# Create Dash app mounted on Flask
# -------------------------------------------------
dash_app = Dash(
    __name__,
    server=server,
    use_pages=True,            # enables Dash Pages
    pages_folder="pages",      # your NBA + NFL pages live here
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    url_base_pathname="/dash/",  # Dash lives under /dash/
)

# -------------------------------------------------
# Dash Layout (global navigation + page container)
# -------------------------------------------------
from components.navbar import Navbar

dash_app.layout = html.Div(
    [
        Navbar(),
        html.Div(style={"height": "60px"}),  # spacer so content isn't hidden
        dash.page_container,
    ]
)
# -------------------------------------------------
# Flask Routes
# -------------------------------------------------
@server.route("/")
def index():
    return render_template("index.html")  # simple landing page

from callbacks import nba_cb, nfl_cb, nba_absence_cb, nba_props_lines_cb
#import callbacks.nba_cb
#import callbacks.nfl_cb
#import callbacks.nba_absence_cb
#import callbacks.nba_props_lines_cb

# -------------------------------------------------
# Run the app
# -------------------------------------------------
if __name__ == "__main__":
    server.run(debug=True)
