import yfinance as yf
import pandas as pd
import numpy as np

def get_sp500_symbols():
    # Get symbols for smp500 companies
    smp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    smp500["Symbol"] = smp500["Symbol"].str.replace(".", "-")
    symbol_list = smp500["Symbol"].unique().tolist()
    return symbol_list


def get_historical_data(symbol, start="2022-01-01", end="2025-01-01", interval="1d", auto_adjust=False):
    df = yf.download(symbol, start=start, end=end, interval=interval)
    df.dropna(inplace=True)
    return df

# Example
if __name__ == "__main__":
    df = get_historical_data("AAPL", "2023-01-01", "2025-01-01")
    dfa = df['Close']
    print(dfa.tail())
    #print(symbol_list)
