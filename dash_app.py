import dash
import dash_bootstrap_components as dbc
from dash import Dash, page_container

# -------------------------------------------------
# Create Dash App (Dash Pages enabled)
# -------------------------------------------------
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# -------------------------------------------------
# Import callbacks (ensures they register)
# -------------------------------------------------
import callbacks.nba_cb
import callbacks.nfl_cb

# -------------------------------------------------
# App Layout (Dash Pages handles routing)
# -------------------------------------------------
app.layout = page_container

# -------------------------------------------------
# Run Server
# -------------------------------------------------
if __name__ == "__main__":
    app.run_server(debug=True)
