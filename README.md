# Quant Dashboard
- generate ticker_model_predictions.csv from xboost treee eval
- use in alpaca.py


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
- daily, monthly, yearly returns if applicable
- Tie it all together in app.py, make it pass all at once
- Backtesting mode – We could add a command to backtest using stored predictions vs actuals.
- Unit test hooks – We could expose these as functions for easier unit testing.
- Add logging (optional) – Replace or supplement print() statements with Python’s logging module for more control.
