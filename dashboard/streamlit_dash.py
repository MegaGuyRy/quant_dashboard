# dashboard/streamlit_dash.py

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import datetime
from alpaca_trade_api.rest import REST
#from app import cur_date
import datetime
#from config import get_alpaca_credentials, BASE_URL

# ---------------------
# Global config
# ---------------------
today = datetime.date.today()

st.set_page_config(page_title="Quant Dashboard", layout="wide")
st.title("Algo Trader Dashboard: S&P500 vs XGBoost Trees Model ")

# Sidebar Strategy Selection
strategy_choice = st.sidebar.selectbox("Select Alpaca Strategy", ["day1", "day7", "day30"])
start_date = datetime.date(2025, 7, 21)

# --------------------------
# Load S&P 500 (SPY) Data
# --------------------------
st.subheader("S&P 500 Performance")

spy = yf.download("^GSPC", start=start_date, end=today, group_by="ticker", progress=False)
st.write("Downloaded S&P500 columns:", spy.columns.tolist())

if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = [f"S&P500_{col[1]}" for col in spy.columns]
else:
    # Not a multi-index: rename single-level column
    spy.rename(columns={"Close": "S&P500_Close"}, inplace=True)
spy.columns
spy["S&P500_returns"] = spy["S&P500_Close"].pct_change() * 10000
spy.reset_index(inplace=True)
spy["Date"] = spy["Date"].dt.date
spy = spy[spy["Date"] >= start_date]

fig_spy = px.line(spy, x="Date", y="S&P500_Close", title="S&P 500 Closing Price")
fig_spy.update_traces(line=dict(color="green"))
st.plotly_chart(fig_spy, use_container_width=True)

with st.expander("Show Raw S&P 500 Data"):
    st.dataframe(spy.tail(50))

# ------------------------
# Load Alpaca Portfolio
# ------------------------
st.subheader("Alpaca Portfolio Equity")

#creds = get_alpaca_credentials(strategy_choice)
#api = REST(creds["API_KEY"], creds["SECRET_KEY"], BASE_URL)

# Read credentials from Streamlit secrets
creds = st.secrets[strategy_choice]
base_url = st.secrets["BASE_URL"]

api = REST(creds["API_KEY"], creds["SECRET_KEY"], base_url)

