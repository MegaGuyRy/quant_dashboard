import os
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

# Load .env variables
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL")

# Create Alpaca API instance
api = REST(API_KEY, SECRET_KEY, BASE_URL)

def check_account():
    account = api.get_account()
    print(f"Account status: {account.status}, Buying power: {account.buying_power}")

def place_market_order(symbol, qty, side='buy'):
    order = api.submit_order(
        symbol=symbol,
        qty=qty,
        side=side,
        type='market',
        time_in_force='gtc'
    )
    print(f"Placed {side} order for {qty} shares of {symbol}")
    return order

def get_positions():
    positions = api.list_positions()
    for p in positions:
        print(f"{p.symbol}: {p.qty} shares at avg entry ${p.avg_entry_price}")

# Example usage
if __name__ == "__main__":
    check_account()
    get_positions()
