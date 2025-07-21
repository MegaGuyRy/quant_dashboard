# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("ALPACA_BASE_URL")

def get_alpaca_credentials(strategy: str = "day1"):
    """
    Get Alpaca credentials for the selected strategy
    """
    strategy = strategy.lower()
    if strategy == "day1":
        return {
            "API_KEY": os.getenv("day1_ALPACA_API_KEY"),
            "SECRET_KEY": os.getenv("day1_ALPACA_SECRET_KEY"),
        }
    elif strategy == "day7":
        return {
            "API_KEY": os.getenv("day7_ALPACA_API_KEY"),
            "SECRET_KEY": os.getenv("day7_ALPACA_SECRET_KEY"),
        }
    elif strategy == "day30":
        return {
            "API_KEY": os.getenv("day30_ALPACA_API_KEY"),
            "SECRET_KEY": os.getenv("day30_ALPACA_SECRET_KEY"),
        }
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
