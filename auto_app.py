import sqlalchemy
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime
from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
import psycopg2
import os
from dotenv import load_dotenv
from init_db import create_database_if_not_exists

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
    Downloads and inserts data into PostgreSQL (only new dates).
    """
    symbols = get_sp500_symbols()
    #symbols = ["AAPL"]  # keep short for testing
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
    today = datetime.now().strftime("%Y-%m-%d")
    with engine.connect() as conn:
        for symbol in symbols:
            try:
                print(f"[INFO] Pulling data for {symbol}")
                df = get_historical_data(symbol, start="2024-01-01", end=today, interval="1d", auto_adjust=False)
                df = compute_return_features(df)
                df["Symbol"] = symbol

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)

                df.reset_index(inplace=True)

                df = df[[
                    "Date", "Close", "High", "Low", "Open", "Volume",
                    "return_1", "return_5", "return_22", "return_252",
                    "ma_5", "ma_10", "ma_20", "ma_5_20_ratio",
                    "rsi_14", "vol_5", "vol_10", "gk_vol", "bollinger_b",
                    "atr", "macd", "macd_signal", "dollar_volume", "Symbol"
                ]]
                df["Date"] = pd.to_datetime(df["Date"]).dt.date  

                existing_dates_query = text("""
                    SELECT "Date" FROM public.market_data WHERE "Symbol" = :symbol
                """)
                existing_dates = pd.read_sql(existing_dates_query, conn, params={"symbol": symbol})

                before = len(df)
                if not existing_dates.empty:
                    df = df[~df["Date"].isin(existing_dates["Date"])]
                after = len(df)

                print(f"[DEBUG] {symbol}: Filtered {before - after} rows. Remaining: {after}")
                print("[DEBUG] Final DataFrame to insert:")
                print(df.head(3))

                if not df.empty:
                    try:
                        with engine.begin() as connection:
                            df.to_sql(
                                "market_data",
                                con=connection,
                                schema="public",
                                if_exists="append",
                                index=False,
                                method="multi",
                                dtype=dtype_map
                            )
                        print(f"[INFO] Inserted {len(df)} new rows for {symbol}")
                    except Exception as db_error:
                        print(f"[ERROR] Insert failed: {db_error}")
                        print("[DEBUG] Data types:")
                        print(df.dtypes)
                        print("[DEBUG] Rows sample:")
                        print(df.head())
                else:
                    print(f"[INFO] No new data for {symbol}")

            except Exception as e:
                print(f"[WARNING] Failed to process {symbol}: {e}")
                




if __name__ == "__main__":
    create_database_if_not_exists()
    create_market_data_table_if_not_exists()
    retrieve_data_to_db()

