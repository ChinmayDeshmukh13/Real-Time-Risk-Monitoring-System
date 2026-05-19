# engine/result_saver.py
from datetime import datetime
from engine.config import get_client


def save_run_results(var_report: dict,
                     greeks_results: list,
                     portfolio_value: float):
    """Saves one complete risk run to var_results table."""
    client = get_client()

    hist  = var_report['historical']
    param = var_report['parametric']
    mc    = var_report['monte_carlo']

    net_delta = sum(r['position_delta'] for r in greeks_results)
    net_theta = sum(r['position_theta'] for r in greeks_results)
    net_vega  = sum(r['position_vega']  for r in greeks_results)

    row = [(
        datetime.now(),
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

    client.execute('INSERT INTO var_results VALUES', row)
    print(f"  ✅ Results saved to ClickHouse at {datetime.now():%H:%M:%S}")