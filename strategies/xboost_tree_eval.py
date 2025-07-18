import argparse
import os
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from datetime import datetime, timedelta
from data.feature_engineering import create_dataframe


def train_models(df, n_trees=100):
    os.makedirs("models", exist_ok=True)
    
    r2_scores = []  # List to store R² values
    
    for symbol, group in df.groupby("Symbol"):
        group = group.sort_values(by="Date").copy()
        group['Target'] = group['Close'].pct_change().shift(-1)
        group.dropna(inplace=True)

        feature_cols = [col for col in group.columns if col not in ['Date', 'Symbol', 'Close', 'target']]
        X = group[feature_cols]
        y = group['Target']

        if len(group) < 100:
            print(f"[SKIP] {symbol}: Not enough data")
            continue

        try:
            split_idx = int(len(group) * 0.8)
            X_train = X.iloc[:split_idx]
            y_train = y.iloc[:split_idx]
            X_test = X.iloc[split_idx:]
            y_test = y.iloc[split_idx:]

            model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=n_trees)
            model.fit(X_train, y_train)

            # Calculate R² score on the test set
            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            r2_scores.append(r2)

            model_path = f"models/model_{symbol}.joblib"
            joblib.dump(model, model_path)

            print(f"[SAVED] {symbol}: Model saved to {model_path} | R² Score: {r2:.4f}")
        except Exception as e:
            print(f"[FAILED] {symbol}: {e}")
    
    # Print average R² across all trained models
    if r2_scores:
        avg_r2 = sum(r2_scores) / len(r2_scores)
        print(f"\n[SUMMARY] Average R² Score across {len(r2_scores)} models: {avg_r2:.4f}")
    else:
        print("\n[SUMMARY] No models trained successfully.")


def evaluate_models(df):
    # Create empty DataFrame with the correct columns
    results_df = pd.DataFrame(columns=["Symbol", "PredictedReturn", "RMSE", "ModelPath"])

    for symbol, group in df.groupby("Symbol"):
        group = group.sort_values(by="Date").copy()
        group['Target'] = group['Close'].pct_change().shift(-1)
        group.dropna(inplace=True)

        feature_cols = [col for col in group.columns if col not in ['Date', 'Symbol', 'Close', 'target']]
        X = group[feature_cols]
        y = group['Target']

        if len(group) < 100:
            continue

        try:
            split_idx = int(len(group) * 0.8)
            X_test = X.iloc[split_idx:]
            y_test = y.iloc[split_idx:]

            model_path = f"models/model_{symbol}.joblib"
            if not os.path.exists(model_path):
                print(f"[MISSING] Model not found for {symbol}")
                continue

            model = joblib.load(model_path)

            latest_feature = X.iloc[-1:].values
            predicted_return = model.predict(latest_feature)[0]
            y_pred = model.predict(X_test)
            rmse = mean_squared_error(y_test, y_pred, squared=False)

            results_df.loc[len(results_df)] = {
                "Symbol": symbol,
                "PredictedReturn": predicted_return,
                "RMSE": rmse,
                "ModelPath": model_path
            }

            print(f"[EVAL] {symbol} | RMSE: {rmse:.4f} | Prediction: {predicted_return:.4f}")

        except Exception as e:
            print(f"[ERROR] Evaluating {symbol}: {e}")

    # Save ranked CSV
    timestamp = datetime.now().strftime("%Y-%m-%d")
    results_df = results_df.sort_values(by="PredictedReturn", ascending=False)
    os.makedirs("logs/rankings", exist_ok=True)
    out_path = f"logs/rankings/ticker_model_predictions_{timestamp}.csv"
    results_df.to_csv(out_path, index=False)

    print(f"[SAVED] Ranking: {out_path}")
    return results_df

