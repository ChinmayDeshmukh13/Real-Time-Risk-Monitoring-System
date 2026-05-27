# data/fetcher.py
# data/fetcher.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ... rest of imports
import yfinance as yf # type: ignore
import pandas as pd
from datetime import datetime, timedelta, date
from engine.config import get_client

STOCKS = [
    "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "SBIN.NS", "BAJFINANCE.NS", "TCS.NS", "INFY.NS", "WIPRO.NS",
    "HCLTECH.NS", "RELIANCE.NS", "ONGC.NS", "POWERGRID.NS",
    "NTPC.NS", "LT.NS", "HINDUNILVR.NS", "NESTLEIND.NS",
    "ASIANPAINT.NS", "SUNPHARMA.NS", "TITAN.NS",
]

HISTORY_DAYS = 750


def get_last_loaded_dates() -> dict:
    """
    Queries ClickHouse for the latest date we have per symbol.
    Returns dict like {'RELIANCE': date(2026,5,20), ...}
    """
    client = get_client()
    try:
        rows = client.execute('''
            SELECT symbol, max(date)
            FROM market_ticks
            GROUP BY symbol
        ''')
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}


def fetch_stock_data(symbols=STOCKS, days=HISTORY_DAYS):
    """
    INCREMENTAL: Only fetches data newer than what's already in DB.
    On first run fetches full history. Subsequent runs fetch 1-2 days max.
    """
    last_dates = get_last_loaded_dates()
    end_date   = datetime.today()
    all_data   = []

    print(f"\nIncremental fetch — checking {len(symbols)} symbols")

    for symbol in symbols:
        clean = symbol.replace('.NS', '')

        # Determine start date for this symbol
        if clean in last_dates:
            # Already have data — fetch only from next day onwards
            start_date = datetime.combine(
                last_dates[clean], datetime.min.time()
            ) + timedelta(days=1)

            days_to_fetch = (end_date - start_date).days
            if days_to_fetch <= 0:
                print(f"  {clean:<12} → up to date ✓")
                continue
        else:
            # First time — fetch full history
            start_date = end_date - timedelta(days=days)

        print(f"  {clean:<12} → fetching from {start_date.date()}...",
              end=" ")

        try:
            ticker = yf.Ticker(symbol)
            df     = ticker.history(
                start       = start_date,
                end         = end_date,
                auto_adjust = True
            )

            if df.empty:
                print("no data")
                continue

            df = df.reset_index()
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

            df['date']    = pd.to_datetime(df['date']).dt.date
            df['symbol']  = clean
            df['returns'] = df['close'].pct_change()
            df            = df.dropna()

            df['open']    = df['open'].round(2)
            df['high']    = df['high'].round(2)
            df['low']     = df['low'].round(2)
            df['close']   = df['close'].round(2)
            df['returns'] = df['returns'].round(6)
            df['volume']  = df['volume'].astype(int)

            df = df[['symbol','date','open','high',
                     'low','close','volume','returns']]

            all_data.append(df)
            print(f"{len(df)} new rows ✅")

        except Exception as e:
            print(f"error: {e} ❌")

    if not all_data:
        print("  All symbols up to date — nothing to insert")
        return None

    combined = pd.concat(all_data, ignore_index=True)
    print(f"\nNew rows to insert: {len(combined):,}")
    return combined


def fetch_full_history(symbols=STOCKS, days=HISTORY_DAYS):
    """Force full re-fetch regardless of what's in DB. One-time use."""
    end_date   = datetime.today()
    start_date = end_date - timedelta(days=days)
    all_data   = []

    for symbol in symbols:
        clean = symbol.replace('.NS', '')
        print(f"  Full fetch {clean}...", end=" ")
        try:
            ticker = yf.Ticker(symbol)
            df     = ticker.history(start=start_date, end=end_date,
                                    auto_adjust=True)
            if df.empty:
                print("empty")
                continue

            df = df.reset_index()
            df = df[['Date','Open','High','Low','Close','Volume']]
            df.columns = ['date','open','high','low','close','volume']
            df['date']    = pd.to_datetime(df['date']).dt.date
            df['symbol']  = clean
            df['returns'] = df['close'].pct_change()
            df = df.dropna()
            df['open']    = df['open'].round(2)
            df['high']    = df['high'].round(2)
            df['low']     = df['low'].round(2)
            df['close']   = df['close'].round(2)
            df['returns'] = df['returns'].round(6)
            df['volume']  = df['volume'].astype(int)
            df = df[['symbol','date','open','high',
                     'low','close','volume','returns']]
            all_data.append(df)
            print(f"{len(df)} rows ✅")
        except Exception as e:
            print(f"error: {e}")

    return pd.concat(all_data, ignore_index=True) if all_data else None