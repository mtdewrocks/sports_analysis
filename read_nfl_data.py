import pandas as pd

# -------------------------------------------------
# Load data ONCE
# -------------------------------------------------
stats_file = r"C:\Users\shawn\Python\Football\2025\Player_Stats_Weekly.parquet"

df_stats = pd.read_parquet(stats_file)
df_stats.columns = (
    df_stats.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)
print(df_stats.columns.tolist())
