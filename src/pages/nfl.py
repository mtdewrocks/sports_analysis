from dash import html, dcc, register_page

register_page(
    __name__,
    path="/nfl-game-logs",
    name="NFL Game Log",
    title="NFL Game Log",
)

layout = html.Div([

    # ---------- Sidebar ----------
    html.Div([
        html.H2("Player Stats Filters", style={"marginBottom": "20px"}),

        html.Label("Player"),
        dcc.Dropdown(
            id="nfl-stats-player-dropdown",
            options=[],
            placeholder="Select a player",
            persistence=True,
            persistence_type="session",
            style={"marginBottom": "12px"},
        ),

        html.Label("Statistic"),
        dcc.Dropdown(
            id="nfl-stats-stat-dropdown",
            options=[],
            placeholder="Select a statistic",
            persistence=True,
            persistence_type="session",
            style={"marginBottom": "12px"},
        ),

        html.Label("Threshold (set using the slider)"),

        html.Div(
            id="nfl-threshold-display",
            style={
                "marginBottom": "8px",
                "padding": "6px 12px",
                "border": "1px solid #ccc",
                "borderRadius": "4px",
                "backgroundColor": "#f8f9fa",
                "fontSize": "14px",
                "color": "#333"
            }
        ),

        dcc.Slider(
            id="nfl-stats-threshold-slider",
            min=0,
            max=50,
            step=1,
            value=10,
            tooltip={"placement": "bottom"},
            updatemode="drag",
            persistence=True,
            persistence_type="session",
        ),

        html.Div(
            id="nfl-stats-range-note",
            style={"marginTop": "8px", "fontSize": "12px", "color": "#666"},
        ),

        html.Div(
            id="nfl-data-load-status",
            style={"marginTop": "12px", "color": "#b00020", "fontSize": "12px"},
        ),

        # hidden trigger to init dropdowns after render
        dcc.Interval(id="nfl-init", interval=500, n_intervals=0, max_intervals=1),

    ],
    style={
        "width": "22%",
        "padding": "20px",
        "backgroundColor": "#f8f9fa",
        "borderRight": "2px solid #dee2e6",
        "height": "100vh",
        "position": "fixed",
        "overflowY": "auto",
    }),

    # ---------- Main Content ----------
    html.Div([
        html.H2("Game-by-Game Chart"),

        dcc.Loading(
            dcc.Graph(id="nfl-stats-game-chart"),
            type="default",
        ),

        html.Div(id="nfl-stats-summary-stats", style={"marginTop": "12px"}),

        html.H3("Over Counts (games ≥ threshold)", style={"marginTop": "20px"}),

        html.Div(id="nfl-stats-rates-table"),

        html.Div(
            id="nfl-stats-rates-footnote",
            style={"marginTop": "8px", "fontSize": "12px", "color": "#666"},
        ),
    ],
    style={"marginLeft": "24%", "padding": "20px"}),
])
