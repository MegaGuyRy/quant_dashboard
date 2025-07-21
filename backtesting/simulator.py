import pandas as pd
import numpy as np

def run_backtest_with_metrics(prediction_csv_path, price_history_df, initial_capital=10000):
    # Load predictions
    predictions = pd.read_csv(prediction_csv_path)
    predictions = predictions.sort_values(by="PredictedReturn", ascending=False)
    predictions["Weight"] = predictions["PredictedReturn"] / predictions["PredictedReturn"].sum()

    portfolio = {}
    capital_used = 0
    daily_equity = []

    # Allocate capital
    for _, row in predictions.iterrows():
        symbol = row["Symbol"]
        weight = row["Weight"]
        allocation = weight * initial_capital

        # Use the first price available in price history for this symbol
        price_series = price_history_df[price_history_df["symbol"] == symbol]
        if price_series.empty:
            continue
        entry_price = price_series.iloc[0]["close"]
        qty = int(allocation // entry_price)
        capital_used += qty * entry_price

        portfolio[symbol] = {
            "shares": qty,
            "entry_price": entry_price,
            "prices": price_series.set_index("date")["close"]
        }

    # Compute daily portfolio value
    all_dates = sorted(price_history_df["date"].unique())
    for date in all_dates:
        value = 0
        for pos in portfolio.values():
            if date in pos["prices"]:
                value += pos["shares"] * pos["prices"][date]
            else:
                value += pos["shares"] * pos["entry_price"]  # fallback to entry price
        daily_equity.append({"date": date, "value": value})

    equity_df = pd.DataFrame(daily_equity)
    equity_df["returns"] = equity_df["value"].pct_change().fillna(0)

    # Metrics
    final_value = equity_df.iloc[-1]["value"]
    net_return = final_value - initial_capital
    roi = net_return / initial_capital
    sharpe_ratio = np.mean(equity_df["returns"]) / np.std(equity_df["returns"]) * np.sqrt(252) if np.std(equity_df["returns"]) > 0 else 0
    rolling_max = equity_df["value"].cummax()
    drawdown = equity_df["value"] / rolling_max - 1
    max_drawdown = drawdown.min()
    volatility = equity_df["returns"].std() * np.sqrt(252)

    results = {
        "initial_capital": initial_capital,
        "final_value": final_value,
        "net_return": net_return,
        "roi": roi,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "equity_curve": equity_df
    }

    import ace_tools as tools; tools.display_dataframe_to_user(name="Equity Curve", dataframe=equity_df)
    return results

