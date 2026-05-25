# engine/greeks_calculator.py
# Calculates option Greeks using QuantLib's Black-Scholes engine

import QuantLib as ql # type: ignore
from datetime import date, datetime
from engine.config import get_client


# ── Helper: Get current stock price from database ───────────
def get_current_price(symbol: str) -> float:
    """Fetches the latest closing price for a symbol from ClickHouse."""
    client = get_client()
    result = client.execute(f"""
        SELECT close
        FROM market_ticks
        WHERE symbol = '{symbol}'
        ORDER BY date DESC
        LIMIT 1
    """)
    if not result:
        raise ValueError(f"No price data found for {symbol}")
    return float(result[0][0])


# ── Helper: Get historical volatility from database ─────────
def get_historical_volatility(symbol: str) -> float:
    """
    Calculates annualized historical volatility for a symbol.
    Uses the last 252 trading days (1 year).
    Formula: daily_std_dev × √252
    """
    client = get_client()
    result = client.execute(f"""
        SELECT stddevPop(returns)
        FROM (
            SELECT returns
            FROM market_ticks
            WHERE symbol = '{symbol}'
            ORDER BY date DESC
            LIMIT 252
        )
    """)
    daily_vol  = float(result[0][0])
    annual_vol = daily_vol * (252 ** 0.5)  # annualize
    return annual_vol


# ══════════════════════════════════════════════════════════════
# CORE FUNCTION: Price one option and return all Greeks
# ══════════════════════════════════════════════════════════════
def calculate_greeks(
    symbol:      str,
    option_type: str,    # 'call' or 'put'
    strike:      float,  # strike price in ₹
    expiry_days: int,    # days until expiry
    risk_free_rate: float = 0.065,  # RBI repo rate ≈ 6.5%
    volatility:  float = None,      # if None, we calculate from history
    spot_price:  float = None       # if None, we fetch from database
) -> dict:
    """
    Prices a European option and returns all Greeks.

    Returns a dict with:
      price, delta, gamma, vega, theta, rho,
      implied_vol, spot, strike, expiry_days
    """

    # ── Step 1: Get market data ─────────────────────────────
    S     = spot_price if spot_price else get_current_price(symbol)
    sigma = volatility if volatility else get_historical_volatility(symbol)

    print(f"  Pricing {symbol} {option_type.upper()} "
          f"| Spot: ₹{S:,.2f} | Strike: ₹{strike:,.2f} "
          f"| Expiry: {expiry_days}d | Vol: {sigma:.1%}")

    # ── Step 2: Set up QuantLib dates ───────────────────────

    # Today's date in QuantLib format
    today = ql.Date(
        datetime.today().day,
        datetime.today().month,
        datetime.today().year
    )
    ql.Settings.instance().evaluationDate = today

    # Expiry date = today + expiry_days calendar days
    expiry_date = today + expiry_days

    # ── Step 3: Build the option object ────────────────────
    # Payoff: What does the option pay at expiry?
    # Call payoff = max(S - K, 0) — profit if stock above strike
    # Put  payoff = max(K - S, 0) — profit if stock below strike

    if option_type.lower() == 'call':
        payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike)
    else:
        payoff = ql.PlainVanillaPayoff(ql.Option.Put, strike)

    # Exercise: European = can only exercise AT expiry (not before)
    exercise = ql.EuropeanExercise(expiry_date)

    # The option itself = payoff + exercise rules
    option = ql.VanillaOption(payoff, exercise)

    # ── Step 4: Build market data handles ──────────────────
    # QuantLib uses "handles" — wrappers around values
    # This allows values to update automatically if market moves

    # Spot price handle
    spot_handle = ql.QuoteHandle(
        ql.SimpleQuote(S)
    )

    # Risk-free rate handle
    # FlatForward = constant interest rate (flat yield curve)
    # Actual/365 = day count convention (how we count days between dates)
    rate_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(today, risk_free_rate, ql.Actual365Fixed())
    )

    # Dividend yield handle (we assume 0 for simplicity)
    dividend_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(today, 0.0, ql.Actual365Fixed())
    )

    # Volatility handle
    # BlackConstantVol = constant volatility (Black-Scholes assumption)
    vol_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(today, ql.NullCalendar(),
                            sigma, ql.Actual365Fixed())
    )

    # ── Step 5: Build the Black-Scholes process ─────────────
    # The BSM process combines all market data into one object
    # BSM = Black-Scholes-Merton
    bsm_process = ql.BlackScholesMertonProcess(
        spot_handle,
        dividend_handle,
        rate_handle,
        vol_handle
    )

    # ── Step 6: Attach the pricing engine ───────────────────
    # The engine uses the BSM process to calculate the price
    # AnalyticEuropeanEngine = closed-form Black-Scholes formula
    engine = ql.AnalyticEuropeanEngine(bsm_process)
    option.setPricingEngine(engine)

    # ── Step 7: Extract results ─────────────────────────────
    # Now we can call these methods — QuantLib calculates them
    # from the Black-Scholes formula
    try:
        price  = option.NPV()       # Net Present Value = option price
        delta  = option.delta()     # dPrice/dSpot
        gamma  = option.gamma()     # dDelta/dSpot
        vega   = option.vega()      # dPrice/dVol  (per 1% vol change)
        theta  = option.theta()     # dPrice/dTime (per calendar day)
        rho    = option.rho()       # dPrice/dRate

        # Vega from QuantLib is per 1.0 vol change (100%)
        # Divide by 100 to get per 1% change (more intuitive)
        vega_per_pct = vega / 100

        # Theta from QuantLib is annual — divide by 365 for daily
        theta_daily  = theta / 365

    except Exception as e:
        return {'error': str(e)}

    result = {
        'symbol':       symbol,
        'option_type':  option_type.upper(),
        'spot':         S,
        'strike':       strike,
        'expiry_days':  expiry_days,
        'volatility':   sigma,
        'risk_free':    risk_free_rate,
        'price':        round(price,  4),
        'delta':        round(delta,  4),
        'gamma':        round(gamma,  6),
        'vega':         round(vega_per_pct, 4),
        'theta':        round(theta_daily,  4),
        'rho':          round(rho / 100,    4),
        'moneyness':    'ITM' if (
                           (option_type=='call' and S > strike) or
                           (option_type=='put'  and S < strike)
                        ) else 'OTM'
    }

    return result


