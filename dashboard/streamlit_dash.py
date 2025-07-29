import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from alpaca_trade_api.rest import REST

# ---------------------
# Global config
# ---------------------
today = datetime.date.today() - datetime.timedelta(days=1)

st.set_page_config(page_title="Quant Dashboard", layout="wide")
st.title("Algo Trader Dashboard: S&P500 vs XGBoost Trees Model ")

# Sidebar Strategy Selection
strategy_choice = st.sidebar.selectbox("Select Alpaca Strategy", ["day1", "day7", "day30"])
start_date = datetime.date(2025, 7, 21)

# ------------------------
# Load Alpaca API with Streamlit Secrets
# ------------------------
creds = st.secrets[strategy_choice]
base_url = st.secrets["BASE_URL"]
api = REST(creds["API_KEY"], creds["SECRET_KEY"], base_url)

# --------------------------
# Load S&P 500 (SPY via Alpaca) Data
# --------------------------
st.subheader("S&P 500 Performance")

try:
    bars = api.get_bars(
        symbol="SPY",
        timeframe="1D",
        start=start_date.isoformat(),
        end=today.isoformat(),
        feed="iex"
    ).df

    if bars.empty:
        raise ValueError("No SPY data returned from Alpaca.")

    spy = bars.reset_index()
    spy["Date"] = spy["timestamp"].dt.date
    spy = spy[spy["Date"] >= start_date]
    spy = spy[["Date", "close"]].rename(columns={"close": "S&P500_Close"})

    fig_spy = px.line(spy, x="Date", y="S&P500_Close", title="S&P 500 Closing Price (via SPY ETF)")
    fig_spy.update_traces(line=dict(color="green"))
    st.plotly_chart(fig_spy, use_container_width=True)

    with st.expander("Show Raw S&P 500 Data"):
        st.dataframe(spy.tail(50))

except Exception as e:
    st.error(f"Failed to load S&P 500 data from Alpaca: {e}")

# ------------------------
# Load Alpaca Portfolio
# ------------------------
st.subheader("Alpaca Portfolio Equity")

try:
    history = api.get_portfolio_history(period="1M", timeframe="1D", extended_hours=False).df.reset_index()
    history["Date"] = pd.to_datetime(history["timestamp"]).dt.date
    history = history[["Date", "profit_loss", "equity"]]
    history = history[history["equity"] > 0]
    history = history[history["Date"] >= start_date]

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

    # Total % change since beginning
    combined_df["S&P500_total%"] = (combined_df["S&P 500"] / combined_df["S&P 500"].iloc[0] - 1) * 100
    combined_df["Alpaca_total%"] = (combined_df["Alpaca Portfolio"] / combined_df["Alpaca Portfolio"].iloc[0] - 1) * 100

    # Daily % change for metrics
    combined_df["S&P500_1d%"] = combined_df["S&P 500"].pct_change() * 100
    combined_df["Alpaca_1d%"] = combined_df["Alpaca Portfolio"].pct_change() * 100

    # Plot Comparison
    st.subheader("Total % Change: S&P 500 vs Alpaca Portfolio")
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Scatter(x=combined_df["Date"], y=combined_df["S&P500_total%"], mode='lines', line=dict(color='green'), name='S&P500 Total % Change'))
    fig_compare.add_trace(go.Scatter(x=combined_df["Date"], y=combined_df["Alpaca_total%"], mode='lines', line=dict(color='gold'), name='Alpaca Total % Change'))
    fig_compare.update_layout(title='Total % Change Since Start', xaxis_title='Date', yaxis_title='Cumulative Return (%)')
    st.plotly_chart(fig_compare, use_container_width=True)

    with st.expander("Show Performance Data"):
        st.dataframe(combined_df.tail(50))

    # ------------------------
    # Sidebar Metrics
    # ------------------------
    latest = combined_df.iloc[-1]

    st.sidebar.header("S&P 500 Metrics")
    st.sidebar.metric("1D Return", f"{latest['S&P500_1d%']:.2f}%")
    st.sidebar.metric("Total Return", f"{latest['S&P500_total%']:.2f}%")
    st.sidebar.metric("Mean Daily Return", f"{combined_df['S&P500_1d%'].mean():.2f}%")
    st.sidebar.metric("Std Dev (1D)", f"{combined_df['S&P500_1d%'].std():.2f}%")
    sharpe_spy = (combined_df['S&P500_1d%'].mean() / combined_df['S&P500_1d%'].std()) * (252 ** 0.5)
    st.sidebar.metric("Sharpe Ratio", f"{sharpe_spy:.2f}")

    st.sidebar.markdown("---")

    st.sidebar.header("Alpaca Metrics")
    st.sidebar.metric("1D Return", f"{latest['Alpaca_1d%']:.2f}%")
    st.sidebar.metric("Total Return", f"{latest['Alpaca_total%']:.2f}%")
    st.sidebar.metric("Mean Daily Return", f"{combined_df['Alpaca_1d%'].mean():.2f}%")
    st.sidebar.metric("Std Dev (1D)", f"{combined_df['Alpaca_1d%'].std():.2f}%")
    sharpe_alpaca = (combined_df['Alpaca_1d%'].mean() / combined_df['Alpaca_1d%'].std()) * (252 ** 0.5)
    st.sidebar.metric("Sharpe Ratio", f"{sharpe_alpaca:.2f}")

except Exception as e:
    st.error(f"Failed to load Alpaca portfolio history: {e}")

