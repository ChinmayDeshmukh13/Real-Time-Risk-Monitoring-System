# data/fetcher.py
# Downloads historical stock data from Yahoo Finance

import yfinance as yf # type: ignore
import pandas as pd
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────
# These are the 5 stocks in our portfolio
# .NS suffix tells yfinance these are NSE-listed Indian stocks
STOCKS = [
    # Large Cap — Banking & Finance
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "KOTAKBANK.NS",
    "AXISBANK.NS",
    "SBIN.NS",
    "BAJFINANCE.NS",

    # Large Cap — IT
    "TCS.NS",
    "INFY.NS",
    "WIPRO.NS",
    "HCLTECH.NS",

    # Large Cap — Energy & Industrial
    "RELIANCE.NS",
    "ONGC.NS",
    "POWERGRID.NS",
    "NTPC.NS",
    "LT.NS",

    # Large Cap — Consumer & Pharma
    "HINDUNILVR.NS",
    "NESTLEIND.NS",
    "ASIANPAINT.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
]

HISTORY_DAYS = 750  # 3 years instead of 2




# ── Main Function ───────────────────────────────────────────
def fetch_stock_data(symbols=STOCKS, days=HISTORY_DAYS):
    """
    Downloads OHLCV data for a list of stock symbols.
    Returns a single cleaned DataFrame with all stocks combined.
    """

    # Calculate date range
    end_date   = datetime.today()
    start_date = end_date - timedelta(days=days)

    print(f"\nFetching data from {start_date.date()} to {end_date.date()}")
    print(f"Stocks: {symbols}\n")

    # This list will collect data for each stock
    all_data = []

    # Loop through each stock one by one
    for symbol in symbols:

        print(f"  Downloading {symbol}...", end=" ")

        try:
            # Download data from Yahoo Finance
            # auto_adjust=True adjusts for stock splits and dividends automatically
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=True
            )

            # If no data came back, skip this stock
            if df.empty:
                print("No data returned. Skipping.")
                continue

            # ── Clean the DataFrame ─────────────────────────

            # Reset index so 'Date' becomes a regular column
            df = df.reset_index()

            # Keep only the columns we need
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            # Rename columns to lowercase (matches our database schema)
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

            # Convert date to just the date part (remove time component)
            df['date'] = pd.to_datetime(df['date']).dt.date

            # Add the stock symbol as a column
            # Remove .NS suffix so we store "RELIANCE" not "RELIANCE.NS"
            df['symbol'] = symbol.replace('.NS', '')

            # ── Calculate Daily Returns ─────────────────────
            # Return = (today's close - yesterday's close) / yesterday's close
            # .pct_change() does exactly this calculation
            # The first row will be NaN (no previous day) — we drop those
            df['returns'] = df['close'].pct_change()

            # Drop the first row (NaN return) and any other missing values
            df = df.dropna()

            # Round prices to 2 decimal places
            df['open']    = df['open'].round(2)
            df['high']    = df['high'].round(2)
            df['low']     = df['low'].round(2)
            df['close']   = df['close'].round(2)
            df['returns'] = df['returns'].round(6)  # returns need more precision

            # Convert volume to integer (yfinance sometimes gives floats)
            df['volume'] = df['volume'].astype(int)

            all_data.append(df)
            print(f"✅  {len(df)} rows")

        except Exception as e:
            print(f"❌  Error: {e}")

    # Combine all stocks into one DataFrame
    if not all_data:
        raise Exception("No data was downloaded. Check your internet connection.")

    combined = pd.concat(all_data, ignore_index=True)

    # Reorder columns to match database schema exactly
    combined = combined[['symbol', 'date', 'open', 'high', 'low',
                          'close', 'volume', 'returns']]

    print(f"\nTotal rows downloaded: {len(combined):,}")
    return combined


# ── Test Block ──────────────────────────────────────────────
# This only runs when you execute this file directly
# It does NOT run when another file imports from this file
if __name__ == "__main__":
    data = fetch_stock_data()
    print("\nSample data (first 3 rows):")
    print(data.head(3).to_string())
    print("\nData types:")
    print(data.dtypes)