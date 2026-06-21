import os
import joblib
import json
import textblob
import requests
import yfinance as yf
import pandas as pd
import datacollect
import numpy as np
import sqlite3
from polynomy import trainModel
from datacollect import (volumeCollect, etfComparison, calcHighLowDiff, returns_daily )

def StockBuyPrice(user_id, ticker_symbol):
    # get the ticker name and the price the user bought it at from the database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT average_buy_price FROM Portfolio WHERE user_id = ? AND ticker = ?",
                   (user_id, ticker_symbol))
    user_stock = cursor.fetchone()
    conn.close()

    # check if user owns said stock
    if not user_stock:
        print(f'User does not own any {ticker_symbol} stock')
        return None

    return user_stock[0]

# run the prediction model
def stockProfit(ticker_symbol):
    features = [
        'Volume',
        '52 Week Range Position',
        'Top Sector ETF Close',
        'Daily Returns'
    ]

    # add the manual feature weights
    weight_Volume = 0.172
    weight_52_week_pos = 0.264
    weight_etf = 0.466
    weight_daily_returns = 0.097

    # set paths for the polynomial, model, and scaler
    poly_path = os.path.join("poly", f"{ticker_symbol}_poly_transformer_grades.pkl")
    model_path = os.path.join("models", f"{ticker_symbol}_polynomial_regression_model_grades.pkl")
    scaler_path = os.path.join("scaler", f"{ticker_symbol}_scaler_grades.pkl")

    # train the model for the given stock even if it exists already because there may be new data to train it on
    trainModel(ticker_symbol)
    print('ok model train yay')
    try:
        poly = joblib.load(poly_path)
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)

        # gets current data for the given features from yfCollectData
        volume = volumeCollect(ticker_symbol)

        etf_hist = etfComparison(ticker_symbol)
        if etf_hist is None or etf_hist.empty:
            raise ValueError(f"Could not get ETF data for {ticker_symbol}")
        etf_current = etf_hist['Close'].iloc[-1]

        position_in_52w_range_hist = calcHighLowDiff(ticker_symbol)
        if position_in_52w_range_hist is None or position_in_52w_range_hist.empty:
            raise ValueError(f"Could not get 52-week range data for {ticker_symbol}")
        position_in_52w_range_current = position_in_52w_range_hist['position_in_52w_range'].iloc[-1]

        daily_returns_hist = calcDailyReturns(ticker_symbol)
        if daily_returns_hist is None or daily_returns_hist.empty:
            raise ValueError(f"Could not get daily returns for {ticker_symbol}")
        daily_returns_current = daily_returns_hist.iloc[-1]

        # puts current features into a dataframe for the model to read
        X_current = pd.DataFrame([{
            'Volume': volume,
            '52 Week Range Position': position_in_52w_range_current,
            'Top Sector ETF Close': etf_current,
            'Daily Returns': daily_returns_current
        }])

        X_current = X_current[features]

        X_current['Volume'] = X_current['Volume'] * weight_Volume
        X_current['52 Week Range Position'] = X_current['52 Week Range Position'] * weight_52_week_pos
        X_current['Top Sector ETF Close'] = X_current['Top Sector ETF Close'] * weight_etf
        X_current['Daily Returns'] = X_current['Daily Returns'] * weight_daily_returns

        X_scaled = scaler.transform(X_current)
        X_poly = poly.transform(X_scaled)

        # gets a prediction from the model and returns the predicted price as a float
        predicted_price = model.predict(X_poly)
        return float(predicted_price.ravel()[0])

    except Exception as e:
        print(e)
        return None

def getNewsSentiment(ticker_symbol):
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker_symbol}&apikey=7VGY7S29TCWQEFB5&limit=1'
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        newsJSON = resp.json()
    except Exception as e:
        # network error, rate limit, bad response — ignore sentiment
        print(f"AlphaVantage request failed/ignored: {e}")
        return None

    # Ensure we have a dict with a non-empty 'feed' list before indexing
    if not isinstance(newsJSON, dict):
        return None

    feed = newsJSON.get('feed')
    if not isinstance(feed, list) or len(feed) == 0:
        # no news items -> ignore sentiment
        return None

    first = feed[0]
    if not isinstance(first, dict):
        return None

    score = first.get('overall_sentiment_score')
    try:
        return float(score) if score is not None else None
    except Exception:
        # non-numeric score -> ignore
        return None

def getStockBeta(ticker_symbol):
    if not ticker_symbol or len(ticker_symbol.strip()) < 1:  # if ticker name is too short
        return None
    ticker = ticker_symbol.upper().strip()
    stock = yf.Ticker(ticker)
    stock_info = stock.info
    try:
        beta = stock_info.get('beta', None)  # get beta value from stock info, return None if not available
        print(f"Beta for {ticker_symbol}: {beta}")
        return beta
    except Exception as e:
        print(e)
        return None


