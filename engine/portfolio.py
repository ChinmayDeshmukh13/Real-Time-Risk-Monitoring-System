# engine/portfolio.py
# Defines the Portfolio — what stocks we hold and how much

import pandas as pd
import numpy as np
from engine.config import get_client


# ── Portfolio Class ─────────────────────────────────────────
class Portfolio:
    """
    Represents a stock portfolio.
    Loads historical returns from ClickHouse and calculates weights.
    """

    def __init__(self, holdings: dict):
        """
        holdings: a dictionary of {symbol: number_of_shares}

        Example:
            holdings = {
                'RELIANCE':  100,
                'INFY':      200,
                'HDFCBANK':  150,
                'TCS':        80,
                'ICICIBANK': 300
            }
        """
        self.holdings = holdings          # e.g. {'RELIANCE': 100, ...}
        self.symbols  = list(holdings.keys())

        # These get filled when we load data
        self.prices_df  = None   # Latest closing prices
        self.returns_df = None   # Historical daily returns matrix
        self.values     = None   # Current ₹ value of each position

        # Load everything from database immediately
        self._load_data()


    def _load_data(self):
        """
        Private method — loads price and returns data from ClickHouse.
        The underscore prefix means 'internal use only'.
        """
        client = get_client()

        # Build a string like: 'RELIANCE','INFY','HDFCBANK','TCS','ICICIBANK'
        # Used inside the SQL WHERE clause
        symbols_str = ",".join([f"'{s}'" for s in self.symbols])

        # ── Fetch historical returns ────────────────────────
        # We need daily returns for every stock, sorted by date
        query = f"""
            SELECT symbol, date, close, returns
            FROM market_ticks
            WHERE symbol IN ({symbols_str})
            ORDER BY symbol, date
        """
        rows = client.execute(query)

        # rows is a list of tuples like:
        # [('RELIANCE', date(2024,5,17), 2847.5, 0.00521), ...]
        # Convert to DataFrame
        raw_df = pd.DataFrame(rows, columns=['symbol', 'date', 'close', 'returns'])

        # ── Latest closing price per stock ──────────────────
        # .groupby('symbol') groups rows by stock
        # .last() takes the last (most recent) row per group
        latest = raw_df.groupby('symbol').last().reset_index()

        # Store latest closing prices as a dict: {'RELIANCE': 1336.40, ...}
        self.prices_df = dict(zip(latest['symbol'], latest['close']))

        # ── Calculate position values ───────────────────────
        # Value of each position = shares × current price
        self.values = {
            symbol: self.holdings[symbol] * self.prices_df[symbol]
            for symbol in self.symbols
        }

        # ── Build returns matrix ────────────────────────────
        # We need a 2D table: rows = dates, columns = stocks
        # Each cell = that stock's return on that date
        #
        # pivot_table reshapes data from:
        #   symbol | date       | returns
        #   INFY   | 2024-05-17 | 0.005
        #   TCS    | 2024-05-17 | -0.003
        #
        # To:
        #   date       | INFY   | TCS    | RELIANCE ...
        #   2024-05-17 | 0.005  | -0.003 | 0.002

        self.returns_df = raw_df.pivot_table(
            index='date',
            columns='symbol',
            values='returns'
        )

        # Drop any dates where we don't have data for ALL stocks
        # (e.g. if one stock was suspended for a day)
        self.returns_df = self.returns_df.dropna()

        print(f"Portfolio loaded: {len(self.symbols)} stocks, "
              f"{len(self.returns_df)} trading days of history")


    def get_total_value(self) -> float:
        """Returns total portfolio value in ₹"""
        return sum(self.values.values())


    def get_weights(self) -> dict:
        """
        Returns each stock's weight in the portfolio.
        Weight = position value / total portfolio value

        Example: If RELIANCE is worth ₹1,00,000 out of ₹5,00,000 total
                 → weight = 0.20 (20%)
        """
        total = self.get_total_value()
        return {symbol: value / total
                for symbol, value in self.values.items()}


    def get_portfolio_returns(self) -> pd.Series:
        """
        Calculates the daily return of the ENTIRE portfolio.

        Formula: portfolio_return = Σ (weight × stock_return)
        for each day in history.

        This is a weighted average of all stock returns each day.
        """
        weights = self.get_weights()

        # Create a list of weights in the same order as DataFrame columns
        weight_array = np.array([weights[col]
                                  for col in self.returns_df.columns])

        # Matrix multiplication:
        # returns_df shape:   (495 days × 5 stocks)
        # weight_array shape: (5 stocks,)
        # result shape:       (495 days,)
        # Each day's result = sum of (each stock's return × its weight)
        portfolio_returns = self.returns_df.values @ weight_array

        return pd.Series(portfolio_returns, index=self.returns_df.index)


    def summary(self):
        """Prints a clean summary of the portfolio."""
        weights = self.get_weights()
        total   = self.get_total_value()

        print("\n" + "═" * 55)
        print("  PORTFOLIO SUMMARY")
        print("═" * 55)
        print(f"  {'Stock':<12} {'Shares':>7} {'Price':>10} "
              f"{'Value':>14} {'Weight':>8}")
        print(f"  {'-'*52}")

        for symbol in self.symbols:
            shares = self.holdings[symbol]
            price  = self.prices_df[symbol]
            value  = self.values[symbol]
            weight = weights[symbol]
            print(f"  {symbol:<12} {shares:>7} "
                  f"₹{price:>9,.2f} "
                  f"₹{value:>13,.2f} "
                  f"{weight:>7.1%}")

        print(f"  {'-'*52}")
        print(f"  {'TOTAL':<12} {'':>7} {'':>10} "
              f"₹{total:>13,.2f} {'100.0%':>8}")
        print("═" * 55)