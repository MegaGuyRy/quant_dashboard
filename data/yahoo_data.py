import yfinance as yf
import pandas as pd

def get_historical_data(symbol, start="2022-01-01", end="2025-01-01", interval="1d"):
    df = yf.download(symbol, start=start, end=end, interval=interval)
    df.dropna(inplace=True)
    return df

# Example
if __name__ == "__main__":
    df = get_historical_data("AAPL", "2023-01-01", "2025-01-01")
    print(df.tail())
