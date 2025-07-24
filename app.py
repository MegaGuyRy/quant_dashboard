import argparse
import os
from datetime import datetime
import pandas as pd

from alpaca_trade_api.rest import REST
from config import get_alpaca_credentials, BASE_URL
from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
from strategies.xboost_tree_eval import train_models, evaluate_models
from trading.alpaca import allocate_portfolio, monitor_positions, check_account, close_all_positions

# Global API object placeholder
api = None

def cur_date():
    """
    Get today's date string
    """
    return datetime.now().strftime("%Y-%m-%d")

def retrieve_data(start_date="2020-01-01", end_date="2025-01-01", interval="1d"):
    """
    Step 1: Download historical data and compute features
    python app.py retrieve_data --start_date 2020-01-01 --end_date 2025-07-24 --interval 1d 
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
    Step 2: Train XGBoost models on saved data
    python app.py train_xgboost_model --n_trees 200 --horizon 1 

    """
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'retrieve_data' first.")
    df = pd.read_csv(file_path)
    train_models(df, n_trees, horizon)

def xgboost_eval(horizon=1):
    """
    Step 3: Evaluate XGBoost models and rank predictions
    python app.py xgboost_eval --horizon 1 
    """
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'retrieve_data' first.")
    df = pd.read_csv(file_path)
    evaluate_models(df, horizon)

def trade(api, diversity, horizon=1):
    """
    Step 4: Allocate capital using ranked model predictions
    python app.py trade --diversity 10 --horizon 1 --strategy DAY1
    """
    timestamp = cur_date()
    file_path = f"logs/rankings/{horizon}/ticker_model_predictions_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'xgboost_eval' first.")
    allocate_portfolio(api, file_path, diversity)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[
        "retrieve_data", "train_xgboost_model", "xgboost_eval", 
        "trade", "monitor_positions", "close_all", "check_account"
    ])
    parser.add_argument("--start_date", type=str, default="2022-01-01")
    parser.add_argument("--end_date", type=str, default="2025-01-01")
    parser.add_argument("--interval", type=str, default="1d")
    parser.add_argument("--n_trees", type=int, default=100)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--diversity", type=int, default=20)
    parser.add_argument("--tp", type=float, default=0.1)
    parser.add_argument("--sl", type=float, default=0.05)
    parser.add_argument("--monitor_interval", type=int, default=300)
    parser.add_argument("--strategy", type=str, default="DAY1", help="Strategy key set to use")

    args = parser.parse_args()

    # Setup Alpaca API client
    creds = get_alpaca_credentials(args.strategy)
    api = REST(creds["API_KEY"], creds["SECRET_KEY"], BASE_URL)


    # Dispatch commands
    if args.command == "retrieve_data":
        retrieve_data(start_date=args.start_date, end_date=args.end_date, interval=args.interval)
    elif args.command == "train_xgboost_model":
        train_xgboost_model(n_trees=args.n_trees, horizon=args.horizon)
    elif args.command == "xgboost_eval":
        xgboost_eval(horizon=args.horizon)
    elif args.command == "trade":
        trade(api, diversity=args.diversity, horizon=args.horizon)
    elif args.command == "monitor_positions":
        monitor_positions(api, take_profit=args.tp, stop_loss=args.sl, interval=args.monitor_interval)
    elif args.command == "close_all":
        close_all_positions(api)
    elif args.command == "check_account":
        check_account(api)
