from dash import html, dcc

def Navbar():
    return html.Div(
        className="navbar",
        children=[

            # -------------------------
            # HOME (Flask route)
            # MUST force full refresh
            # -------------------------
            html.A(
                "Home",
                href="https://sports-prop-research.onrender.com/",       # 🔑 THIS FIXES THE ERROR
                className="nav-item"
            ),

            # -------------------------
            # NFL DROPDOWN (Dash pages)
            # -------------------------
            html.Div(
                className="nav-item dropdown",
                children=[
                    html.Div("NFL", className="dropdown-title"),
                    html.Div(
                        className="dropdown-menu",
                        children=[
                            dcc.Link(
                                "Game Matchup",
                                href="/dash/nfl-matchups",
                                className="dropdown-link"
                            ),
                            dcc.Link(
                                "Game Log",
                                href="/dash/nfl-game-logs",
                                className="dropdown-link"
                            ),
                            dcc.Link(
                                "Dashboard 3",
                                href="/dash/nfl/dashboard3",
                                className="dropdown-link"
                            ),
                        ],
                    ),
                ],
            ),

            # -------------------------
            # NBA DROPDOWN (Dash pages)
            # -------------------------
            html.Div(
                className="nav-item dropdown",
                children=[
                    html.Div("NBA", className="dropdown-title"),
                    html.Div(
                        className="dropdown-menu",
                        children=[
                            dcc.Link(
                                "Game Logs",
                                href="/dash/nba",
                                className="dropdown-link"
                            ),
                            dcc.Link(
                                "In/Out Analysis",
                                href="/dash/nba_in_out",
                                className="dropdown-link"
                            ),
                            dcc.Link(
                                "NBA Props",
                                href="/dash/nba_props",
                                className="dropdown-link"
                            ),
                        ],
                    ),
                ],
            ),

            # -------------------------
            # MLB DROPDOWN (Dash pages)
            # -------------------------
            html.Div(
                className="nav-item dropdown",
                children=[
                    html.Div("MLB", className="dropdown-title"),
                    html.Div(
                        className="dropdown-menu",
                        children=[
                            dcc.Link(
                                "Matchup",
                                href="/dash/mlb/matchup",
                                className="dropdown-link"
                            ),
                            dcc.Link(
                                "Hot Hitters",
                                href="/dash/mlb/hot-hitters",
                                className="dropdown-link"
                            ),
                            dcc.Link(
                                "Props",
                                href="/dash/mlb/props",
                                className="dropdown-link"
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
