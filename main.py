# main.py
from engine.portfolio         import Portfolio
from engine.var_calculator    import VaRCalculator
from engine.greeks_calculator import portfolio_greeks, print_greeks_report
from engine.alert_engine      import AlertEngine, RiskLimits
from engine.backtester        import VaRBacktester
from engine.result_saver import save_run_results

# ── Holdings ────────────────────────────────────────────────
holdings = {
    'RELIANCE':  100,
    'INFY':      200,
    'HDFCBANK':  150,
    'TCS':        80,
    'ICICIBANK': 300
}

# ── Options ─────────────────────────────────────────────────
options = [
    {'symbol': 'RELIANCE', 'option_type': 'call',
     'strike': 1400, 'expiry_days': 30, 'quantity': 100},
    {'symbol': 'INFY',     'option_type': 'put',
     'strike': 1050, 'expiry_days': 45, 'quantity': 200},
    {'symbol': 'TCS',      'option_type': 'call',
     'strike': 2300, 'expiry_days': 60, 'quantity':  50},
]

if __name__ == "__main__":

    print("█" * 60)
    print("  RISK MONITOR — FULL SYSTEM RUN")
    print("█" * 60)

    # ── STEP 1: Portfolio + VaR ─────────────────────────
    print("\n" + "━"*40)
    print("━━━ STEP 1: PORTFOLIO & VAR ━━━")
    print("━"*40)

    portfolio  = Portfolio(holdings)
    portfolio.summary()

    calc       = VaRCalculator(portfolio, confidence=0.95)
    var_report = calc.full_report()

    # ── STEP 2: Greeks ──────────────────────────────────
    print("\n" + "━"*40)
    print("━━━ STEP 2: OPTION GREEKS ━━━")
    print("━"*40)

    greeks = portfolio_greeks(options)
    print_greeks_report(greeks)

   # ── STEP 3: Alerts ──────────────────────────────────
    print("\n" + "━"*40)
    print("━━━ STEP 3: RISK ALERTS ━━━")
    print("━"*40)

    limits = RiskLimits()
    engine = AlertEngine(limits)
    engine.check_all(
        var_result     = var_report,
        greeks_results  = greeks,
        portfolio_value = portfolio.get_total_value()
    )
    engine.print_report()

    # ── STEP 4: Kupiec Backtesting ───────────────────────
    print("\n" + "━"*40)
    print("━━━ STEP 4: KUPIEC BACKTESTING ━━━")
    print("━"*40)

    port_returns = portfolio.get_portfolio_returns()

    backtester = VaRBacktester(
        portfolio_returns = port_returns,
        confidence        = 0.95,
        window            = 252
    )

    results_df   = backtester.run_backtest()
    kupiec_result = backtester.print_report()

    # ── STEP 5: Save Results to Database ────────────────
    print("\n" + "━"*40)
    print("━━━ STEP 5: SAVING RESULTS ━━━")
    print("━"*40)
    save_run_results(var_report, greeks, portfolio.get_total_value())