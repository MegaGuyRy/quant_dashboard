# app.py
import argparse
import os
from datetime import datetime, timedelta
import pandas as pd
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv

from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
from strategies.xboost_tree_eval import train_models, evaluate_models
from trading.alpaca import allocate_portfolio, monitor_positions

def cur_date():
    """
    Get todays date
    """
    timestamp = datetime.now().strftime("%Y-%m-%d") # Get todays date
    return (timestamp)

def retrieve_data(start_date="2022-01-01", end_date="2025-01-01"):
    """
    Step 1: Get data and engineered features
    Run: python app.py retrieve_data --start_date 2022-01-01 --end_date 2025-07-17
    Returns: df with all needed data and calculated features to train xboost trees
    """
    print("[INFO] Pulling Yahoo Finance data for S&P 500 symbols...")
    symbols = get_sp500_symbols()
    all_data = pd.DataFrame() # Declare empty data
    for symbol in symbols:
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
            print(f"[WARNING] Failed to pull {symbol}: {e}")
            
    all_data['Date'] = pd.to_datetime(all_data['Date'])
    all_data = all_data.sort_values(by='Date')
    
    os.makedirs("logs/features", exist_ok=True) # Make logs directory
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv" # Save CSV data 
    all_data.to_csv(file_path, index=False)
    print(f"[INFO] Saved combined data to {file_path}")
    return (df)
    
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
    else:
        df = pd.read_csv(file_path)
        train_models(df, n_trees)
    
def xgboost_eval(horizon=1):
    """
    Step 3: Evaluate XGBoost models on latest data
    Run: python app.py xgboost_eval --horizon=1
    """
    timestamp = cur_date()
    file_path = f"logs/features/feature_df_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'retrieve_data' first.")
    else:
        df = pd.read_csv(file_path)
        results = evaluate_models(df)
        
def trade(diversity):
    """
    Step 4: Make trades based on todays ticker_model_predictions csv
    diversity: amount of stocks to spread buying power between
    Run: python app.py xgboost_eval
    """
    timestamp = cur_date()
    file_path = f"logs/rankings/ticker_model_predictions_{timestamp}.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[ERROR] {file_path} not found. Run 'retrieve_data' first.")
    else:
        ranking_csv = pd.read_csv(file_path)
        allocate_portfolio(ranking_csv, diversity)

def close_all():
    """
    Used to close positions at at BOD or EOD (currently manual)
    Run: python app.py close_all_positions
    """
    positions = api.list_positions()
    if not positions:
        print("[INFO] No open positions to close.")
        return

    print("[WARNING] The following positions will be closed:")
    for pos in positions:
        print(f" - {pos.symbol}: {pos.qty} shares")

    confirm = input("Are you sure you want to close ALL positions? Type 'YES' to confirm else will cancel: ")
    if confirm == "Y":
        api.close_all_positions()
        print("[INFO] All positions have been closed.")
    else:
        print("[CANCELLED] No positions were closed.")


if __name__ == "__main__":
    
    # Load .env variables
    load_dotenv()
    api = REST(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        os.getenv("ALPACA_BASE_URL")
    )


    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["retrieve_data", "train_xgboost_model", "xgboost_eval", 
                                            "trade", "monitor", "close_all"], 
                                            help="Which step to run")
    parser.add_argument("--start_date", type=str, default="2022-01-01")
    parser.add_argument("--end_date", type=str, default="2025-01-01")
    parser.add_argument("--n_trees", type=int, default=100)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--diversity", type=int, default=20)
    parser.add_argument("--API_KEY", type=str, default="2025-01-01")
    parser.add_argument("--ALPACA_API_KEY", type=str, default="ALPACA_API_KEY")
    parser.add_argument("--ALPACA_SECRET_KEY", type=str, default="ALPACA_SECRET_KEY")
    parser.add_argument("--ALPACA_BASE_URL", type=str, default="https://paper-api.alpaca.markets")
    parser.add_argument("--tp", type=float, default=0.1)
    parser.add_argument("--sl", type=float, default=0.05)

    args = parser.parse_args()

    if args.command == "retrieve_data":
        retrieve_data(start_date=args.start_date, end_date=args.end_date)
    elif args.command == "train_xgboost_model":
        train_xgboost_model(n_trees=100, horizon=1)
    elif args.command == "xgboost_eval":
        xgboost_eval()
    elif args.command == "trade":
        trade(diversity=args.diversity, API_KEY=ALPACA_API_KEY, ALPACA_SECRET_KEY=ALPACA_SECRET_KEY, ALPACA_BASE_URL=ALPACA_BASE_URL)
    elif args.command == "monitor":
        monitor(tp=args.tp, sl=args.sl, API_KEY=ALPACA_API_KEY, ALPACA_SECRET_KEY=ALPACA_SECRET_KEY, ALPACA_BASE_URL=ALPACA_BASE_URL)
    elif args.command == "close_all":
        close_all()
