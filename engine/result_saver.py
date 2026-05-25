# engine/result_saver.py
from datetime import datetime
from engine.config import get_client


def ensure_option_greeks_table(client):
    """Creates the option-level dashboard table if it is missing."""
    client.execute(
        '''
        CREATE TABLE IF NOT EXISTS option_greeks_results (
            run_time       DateTime,
            symbol         String,
            option_type    String,
            spot           Float64,
            strike         Float64,
            expiry_days    UInt16,
            volatility     Float64,
            price          Float64,
            delta          Float64,
            gamma          Float64,
            vega           Float64,
            theta          Float64,
            rho            Float64,
            moneyness      String,
            quantity       Float64,
            position_value Float64,
            position_delta Float64,
            position_vega  Float64,
            position_theta Float64
        )
        ENGINE = MergeTree()
        ORDER BY (run_time, symbol, option_type, strike)
        '''
    )


def save_run_results(var_report: dict,
                     greeks_results: list,
                     portfolio_value: float):
    """Saves one complete risk run to var_results table."""
    client = get_client()
    ensure_option_greeks_table(client)
    run_time = datetime.now()

    hist  = var_report['historical']
    param = var_report['parametric']
    mc    = var_report['monte_carlo']

    net_delta = sum(r['position_delta'] for r in greeks_results)
    net_theta = sum(r['position_theta'] for r in greeks_results)
    net_vega  = sum(r['position_vega']  for r in greeks_results)

    row = [(
        run_time,
        portfolio_value,
        hist['var_inr'],
        hist['var_pct'],
        param['var_inr'],
        mc['var_inr'],
        hist['cvar_inr'],
        net_delta,
        net_theta,
        net_vega
    )]

    client.execute(
        '''
        INSERT INTO var_results (
            run_time,
            portfolio_value,
            hist_var_inr,
            hist_var_pct,
            param_var_inr,
            mc_var_inr,
            hist_cvar_inr,
            net_delta,
            net_theta,
            net_vega
        ) VALUES
        ''',
        row
    )
    option_rows = [
        (
            run_time,
            r['symbol'],
            r['option_type'],
            r['spot'],
            r['strike'],
            int(r['expiry_days']),
            r['volatility'],
            r['price'],
            r['delta'],
            r['gamma'],
            r['vega'],
            r['theta'],
            r.get('rho', 0.0),
            r['moneyness'],
            r.get('quantity', 1),
            r.get('position_value', 0.0),
            r.get('position_delta', 0.0),
            r.get('position_vega', 0.0),
            r.get('position_theta', 0.0),
        )
        for r in greeks_results
    ]
    if option_rows:
        client.execute(
            '''
            INSERT INTO option_greeks_results (
                run_time,
                symbol,
                option_type,
                spot,
                strike,
                expiry_days,
                volatility,
                price,
                delta,
                gamma,
                vega,
                theta,
                rho,
                moneyness,
                quantity,
                position_value,
                position_delta,
                position_vega,
                position_theta
            ) VALUES
            ''',
            option_rows
        )

    print(f"  ✅ Results saved to ClickHouse at {run_time:%H:%M:%S}")
