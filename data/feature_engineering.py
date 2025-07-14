import pandas as pd

def compute_return_features(df):
    df = compute_lagging_return(df)
    df = compute_ma_features(df)
    df = compute_rsi(df)
    df = compute_volatility_features(df)
    df.dropna(inplace=True)
    return df

def compute_lagging_return(df):
	"""
	Compute simple lagged return features for the dataframe.
	Assumes df has a 'Close' column and is indexed by date.
	"""
	df['return_1'] = df['Close'].pct_change(1)
	df['return_5'] = df['Close'].pct_change(5)
	df['return_22'] = df['Close'].pct_change(22)
	df['return_252'] = df['Close'].pct_change(252)
	
	return df
	
def compute_ma_features(df):
	"""
	Compute moving averages return features for the dataframe.
	Assumes df has a 'Close' column and is indexed by date.
	"""
	df['ma_5'] = df['Close'].rolling(5).mean()
	df['ma_10'] = df['Close'].rolling(10).mean()
	df['ma_20'] = df['Close'].rolling(20).mean()

	# Moving average ratio short vs long
	df['ma_5_20_ratio'] = df['ma_5'] / (df['ma_20'] + 1e-6) # avoid div by 0
	
	return df
	
def compute_rsi(df, period=14):
	"""
	Compute relative strength index(RSI) return features for the dataframe.
	Assumes df has a 'Close' column and is indexed by date.
	"""
	delta = df['Close'].diff() # Computes daily price change
	gain = (delta.where(delta > 0, 0)).rolling(window=period).mean() # Takes only the positive price changes
	loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean() # Keeps only negative changes changes all else to 0
	rs = gain / (loss + 1e-6) # rs = avg gain/avg loss
	df[f'rsi_{period}'] = 100 - (100 / (1 + rs)) # Values oscillate between 0 and 100, RSI > 70 → overbought, RSI < 30 → oversold
	
	return df

def compute_volatility_features(df):
	"""
	Compute volatility return features for the dataframe.
	Assumes df has a 'Close' column and is indexed by date.
	"""
	daily_returns = df['Close'].pct_change()
	df['vol_5'] = daily_returns.rolling(5).std()
	df['vol_10'] = daily_returns.rolling(10).std()
	
	return df

if __name__ == "__main__":
    from yahoo_data import get_historical_data
    df = get_historical_data("AAPL", start="2022-01-01", end="2025-01-01")
    df = compute_return_features(df)
    print(df.tail())