# ══════════════════════════════════════════════════════════════
# PORTFOLIO GREEKS: Calculate Greeks for multiple options
# ══════════════════════════════════════════════════════════════
def portfolio_greeks(options_list: list) -> list:
    """
    Calculates Greeks for a list of options.

    options_list: list of dicts, each with:
      symbol, option_type, strike, expiry_days, quantity

    Returns list of result dicts with Greeks + position sizing.
    """
    results = []

    for opt in options_list:
        result = calculate_greeks(
            symbol      = opt['symbol'],
            option_type = opt['option_type'],
            strike      = opt['strike'],
            expiry_days = opt['expiry_days']
        )

        if 'error' in result:
            print(f"  ❌ Error pricing {opt['symbol']}: {result['error']}")
            continue

        # Add quantity and position value
        qty = opt.get('quantity', 1)
        result['quantity']       = qty
        result['position_value'] = result['price'] * qty

        # Scale Greeks by quantity (100 options = 100× the exposure)
        result['position_delta'] = result['delta'] * qty
        result['position_vega']  = result['vega']  * qty
        result['position_theta'] = result['theta'] * qty

        results.append(result)

    return results


# ══════════════════════════════════════════════════════════════
# REPORT: Print formatted Greeks table
# ══════════════════════════════════════════════════════════════
def print_greeks_report(results: list):
    """Prints a formatted Greeks report for all options."""

    print("\n" + "═" * 75)
    print("  OPTION GREEKS REPORT")
    print("═" * 75)
    print(f"  {'Symbol':<10} {'Type':<5} {'Strike':>8} "
          f"{'Days':>5} {'Price':>8} {'Delta':>7} "
          f"{'Gamma':>8} {'Vega':>7} {'Theta':>8} {'M/O':>5}")
    print(f"  {'-'*72}")

    total_delta = 0
    total_theta = 0
    total_vega  = 0

    for r in results:
        print(f"  {r['symbol']:<10} {r['option_type']:<5} "
              f"₹{r['strike']:>7,.0f} "
              f"{r['expiry_days']:>5} "
              f"₹{r['price']:>7.2f} "
              f"{r['delta']:>7.4f} "
              f"{r['gamma']:>8.6f} "
              f"{r['vega']:>7.4f} "
              f"{r['theta']:>8.4f} "
              f"{r['moneyness']:>5}")

        total_delta += r['position_delta']
        total_theta += r['position_theta']
        total_vega  += r['position_vega']

    print(f"  {'-'*72}")
    print(f"\n  Portfolio Greeks (scaled by quantity):")
    print(f"    Net Delta : {total_delta:>8.4f}  "
          f"← For every ₹1 spot moves, portfolio gains/loses ₹{total_delta:.2f}")
    print(f"    Net Theta : {total_theta:>8.4f}  "
          f"← Portfolio loses ₹{abs(total_theta):.4f} per day from time decay")
    print(f"    Net Vega  : {total_vega:>8.4f}  "
          f"← For every 1% vol spike, portfolio gains/loses ₹{total_vega:.4f}")

    print("\n" + "═" * 75)


# ── Direct run test ─────────────────────────────────────────
if __name__ == "__main__":

    # Define 3 options — strikes near current market prices
    options = [
        {
            'symbol':      'RELIANCE',
            'option_type': 'call',
            'strike':      1400,
            'expiry_days': 30,
            'quantity':    100
        },
        {
            'symbol':      'INFY',
            'option_type': 'put',
            'strike':      1050,
            'expiry_days': 45,
            'quantity':    200
        },
        {
            'symbol':      'TCS',
            'option_type': 'call',
            'strike':      2300,
            'expiry_days': 60,
            'quantity':    50
        }
    ]

    print("\nCalculating Greeks for 3 options...")
    results = portfolio_greeks(options)
    print_greeks_report(results)