# engine/var_calculator.py
# Calculates Value at Risk using 3 methods:
# 1. Historical Simulation
# 2. Parametric (Normal Distribution)
# 3. Monte Carlo Simulation

import numpy as np
import pandas as pd
from scipy import stats
from engine.portfolio import Portfolio


class VaRCalculator:
    """
    Calculates VaR and CVaR for a given portfolio.
    """

    def __init__(self, portfolio: Portfolio, confidence: float = 0.95):
        """
        portfolio:  a Portfolio object (already loaded with data)
        confidence: confidence level — 0.95 means 95% VaR
        """
        self.portfolio   = portfolio
        self.confidence  = confidence
        self.alpha       = 1 - confidence   # alpha = 0.05 for 95% VaR

        # Get the portfolio's daily returns as a numpy array
        self.port_returns = portfolio.get_portfolio_returns().values
        self.total_value  = portfolio.get_total_value()

        print(f"VaR Engine ready | "
              f"Confidence: {confidence:.0%} | "
              f"Portfolio: ₹{self.total_value:,.2f} | "
              f"History: {len(self.port_returns)} days")


    # ══════════════════════════════════════════════════════════
    # METHOD 1: HISTORICAL SIMULATION
    # ══════════════════════════════════════════════════════════
    def historical_var(self) -> dict:
        """
        Historical Simulation VaR.

        Steps:
        1. Take all historical daily returns
        2. Sort from worst to best
        3. Find the return at the alpha percentile (worst 5%)
        4. Multiply by portfolio value to get ₹ loss
        """

        # np.percentile finds the value at a given percentile
        # alpha*100 = 5 for 95% confidence
        # This finds the return that only 5% of days were worse than
        var_return = np.percentile(self.port_returns, self.alpha * 100)

        # VaR is always expressed as a positive loss amount
        # var_return is negative (it's a bad day), so we negate it
        var_amount = abs(var_return) * self.total_value

        # ── CVaR: average of all returns WORSE than VaR ────
        # Filter: keep only the days where return was below var_return
        tail_returns = self.port_returns[
            self.port_returns <= var_return
        ]

        # Average of those worst days × portfolio value
        cvar_amount = abs(np.mean(tail_returns)) * self.total_value

        return {
            'method':     'Historical Simulation',
            'confidence': self.confidence,
            'var_pct':    abs(var_return),
            'var_inr':    var_amount,
            'cvar_inr':   cvar_amount,
            'days_used':  len(self.port_returns)
        }


    # ══════════════════════════════════════════════════════════
    # METHOD 2: PARAMETRIC VaR
    # ══════════════════════════════════════════════════════════
    def parametric_var(self) -> dict:
        """
        Parametric VaR (Normal Distribution method).

        Steps:
        1. Calculate mean and std dev of historical returns
        2. Use Z-score for the confidence level
        3. VaR = portfolio_value × (mean - Z × std_dev)
        """

        mu    = np.mean(self.port_returns)   # average daily return
        sigma = np.std(self.port_returns)    # standard deviation

        # scipy.stats.norm.ppf gives the Z-score for any percentile
        # ppf = Percent Point Function (inverse of normal distribution)
        # norm.ppf(0.05) = -1.645 for 95% confidence
        z_score = stats.norm.ppf(self.alpha)

        # VaR formula from Lesson 2:
        # VaR = portfolio_value × (μ - Z × σ)
        # Note: z_score is already negative (-1.645)
        # so (mu + z_score * sigma) is the bad-day return
        var_return = mu + z_score * sigma
        var_amount = abs(var_return) * self.total_value

        # CVaR for normal distribution has a closed-form formula:
        # CVaR = portfolio_value × (μ - σ × φ(Z) / α)
        # where φ(Z) is the standard normal PDF at Z
        # This gives the exact expected loss in the tail
        phi       = stats.norm.pdf(z_score)
        cvar_return = mu - sigma * (phi / self.alpha)
        cvar_amount = abs(cvar_return) * self.total_value

        return {
            'method':     'Parametric (Normal)',
            'confidence': self.confidence,
            'mu':         mu,
            'sigma':      sigma,
            'z_score':    z_score,
            'var_pct':    abs(var_return),
            'var_inr':    var_amount,
            'cvar_inr':   cvar_amount
        }


    # ══════════════════════════════════════════════════════════
    # METHOD 3: MONTE CARLO SIMULATION
    # ══════════════════════════════════════════════════════════
    def monte_carlo_var(self, simulations: int = 10000) -> dict:
        """
        Monte Carlo VaR.

        Steps:
        1. Calculate mean and std dev from historical data
        2. Generate 'simulations' random daily returns
        3. Apply each return to portfolio value
        4. Find the loss at the alpha percentile
        """

        mu    = np.mean(self.port_returns)
        sigma = np.std(self.port_returns)

        # Generate random returns from a normal distribution
        # np.random.normal(mean, std_dev, count)
        # This creates 10,000 random "possible tomorrows"
        np.random.seed(42)   # seed=42 makes results reproducible
                             # (same seed = same random numbers every run)
        simulated_returns = np.random.normal(mu, sigma, simulations)

        # Apply each simulated return to portfolio value
        # If return = -0.03 → simulated P&L = 10,00,000 × -0.03 = -₹30,000
        simulated_pnl = simulated_returns * self.total_value

        # VaR = the loss we'd exceed only alpha% of the time
        # np.percentile finds the alpha*100 th percentile of losses
        var_amount  = abs(np.percentile(simulated_pnl, self.alpha * 100))

        # CVaR = average of all simulated losses worse than VaR
        tail_pnl    = simulated_pnl[simulated_pnl <= -var_amount]
        cvar_amount = abs(np.mean(tail_pnl)) if len(tail_pnl) > 0 else var_amount

        return {
            'method':      'Monte Carlo',
            'confidence':  self.confidence,
            'simulations': simulations,
            'var_pct':     var_amount / self.total_value,
            'var_inr':     var_amount,
            'cvar_inr':    cvar_amount,
            'mu':          mu,
            'sigma':       sigma
        }


    # ══════════════════════════════════════════════════════════
    # FULL REPORT
    # ══════════════════════════════════════════════════════════
    def full_report(self):
        """
        Runs all 3 methods and prints a side-by-side comparison.
        """

        hist   = self.historical_var()
        param  = self.parametric_var()
        mc     = self.monte_carlo_var()

        print("\n" + "═" * 60)
        print("  VALUE AT RISK REPORT")
        print(f"  Confidence Level : {self.confidence:.0%}")
        print(f"  Portfolio Value  : ₹{self.total_value:,.2f}")
        print(f"  Time Horizon     : 1 Day")
        print("═" * 60)

        print(f"\n  {'Method':<25} {'VaR (₹)':>14} {'VaR %':>8} {'CVaR (₹)':>14}")
        print(f"  {'-'*57}")

        for result in [hist, param, mc]:
            print(f"  {result['method']:<25} "
                  f"₹{result['var_inr']:>13,.2f} "
                  f"{result['var_pct']:>7.2%} "
                  f"₹{result['cvar_inr']:>13,.2f}")

        print(f"  {'-'*57}")

        # Interpretation of Historical VaR
        print(f"""
  📊 Reading this table:
  At {self.confidence:.0%} confidence, on any given trading day:

  Historical : 95% chance losses won't exceed
               ₹{hist['var_inr']:>10,.2f}  ({hist['var_pct']:.2%} of portfolio)

  On the worst 5% of days (CVaR), expected loss:
               ₹{hist['cvar_inr']:>10,.2f}
""")
        print("═" * 60)

        return {'historical': hist, 'parametric': param, 'monte_carlo': mc}