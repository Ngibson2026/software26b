import yfinance as yf

"""
ticker = "NVDA"

stock = yf.Ticker(ticker)

print(f"Company Name: {stock.info.get('longName')}")
print(stock.info.get('longBusinessSummary')[:300] + "...")  # Truncatedflak
print(f"Current Price: ${stock.info.get('currentPrice')}")
print(f"Previous Close: ${stock.info.get('regularMarketPreviousClose')}")
print(f"Market Cap: ${stock.info.get('marketCap'):,}")

print("\n=== Recent Historical Data (last 5 days) ===")
hist = stock.history(period="1mo")
print(hist[['Open', 'High', 'Low', 'Close', 'Volume']].tail(5))
"""