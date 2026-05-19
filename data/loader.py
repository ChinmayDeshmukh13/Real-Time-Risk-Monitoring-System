# data/loader.py
# Handles all database operations — creating tables and inserting data


from data.fetcher import fetch_stock_data
import pandas as pd
from engine.config import get_client

# ── Database Connection ─────────────────────────────────────



# ── Create Table ────────────────────────────────────────────
def create_table():
    """Reads schema.sql and creates the table in ClickHouse."""
    client = get_client()

    # Read the SQL file we wrote
    with open('data/schema.sql', 'r') as f:
        sql = f.read()

    # ClickHouse can't execute multiple statements at once
    # So we split by semicolon and run each statement separately
    statements = [s.strip() for s in sql.split(';') if s.strip()]

    for statement in statements:
        client.execute(statement)

    print("✅  Table created successfully")


# ── Insert Data ─────────────────────────────────────────────
def insert_data(df: pd.DataFrame):
    """
    Inserts a DataFrame into the market_ticks table.
    
    df: the DataFrame from fetch_stock_data()
    """
    client = get_client()

    # Convert DataFrame to list of tuples — ClickHouse format
    # Each tuple is one row: (symbol, date, open, high, low, close, volume, returns)
    rows = list(df.itertuples(index=False, name=None))

    # Insert all rows in one batch (much faster than row by row)
    client.execute(
        'INSERT INTO market_ticks VALUES',
        rows
    )

    print(f"✅  Inserted {len(rows):,} rows into ClickHouse")


# ── Verify Data ─────────────────────────────────────────────
def verify_data():
    """Runs basic checks to confirm data loaded correctly."""
    client = get_client()

    print("\n── Verification ────────────────────────────")

    # Total row count
    result = client.execute('SELECT count() FROM market_ticks')
    print(f"  Total rows:     {result[0][0]:,}")

    # Rows per stock
    result = client.execute('''
        SELECT symbol, count() as rows, min(date) as start, max(date) as end
        FROM market_ticks
        GROUP BY symbol
        ORDER BY symbol
    ''')
    print(f"\n  {'Symbol':<12} {'Rows':<8} {'Start':<12} {'End'}")
    print(f"  {'-'*45}")
    for row in result:
        print(f"  {row[0]:<12} {row[1]:<8} {str(row[2]):<12} {str(row[3])}")

    # Sample returns statistics
    result = client.execute('''
        SELECT
            symbol,
            round(avg(returns) * 100, 4)   as avg_return_pct,
            round(stddevPop(returns) * 100, 4) as volatility_pct
        FROM market_ticks
        GROUP BY symbol
        ORDER BY symbol
    ''')
    print(f"\n  {'Symbol':<12} {'Avg Return %':<15} {'Daily Volatility %'}")
    print(f"  {'-'*45}")
    for row in result:
        print(f"  {row[0]:<12} {row[1]:<15} {row[2]}")

    print(f"\n────────────────────────────────────────────")


# ── Master Function ─────────────────────────────────────────
def load_all_data():
    """Runs the complete pipeline: create table → fetch → insert → verify."""

    print("=" * 50)
    print("  DATA LOADING PIPELINE")
    print("=" * 50)

    # Step 1: Create the table
    print("\n[1] Creating database table...")
    create_table()

    # Step 2: Fetch data from internet
    print("\n[2] Fetching market data...")
    df = fetch_stock_data()

    # Step 3: Insert into database
    print("\n[3] Inserting into ClickHouse...")
    insert_data(df)

    # Step 4: Verify everything loaded
    print("\n[4] Verifying data...")
    verify_data()

    print("\n✅  Data pipeline complete!")
    print("=" * 50)


# ── Run directly ────────────────────────────────────────────
if __name__ == "__main__":
    load_all_data()