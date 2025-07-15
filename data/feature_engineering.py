import pandas as pd
import numpy as np

def compute_return_features(df):
    df = compute_lagging_return(df)
    df = compute_ma_features(df)
    df = compute_rsi(df)
    df = compute_volatility_features(df)
    df = compute_garman_klass(df)
    df = compute_bollinger_bands(df)
    df = compute_atr(df)
    df = comute_macd(df)
    df = compute_dollar_volume(df)
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

def compute_garman_klass(df):
    """
	Compute robust estimate of volatility than std dev for the dataframe.
	Assumes df has a daily 'high/low/open/close' column and is indexed by date.
	"""
    log_hl = np.log(df['High'] / df['Low'])
    log_co = np.log(df['Close'] / df['Open'])
    df['gk_vol'] = np.sqrt(0.5 * log_hl**2 - (2*np.log(2)-1) * log_co**2)
    return df

def compute_bollinger_bands(df, period=22):
    """
	Compute Bollinger Bands / %B features for the dataframe.
	Assumes df has a 'Close' column and is indexed by date.
    """
    ma = df['Close'].rolling(period).mean() # rolling mean
    std = df['Close'].rolling(period).mean() # rolling std/volatility
    upper = ma + 2 * std # upper is 2 std above
    lower = ma - 2 * std # lower is 2 std below
    df['bollinger_b'] = (df['Close'] - lower) / (upper - lower + 1e-6)
    return df

def compute_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close_prev = (df['High'] - df['Close'].shift()).abs()
    low_close_prev = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1) # true range
    df['atr'] = tr.rolling(period).mean()
    return df
    
def comute_macd(df):
    # could use slider or custom spans
    # 9 & 21 on hourly
    """
	Compute MACD for the dataframe.
	Assumes df has a 'Close' column and is indexed by date.
    """
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    return df
    
def compute_dollar_volume(df):
    df['dollar_volume'] = df['Close'] * df['Volume']
    return df

if __name__ == "__main__":
    from yahoo_data import get_historical_data
    df = get_historical_data("AAPL", start="2022-01-01", end="2025-01-01")
    df = compute_return_features(df)
    print(df.tail())

