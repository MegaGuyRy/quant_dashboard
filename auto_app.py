import sqlalchemy
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime
from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
import psycopg2
import os
from dotenv import load_dotenv
from init_db import create_database_if_not_exists
from strategies.xboost_tree_eval import train_models, evaluate_models

# Load environment variables
load_dotenv()

# Connect details
DATABASE_URL = os.getenv("DATABASE_URL")

def create_market_data_table_if_not_exists():
    """
    Creates the 'market_data' table in the 'public' schema if it doesn't already exist.
    """
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="localhost",
        port=5432
    )
    cur = conn.cursor()

    create_table_query = """
    CREATE TABLE IF NOT EXISTS public.market_data (
        "Date" DATE,
        "Close" FLOAT,
        "High" FLOAT,
        "Low" FLOAT,
        "Open" FLOAT,
        "Volume" BIGINT,
        "return_1" FLOAT,
        "return_5" FLOAT,
        "return_22" FLOAT,
        "return_252" FLOAT,
        "ma_5" FLOAT,
        "ma_10" FLOAT,
        "ma_20" FLOAT,
        "ma_5_20_ratio" FLOAT,
        "rsi_14" FLOAT,
        "vol_5" FLOAT,
        "vol_10" FLOAT,
        "gk_vol" FLOAT,
        "bollinger_b" FLOAT,
        "atr" FLOAT,
        "macd" FLOAT,
        "macd_signal" FLOAT,
        "dollar_volume" FLOAT,
        "Symbol" TEXT,
        PRIMARY KEY ("Date", "Symbol")
    );
    """
    try:
        cur.execute(create_table_query)
        conn.commit()
        print("[INFO] public.market_data table is ready.")
    except Exception as e:
        print(f"[ERROR] Could not connect to Database: {e}")
    finally:
        cur.close()
        conn.close()

def retrieve_data_to_db():
    """
    Downloads and inserts only *new* data for each symbol into PostgreSQL.
    Optimized to avoid redundant downloads and DB connections.
    """
    symbols = get_sp500_symbols()
    today = datetime.now().strftime("%Y-%m-%d")
    engine = create_engine(DATABASE_URL)

    dtype_map = {
        "Date": sqlalchemy.Date,
        "Close": sqlalchemy.Float,
        "High": sqlalchemy.Float,
        "Low": sqlalchemy.Float,
        "Open": sqlalchemy.Float,
        "Volume": sqlalchemy.BigInteger,
        "return_1": sqlalchemy.Float,
        "return_5": sqlalchemy.Float,
        "return_22": sqlalchemy.Float,
        "return_252": sqlalchemy.Float,
        "ma_5": sqlalchemy.Float,
        "ma_10": sqlalchemy.Float,
        "ma_20": sqlalchemy.Float,
        "ma_5_20_ratio": sqlalchemy.Float,
        "rsi_14": sqlalchemy.Float,
        "vol_5": sqlalchemy.Float,
        "vol_10": sqlalchemy.Float,
        "gk_vol": sqlalchemy.Float,
        "bollinger_b": sqlalchemy.Float,
        "atr": sqlalchemy.Float,
        "macd": sqlalchemy.Float,
        "macd_signal": sqlalchemy.Float,
        "dollar_volume": sqlalchemy.Float,
        "Symbol": sqlalchemy.Text
    }

    # Open single connection for all operations
    with engine.begin() as connection:
        # STEP 1: Get latest available dates per symbol from the DB
        latest_dates_query = """
            SELECT "Symbol", MAX("Date") AS last_date
            FROM public.market_data
            GROUP BY "Symbol"
        """
        latest_df = pd.read_sql(latest_dates_query, connection)
        latest_map = dict(zip(latest_df["Symbol"], latest_df["last_date"]))

        for symbol in symbols:
            try:
                # STEP 2: Use latest DB date as the start for new download
                start_date = latest_map.get(symbol, "2015-01-01")
                start_date = pd.to_datetime(start_date) + pd.Timedelta(days=1)

                if start_date >= pd.to_datetime(today):
                    print(f"[SKIP] {symbol}: Already up-to-date.")
                    continue

                print(f"[INFO] Pulling data for {symbol} from {start_date.date()} to {today}")
                df = get_historical_data(symbol, start=start_date.strftime("%Y-%m-%d"), end=today, interval="1d", auto_adjust=False)
                if df.empty:
                    print(f"[INFO] {symbol}: No new data returned by Yahoo.")
                    continue

                df = compute_return_features(df)
                df["Symbol"] = symbol

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)

                df.reset_index(inplace=True)
                df["Date"] = pd.to_datetime(df["Date"]).dt.date

                df = df[[
                    "Date", "Close", "High", "Low", "Open", "Volume",
                    "return_1", "return_5", "return_22", "return_252",
                    "ma_5", "ma_10", "ma_20", "ma_5_20_ratio",
                    "rsi_14", "vol_5", "vol_10", "gk_vol", "bollinger_b",
                    "atr", "macd", "macd_signal", "dollar_volume", "Symbol"
                ]]

                # STEP 3: Insert only if there is new data
                if not df.empty:
                    df.to_sql(
                        "market_data",
                        con=connection,
                        schema="public",
                        if_exists="append",
                        index=False,
                        method="multi",
                        dtype=dtype_map
                    )
                    print(f"[INSERTED] {symbol}: {len(df)} new rows")
                else:
                    print(f"[SKIP] {symbol}: No new rows to insert")

            except Exception as e:
                print(f"[ERROR] {symbol}: {e}")


def train_xgboost_models_from_db(n_trees=100, horizon=1):
    """
    Pulls symbol data from the DB, filters out those not updated to yesterday,
    and trains a separate XGBoost model per symbol using GPU.
    """
    engine = create_engine(DATABASE_URL)
    yesterday = (datetime.now() - timedelta(days=1)).date()

    query = """
        SELECT * FROM public.market_data
        WHERE "Date" IS NOT NULL AND "Symbol" IS NOT NULL
        ORDER BY "Symbol", "Date"
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        print("[WARNING] No data found in database.")
        return

    df.dropna(inplace=True)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # Only keep symbols that have data for yesterday
    latest_df = df.groupby("Symbol")["Date"].max().reset_index()
    latest_df = latest_df[latest_df["Date"] >= yesterday]
    valid_symbols = set(latest_df["Symbol"])

    df = df[df["Symbol"].isin(valid_symbols)]

    if df.empty:
        print(f"[INFO] No symbols with data for yesterday ({yesterday}) found.")
        return

    print(f"[INFO] Training models for {len(valid_symbols)} symbols with data up to yesterday.")

    # Use patched train_models with GPU support
    train_models(df, n_trees=n_trees, horizon=horizon, use_gpu=True)



if __name__ == "__main__":
    #create_database_if_not_exists()
    #create_market_data_table_if_not_exists()
    #retrieve_data_to_db()
    train_xgboost_models_from_db(n_trees=200, horizon=1)
