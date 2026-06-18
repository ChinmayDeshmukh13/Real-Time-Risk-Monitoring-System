from datetime import datetime
from engine.config import get_client
from engine.db_schema import ensure_tables


def save_run_results(
    var_report: dict,
    greeks_results: list,
    portfolio_value: float
):
    conn = get_client()
    ensure_tables(conn)

    cur = conn.cursor()

    run_time = datetime.now()

    hist = var_report["historical"]
    param = var_report["parametric"]
    mc = var_report["monte_carlo"]

    portfolio_value = float(portfolio_value)

    net_delta = float(
        sum(float(r.get("position_delta", 0.0))
            for r in greeks_results)
    )

    net_theta = float(
        sum(float(r.get("position_theta", 0.0))
            for r in greeks_results)
    )

    net_vega = float(
        sum(float(r.get("position_vega", 0.0))
            for r in greeks_results)
    )

    hist_var_inr = float(hist["var_inr"])
    hist_var_pct = float(hist["var_pct"])
    hist_cvar_inr = float(hist["cvar_inr"])

    param_var_inr = float(param["var_inr"])
    mc_var_inr = float(mc["var_inr"])

    cur.execute(
        """
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
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            run_time,
            portfolio_value,
            hist_var_inr,
            hist_var_pct,
            param_var_inr,
            mc_var_inr,
            hist_cvar_inr,
            net_delta,
            net_theta,
            net_vega,
        ),
    )

    for r in greeks_results:

        cur.execute(
            """
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
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                run_time,
                str(r["symbol"]),
                str(r["option_type"]),
                float(r["spot"]),
                float(r["strike"]),
                int(r["expiry_days"]),
                float(r["volatility"]),
                float(r["price"]),
                float(r["delta"]),
                float(r["gamma"]),
                float(r["vega"]),
                float(r["theta"]),
                float(r.get("rho", 0.0)),
                str(r["moneyness"]),
                int(r.get("quantity", 1)),
                float(r.get("position_value", 0.0)),
                float(r.get("position_delta", 0.0)),
                float(r.get("position_vega", 0.0)),
                float(r.get("position_theta", 0.0)),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Results saved to Supabase at {run_time:%H:%M:%S}")


def save_greeks(greeks_results: list):

    conn = get_client()
    cur = conn.cursor()

    now = datetime.now()

    for r in greeks_results:

        cur.execute(
            """
            INSERT INTO greeks_log (
                run_time,
                symbol,
                option_type,
                strike,
                expiry_days,
                spot,
                price,
                delta,
                gamma,
                theta,
                vega,
                moneyness
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                now,
                str(r["symbol"]),
                str(r["option_type"]),
                float(r["strike"]),
                int(r["expiry_days"]),
                float(r["spot"]),
                float(r["price"]),
                float(r["delta"]),
                float(r["gamma"]),
                float(r["theta"]),
                float(r["vega"]),
                str(r["moneyness"]),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Greeks saved — {len(greeks_results)} options logged")