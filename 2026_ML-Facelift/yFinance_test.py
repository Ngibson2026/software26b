import yfinance as yf
import pandas as pd
from datetime import datetime

# Example: Get current info for a stock
# ticker = "AAPL"   # Apple Inc.
tickers = ["MSFT", "GOOGL", "TSLA", "BHP.AX", "NVDA"]

for ticker in tickers:
    stock = yf.Ticker(ticker)

    print(f"=== {ticker} Stock Information ===")
    print(f"Company Name: {stock.info.get('longName')}")
    print(f"Current Price: ${stock.info.get('currentPrice')}")
    print(f"Previous Close: ${stock.info.get('regularMarketPreviousClose')}")
    print(f"Market Cap: ${stock.info.get('marketCap'):,}")

    # Get historical data (last 1 month)
    print("\n=== Recent Historical Data (last 5 days) ===")
    hist = stock.history(period="1mo")
    print(hist[['Open', 'High', 'Low', 'Close', 'Volume']].tail(5))

    # Basic info summary
    print("\n=== Quick Summary ===")
    print(stock.info.get('longBusinessSummary')[:300] + "...")  # Truncated
    