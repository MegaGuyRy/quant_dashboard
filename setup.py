# setup.py
from setuptools import setup, find_packages

setup(
    name="quant_dashboard",
    version="0.1.0",
    description="A modular quant trading system with Alpaca and backtesting dashboard",
    author="Your Name",
    packages=find_packages(),  # finds all folders with __init__.py
    include_package_data=True,
    install_requires=[
        "streamlit==1.47.0",
        "pandas==2.2.2",
        "numpy==1.26.4",
        "matplotlib==3.8.4",
        "plotly==6.2.0",
        "yfinance==0.2.40",
        "alpaca-trade-api==3.2.0",
        "pandas-ta==0.3.14b0",
        "scikit-learn==1.4.2",
        "requests==2.31.0",
        "sqlalchemy==2.0.30",
        "websocket-client==1.7.0",
        "lxml==4.9.3",
        "xgboost==2.0.3",
        "joblib==1.4.2",
        "python-dotenv==1.0.1"
    ],
    entry_points={
        "console_scripts": [
            # Optional: uncomment if you want to run with `quant-dashboard` CLI
            # "quant-dashboard = app:main"
        ]
    },
    python_requires=">=3.10",
)

