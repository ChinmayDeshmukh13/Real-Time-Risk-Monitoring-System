from engine.config import get_client


def ensure_tables(client=None):
    client = client or get_client()

    cur = client.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_ticks (
        symbol VARCHAR(20),
        date DATE,
        open DOUBLE PRECISION,
        high DOUBLE PRECISION,
        low DOUBLE PRECISION,
        close DOUBLE PRECISION,
        volume BIGINT,
        returns DOUBLE PRECISION
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS var_results (
        run_time TIMESTAMP,
        portfolio_value DOUBLE PRECISION,
        hist_var_inr DOUBLE PRECISION,
        hist_var_pct DOUBLE PRECISION,
        param_var_inr DOUBLE PRECISION,
        mc_var_inr DOUBLE PRECISION,
        hist_cvar_inr DOUBLE PRECISION,
        net_delta DOUBLE PRECISION,
        net_theta DOUBLE PRECISION,
        net_vega DOUBLE PRECISION
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS breach_log (
        breach_time TIMESTAMP,
        method VARCHAR(50),
        var_amount DOUBLE PRECISION,
        limit_amount DOUBLE PRECISION,
        breach_pct DOUBLE PRECISION,
        portfolio_value DOUBLE PRECISION,
        severity VARCHAR(20)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS greeks_log (
        run_time TIMESTAMP,
        symbol VARCHAR(20),
        option_type VARCHAR(10),
        strike DOUBLE PRECISION,
        expiry_days INTEGER,
        spot DOUBLE PRECISION,
        price DOUBLE PRECISION,
        delta DOUBLE PRECISION,
        gamma DOUBLE PRECISION,
        theta DOUBLE PRECISION,
        vega DOUBLE PRECISION,
        moneyness VARCHAR(20)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_greeks_results (
        run_time TIMESTAMP,
        symbol VARCHAR(20),
        option_type VARCHAR(10),
        spot DOUBLE PRECISION,
        strike DOUBLE PRECISION,
        expiry_days INTEGER,
        volatility DOUBLE PRECISION,
        price DOUBLE PRECISION,
        delta DOUBLE PRECISION,
        gamma DOUBLE PRECISION,
        vega DOUBLE PRECISION,
        theta DOUBLE PRECISION,
        rho DOUBLE PRECISION,
        moneyness VARCHAR(20),
        quantity DOUBLE PRECISION,
        position_value DOUBLE PRECISION,
        position_delta DOUBLE PRECISION,
        position_vega DOUBLE PRECISION,
        position_theta DOUBLE PRECISION
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_positions (
        symbol VARCHAR(20),
        sector VARCHAR(50),
        quantity DOUBLE PRECISION
    )
    """)

    client.commit()
    cur.close()