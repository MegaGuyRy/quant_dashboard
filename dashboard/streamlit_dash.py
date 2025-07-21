# dashboard/streamlit_dash.py

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Quant Dashboard", layout="wide")

st.title("Quant Dashboard: Alpaca vs S&P 500")

# Load S&P 500 data (SPY)
st.subheader("S&P 500 Performance (via SPY ETF)")

# Pull SPY data
spy = yf.download("^GSPC", start="2022-01-01", end="2025-01-01", group_by="ticker", progress=False)

# Flatten multi-level columns if needed
if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = [f"{col[0]}_{col[1]}" for col in spy.columns]

# Calculate daily returns
spy.columns
spy["returns"] = spy["^GSPC_Close"].pct_change()

# Show line chart for SPY closing price
fig = px.line(spy.reset_index(), x="Date", y="^GSPC_Close", title="SPY Closing Price")
st.plotly_chart(fig, use_container_width=True)

# Show SPY return stats
st.write("**S&P 500 Daily Returns Stats**")
st.dataframe(spy["returns"].describe().to_frame())

# Optional: show raw SPY data
with st.expander("Show Raw SPY Data"):
    st.dataframe(spy.tail(50))

# Future: Load Alpaca returns from your model or live trades
# Compare performance with SPY here...