try:
    history = api.get_portfolio_history(period="1M", timeframe="1D", extended_hours=False).df.reset_index()
    history["Date"] = pd.to_datetime(history["timestamp"]).dt.date
    history = history[["Date", "profit_loss", "equity"]]
    history = history[history["equity"] > 0]
    history = history[history["Date"] >= start_date]
    history["returns"] = history["equity"].pct_change() * 10000

    fig_alpaca = px.line(history, x="Date", y="equity", title="Alpaca Portfolio Equity")
    fig_alpaca.update_traces(line=dict(color="gold"))
    st.plotly_chart(fig_alpaca, use_container_width=True)

    with st.expander("Show Raw Alpaca Data"):
        st.dataframe(history.tail(50))

    # ------------------------
    # Merge and Metrics
    # ------------------------
    spy["Date"] = pd.to_datetime(spy["Date"]).dt.date
    history["Date"] = pd.to_datetime(history["Date"]).dt.date

    spy_subset = spy[["Date", "S&P500_Close"]].rename(columns={"S&P500_Close": "S&P 500"})
    alpaca_subset = history[["Date", "equity"]].rename(columns={"equity": "Alpaca Portfolio"})

    combined_df = pd.merge(spy_subset, alpaca_subset, on="Date", how="inner")
    combined_df["S&P500_1d%"] = combined_df["S&P 500"].pct_change(periods=1) * 100
    combined_df["Alpaca_1d%"] = combined_df["Alpaca Portfolio"].pct_change(periods=1) * 100
    combined_df["S&P500_5d%"] = combined_df["S&P 500"].pct_change(periods=5) * 100
    combined_df["Alpaca_5d%"] = combined_df["Alpaca Portfolio"].pct_change(periods=5) * 100
    combined_df["S&P500_1mo%"] = combined_df["S&P 500"].pct_change(periods=21) * 100
    combined_df["Alpaca_1mo%"] = combined_df["Alpaca Portfolio"].pct_change(periods=21) * 100

    # Plot Comparison
    st.subheader("S&P 500 vs Alpaca Portfolio")
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Scatter(x=combined_df["Date"], y=combined_df["S&P500_1d%"], mode='lines', line=dict(color='green'), name='S&P500 1d% Change'))
    fig_compare.add_trace(go.Scatter(x=combined_df["Date"], y=combined_df["Alpaca_1d%"], mode='lines', line=dict(color='gold'), name='Alpaca 1d% Change'))
    fig_compare.update_layout(title='1 Day Change Comparison', xaxis_title='Date', yaxis_title='1 Day Change')
    st.plotly_chart(fig_compare, use_container_width=True)

    with st.expander("Show Performance Data"):
        st.dataframe(combined_df.tail(50))

    # ------------------------
    # Organized Sidebar Metrics
    # ------------------------
    latest = combined_df.iloc[-1]

    st.sidebar.markdown("S&P 500 Metrics")
    st.sidebar.metric("1D Change", f"{latest['S&P500_1d%']:.2f}%")
    st.sidebar.metric("5D Change", f"{latest['S&P500_5d%']:.2f}%")
    st.sidebar.metric("30D Change", f"{latest['S&P500_1mo%']:.2f}%")
    st.sidebar.metric("Mean Return", f"{combined_df['S&P500_1d%'].mean():.2f}%")
    st.sidebar.metric("Std Dev", f"{combined_df['S&P500_1d%'].std():.2f}%")
    st.sidebar.metric("Max Return", f"{combined_df['S&P500_1d%'].max():.2f}%")
    st.sidebar.metric("Min Return", f"{combined_df['S&P500_1d%'].min():.2f}%")
    total_profit_sp500 = spy_subset["S&P 500"].iloc[-1] - spy_subset["S&P 500"].iloc[0]
    st.sidebar.metric("Total Profit", f"${total_profit_sp500:,.2f}")
    sharpe_spy = (combined_df['S&P500_1d%'].mean() / combined_df['S&P500_1d%'].std()) * (252 ** 0.5)
    st.sidebar.metric("Sharpe Ratio", f"{sharpe_spy:.2f}")


    st.sidebar.markdown("---")
    st.sidebar.markdown("Alpaca Metrics")
    st.sidebar.metric("1D Change", f"{latest['Alpaca_1d%']:.2f}%")
    st.sidebar.metric("5D Change", f"{latest['Alpaca_5d%']:.2f}%")
    st.sidebar.metric("30D Change", f"{latest['Alpaca_1mo%']:.2f}%")
    st.sidebar.metric("Mean Return", f"{combined_df['Alpaca_1d%'].mean():.2f}%")
    st.sidebar.metric("Std Dev", f"{combined_df['Alpaca_1d%'].std():.2f}%")
    st.sidebar.metric("Max Return", f"{combined_df['Alpaca_1d%'].max():.2f}%")
    st.sidebar.metric("Min Return", f"{combined_df['Alpaca_1d%'].min():.2f}%")
    total_profit_alpaca = alpaca_subset["Alpaca Portfolio"].iloc[-1] - alpaca_subset["Alpaca Portfolio"].iloc[0]
    st.sidebar.metric("Total Profit", f"${total_profit_alpaca:,.2f}")
    sharpe_alpaca = (combined_df['Alpaca_1d%'].mean() / combined_df['Alpaca_1d%'].std()) * (252 ** 0.5)
    st.sidebar.metric("Sharpe Ratio", f"{sharpe_alpaca:.2f}")

except Exception as e:
    st.error(f"Failed to load Alpaca portfolio history: {e}")

