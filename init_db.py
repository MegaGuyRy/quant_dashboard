import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB")          # e.g., 'trading'
DB_USER = os.getenv("POSTGRES_USER")        # e.g., 'ryan'
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = "localhost"
DB_PORT = 5432

def create_database_if_not_exists():
    """
    Connects to the default 'postgres' DB and creates the target DB if it doesn't exist.
    """
    try:
        # Connect to the default postgres database
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Check if the target DB exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cur.fetchone()

        if not exists:
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"[INFO] Database '{DB_NAME}' created.")
        else:
            print(f"[INFO] Database '{DB_NAME}' already exists.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Could not create database: {e}")

if __name__ == "__main__":
    create_database_if_not_exists()
