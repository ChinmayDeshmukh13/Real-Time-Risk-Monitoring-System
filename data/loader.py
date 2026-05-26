# data/loader.py
from engine.config import get_client
from data.fetcher  import fetch_stock_data
import pandas as pd


def create_tables_if_not_exist():
    """
    Creates tables ONLY if they don't exist.
    Safe to call every run — won't drop existing data.
    """
    client = get_client()

    client.execute('''
        CREATE TABLE IF NOT EXISTS market_ticks (
            symbol  String, date    Date,
            open    Float64, high   Float64,
            low     Float64, close  Float64,
            volume  UInt64,  returns Float64
        ) ENGINE = MergeTree() ORDER BY (symbol, date)
    ''')

    client.execute('''
        CREATE TABLE IF NOT EXISTS var_results (
            run_time        DateTime,
            portfolio_value Float64, hist_var_inr  Float64,
            hist_var_pct    Float64, param_var_inr Float64,
            mc_var_inr      Float64, hist_cvar_inr Float64,
            net_delta       Float64, net_theta     Float64,
            net_vega        Float64
        ) ENGINE = MergeTree() ORDER BY run_time
    ''')

    client.execute('''
        CREATE TABLE IF NOT EXISTS breach_log (
            breach_time     DateTime, method          String,
            var_amount      Float64,  limit_amount    Float64,
            breach_pct      Float64,  portfolio_value Float64,
            severity        String
        ) ENGINE = MergeTree() ORDER BY breach_time
    ''')

    client.execute('''
        CREATE TABLE IF NOT EXISTS greeks_log (
            run_time    DateTime, symbol      String,
            option_type String,   strike      Float64,
            expiry_days Int32,    spot        Float64,
            price       Float64,  delta       Float64,
            gamma       Float64,  theta       Float64,
            vega        Float64,  moneyness   String
        ) ENGINE = MergeTree() ORDER BY (run_time, symbol)
    ''')

    print("✅ Tables verified (created if missing)")


def insert_data(df: pd.DataFrame):
    """Inserts only new rows — called after incremental fetch."""
    if df is None or len(df) == 0:
        print("  Nothing to insert")
        return

    client = get_client()
    rows   = list(df.itertuples(index=False, name=None))
    client.execute('INSERT INTO market_ticks VALUES', rows)
    print(f"✅ Inserted {len(rows):,} new rows")


def run_incremental_pipeline():
    """
    Production-safe pipeline:
    1. Ensure tables exist (safe, fast)
    2. Fetch only missing data (incremental)
    3. Insert new rows only
    """
    create_tables_if_not_exist()
    df = fetch_stock_data()
    insert_data(df)


if __name__ == "__main__":
    run_incremental_pipeline()