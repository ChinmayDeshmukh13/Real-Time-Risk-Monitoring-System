# engine/backtester.py
# Validates the VaR model using Kupiec's Proportion of Failures test

import numpy as np
import pandas as pd
from scipy import stats
from clickhouse_driver import Client # type: ignore
from datetime import datetime


# ── Database connection ─────────────────────────────────────
def get_client():
    return Client(host='localhost', port=9000,
                  user='default', password='')


# ══════════════════════════════════════════════════════════════
# MAIN CLASS: VaRBacktester
# ══════════════════════════════════════════════════════════════
class VaRBacktester:
    """
    Backtests the Historical Simulation VaR model.

    Uses a rolling window approach:
    - Train on last `window` days
    - Test on the next day
    - Slide forward one day at a time
    - Record breaches
    - Run Kupiec POF test on breach count
    """

    def __init__(self,
                 portfolio_returns: pd.Series,
                 confidence:        float = 0.95,
                 window:            int   = 252):
        """
        portfolio_returns: daily returns of the full portfolio (as decimals)
        confidence:        VaR confidence level (0.95 = 95%)
        window:            rolling window size in trading days
        """
        self.returns    = portfolio_returns.values   # numpy array
        self.confidence = confidence
        self.alpha      = 1 - confidence             # 0.05 for 95%
        self.window     = window
        self.n_test     = len(self.returns) - window # number of test days

        print(f"\nBacktester initialized")
        print(f"  Total days      : {len(self.returns)}")
        print(f"  Window size     : {window} days (1 year)")
        print(f"  Test days       : {self.n_test}")
        print(f"  Confidence      : {confidence:.0%}")
        print(f"  Expected breaches: "
              f"{self.n_test * self.alpha:.1f} "
              f"({self.alpha:.0%} × {self.n_test} days)")


    # ══════════════════════════════════════════════════════
    # STEP 1: Run the rolling backtest
    # ══════════════════════════════════════════════════════
    def run_backtest(self) -> pd.DataFrame:
        """
        Runs the rolling window backtest.

        For each test day:
          1. Take the previous `window` days as training data
          2. Calculate Historical VaR from training data
          3. Compare actual return on test day vs VaR
          4. Record breach if actual loss > VaR

        Returns a DataFrame with one row per test day.
        """

        print(f"\n  Running rolling backtest ({self.n_test} iterations)...")

        records = []

        for i in range(self.n_test):

            # Training window: days i to i+window
            train = self.returns[i : i + self.window]

            # Test day: the day immediately after the window
            test_return = self.returns[i + self.window]

            # Calculate Historical VaR from training data
            # np.percentile(data, 5) gives the 5th percentile return
            # That's the threshold below which only 5% of days fall
            var_return = np.percentile(train, self.alpha * 100)

            # Is today a breach?
            # Breach = actual loss exceeded VaR prediction
            # test_return < var_return means actual loss was worse
            is_breach = bool(test_return < var_return)

            records.append({
                'test_day':    i + self.window,
                'actual_return': test_return,
                'var_threshold': var_return,  # negative number
                'actual_loss': -test_return,  # positive = loss
                'var_loss':    -var_return,   # positive = VaR amount
                'is_breach':   is_breach,
                'excess_loss': max(0, (-test_return) - (-var_return))
            })

        self.results_df = pd.DataFrame(records)
        n_breaches = self.results_df['is_breach'].sum()

        print(f"  Done. Breaches found: {n_breaches} / {self.n_test} days "
              f"({n_breaches/self.n_test:.1%})")

        return self.results_df


    # ══════════════════════════════════════════════════════
    # STEP 2: Kupiec's POF Test
    # ══════════════════════════════════════════════════════
    def kupiec_test(self) -> dict:
        """
        Runs Kupiec's Proportion of Failures (POF) test.

        Tests whether the observed breach rate is statistically
        consistent with the expected breach rate.

        H₀: actual breach rate = expected breach rate (model is correct)
        H₁: actual breach rate ≠ expected rate (model is wrong)

        Test statistic: Likelihood Ratio (LR)
        Critical value: 3.84 (chi-squared with 1 df at 95% confidence)

        If LR > 3.84 → reject H₀ → model is statistically wrong
        If LR ≤ 3.84 → fail to reject H₀ → model is acceptable
        """

        T = self.n_test                                    # total test days
        N = int(self.results_df['is_breach'].sum())        # actual breaches
        p = self.alpha                                     # expected rate (0.05)
        p_hat = N / T                                      # observed rate

        # ── Kupiec's Likelihood Ratio statistic ─────────
        # Formula: LR = -2 × ln[L(p) / L(p_hat)]
        # Where L(p) = probability of N breaches under H₀
        #       L(p_hat) = maximum likelihood (using observed rate)
        #
        # Simplified:
        # LR = -2 × [N×ln(p) + (T-N)×ln(1-p)]
        #      +2 × [N×ln(p_hat) + (T-N)×ln(1-p_hat)]

        # Guard against log(0) errors
        if N == 0:
            # No breaches at all — model may be over-conservative
            lr_stat = -2 * (T * np.log(1 - p))
        elif N == T:
            # All days were breaches — definitely wrong
            lr_stat = -2 * (T * np.log(p))
        else:
            # Standard formula
            log_l0 = (N * np.log(p) +
                      (T - N) * np.log(1 - p))

            log_l1 = (N * np.log(p_hat) +
                      (T - N) * np.log(1 - p_hat))

            lr_stat = -2 * (log_l0 - log_l1)

        # ── P-value from Chi-squared distribution ───────
        # LR follows a chi-squared distribution with 1 degree of freedom
        # p_value tells us: "if the model were correct, how likely is
        # this breach count?"
        # Low p_value → model is likely wrong
        p_value = 1 - stats.chi2.cdf(lr_stat, df=1)

        # ── Critical value at 95% ───────────────────────
        # chi2.ppf(0.95, df=1) = 3.841 — the threshold
        critical_value = stats.chi2.ppf(0.95, df=1)

        # ── Verdict ─────────────────────────────────────
        reject_h0 = lr_stat > critical_value

        # ── Basel Traffic Light Zone ─────────────────────
        # Based on 250 test days — scale to our test period
        scaled_n = N * (250 / T)   # equivalent breaches on 250-day period

        if scaled_n <= 4:
            zone = 'GREEN (Conservative)'
        elif scaled_n <= 9:
            zone = 'GREEN (Acceptable)'
        elif scaled_n <= 15:
            zone = 'YELLOW (Investigate)'
        else:
            zone = 'RED (Model Failure)'

        return {
            'T':               T,
            'N':               N,
            'p_expected':      p,
            'p_observed':      p_hat,
            'expected_breaches': T * p,
            'lr_statistic':    lr_stat,
            'critical_value':  critical_value,
            'p_value':         p_value,
            'reject_h0':       reject_h0,
            'verdict':         'FAIL — Model rejected' if reject_h0
                               else 'PASS — Model acceptable',
            'basel_zone':      zone,
            'scaled_n_250':    scaled_n
        }


    # ══════════════════════════════════════════════════════
    # STEP 3: Print the full backtest report
    # ══════════════════════════════════════════════════════
    def print_report(self):
        """Prints a complete backtesting and Kupiec test report."""

        kupiec = self.kupiec_test()

        T     = kupiec['T']
        N     = kupiec['N']
        p_hat = kupiec['p_observed']
        exp   = kupiec['expected_breaches']

        print("\n" + "═" * 62)
        print("  VAR MODEL BACKTESTING REPORT — KUPIEC POF TEST")
        print("═" * 62)

        # ── Section 1: Breach Statistics ────────────────
        print(f"\n  ── Breach Statistics ──────────────────────────────")
        print(f"  Test period         : {T} trading days")
        print(f"  VaR confidence      : {self.confidence:.0%}")
        print(f"  Expected breaches   : {exp:.1f}  "
              f"({self.alpha:.0%} × {T} days)")
        print(f"  Actual breaches     : {N}")
        print(f"  Observed rate       : {p_hat:.2%}  "
              f"(expected: {self.alpha:.2%})")

        # Breach comparison
        diff = N - exp
        if diff > 0:
            print(f"  Difference          : +{diff:.1f} more breaches than expected")
        else:
            print(f"  Difference          : {diff:.1f} fewer breaches than expected")

        # ── Section 2: Kupiec Test Result ────────────────
        print(f"\n  ── Kupiec POF Test ────────────────────────────────")
        print(f"  LR Statistic        : {kupiec['lr_statistic']:.4f}")
        print(f"  Critical Value      : {kupiec['critical_value']:.4f}  (χ² at 95%)")
        print(f"  P-Value             : {kupiec['p_value']:.4f}")
        print(f"  Decision            : {'Reject H₀' if kupiec['reject_h0'] else 'Fail to Reject H₀'}")
        print(f"  Verdict             : {kupiec['verdict']}")

        # ── Section 3: Basel Zone ────────────────────────
        print(f"\n  ── Basel III Traffic Light ────────────────────────")
        print(f"  Scaled to 250 days  : {kupiec['scaled_n_250']:.1f} equivalent breaches")
        zone = kupiec['basel_zone']

        # Color the zone with formatting
        if 'GREEN' in zone:
            indicator = '🟢'
        elif 'YELLOW' in zone:
            indicator = '🟡'
        else:
            indicator = '🔴'

        print(f"  Basel Zone          : {indicator}  {zone}")

        print(f"\n  Reference:")
        print(f"    🟢 Green  (0–9  breaches/250d) → Model acceptable")
        print(f"    🟡 Yellow (10–15 breaches/250d) → Investigate model")
        print(f"    🔴 Red   (16+  breaches/250d)  → Capital surcharge")

        # ── Section 4: Worst Breach Days ─────────────────
        print(f"\n  ── Worst Breach Days ──────────────────────────────")

        breach_days = self.results_df[
            self.results_df['is_breach']
        ].nlargest(5, 'excess_loss')

        if len(breach_days) > 0:
            print(f"  {'Day':<8} {'Actual Loss':>13} "
                  f"{'VaR Predicted':>15} {'Excess Loss':>13}")
            print(f"  {'-'*52}")

            for _, row in breach_days.iterrows():
                print(f"  Day {int(row['test_day']):<4} "
                      f"  {row['actual_loss']*100:>10.3f}%  "
                      f"  {row['var_loss']*100:>12.3f}%  "
                      f"  {row['excess_loss']*100:>10.3f}%")
        else:
            print("  No breaches recorded.")

        # ── Section 5: Overall Model Health ──────────────
        print(f"\n  ── Model Health Summary ───────────────────────────")

        if not kupiec['reject_h0'] and 'GREEN' in zone:
            health = "EXCELLENT — Model is statistically valid"
            icon   = "✅"
        elif not kupiec['reject_h0']:
            health = "ACCEPTABLE — Within tolerance, monitor closely"
            icon   = "⚠️ "
        else:
            health = "POOR — Model requires recalibration"
            icon   = "🚨"

        print(f"  {icon}  {health}")

        # What to say in an interview
        print(f"""
  Interview Answer:
  "I backtested the Historical Simulation VaR model over {T}
   trading days. The model recorded {N} breaches against an
   expected {exp:.0f}. The Kupiec LR statistic of
   {kupiec['lr_statistic']:.2f} is {'above' if kupiec['reject_h0']
   else 'below'} the critical value of 3.84, so we
   {'reject' if kupiec['reject_h0'] else 'fail to reject'} the null
   hypothesis. The model is in the Basel {zone.split('(')[0].strip()}
   zone — {kupiec['verdict']}."
""")
        print("═" * 62)

        return kupiec