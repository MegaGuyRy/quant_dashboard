# app.py
import argparse
import os
from datetime import datetime, timedelta
import pandas as pd

from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
from strategies.xboost_tree_eval import train_tree_eval
from trading.alpaca import allocate_portfolio, monitor_positions

def cur_date():
    """
    Get todays date
    """
    timestamp = datetime.now().strftime("%Y-%m-%d") # Get todays date
    return timestamp

def retrieve_data(start_date="2022-01-01", end_date="2025-01-01"):
    """
    Step 1: Get data and engineered features
    Run: python app.py retrieve_data --start_date 2022-01-01 --end_date 2025-01-01
    Returns: df with all needed data and calculated features to train xboost trees
    """
    print("[INFO] Pulling Yahoo Finance data for S&P 500 symbols...")
    symbols = get_sp500_symbols()
    all_data = pd.DataFrame() # Declare empty data
    for symbol in symbols[:3]:  # Limit for testing; remove `[:3]` to run on all symbols
        try:
            df = get_historical_data(symbol, start=start_date, end=end_date)
            if isinstance(df.columns, pd.MultiIndex):
                df = compute_return_features(df) # Compute and add features from feature engineering
                ticker = df.columns.levels[1][0] # Get ticker symbols for each stock
                df["Symbol"] = symbol 
                df.columns = df.columns.droplevel(1) # Format df without index
            else:
                df['Symbol'] = symbol
                
            df.reset_index(inplace=True)
            all_data = pd.concat([all_data, df], ignore_index=True)
            
            print(f"[INFO] Pulled {symbol}")
        except Exception as e:
            print(f"[WARN] Failed to pull {symbol}: {e}")
            
    all_data['Date'] = pd.to_datetime(all_data['Date'])
    all_data = all_data.sort_values(by='Date')
    
    os.makedirs("logs", exist_ok=True) # Make logs directory
    timestamp = cur_date()
    file_path = f"logs/feature_df_{timestamp}.csv" # Save CSV data 
    all_data.to_csv(file_path, index=False)
    print(f"[INFO] Saved combined data to {file_path}")

if __name__ == "__main__":
# pyton app.py.
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["retrieve_data"], help="Which function to run")
    parser.add_argument("--start_date", type=str, default="2022-01-01")
    parser.add_argument("--end_date", type=str, default="2025-01-01")

    args = parser.parse_args()

    if args.command == "retrieve_data":
        retrieve_data(start_date=args.start_date, end_date=args.end_date)
