# auto_app.py
import os
import sqlalchemy
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from dotenv import load_dotenv

from data.yahoo_data import get_historical_data, get_sp500_symbols
from data.feature_engineering import compute_return_features
from strategies.xboost_tree_eval import train_models, evaluate_models

# ----------------------------
# Env & Engine
# ----------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql://ryan:pass@localhost:5432/trading
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is not set.")

# ----------------------------
# DDL: create market_data table
# ----------------------------
def create_market_data_table_if_not_exists():
    """
    Creates the 'public.market_data' table if it doesn't already exist.
    """
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
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
    finally:
        cur.close()
        conn.close()

# ----------------------------
# ETL: retrieve & append only new rows
# ----------------------------
def retrieve_data_to_db(start="2015-01-01", end=None, symbols=None):
    """
    Downloads OHLCV, computes features, and inserts only new dates per symbol.
    """
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    # Avoid start=end (yfinance will error); nudge end forward by 1 day if needed
    if pd.to_datetime(start) >= pd.to_datetime(end):
        end = (pd.to_datetime(start) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    if symbols is None:
        symbols = get_sp500_symbols()  # or pass a smaller list while testing

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
        "Symbol": sqlalchemy.Text,
    }

    with engine.connect() as conn:
        for symbol in symbols:
            try:
                print(f"[INFO] Pulling data for {symbol}")
                df = get_historical_data(symbol, start=start, end=end, interval="1d", auto_adjust=False)
                df = compute_return_features(df)
                df["Symbol"] = symbol

                # Drop multiindex from yfinance if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)

                df = df.reset_index()

                # Keep exact feature set we expect in DB
                df = df[[
                    "Date", "Close", "High", "Low", "Open", "Volume",
                    "return_1", "return_5", "return_22", "return_252",
                    "ma_5", "ma_10", "ma_20", "ma_5_20_ratio",
                    "rsi_14", "vol_5", "vol_10", "gk_vol", "bollinger_b",
                    "atr", "macd", "macd_signal", "dollar_volume", "Symbol"
                ]]

                # Ensure Date is a date (not datetime)
                df["Date"] = pd.to_datetime(df["Date"]).dt.date

                # Find existing dates for this symbol
                existing_dates = pd.read_sql(
                    text('SELECT "Date" FROM public.market_data WHERE "Symbol" = :symbol'),
                    conn,
                    params={"symbol": symbol},
                )

                before = len(df)
                if not existing_dates.empty:
                    df = df[~df["Date"].isin(existing_dates["Date"])]
                after = len(df)
                print(f"[DEBUG] {symbol}: Filtered {before - after} rows. Remaining: {after}")

                # Insert new rows
                if not df.empty:
                    with engine.begin() as connection:
                        df.to_sql(
                            "market_data",
                            con=connection,
                            schema="public",
                            if_exists="append",
                            index=False,
                            method="multi",
                            dtype=dtype_map,
                        )
                    print(f"[INFO] Inserted {len(df)} new rows for {symbol}")
                else:
                    print(f"[SKIP] {symbol}: Already up-to-date.")
            except Exception as e:
                print(f"[WARNING] Failed to process {symbol}: {e}")

# ----------------------------
# Helpers for training/evaluation from DB
# ----------------------------
FEATURE_COLS = [
    "return_1","return_5","return_22","return_252",
    "ma_5","ma_10","ma_20","ma_5_20_ratio",
    "rsi_14","vol_5","vol_10","gk_vol",
    "bollinger_b","atr","macd","macd_signal","dollar_volume",
]

def _load_df_for_training(engine, require_yesterday=False):
    """
    Pull the exact feature set + Close/Date/Symbol from DB so we never drift.
    Optionally filter symbols to those with data for yesterday.
    """
    q = """
        SELECT "Date", "Close", "Symbol", """ + ",".join(f'"{c}"' for c in FEATURE_COLS) + """
        FROM public.market_data
        WHERE "Date" IS NOT NULL AND "Symbol" IS NOT NULL
        ORDER BY "Symbol","Date"
    """
    df = pd.read_sql(q, engine)
    df["Date"] = pd.to_datetime(df["Date"])

    if require_yesterday:
        yday = (datetime.utcnow() - timedelta(days=1)).date()
        have_yday = df[df["Date"].dt.date == yday][["Symbol"]].drop_duplicates()
        df = df.merge(have_yday, on="Symbol", how="inner")

    return df

def train_from_db(engine, n_trees=100, horizon=1, require_yesterday=True):
    """
    Load feature frame from DB and call your existing trainer.
    """
    df = _load_df_for_training(engine, require_yesterday=require_yesterday)
    train_models(df, n_trees=n_trees, horizon=horizon)

def evaluate_to_csv(engine, horizon=1, require_yesterday=True):
    """
    Load feature frame from DB and call your existing evaluator.
    evaluate_models() saves CSV to logs/rankings/<horizon>/ticker_model_predictions_<date>.csv
    and returns the DataFrame.
    """
    df = _load_df_for_training(engine, require_yesterday=require_yesterday)
    results_df = evaluate_models(df, horizon=horizon)
    return results_df

# ----------------------------
# Entrypoint to run the pipeline
# ----------------------------
if __name__ == "__main__":
    # 1) Ensure table exists
    create_market_data_table_if_not_exists()

    # 2) Ingest/refresh data (only new rows)
    #    While testing, pass a small list like symbols=["AAPL","MSFT","NVDA"]
    retrieve_data_to_db(start="2015-01-01")

    # 3) Train all models from DB (requires symbols have yesterday's data)
    engine = create_engine(DATABASE_URL)
    train_from_db(engine, n_trees=200, horizon=1, require_yesterday=True)

    # 4) Evaluate and save rankings CSV (your strategies code handles the CSV write)
    rankings = evaluate_to_csv(engine, horizon=1, require_yesterday=True)

    # 5) Print top 10
    print("\n[TOP 10 RANKINGS]")
    print(rankings.sort_values("PredictedReturn", ascending=False).head(10).to_string(index=False))

