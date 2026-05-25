# main.py
from engine.portfolio         import Portfolio
from engine.var_calculator    import VaRCalculator
from engine.greeks_calculator import portfolio_greeks, print_greeks_report
from engine.alert_engine      import AlertEngine, RiskLimits
from engine.backtester        import VaRBacktester
from engine.result_saver      import save_run_results
from engine.nse_calendar      import get_all_expiries
import sys
from engine.result_saver import save_run_results, save_greeks

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── 20-Stock Portfolio ──────────────────────────────────────
holdings = {
    # Banking & Finance
    'HDFCBANK':   200,
    'ICICIBANK':  300,
    'KOTAKBANK':  100,
    'AXISBANK':   250,
    'SBIN':       400,
    'BAJFINANCE':  80,

    # IT
    'TCS':        100,
    'INFY':       200,
    'WIPRO':      500,
    'HCLTECH':    300,

    # Energy & Industrial
    'RELIANCE':   150,
    'ONGC':       600,
    'POWERGRID':  800,
    'NTPC':       700,
    'LT':         100,

    # Consumer & Pharma
    'HINDUNILVR': 120,
    'NESTLEIND':   50,
    'ASIANPAINT': 100,
    'SUNPHARMA':  200,
    'TITAN':      150,
}

# ── Dynamic NSE Expiry Options ──────────────────────────────
# Expiry days recalculated every run — Greeks change daily
expiries = get_all_expiries()

options = [
    # Near-month options (most actively traded)
    {'symbol': 'RELIANCE',  'option_type': 'call',
     'strike': None,  # set below after fetching price
     'expiry_days': expiries['near'], 'quantity': 100},

    {'symbol': 'INFY',      'option_type': 'put',
     'strike': None,
     'expiry_days': expiries['mid'],  'quantity': 200},

    {'symbol': 'TCS',       'option_type': 'call',
     'strike': None,
     'expiry_days': expiries['far'],  'quantity':  50},

    {'symbol': 'HDFCBANK',  'option_type': 'put',
     'strike': None,
     'expiry_days': expiries['near'], 'quantity': 150},

    {'symbol': 'ICICIBANK', 'option_type': 'call',
     'strike': None,
     'expiry_days': expiries['mid'],  'quantity': 200},
]


def set_atm_strikes(options_list: list, portfolio: Portfolio) -> list:
    """
    Sets strike price to nearest round number above/below current price.
    ATM = At The Money — strike closest to current spot price.
    This makes Greeks meaningful and changes as prices move.
    """
    import math
    for opt in options_list:
        spot = portfolio.prices_df[opt['symbol']]

        if opt['option_type'] == 'call':
            # Call strike: round up to nearest 50
            opt['strike'] = math.ceil(spot / 50) * 50
        else:
            # Put strike: round down to nearest 50
            opt['strike'] = math.floor(spot / 50) * 50

    return options_list


if __name__ == "__main__":

    print("█" * 60)
    print("  RISK MONITOR — FULL SYSTEM RUN")
    print("█" * 60)

    # ── STEP 1: Portfolio + VaR ─────────────────────────
    print("\n" + "━"*45)
    print("━━━ STEP 1: PORTFOLIO & VAR (20 STOCKS) ━━━")
    print("━"*45)

    portfolio  = Portfolio(holdings)
    portfolio.summary()

    calc       = VaRCalculator(portfolio, confidence=0.95)
    var_report = calc.full_report()

    # ── STEP 2: Dynamic Greeks ──────────────────────────
    print("\n" + "━"*45)
    print("━━━ STEP 2: OPTION GREEKS (DYNAMIC EXPIRY) ━━━")
    print("━"*45)

    print(f"\n  NSE Expiry countdown:")
    print(f"    Near : {expiries['near']} days")
    print(f"    Mid  : {expiries['mid']} days")
    print(f"    Far  : {expiries['far']} days")

    # Set ATM strikes based on current prices
    options_with_strikes = set_atm_strikes(options, portfolio)

    greeks = portfolio_greeks(options_with_strikes)
    print_greeks_report(greeks)

    # ── STEP 3: Alerts ──────────────────────────────────
    print("\n" + "━"*45)
    print("━━━ STEP 3: RISK ALERTS ━━━")
    print("━"*45)

    limits = RiskLimits()
    engine = AlertEngine(limits)
    engine.check_all(
        var_result      = var_report,
        greeks_results  = greeks,
        portfolio_value = portfolio.get_total_value()
    )
    engine.print_report()

    # ── STEP 4: Kupiec Backtesting ───────────────────────
    print("\n" + "━"*45)
    print("━━━ STEP 4: KUPIEC BACKTESTING ━━━")
    print("━"*45)

    port_returns  = portfolio.get_portfolio_returns()
    backtester    = VaRBacktester(port_returns, confidence=0.95, window=252)
    results_df    = backtester.run_backtest()
    kupiec_result = backtester.print_report()

    # ── STEP 5: Save Results ─────────────────────────────
    print("\n" + "━"*45)
    print("━━━ STEP 5: SAVING TO CLOUD ━━━")
    print("━"*45)

    save_run_results(var_report, greeks, portfolio.get_total_value())
    save_greeks(greeks)
    