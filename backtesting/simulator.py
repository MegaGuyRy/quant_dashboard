import pandas as pd

def run_backtest(prediction_csv, initial_capital=100000):
    df = pd.read_csv(prediction_csv)

    df = df.sort_values(by="PredictedReturn", ascending=False)
    df["Weight"] = df["PredictedReturn"] / df["PredictedReturn"].sum()

    portfolio = {}
    capital_left = initial_capital

    for _, row in df.iterrows():
        symbol = row["Symbol"]
        weight = row["Weight"]
        allocation = weight * initial_capital
        price = row.get("Price", 100)  # You should pull real price from Yahoo or Alpaca if available
        qty = int(allocation // price)

        portfolio[symbol] = {
            "allocation": allocation,
            "shares": qty,
            "price": price,
        }

    # Mock example of result
    result = {
        "initial_capital": initial_capital,
        "capital_used": initial_capital - capital_left,
        "portfolio": portfolio,
        "returns": sum(p["shares"] * p["price"] * 1.05 for p in portfolio.values())  # Assume 5% gain
    }

    return result

