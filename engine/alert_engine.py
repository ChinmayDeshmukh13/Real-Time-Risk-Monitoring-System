# engine/alert_engine.py
# Monitors portfolio risk and fires alerts when limits are breached

import os
import json
from datetime import datetime
from enum import Enum


# ── Alert Severity Levels ───────────────────────────────────
class Severity(Enum):
    """
    Enum = a fixed set of named constants.
    We use it so severity levels are never misspelled.
    Instead of writing "WARNING" (a string that could be typo'd),
    we write Severity.WARNING — Python enforces it exists.
    """
    INFO    = "INFO"      # Normal, informational
    WARNING = "WARNING"   # Approaching limit
    BREACH  = "BREACH"    # Limit exceeded — action needed
    CRITICAL= "CRITICAL"  # Severe breach — immediate action


# ── A Single Alert ──────────────────────────────────────────
class Alert:
    """
    Represents one risk alert event.
    Bundles together all the information about what happened.
    """

    def __init__(self,
                 severity:    Severity,
                 limit_type:  str,
                 message:     str,
                 actual:      float,
                 limit:       float,
                 portfolio_value: float):

        self.timestamp       = datetime.now()
        self.severity        = severity
        self.limit_type      = limit_type
        self.message         = message
        self.actual          = actual
        self.limit           = limit
        self.portfolio_value = portfolio_value

        # Breach % = how far over the limit we are
        # Positive = over limit (bad)
        # Negative = under limit (fine)
        self.breach_pct = ((actual - limit) / limit) * 100

    def to_dict(self) -> dict:
        """Converts alert to dictionary — needed for JSON logging."""
        return {
            'timestamp':       self.timestamp.isoformat(),
            'severity':        self.severity.value,
            'limit_type':      self.limit_type,
            'message':         self.message,
            'actual':          round(self.actual,  4),
            'limit':           round(self.limit,   4),
            'breach_pct':      round(self.breach_pct, 2),
            'portfolio_value': round(self.portfolio_value, 2)
        }

    def __str__(self):
        """How the alert looks when printed."""
        icons = {
            Severity.INFO:     "ℹ️ ",
            Severity.WARNING:  "⚠️ ",
            Severity.BREACH:   "🚨",
            Severity.CRITICAL: "🔴"
        }
        icon = icons[self.severity]
        return (
            f"{icon}  [{self.severity.value}] {self.limit_type}\n"
            f"     Message : {self.message}\n"
            f"     Actual  : {self.actual:.4f}\n"
            f"     Limit   : {self.limit:.4f}\n"
            f"     Breach  : {self.breach_pct:+.1f}%\n"
            f"     Time    : {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )


# ══════════════════════════════════════════════════════════════
# RISK LIMITS CONFIGURATION
# ══════════════════════════════════════════════════════════════
class RiskLimits:
    """
    Stores all risk limits for the portfolio.
    Centralizing limits here means we change one place
    and it propagates everywhere — no hunting through code.
    """

    def __init__(self,
                 var_limit_pct:    float = 0.02,    # VaR ≤ 2% of portfolio
                 cvar_limit_pct:   float = 0.03,    # CVaR ≤ 3% of portfolio
                 delta_limit:      float = 50.0,    # |Net Delta| ≤ 50
                 theta_limit:      float = -500.0,  # Theta ≥ -₹500/day
                 vega_limit:       float = 2000.0,  # |Net Vega| ≤ ₹2,000
                 warning_trigger:  float = 0.80):   # Warn at 80% of limit

        self.var_limit_pct   = var_limit_pct
        self.cvar_limit_pct  = cvar_limit_pct
        self.delta_limit     = delta_limit
        self.theta_limit     = theta_limit
        self.vega_limit      = vega_limit
        self.warning_trigger = warning_trigger  # 0.80 = warn at 80% used


# ══════════════════════════════════════════════════════════════
# THE ALERT ENGINE
# ══════════════════════════════════════════════════════════════
class AlertEngine:
    """
    The core risk monitoring system.
    Checks risk metrics against limits and generates alerts.
    """

    def __init__(self,
                 limits:   RiskLimits,
                 log_file: str = "logs/risk_alerts.log"):

        self.limits   = limits
        self.log_file = log_file
        self.alerts   = []   # In-memory history of all alerts this session

        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        print(f"Alert Engine initialized | Log: {log_file}")


    # ── Core Check: Compare actual vs limit ────────────────
    def _check_limit(self,
                     actual:       float,
                     limit:        float,
                     limit_type:   str,
                     message_tmpl: str,
                     portfolio_value: float,
                     reverse: bool = False) -> Alert:
        """
        Compares an actual metric against its limit.

        reverse=False → breach when actual > limit  (e.g. VaR too high)
        reverse=True  → breach when actual < limit  (e.g. Theta too negative)

        Returns an Alert object with appropriate severity.
        """

        # Is this a breach?
        if reverse:
            # Breach when actual is more negative than limit
            # e.g. Theta = -600 vs limit = -500  → breach
            is_breach  = actual < limit
            usage_ratio = actual / limit  # both negative → ratio > 1 is bad
        else:
            # Breach when actual exceeds limit
            is_breach  = actual > limit
            usage_ratio = actual / limit  # ratio > 1 means over limit

        # Determine severity
        if is_breach:
            if usage_ratio > 1.5:
                severity = Severity.CRITICAL   # 50%+ over limit
            else:
                severity = Severity.BREACH     # Over limit
        elif usage_ratio >= self.limits.warning_trigger:
            severity = Severity.WARNING        # 80-100% of limit used
        else:
            severity = Severity.INFO           # All clear

        # Build message
        message = message_tmpl.format(
            actual=actual,
            limit=limit,
            usage=usage_ratio * 100
        )

        alert = Alert(
            severity        = severity,
            limit_type      = limit_type,
            message         = message,
            actual          = actual,
            limit           = limit,
            portfolio_value = portfolio_value
        )

        return alert


    # ── Check All Risk Limits ───────────────────────────────
    def check_all(self,
                  var_result:   dict,
                  greeks_results: list,
                  portfolio_value: float) -> list:
        """
        Runs all limit checks and returns list of alerts.

        var_result:      output from VaRCalculator
        greeks_results:  output from portfolio_greeks()
        portfolio_value: total ₹ value of portfolio
        """

        self.alerts = []   # Reset for this run

        # ── 1. VaR Limit ────────────────────────────────────
        var_pct   = var_result['historical']['var_pct']
        var_limit = self.limits.var_limit_pct

        alert = self._check_limit(
            actual          = var_pct,
            limit           = var_limit,
            limit_type      = "VaR Limit",
            message_tmpl    = (
                "Historical VaR = {actual:.2%} | "
                "Limit = {limit:.2%} | "
                "Used {usage:.1f}% of limit"
            ),
            portfolio_value = portfolio_value
        )
        self.alerts.append(alert)

        # ── 2. CVaR Limit ───────────────────────────────────
        cvar_pct   = var_result['historical']['cvar_inr'] / portfolio_value
        cvar_limit = self.limits.cvar_limit_pct

        alert = self._check_limit(
            actual          = cvar_pct,
            limit           = cvar_limit,
            limit_type      = "CVaR Limit",
            message_tmpl    = (
                "CVaR = {actual:.2%} of portfolio | "
                "Limit = {limit:.2%} | "
                "Used {usage:.1f}% of limit"
            ),
            portfolio_value = portfolio_value
        )
        self.alerts.append(alert)

        # ── 3. Delta Limit ───────────────────────────────────
        # Sum net delta across all options
        net_delta  = sum(r['position_delta'] for r in greeks_results)
        abs_delta  = abs(net_delta)
        delta_limit = self.limits.delta_limit

        alert = self._check_limit(
            actual          = abs_delta,
            limit           = delta_limit,
            limit_type      = "Delta Limit",
            message_tmpl    = (
                "Net |Delta| = {actual:.2f} | "
                "Limit = {limit:.2f} | "
                "Used {usage:.1f}% of limit"
            ),
            portfolio_value = portfolio_value
        )
        self.alerts.append(alert)

        # ── 4. Theta Limit ───────────────────────────────────
        net_theta   = sum(r['position_theta'] for r in greeks_results)
        theta_limit = self.limits.theta_limit

        # reverse=True because theta is negative — too negative = breach
        alert = self._check_limit(
            actual          = net_theta,
            limit           = theta_limit,
            limit_type      = "Theta Limit",
            message_tmpl    = (
                "Net Theta = ₹{actual:.2f}/day | "
                "Limit = ₹{limit:.2f}/day | "
                "Used {usage:.1f}% of limit"
            ),
            portfolio_value = portfolio_value,
            reverse         = True
        )
        self.alerts.append(alert)

        # ── 5. Vega Limit ────────────────────────────────────
        net_vega   = abs(sum(r['position_vega'] for r in greeks_results))
        vega_limit = self.limits.vega_limit

        alert = self._check_limit(
            actual          = net_vega,
            limit           = vega_limit,
            limit_type      = "Vega Limit",
            message_tmpl    = (
                "Net |Vega| = ₹{actual:.2f} | "
                "Limit = ₹{limit:.2f} | "
                "Used {usage:.1f}% of limit"
            ),
            portfolio_value = portfolio_value
        )
        self.alerts.append(alert)

        return self.alerts


    # ── Log Alerts to File ──────────────────────────────────
    def log_alerts(self):
        """
        Writes all alerts to a JSON log file.
        Each run appends — never overwrites.
        This creates an audit trail, required by regulators.
        """

        with open(self.log_file, 'a') as f:   # 'a' = append mode
            for alert in self.alerts:
                # Write each alert as one JSON line
                # json.dumps converts dict to JSON string
                f.write(json.dumps(alert.to_dict()) + '\n')


    # ── Print Alert Report ──────────────────────────────────
    def print_report(self):
        """Prints all alerts in a formatted, colour-coded report."""

        # Count by severity
        counts = {s: 0 for s in Severity}
        for alert in self.alerts:
            counts[alert.severity] += 1

        print("\n" + "═" * 60)
        print("  RISK ALERT REPORT")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Checks run: {len(self.alerts)}  |  "
              f"INFO: {counts[Severity.INFO]}  |  "
              f"WARN: {counts[Severity.WARNING]}  |  "
              f"BREACH: {counts[Severity.BREACH]}  |  "
              f"CRITICAL: {counts[Severity.CRITICAL]}")
        print("═" * 60)

        # Print each alert
        for alert in self.alerts:
            print(f"\n{alert}")

        # Summary verdict
        print("\n" + "─" * 60)
        if counts[Severity.CRITICAL] > 0:
            print("  🔴 VERDICT: CRITICAL — Escalate to CRO immediately")
        elif counts[Severity.BREACH] > 0:
            print("  🚨 VERDICT: BREACH — Reduce positions or hedge now")
        elif counts[Severity.WARNING] > 0:
            print("  ⚠️  VERDICT: WARNING — Monitor closely, prepare hedges")
        else:
            print("  ✅ VERDICT: ALL CLEAR — Portfolio within all limits")
        print("═" * 60)