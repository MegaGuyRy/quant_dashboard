# app.py
import argparse
import os
from datetime import datetime
import pandas as pd
from alpaca_trade_api.rest import REST

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
from strategies.xboost_tree_eval import train_models, evaluate_models
from trading.alpaca import allocate_portfolio, monitor_positions, check_account

# Create Alpaca API instance globally
api = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

def cur_date():
    """
    Get todays date
    """
    return datetime.now().strftime("%Y-%m-%d")

def retrieve_data(start_date="2022-01-01", end_date="2025-01-01"):
    """
    Step 1: Get data and engineered features
    Run: python app.py retrieve_data --start_date 2022-01-01 --end_date 2025-07-17
    Returns: df with all needed data and calculated features to train xboost trees
    """
    print("[INFO] Pulling Yahoo Finance data for S&P 500 symbols...")
    symbols = get_sp500_symbols()
    all_data = pd.DataFrame()

    for symbol in symbols:
        try:
            df = get_historical_data(symbol, start=start_date, end=end_date)
            if isinstance(df.columns, pd.MultiIndex):
                df = compute_return_features(df)
                df["Symbol"] = symbol 
                df.columns = df.columns.droplevel(1)
            else:
                df['Symbol'] = symbol

            df.reset_index(inplace=True)
            all_data = pd.concat([all_data, df], ignore_index=True)
            print(f"[INFO] Pulled {symbol}")
        except Exception as e:
            print(f"[WARNING] Failed to pull {symbol}: {e}")

    all_data['Date'] = pd.to_datetime(all_data['Date'])
    all_data = all_data.sort_values(by='Date')

    os.makedirs("logs/features", exist_ok=True)
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv"
    all_data.to_csv(file_path, index=False)
    print(f"[INFO] Saved combined data to {file_path}")
    return all_data

def train_xgboost_model(n_trees=100, horizon=1):
    """
    Step 2: Train XGBoost models on latest data
    n_trees: number of trees in forest
    Run: python app.py train_xgboost_model --n_trees 100 --horizon=1
    """
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'retrieve_data' first.")
    df = pd.read_csv(file_path)
    train_models(df, n_trees, horizon)

def xgboost_eval(horizon=1):
    """
    Step 3: Evaluate XGBoost models on latest data
    Run: python app.py xgboost_eval --horizon=1
    """
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'retrieve_data' first.")
    df = pd.read_csv(file_path)
    evaluate_models(df, horizon)

def trade(diversity):
    """
    Step 4: Make trades based on todays ticker_model_predictions csv
    diversity: amount of stocks to spread buying power between
    Run: python app.py trade
    """
    timestamp = cur_date()
    file_path = f"logs/rankings/ticker_model_predictions_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'xgboost_eval' first.")
    ranking_csv = pd.read_csv(file_path)
    allocate_portfolio(ranking_csv, diversity)

def close_all():
    """
    Used to close positions at at BOD or EOD (currently manual)
    Run: python app.py close_all
    """
    positions = api.list_positions()
    if not positions:
        print("[INFO] No open positions to close.")
        return

    print("[WARNING] The following positions will be closed:")
    for pos in positions:
        print(f" - {pos.symbol}: {pos.qty} shares")

    confirm = input("Are you sure you want to close ALL positions? Type 'YES' to confirm: ")
    if confirm == "YES":
        api.close_all_positions()
        print("[INFO] All positions have been closed.")
    else:
        print("[CANCELLED] No positions were closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[
        "retrieve_data", "train_xgboost_model", "xgboost_eval", 
        "trade", "monitor_positions", "close_all", "check_account"
    ])
    parser.add_argument("--start_date", type=str, default="2022-01-01")
    parser.add_argument("--end_date", type=str, default="2025-01-01")
    parser.add_argument("--n_trees", type=int, default=100)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--diversity", type=int, default=20)
    parser.add_argument("--tp", type=float, default=0.1)
    parser.add_argument("--sl", type=float, default=0.05)

    args = parser.parse_args()

    if args.command == "retrieve_data":
        retrieve_data(start_date=args.start_date, end_date=args.end_date)
    elif args.command == "train_xgboost_model":
        train_xgboost_model(n_trees=args.n_trees, horizon=args.horizon)
    elif args.command == "xgboost_eval":
        xgboost_eval(horizon=args.horizon)
    elif args.command == "trade":
        trade(diversity=args.diversity)
    elif args.command == "monitor_positions":
        monitor_positions(take_profit=args.tp, stop_loss=args.sl)
    elif args.command == "close_all":
        close_all()
    elif args.command == "check_account":
        check_account()
