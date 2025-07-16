import pandas as pd
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
import joblib
from data.yahoo_data import get_historical_data, symbol_list
from data.feature_engineering import compute_return_features
from data.feature_engineering import create_dataframe

# Get symbols for smp500 companies
smp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
smp500["Symbol"] = smp500["Symbol"].str.replace(".", "-")
stock_list = smp500["Symbol"].unique().tolist()

# Get the dataset
df = create_dataframe(stock_list, start="2022-01-01", end="2025-01-01")

print(df.shape)
print(df.head())

