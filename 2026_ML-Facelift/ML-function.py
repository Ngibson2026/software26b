from yfinance import Ticker

def stockdatafetcher(ticker):
    stockdata = {}
    ticker = Ticker(ticker)
    try:
        info = ticker.info
        hist = ticker.history(period="3mo")

        stock_data = {
            'ticker': ticker,
            'market_cap': info.get('market_cap'),

        }

        print(hist)

    except Exception as e:
        print(f"error fetching {ticker}: {e}")
        return None, None, F"failed to fetch data for {ticker}"

stockdatafetcher('NVDA')
