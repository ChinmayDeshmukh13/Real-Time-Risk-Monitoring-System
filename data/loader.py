# data/loader.py
# data/loader.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import get_client
from engine.db_schema import ensure_tables
from data.fetcher  import fetch_stock_data
import pandas as pd


def create_tables_if_not_exist():
    """
    Creates tables ONLY if they don't exist.
    Safe to call every run — won't drop existing data.
    """
    ensure_tables()
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