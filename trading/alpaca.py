import pandas as pd
from alpaca_trade_api.rest import REST
from datetime import datetime
import time

def check_account(api: REST):
    """
    Print and return account status and buying power.
    """
    account = api.get_account()
    print(f"Account status: {account.status}, Buying power: ${account.buying_power}")
    return account

def place_market_order(api: REST, symbol, qty, side='buy'):
    """
    Submit a market order to buy or sell a given stock.
    """
    order = api.submit_order(
        symbol=symbol,
        qty=qty,
        side=side,
        type='market',
        time_in_force='gtc'
    )
    print(f"Placed {side} order for {qty} shares of {symbol}")
    return order

def get_positions(api: REST):
    """
    Display current open positions.
    """
    positions = api.list_positions()
    for p in positions:
        print(f"{p.symbol}: {p.qty} shares at avg entry ${p.avg_entry_price}")

def allocate_portfolio(api: REST, ranking_csv, diversity):
    """
    Allocate portfolio based on predicted return rankings.
    """
    df = pd.read_csv(ranking_csv).head(diversity)

    account = api.get_account()
    buying_power = float(account.buying_power)

    total_score = df["PredictedReturn"].sum()
    df["Weight"] = df["PredictedReturn"] / total_score

    print(f"\nAllocating capital across top {diversity} stocks...\n")

    for _, row in df.iterrows():
        symbol = row["Symbol"]
        weight = row["Weight"]
        allocation = buying_power * weight

        try:
            last_quote = api.get_latest_trade(symbol)
            price = float(last_quote.price)
            qty = int(allocation // price)

            print(f"{symbol}: ${price:.2f}/share | Allocating ${allocation:.2f} => Buying {qty} shares")

            if qty > 0:
                place_market_order(api, symbol, qty, side="buy")
            else:
                print(f"Skipping {symbol}, not enough funds for even 1 share.")
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

def monitor_positions(api: REST, take_profit=0.10, stop_loss=0.05, check_time=300):
    """
    Monitor open positions and trigger sell orders on TP or SL conditions.
    """
    print(f"Monitoring positions every {check_time // 60} minutes...")
    print(f"Take Profit: {take_profit * 100:.1f}% | Stop Loss: {stop_loss * 100:.1f}%\n")

    while True:
        try:
            positions = api.list_positions()
            for p in positions:
                try:
                    current_price = float(p.current_price)
                    avg_entry_price = float(p.avg_entry_price)
                    change_pct = (current_price - avg_entry_price) / avg_entry_price

                    print(f"{p.symbol}: {change_pct:.2%} | Entry: {avg_entry_price} | Current: {current_price}")

                    if change_pct >= take_profit:
                        print(f"Taking profit on {p.symbol} ({change_pct:.2%})")
                        place_market_order(api, p.symbol, int(float(p.qty)), side="sell")

                    elif change_pct <= -stop_loss:
                        print(f"Stopping loss on {p.symbol} ({change_pct:.2%})")
                        place_market_order(api, p.symbol, int(float(p.qty)), side="sell")

                except Exception as e:
                    print(f"Error checking {p.symbol}: {e}")
        except Exception as main_e:
            print(f"Main loop error: {main_e}")

        print(f"Sleeping {check_time} seconds...\n")
        time.sleep(check_time)

def close_all_positions(api: REST):
    """
    Close all open positions immediately.
    """
    print("\nClosing all open positions...\n")
    positions = api.list_positions()
    for p in positions:
        try:
            qty = int(float(p.qty))
            place_market_order(api, p.symbol, qty, side="sell")
        except Exception as e:
            print(f"Error closing {p.symbol}: {e}")

