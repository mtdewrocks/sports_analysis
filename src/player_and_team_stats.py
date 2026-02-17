import pandas as pd
import os
import time
import numpy as np
import nfl_data_py as nfl
import requests
from io import StringIO

os.chdir(r'C:\Users\shawn\Python\sports_dash_app\data')
week = 18

beginningTime = time.time()

schedule = nfl.import_schedules(years=[2025])

schedule["Matchup"] = schedule["game_id"].str[8:]
schedule["Matchup"] = schedule["Matchup"].str.replace("_", " @ ")
schedule = schedule[["week", "away_team", "home_team", "Matchup","home_score","away_score"]]

#Currently not working due to issues with package - manually downloaded it
#weekly = nfl.import_weekly_data(years=[2025])

url = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv"
output_path = r"C:\Users\shawn\Python\sports_dash_app\data\Player_Stats_Weekly.xlsx"

# Download the CSV content
response = requests.get(url)

# Read CSV into a DataFrame
csv_data = StringIO(response.text)
weekly = pd.read_csv(csv_data)

# Write to Excel
weekly.to_excel(output_path, index=False)
weekly = weekly.query("week <=@week")

team_stats = weekly.copy()

##Offense
team_stats["total_plays"] = team_stats[["attempts", "carries", "sacks_suffered"]].sum(axis=1)
team_stats["total_team_plays"] = team_stats.groupby("team")["total_plays"].transform("sum")
teams = team_stats[["team", "opponent_team"]]

def create_new_stat(new_column, column, transform):
    team_stats[new_column] = team_stats.groupby("team")[column].transform(transform)


create_new_stat("team_rush_yards", "rushing_yards", "sum")
create_new_stat("team_pass_yards", "passing_yards", "sum")
create_new_stat("Pass Attempts", "attempts", "sum")
create_new_stat("Sacks Allowed", "sacks_suffered","sum")

team_stats["games_count"] = team_stats.groupby("team")['week'].transform('nunique')
team_stats["Plays Per Game"] = team_stats["total_team_plays"]/team_stats["games_count"]
team_stats["Rush Yards Per Game"] = team_stats["team_rush_yards"]/team_stats["games_count"]
team_stats["Pass Yards Per Game"] = team_stats["team_pass_yards"]/team_stats["games_count"]
team_stats["rush_attempts"] = team_stats.groupby("team")['carries'].transform('sum')

team_stats["total_pass_plays"] = team_stats[["attempts", "sacks_suffered"]].sum(axis=1)
team_stats["pass_attempts"] = team_stats.groupby("team")['total_pass_plays'].transform('sum')
team_stats["run_share"] = team_stats["rush_attempts"]/team_stats["total_team_plays"]*100
team_stats["pass_share"] = team_stats["pass_attempts"]/team_stats["total_team_plays"]*100
team_stats["Yards Per Carry"] = team_stats["team_rush_yards"]/team_stats["rush_attempts"]
team_stats["Yards Per Pass Attempt"] = team_stats["team_pass_yards"]/team_stats["Pass Attempts"]

offense = team_stats[["team", "Plays Per Game", "run_share", "pass_share", "Yards Per Carry", "Yards Per Pass Attempt", "Rush Yards Per Game", "Pass Yards Per Game", "Sacks Allowed"]]
offense = offense.drop_duplicates(subset="team", keep="first")

##Defense

