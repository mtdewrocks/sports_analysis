# mlb_data.py
import os
import pandas as pd

# -------------------------------------------------
# CONFIG: data sources + image base
# -------------------------------------------------
DATA_BASE_RAW = os.getenv(
    "MLB_DATA_BASE_RAW",
    "https://github.com/mtdewrocks/matchup/raw/main/assets"
)

MLB_IMAGE_BASE = os.getenv(
    "MLB_IMAGE_BASE",
    "https://github.com/mtdewrocks/matchup/raw/main/assets"
)

PITCHER_SEASON_STATS_URL = f"{DATA_BASE_RAW}/Pitcher_Season_Stats.xlsx"
HIST_STARTING_PITCHERS_URL = f"{DATA_BASE_RAW}/Historical_Starting_Pitchers.xlsx"
PITCHING_LOGS_URL = f"{DATA_BASE_RAW}/2025_Pitching_Logs.xlsx"
SEASON_SPLITS_URL = f"{DATA_BASE_RAW}/Season_Aggregated_Pitcher_Statistics.xlsx"
PITCHER_PCT_URL = f"{DATA_BASE_RAW}/Pitcher_Percentile_Rankings.csv"
LAST_WEEK_URL = f"{DATA_BASE_RAW}/Last_Week_Stats.xlsx"
DAILY_COMBINED_URL = f"{DATA_BASE_RAW}/Combined_Daily_Data.xlsx"
HITTER_PCT_URL = f"{DATA_BASE_RAW}/Hitter_Percentile_Rankings.csv"
DAILY_PROPS_URL = f"{DATA_BASE_RAW}/Daily_Props.xlsx"
MY_PITCHER_LIST_URL = f"{DATA_BASE_RAW}/My_Pitcher_Listing.xlsx"
MY_HITTER_LIST_URL = f"{DATA_BASE_RAW}/My_Hitter_Listing.xlsx"

# -------------------------------------------------
# LOAD DATA (module import time = once per server start)
# -------------------------------------------------
df = pd.read_excel(PITCHER_SEASON_STATS_URL, usecols=["Name", "W", "L", "ERA", "IP", "SO", "WHIP", "GS"])
df["K/IP"] = (df["SO"] / df["IP"]).round(2)
df["WHIP"] = df["WHIP"].round(2)

dfPitchers = pd.read_excel(
    HIST_STARTING_PITCHERS_URL,
    usecols=["Baseball_Savant_Name", "Savant ID", "Handedness"]
).dropna()

df = df.merge(dfPitchers, left_on="Name", right_on="Baseball_Savant_Name", how="left")
df = df[["Name", "Baseball_Savant_Name", "Handedness", "GS", "W", "L", "ERA", "IP", "SO", "K/IP", "WHIP"]]

dfGameLogs = pd.read_excel(
    PITCHING_LOGS_URL,
    usecols=["Name", "Date", "Opp", "W", "L", "IP", "BF", "H", "R", "ER", "HR", "BB", "SO", "Pit"]
)
dfGameLogs["Date"] = pd.to_datetime(dfGameLogs["Date"], format="%Y-%m-%d").dt.date
dfGameLogs = dfGameLogs.rename(columns={"Opp": "Opponent"}).sort_values(by="Date", ascending=False)

dfS = pd.read_excel(SEASON_SPLITS_URL)
dfSplits = pd.melt(
    dfS,
    id_vars=["Pitcher", "Team", "Handedness", "Opposing Team", "Name", "Rotowire Name", "Split", "Baseball Savant Name", "Tm"],
    var_name="Statistic",
    value_name="Value",
)

dfpct = pd.read_csv(PITCHER_PCT_URL).rename(columns={
    "xera": "Expected ERA",
    "xba": "Expected Batting Avg",
    "fb_velocity": "Fastball Velo",
    "exit_velocity": "Avg Exit Velocity",
    "k_percent": "K %",
    "chase_percent": "Chase %",
    "whiff_percent": "Whiff %",
    "brl_percent": "Barrel %",
    "hard_hit_percent": "Hard-Hit %",
    "bb_percent": "BB %",
}).drop(columns=["year"], errors="ignore")

# keep your suffix scheme
dfpct = dfpct.rename(columns=lambda x: x + "_pitcher")
dfpct = dfpct[
    [
        "player_name_pitcher", "player_id_pitcher",
        "Expected ERA_pitcher", "Expected Batting Avg_pitcher", "Fastball Velo_pitcher",
        "Avg Exit Velocity_pitcher", "Chase %_pitcher", "Whiff %_pitcher", "K %_pitcher",
        "BB %_pitcher", "Barrel %_pitcher", "Hard-Hit %_pitcher",
    ]
]

dfpct_chart = dfpct.rename(columns=lambda x: x.replace("_pitcher", "")).rename(
    columns={"player_name": "player_name", "player_id": "player_id"}
)
dfpct_reshaped = pd.melt(dfpct_chart, id_vars=["player_name", "player_id"], var_name="Statistic", value_name="Percentile")

def convert_name(name: str) -> str:
    last_name, first_name = name.split(", ")
    return f"{first_name} {last_name}"

