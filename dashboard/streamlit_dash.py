import streamlit as st
import pandas as pd
import os

# Load CSV file (you can update the path or make it dynamic)
default_file = "logs/rankings/1/ticker_model_predictions_2025-07-21.csv"

st.title("Trading Predictions Dashboard")

# File selector
file_path = st.text_input("Enter path to CSV file:", default_file)

if file_path and os.path.exists(file_path):
    with open(file_path, "r") as f:
        csv_data = f.read()

    st.subheader("Raw CSV Data")
    st.code(csv_data, language='csv')

    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=os.path.basename(file_path),
        mime="text/csv"
    )
else:
    st.warning(f"No file found at {file_path}")

