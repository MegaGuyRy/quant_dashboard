import argparse
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import joblib
import os
from datetime import datetime, timedelta
from data.feature_engineering import create_dataframe

def smp500_df(start_date="2022-01-01", end_date="2025-01-01", use_csv=True):
    os.makedirs("logs", exist_ok=True)

    if not use_csv:
        # Pull fresh S&P500 symbols
        smp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        smp500["Symbol"] = smp500["Symbol"].str.replace(".", "-")
        stock_list = smp500["Symbol"].unique().tolist()
        
        # Create dataframe
        df = create_dataframe(stock_list, start=start_date, end=end_date)
        
        # Save to CSV
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d")
        file_path = os.path.join("logs", f"feature_df_{timestamp}.csv")
        df.to_csv(file_path, index=False)
        print(f"Saved DataFrame to {file_path}")
        
    else:
        # Load today's CSV
        today_str = datetime.now().strftime("%Y-%m-%d")
        found_file = None
        for fname in os.listdir("logs"):
            if today_str in fname and fname.endswith(".csv"):
                found_file = os.path.join("logs", fname)
                break
        
        if not found_file:
            raise FileNotFoundError(f"No CSV found in logs/ with today's date: {today_str}")
        
        print(f"Loading DataFrame from {found_file}")
        df = pd.read_csv(found_file)
    
    print(df.shape)
    print(df.head(10))
    return df
    
    
def train_tree_eval(df):
    results = []
    
    # Ensure model directory
    os.makedirs("models", exist_ok=True)
    
    for symbol, group in df.groupby("Symbol"):
        group = group.sort_values(by="Date").copy()
        
        # Compute next day close price
        group['Target'] = group['Close'].pct_change().shift(-1) # calculates the percentage change from yesterday to today
        group.dropna(inplace=True)
        
        # Select features
        feature_cols = [col for col in group.columns if col not in ['Date', 'Symbol', 'Close', 'target']]
        X = group[feature_cols]
        y = group['Target']
        
        if len(group) < 100: # not enough data
            print(f"Skipping {symbol} not enough data")
            continue
        
        try:
            # Split data
            split_idx = int(len(group) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
            
            # Train model
            model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100)
            model.fit(X_train, y_train)
            
            # Predict on latest row for ranking
            latest_feature = X.iloc[-1:].values
            predicted_return = model.predict(latest_feature)[0]
            
            # Evaluate
            y_pred = model.predict(X_test)
            rmse = mean_squared_error(y_test, y_pred, squared=False)
            
            # Save models
            model_path = f"models/model_{symbol}.joblib"
            joblib.dump(model, model_path)
            
            results.append({
            'Symbol': symbol,
            'PredictedReturn': predicted_return,
            'RMSE': rmse,
            'ModelPath': model_path
            })
            print(f"Trained {symbol} | RMSE: {rmse:.5f} | Pred: {predicted_return:.5f}")

        except Exception as e:
            print(f"Failed for {symbol}: {e}")
    
    # Return predictions and scores as a summary dataframe
    results_df = pd.DataFrame(results).sort_values(by="PredictedReturn", ascending=False)
    results_df.to_csv("logs/ticker_model_predictions.csv", index=False)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d")
    print(f"\n saved prediction ranking to logs/ticker_predictions_{timestamp}.csv")
    return results_df
    
    
if __name__ == "__main__":
# Use in morning before market open to generate all needed files
# python -m strategies.xboost_tree_eval --use_csv False --start_date 2022-01-01 --end_date yesterday

    parser = argparse.ArgumentParser()
    parser.add_argument("--use_csv", type=lambda x: x.lower() == 'true', default=True,
                        help="True to load today's CSV from logs/, False to pull fresh data")
    #parser.add_argument("--horizon", type=int, default=1, help="Number of days ahead to predict (e.g., 1 for next day)")
    parser.add_argument("--start_date", type=str, default="2022-01-01")
    parser.add_argument("--end_date", type=str, default="2025-01-01")
    args = parser.parse_args()
    
    # Handle keyword 'yesterday'
    if args.end_date.lower() == "yesterday":
        args.end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    df = smp500_df(start_date=args.start_date, end_date=args.end_date, use_csv=args.use_csv)
    train_tree_eval(df)
    
