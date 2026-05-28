# main.py
from config.portfolio         import HOLDINGS, OPTIONS_CONFIG, CONFIDENCE_LEVEL
from engine.portfolio         import Portfolio
from engine.var_calculator    import VaRCalculator
from engine.greeks_calculator import portfolio_greeks, print_greeks_report
from engine.alert_engine      import AlertEngine, RiskLimits
from engine.backtester        import VaRBacktester
from engine.result_saver      import save_run_results, save_greeks
from engine.nse_calendar      import get_all_expiries
from data.loader              import run_incremental_pipeline
import math

def set_atm_strikes(options_list, portfolio):
    expiries = get_all_expiries()
    opts = []
    for opt in options_list:
        spot = portfolio.prices_df[opt['symbol']]
        strike = (math.ceil(spot/50)*50 if opt['option_type']=='call'
                  else math.floor(spot/50)*50)
        opts.append({**opt,
                     'strike':      strike,
                     'expiry_days': expiries['near']})
    return opts

if __name__ == "__main__":
    print("█"*60)
    print("  NSE RISK MONITOR — PIPELINE RUN")
    print("█"*60)

    # Step 0: Incremental data update
    print("\n━━━ STEP 0: DATA UPDATE (INCREMENTAL) ━━━")
    run_incremental_pipeline()

    # Step 1: Portfolio + VaR
    print("\n━━━ STEP 1: PORTFOLIO & VAR ━━━")
    portfolio  = Portfolio(HOLDINGS)
    portfolio.summary()
    calc       = VaRCalculator(portfolio, confidence=CONFIDENCE_LEVEL)
    var_report = calc.full_report()

    # Step 2: Greeks
    print("\n━━━ STEP 2: GREEKS ━━━")
    options = set_atm_strikes(OPTIONS_CONFIG, portfolio)
    greeks  = portfolio_greeks(options)
    print_greeks_report(greeks)

    # Step 3: Alerts
    print("\n━━━ STEP 3: ALERTS ━━━")
    engine = AlertEngine(RiskLimits())
    engine.check_all(var_report, greeks, portfolio.get_total_value())
    engine.print_report()
    engine.log_alerts()

    # Step 4: Backtest
    print("\n━━━ STEP 4: KUPIEC BACKTEST ━━━")
    bt = VaRBacktester(portfolio.get_portfolio_returns(),
                       confidence=CONFIDENCE_LEVEL, window=252)
    bt.run_backtest()
    bt.print_report()

    # Step 5: Save
    print("\n━━━ STEP 5: SAVING TO CLOUD ━━━")
    save_run_results(var_report, greeks, portfolio.get_total_value())
    save_greeks(greeks)