team_stats["Defense Plays Per Game"] = team_stats.groupby("opponent_team")["total_plays"].transform('sum')/team_stats.groupby("opponent_team")['week'].transform("nunique")
team_stats[["Defense Total Plays", "Defense Rush Attempts", "Defense Pass Attempts"]] = team_stats.groupby("opponent_team")[["total_plays", "carries", "total_pass_plays"]].transform('sum')
team_stats["Defense Rush Share"] = team_stats["Defense Rush Attempts"]/team_stats["Defense Total Plays"]*100
team_stats["Defense Pass Share"] = team_stats["Defense Pass Attempts"]/team_stats["Defense Total Plays"]*100
team_stats["Defense Rush Yards Per Game"] = team_stats.groupby("opponent_team")["rushing_yards"].transform('sum')/team_stats.groupby("opponent_team")['week'].transform("nunique")
team_stats["Defense Pass Yards Per Game"] = team_stats.groupby("opponent_team")["passing_yards"].transform('sum')/team_stats.groupby("opponent_team")['week'].transform("nunique")
team_stats["Defense Rush Yards Per Attempt"] = team_stats.groupby("opponent_team")["rushing_yards"].transform('sum')/team_stats["Defense Rush Attempts"]
team_stats["Defense Pass Yards Per Attempt"] = team_stats.groupby("opponent_team")["passing_yards"].transform('sum')/team_stats["Defense Pass Attempts"]
team_stats["Defensive Sacks"] = team_stats.groupby("opponent_team")["sacks_suffered"].transform("sum")

defense = team_stats[["opponent_team", "Defense Plays Per Game", "Defense Rush Share", "Defense Pass Share", "Defense Rush Yards Per Attempt", "Defense Rush Yards Per Game",
                      "Defense Pass Yards Per Attempt", "Defense Pass Yards Per Game","Defensive Sacks"]]
defense = defense.drop_duplicates(subset="opponent_team", keep="first")

def offense_rank(new_column, column, ascending, method):
    offense[new_column] = offense[column].rank(ascending=ascending, method=method)

def defense_rank(new_column, column, ascending, method):
    defense[new_column] = defense[column].rank(ascending=ascending, method=method)

columns = ["Plays Per Game", "run_share", "pass_share", "Rush Yards Per Game", "Yards Per Carry", "Pass Yards Per Game", "Yards Per Pass Attempt","Sacks Allowed"]
for column in columns:
    offense_rank("Rank - " + column, column, False, "min")


def_columns = ["Defense Plays Per Game", "Defense Rush Share", "Defense Pass Share", "Defense Rush Yards Per Game", "Defense Rush Yards Per Attempt",
               "Defense Pass Yards Per Game", "Defense Pass Yards Per Attempt", "Defensive Sacks"]

for column in def_columns:
    defense_rank("Rank - " + column, column, True, "min")

combined_team_stats = offense.merge(defense, left_on="team", right_on="opponent_team", how="inner")


offense = team_stats[["team", "opponent_team", "Plays Per Game", "run_share", "pass_share"]]

df_scores = schedule.query("week<=@week")

home = df_scores[["home_team", "home_score"]]
away = df_scores[["away_team", "away_score"]]

home = home.rename(columns={"home_team":"team", "home_score":"score"})
away = away.rename(columns={"away_team":"team", "away_score":"score"})

offense_scores = pd.concat([home,away])
offense_scores_per_game = offense_scores.groupby("team")["score"].mean().reset_index()
offense_scores_per_game["Rank - Scoring Offense"] = offense_scores_per_game["score"].rank(ascending=False, method="min")

defense_home = df_scores[["home_team", "away_score"]]

defense_away = df_scores[["away_team", "home_score"]]

defense_home_score = defense_home.rename(columns={"home_team":"team", "away_score":"score"})
defense_away_score = defense_away.rename(columns={"away_team":"team", "home_score":"score"})

defense_scores = pd.concat([defense_home_score, defense_away_score])
defense_scores_per_game = defense_scores.groupby("team")["score"].mean().reset_index()
defense_scores_per_game["Rank - Scoring Defense"] = defense_scores_per_game["score"].rank(ascending=True, method="min")

scores_per_game = offense_scores_per_game.merge(defense_scores_per_game, on="team", how="inner", suffixes=["_offense", "_defense"])
scores_per_game.to_excel('Points Per Game.xlsx', index=False)

team_stats_final = combined_team_stats.merge(scores_per_game, left_on="team", right_on="team", how="inner")
team_stats_final.to_excel("2025 Team Stats.xlsx", index=False)
