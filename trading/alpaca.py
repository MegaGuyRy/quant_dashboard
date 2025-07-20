import pandas as pd
from alpaca_trade_api.rest import REST, TimeFrame
from datetime import datetime
import argparse
import time

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL  # <- use config

# Create Alpaca API instance
api = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

def check_account():
    account = api.get_account()
    print(f"Account status: {account.status}, Buying power: ${account.buying_power}")
    return account

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

def allocate_portfolio(ranking_csv, diversity):
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
                place_market_order(symbol, qty, side="buy")
            else:
                print(f"Skipping {symbol}, not enough funds for even 1 share.")
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

def monitor_positions(take_profit=0.10, stop_loss=0.05, interval=5):
    print(f"Monitoring positions every {interval // 60} minutes...")
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
                        place_market_order(p.symbol, int(float(p.qty)), side="sell")

                    elif change_pct <= -stop_loss:
                        print(f"Stopping loss on {p.symbol} ({change_pct:.2%})")
                        place_market_order(p.symbol, int(float(p.qty)), side="sell")

                except Exception as e:
                    print(f"Error checking {p.symbol}: {e}")
        except Exception as main_e:
            print(f"Main loop error: {main_e}")

        print(f"Sleeping {interval} seconds...\n")
        time.sleep(interval)

def close_all_positions():
    print("\nClosing all open positions...\n")
    positions = api.list_positions()
    for p in positions:
        try:
            qty = int(float(p.qty))
            place_market_order(p.symbol, qty, side="sell")
        except Exception as e:
            print(f"Error closing {p.symbol}: {e}")

if __name__ == "__main__":
    today_str = datetime.now().strftime("%Y-%m-%d")
    default_csv_path = f"logs/feature_df_{today_str}.csv"
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking_csv", type=str, default=default_csv_path)
    parser.add_argument("--diversity", type=int, default=20)
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--tp", type=float, default=0.10)
    parser.add_argument("--sl", type=float, default=0.05)
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--get_positions", action="store_true")
    parser.add_argument("--close_all", action="store_true")

    args = parser.parse_args()

    check_account()

    if args.get_positions:
        get_positions()
        exit()

    if args.close_all:
        close_all_positions()
        exit()

    if args.monitor:
        monitor_positions(take_profit=args.tp, stop_loss=args.sl, interval=args.interval)
    else:
        allocate_portfolio(args.ranking_csv, args.diversity)
