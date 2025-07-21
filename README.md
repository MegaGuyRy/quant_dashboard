# Quant Dashboard


### TODO:
- Improve decision making
- Setup live paper trading through ALPACA API
    - Selling positions (more strategy)
    - code around pattern day trading protection
    
- Backtesting and result eval with streamlit Dashboard
    - Compare agaenst NASDAC 
    - live trades made today window

- Update Xboost_eval with the ability to choose the horizon

### Future changes:
- daily, weekly, monthly, yearly returns if applicable
- Tie it all together in app.py, make it pass all at once
- Backtesting mode – We could add a command to backtest using stored predictions vs actuals.
- Unit test hooks – We could expose these as functions for easier unit testing.
- Add logging (optional) – Replace or supplement print() statements with Python’s logging module for more control.
- always unused buying power after trades
- improve monitoring interface
- Fix pandas read.csv in trade 
- make it so can choose days / keys easier 

### Very future changes 
- Integrate crypto
- Deploy so it can run outside of my local machine
- Employ other strategies and alter back tester to reflect them (XBoost, Mean Reversal, TBD)