def choosing(ticker_symbol, user_id=None, desired_change=None):
    # can edit variables later if they aren't doing well
    BUY= 8.0
    STOP= 5.0
    MARGIN = 3

    details = {}
    buy_contribs = []
    sell_contribs = []
    def b(points, reason): buy_contribs.append((points, reason))
    def s(points, reason): sell_contribs.append((points, reason))

    # core signals (safe calls, treat missing values as None)
    pred = stockProfit(ticker_symbol)
    details['predicted_price'] = pred
    user_price = None
    try:
        user_price = userStockBuyPrice(user_id, ticker_symbol)
    except Exception:
        user_price = None
    details['user_buy_price'] = user_price
    owns = user_price is not None
    details['owns'] = owns

    # if no prediction then Hold
    if pred is None:
        return "Hold", {**details, "reason": "no_prediction"}

    # current market price
    current = None
    try:
        t = yf.Ticker(ticker_symbol)
        info = getattr(t, "info", {}) or {}
        current = info.get('regularMarketPrice') or info.get('previousClose')
        if current is None:
            hist = t.history(period="1d")
            if not hist.empty:
                current = float(hist['Close'].iloc[-1])
    except Exception:
        current = None
    details['current_price'] = current

    # percent metrics (guard zero/None)
    def pct(a, b):
        try:
            return ((a - b) / b) * 100 if (a is not None and b) else None
        except Exception:
            return None

    pred_vs_buy = pct(pred, user_price) if owns else None
    pred_vs_now = pct(pred, current)
    details['predicted_pct_vs_buy'] = pred_vs_buy
    details['predicted_pct_vs_now'] = pred_vs_now

    # lightweight extras (best-effort)
    sentiment = getNewsSentiment(ticker_symbol)
    beta = getStockBeta(ticker_symbol)
    momentum = None
    try:
        dr = calcDailyReturns(ticker_symbol)
        if dr is not None:
            r = dr.dropna().tail(5)
            momentum = float(r.mean() * 100) if len(r) else None
    except Exception:
        momentum = None
    volume = None
    try:
        volume = volumeCollect(ticker_symbol)
    except Exception:
        volume = None

    details.update({'sentiment': sentiment, 'beta': beta, 'momentum': momentum, 'volume': volume})

    # scoring rules
    # ownership rules (strong)
    if owns and pred_vs_buy is not None and desired_change is not None and pred_vs_buy >= desired_change:
        s(6, "take_profit")
    if owns and pred_vs_buy is not None and pred_vs_buy <= -STOP:
        s(5, "stop_loss")

    # buy opportunity vs current price
    if pred_vs_now is not None:
        if pred_vs_now >= BUY:
            b(5, "strong_upside")
        elif pred_vs_now >= BUY / 2:
            b(2, "moderate_upside")

    # sentiment
    try:
        if sentiment is not None:
            s_val = float(sentiment)
            if s_val >= 0.35: b(3, "sentiment_pos")
            elif s_val <= -0.35: s(3, "sentiment_neg")
            elif s_val >= 0.15: b(1, "sentiment_weak_pos")
            elif s_val <= -0.15: s(1, "sentiment_weak_neg")
    except Exception:
        pass

    # beta (small risk modifier)
    try:
        if beta is not None:
            b(1, "low_beta") if float(beta) < 0.8 else (s(1, "high_beta") if float(beta) > 1.3 else None)
    except Exception:
        pass

    # momentum small modifier
    if momentum is not None:
        if momentum > 0.5: b(1, "momentum_pos")
        elif momentum < -0.5: s(1, "momentum_neg")

    # liquidity tiny penalty
    try:
        if volume is not None and volume < 1000:
            b(-1, "low_volume_penalty")
    except Exception:
        pass

    # 3) sum and decide
    buy_score = sum(p for p, _ in buy_contribs)
    sell_score = sum(p for p, _ in sell_contribs)
    details['buy_contribs'] = buy_contribs
    details['sell_contribs'] = sell_contribs
    details['buy_score'] = buy_score
    details['sell_score'] = sell_score

    if sell_score - buy_score >= MARGIN:
        action = "Sell" if owns else "Avoid (do not buy)"
    elif buy_score - sell_score >= MARGIN:
        action = "Buy"
    else:
        action = "Hold"

    # pick the largest absolute contributor as primary reason
    all_contribs = buy_contribs + sell_contribs
    if all_contribs:
        primary = max(all_contribs, key=lambda x: abs(x[0]))
        details['primary_reason'] = {"points": primary[0], "reason": primary[1]}
    else:
        details['primary_reason'] = None

    print(f"Decision for {ticker_symbol}: {action} (Buy score: {buy_score}, Sell score: {sell_score})")

    return action, details

decisionTree("ABCD", 6, desired_change=10.0)