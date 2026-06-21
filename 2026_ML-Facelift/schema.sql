-- =============================================
-- Smart Study Progress + Stock Trading App
-- Schema File
-- =============================================

-- CREATE DATABASE IF NOT EXISTS database;

-- Basic user info for login/registration
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT
);

-- Store progress logs for each user
CREATE TABLE IF NOT EXISTS ProgressLogs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    details TEXT NOT NULL,
    image_path TEXT
);

-- STOCK TRADING SIMULATION

-- Stores each user's cash balance (with starter capital)
CREATE TABLE IF NOT EXISTS UserBalances (
    user_id INTEGER PRIMARY KEY,
    cash_balance REAL DEFAULT 10000.00,      -- $10,000 starting capital
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- Tracks user's stock holdings
CREATE TABLE IF NOT EXISTS Portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,                    -- e.g. AAPL, MSFT, BHP.AX
    shares INTEGER NOT NULL DEFAULT 0,
    average_buy_price REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    UNIQUE(user_id, ticker)
);

-- Records every buy and sell transaction
CREATE TABLE IF NOT EXISTS Transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    transaction_type TEXT CHECK(transaction_type IN ('BUY', 'SELL')),
    shares INTEGER NOT NULL,
    price_per_share REAL NOT NULL,
    total_amount REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- Optional: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_portfolio_user ON Portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON Transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON Transactions(ticker);


--- sqlite3 database.db ".read schema.sql"