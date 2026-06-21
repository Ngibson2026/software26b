import yfinance as yf
import pandas as pd

pd.set_option('display.max_columns', None) # show all columns in the dataframe for testing

def returns_daily(ticker_symbol):
    if not ticker_symbol or len(ticker_symbol.strip()) < 1:  # if ticker name is too short
        return None, None, "Please enter a valid ticker symbol"
    ticker = ticker_symbol.upper().strip()

    try:
        stock = yf.Ticker(ticker)  # establishes ticker
        hist = stock.history(period="5y") # gets 5 year history

        daily_returns = hist['Close'].pct_change()
        return daily_returns
    except Exception as e: # error handling
        print(f"Error fetching {ticker}: {e}")
        return None
def calcHighLowDiff(ticker_symbol):
    if not ticker_symbol or len(ticker_symbol.strip()) < 1:  # if ticker name is too short
        return None
    ticker = ticker_symbol.upper().strip()
    stock = yf.Ticker(ticker)  # establishes ticker
    hist = stock.history(period="6y", interval="1d") # sets period to 6 years since we need a year more of data to compare earlier dates
    # finds highest and lowest price in the past year
    hist["52_week_high"] = hist["High"].rolling(window=252, min_periods=1).max()
    hist["52_week_low"] = hist["Low"].rolling(window=252, min_periods=1).min()

    hist["position_in_52w_range"] = ( # creates a value finding the current stock price's position within the 52w range
        (hist["Close"] - hist["52_week_low"]) /
        (hist["52_week_high"] - hist["52_week_low"])
    )
    five_years = hist.index.max() - pd.DateOffset(years=5) # limits the data to 5 years
    hist_5y = hist.loc[hist.index >= five_years]
    return hist_5y
def etfComparison(ticker_symbol):
    if not ticker_symbol or len(ticker_symbol.strip()) < 1:  # if ticker name is too short
        return None
    ticker = ticker_symbol.upper().strip()

    try:
        stock = yf.Ticker(ticker) # establishes ticker
        sector_key = stock.info.get('sector') # finds sector of ticker
        if sector_key:
            sector_key = sector_key.lower().replace(" ", "-") # sectors need to be lower case
        sector_data = yf.Sector(sector_key)

        # fetches the top ETFs in the sector and gets the ticker symbol of the first one
        sector_etfs = sector_data.top_etfs
        etf_symbol = next(iter(sector_etfs))

        # gets another ticker for the etf
        etf = yf.Ticker(etf_symbol)
        etf_hist = etf.history(period="5y", interval="1d") # get etf history
        return etf_hist


    except Exception as e: # error handling
        print(f"Error fetching {ticker}: {e}")
        return None
def volumeCollect(ticker_symbol):
    if not ticker_symbol or len(ticker_symbol.strip()) < 1:  # if ticker name is too short
        return None
    ticker = ticker_symbol.upper().strip()

    try:
        stock = yf.Ticker(ticker)
        volume = stock.info["volume"]
        return volume
    except Exception as e:
        print(e)
        return None

def stockDataCollection(ticker_symbol):
    if not ticker_symbol or len(ticker_symbol.strip()) < 1:  # if ticker name is too short
        return None
    ticker = ticker_symbol.upper().strip()

    try:
        stock = yf.Ticker(ticker) # establishes ticker

        hist = stock.history(period="5y", interval="1d") # retrieves ticker history
        high_low_features = calcHighLowDiff(ticker_symbol) # grab the relative position within 52 week high/low datafram from previous function
        etf_hist = etfComparison(ticker_symbol) # gets the closing price of the relevant ETF
        daily_returns = calcDailyReturns(ticker_symbol) # get the percentage change from the previous day's price

        # sets the indexing of each column to align to the date to avoid having multiple entries per day
        hist.index = hist.index.date
        high_low_features.index = high_low_features.index.date
        etf_hist.index = etf_hist.index.date
        daily_returns.index = daily_returns.index.date

        features = pd.DataFrame({ # collates all the features into a dataframe using pandas
            'Close': hist['Close'],
            'Volume': hist['Volume'],
            '52 Week Range Position': high_low_features["position_in_52w_range"],
            'Top Sector ETF Close': etf_hist['Close'],
            'Daily Returns': daily_returns
        })
        features = features.dropna()
        return features

    except Exception as e: # error handling
        print(f"Error fetching {ticker}: {e}")
        return None


volumeCollect("NVDA")
# calcHighLowDiff(yf.Ticker("NVDA"))
# etfComparison("CBA.AX")