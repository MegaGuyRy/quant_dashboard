# app_auto.py

import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import psycopg2

from config import BASE_URL
from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
from strategies.xboost_tree_eval import train_models, evaluate_models
from trading.db_utils import insert_predictions_to_db
from trading.alpaca import get_alpaca_credentials

# ------------------------
# Load .env and credentials
# ------------------------
load_dotenv()
strategy = os.getenv("STRATEGY", "day1")
db_password = os.getenv("POSTGRES_PASSWORD")

conn = psycopg2.connect(
    dbname="quant_trading",
    user="ryan",
    password=db_password,
    host="localhost",
    port="5432"
)

def run_daily_pipeline():
    print("[INFO] Starting automated pipeline...")

    # 1. Load tickers
    tickers = get_sp500_symbols()
    start_date = "2020-01-01"
    end_date = datetime.today().strftime("%Y-%m-%d")

    # 2. Pull and combine data
    all_data = pd.DataFrame()
    for symbol in tickers:
        try:
            df = get_historical_data(symbol, start=start_date, end=end_date)
            if isinstance(df.columns, pd.MultiIndex):
                df = compute_return_features(df)
                df["Symbol"] = symbol
                df.columns = df.columns.droplevel(1)
            else:
                df["Symbol"] = symbol
            df.reset_index(inplace=True)
            all_data = pd.concat([all_data, df], ignore_index=True)
            print(f"[DATA] Collected: {symbol}")
        except Exception as e:
            print(f"[WARN] {symbol} failed: {e}")

    # 3. Train and evaluate
    horizon = 1  # change if needed
    all_data['Date'] = pd.to_datetime(all_data['Date'])
    train_models(all_data, n_trees=200, horizon=horizon)
    prediction_df = evaluate_models(all_data, horizon=horizon)

    # 4. Write predictions to PostgreSQL
    insert_predictions_to_db(conn, prediction_df, horizon, strategy.upper())

    print("[INFO] Finished model creation + DB write")

if __name__ == "__main__":
    run_daily_pipeline()
