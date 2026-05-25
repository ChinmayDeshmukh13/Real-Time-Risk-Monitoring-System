from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_client
from main import holdings


SECTORS = {
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "SBIN": "Banking",
    "BAJFINANCE": "Banking",
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "HCLTECH": "IT",
    "RELIANCE": "Energy & Industrial",
    "ONGC": "Energy & Industrial",
    "POWERGRID": "Energy & Industrial",
    "NTPC": "Energy & Industrial",
    "LT": "Energy & Industrial",
    "HINDUNILVR": "Consumer & Pharma",
    "NESTLEIND": "Consumer & Pharma",
    "ASIANPAINT": "Consumer & Pharma",
    "SUNPHARMA": "Consumer & Pharma",
    "TITAN": "Consumer & Pharma",
}


def main() -> None:
    client = get_client()

    client.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            symbol   String,
            sector   String,
            quantity Float64
        )
        ENGINE = MergeTree()
        ORDER BY symbol
        """
    )

    client.execute("TRUNCATE TABLE portfolio_positions")

    rows = [
        (symbol, SECTORS.get(symbol, "Other"), float(quantity))
        for symbol, quantity in holdings.items()
    ]
    client.execute("INSERT INTO portfolio_positions VALUES", rows)

    count = client.execute("SELECT count() FROM portfolio_positions")[0][0]
    print(f"portfolio_positions synced: {count} rows")


if __name__ == "__main__":
    main()
