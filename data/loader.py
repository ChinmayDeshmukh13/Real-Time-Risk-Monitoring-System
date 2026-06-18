# data/loader.py
# data/loader.py
import sys, os
from time import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import get_client
from engine.db_schema import ensure_tables
from data.fetcher  import fetch_stock_data
import pandas as pd
from psycopg2.extras import execute_values


def create_tables_if_not_exist():
    """
    Creates tables ONLY if they don't exist.
    Safe to call every run — won't drop existing data.
    """
    ensure_tables()
    print("✅ Tables verified (created if missing)")


def insert_data(df: pd.DataFrame):
    """Insert rows into Supabase PostgreSQL."""
    import time
    start = time.time()
    if df is None or len(df) == 0:
        print("Nothing to insert")
        return

    conn = get_client()
    cur = conn.cursor()

    rows = list(df.itertuples(index=False, name=None))


    execute_values(
        cur,
        """
        INSERT INTO market_ticks (
            symbol,
            date,
            open,
            high,
            low,
            close,
            volume,
            returns
        ) VALUES %s
        """,
        rows,
        page_size=1000
    )

    conn.commit()

    print(f"✅ Inserted {len(rows):,} new rows")
    print(f"Insert took {time.time()-start:.2f} sec")

    cur.close()
    conn.close()


    
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