dfpct_reshaped["converted_name"] = dfpct_reshaped["player_name"].apply(convert_name)

dfLast7 = pd.read_excel(LAST_WEEK_URL)
dfHot = dfLast7.query("PA>=20 & BA>=.350")

dfLastWeek = dfLast7[["Name", "BA"]].rename(columns={"BA": "Last Week Average"})

dfDaily = pd.read_excel(DAILY_COMBINED_URL)

dfHitters = dfDaily[
    ["fg_name", "Savant Name", "Bats", "Batting Order", "Average", "wOBA",
     "ISO", "K%", "BB%", "Fly Ball %", "Hard Contact %", "Pitcher", "Baseball Savant Name"]
]

df_hitter_pct = pd.read_csv(
    HITTER_PCT_URL,
    usecols=["player_name", "xwoba", "xba", "xslg", "xiso", "xobp", "brl_percent",
             "exit_velocity", "hard_hit_percent", "k_percent", "bb_percent", "whiff_percent", "chase_percent"]
).rename(columns=lambda x: x + "_hitter")

dfHittersFinal = dfHitters.merge(dfLastWeek, left_on="Savant Name", right_on="Name", how="left").drop(columns=["Name"], errors="ignore")

dfHitterMerge = dfDaily.merge(df_hitter_pct, left_on="Savant Name", right_on="player_name_hitter", how="left")
dfFinalMatchup = dfHitterMerge.merge(
    dfpct,
    left_on="Baseball Savant Name",
    right_on="player_name_pitcher",
    how="left",
    suffixes=["_Hitter", "_Pitcher"],
)

df_props = pd.read_excel(DAILY_PROPS_URL)
df_pitchers = pd.read_excel(MY_PITCHER_LIST_URL, usecols=["Props Name", "mlb_team_long"])
df_hitters = pd.read_excel(MY_HITTER_LIST_URL, usecols=["Props Name", "mlb_team_long"])

df_players = pd.concat([df_pitchers, df_hitters], ignore_index=True)
df_daily_props = df_props.merge(df_players, left_on="Player", right_on="Props Name", how="left").dropna(subset=["mlb_team_long"])
df_props_matchup = df_daily_props.merge(dfFinalMatchup, on=["Props Name", "mlb_team_long"], how="left")

# -------------------------------------------------
# Shared styling
# -------------------------------------------------
hitter_style = [
    {"if": {"filter_query": "{Average} < .250", "column_id": "Average"}, "backgroundColor": "lightcoral"},
    {"if": {"filter_query": "{Average} < 0.200", "column_id": "Average"}, "backgroundColor": "darkred"},
    {"if": {"filter_query": "{Average} >= 0.250", "column_id": "Average"}, "backgroundColor": "dodgerblue"},
    {"if": {"filter_query": "{Average} >= 0.275", "column_id": "Average"}, "backgroundColor": "blue"},
    {"if": {"filter_query": "{Average} > 0.300", "column_id": "Average"}, "backgroundColor": "darkgreen"},
    {"if": {"column_id": "Average"}, "color": "white"},

    {"if": {"filter_query": "{wOBA} < .325", "column_id": "wOBA"}, "backgroundColor": "lightcoral"},
    {"if": {"filter_query": "{wOBA} <= 0.275", "column_id": "wOBA"}, "backgroundColor": "darkred"},
    {"if": {"filter_query": "{wOBA} >= 0.325", "column_id": "wOBA"}, "backgroundColor": "dodgerblue"},
    {"if": {"filter_query": "{wOBA} >= 0.360", "column_id": "wOBA"}, "backgroundColor": "blue"},
    {"if": {"filter_query": "{wOBA} > 0.400", "column_id": "wOBA"}, "backgroundColor": "darkgreen"},
    {"if": {"column_id": "wOBA"}, "color": "white"},

    {"if": {"filter_query": "{ISO} < .175", "column_id": "ISO"}, "backgroundColor": "lightcoral"},
    {"if": {"filter_query": "{ISO} <= 0.125", "column_id": "ISO"}, "backgroundColor": "darkred"},
    {"if": {"filter_query": "{ISO} >= 0.175", "column_id": "ISO"}, "backgroundColor": "dodgerblue"},
    {"if": {"filter_query": "{ISO} >= 0.225", "column_id": "ISO"}, "backgroundColor": "blue"},
    {"if": {"filter_query": "{ISO} > 0.275", "column_id": "ISO"}, "backgroundColor": "darkgreen"},
    {"if": {"column_id": "ISO"}, "color": "white"},

    {"if": {"filter_query": "{K%} < 25", "column_id": "K%"}, "backgroundColor": "lightcoral"},
    {"if": {"filter_query": "{K%} >= 25", "column_id": "K%"}, "backgroundColor": "darkred"},
    {"if": {"filter_query": "{K%} < 20", "column_id": "K%"}, "backgroundColor": "dodgerblue"},
    {"if": {"filter_query": "{K%} < 15", "column_id": "K%"}, "backgroundColor": "blue"},
    {"if": {"filter_query": "{K%} < 10", "column_id": "K%"}, "backgroundColor": "darkgreen"},
    {"if": {"column_id": "K%"}, "color": "white"},
]
