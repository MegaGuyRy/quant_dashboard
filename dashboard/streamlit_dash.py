# dashboard/streamlit_dash.py

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from alpaca_trade_api.rest import REST
from config import get_alpaca_credentials, BASE_URL

"""
Get a df with daily change stats 
have it dynamicly update with new data 
add 2 other accouts
"""

st.set_page_config(page_title="Quant Dashboard", layout="wide")

st.title("Quant Dashboard: Alpaca vs S&P 500")

# Load S&P 500 data (SPY)
st.subheader("S&P 500 Performance")

# Pull SPY data
spy = yf.download("^GSPC", start="2025-06-22", end="2025-07-22", group_by="ticker", progress=False)

# Flatten multi-level columns if needed
if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = [f"{col[0]}_{col[1]}" for col in spy.columns]

# Calculate daily returns
spy.columns
spy["returns"] = spy["^GSPC_Close"].pct_change()

# Show line chart for SPY closing price
fig = px.line(spy.reset_index(), x="Date", y="^GSPC_Close", title="S&P 500 Closing Price")
st.plotly_chart(fig, use_container_width=True)

# Optional: show raw SPY data
with st.expander("Show Raw S&P500 Data"):
    st.dataframe(spy.tail(50))

# ------------------------
# Alpaca Portfolio History
# ------------------------

creds = get_alpaca_credentials("day1")
api = REST(creds["API_KEY"], creds["SECRET_KEY"], BASE_URL)

st.subheader("Alpaca Portfolio Equity")
try:
    history = api.get_portfolio_history(
        period="1M",
        timeframe="1D",
        extended_hours=False
    ).df
    history.columns

    history["returns"] = history["equity"].pct_change()

    fig2 = px.line(history.reset_index(), x="timestamp", y="equity", title="Alpaca Portfolio Equity")
    st.plotly_chart(fig2, use_container_width=True)

    st.write("**Alpaca Daily Returns Stats**")
    st.dataframe(history["returns"].describe().to_frame())

    st.dataframe(history.tail(50))
    
except Exception as e:
    st.error(f"Failed to load Alpaca portfolio history: {e}")
    
# Combine SPY and Alpaca into a single DataFrame for Plotly
combined_df = pd.DataFrame({
    "Date": spy.reset_index()["Date"],
    "S&P 500": spy["^GSPC_Close"].values,
    "Alpaca Portfolio": history["equity"].values  # Replace with your actual Alpaca data
})

# Melt to long format for Plotly
melted_df = combined_df.melt(id_vars="Date", var_name="Source", value_name="Value")

# Plot with both lines
fig2 = px.line(melted_df, x="Date", y="Value", color="Source", title="S&P 500 vs Alpaca Portfolio")
st.plotly_chart(fig2, use_container_width=True)

