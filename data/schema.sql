-- data/schema.sql
-- This file defines the structure of our market data table in ClickHouse

-- Drop table if it already exists (useful when we want to start fresh)
DROP TABLE IF EXISTS market_ticks;

-- Create the main table
CREATE TABLE market_ticks (
    symbol      String,
    date        Date,
    open        Float64,
    high        Float64,
    low         Float64,
    close       Float64,
    volume      UInt64,
    returns     Float64
)
ENGINE = MergeTree()
ORDER BY (symbol, date);


-- Risk run output table used by Grafana dashboard panels
CREATE TABLE IF NOT EXISTS var_results (
    run_time        DateTime,
    portfolio_value Float64,
    hist_var_inr    Float64,
    hist_var_pct    Float64,
    param_var_inr   Float64,
    mc_var_inr      Float64,
    hist_cvar_inr   Float64,
    net_delta       Float64,
    net_theta       Float64,
    net_vega        Float64
)
ENGINE = MergeTree()
ORDER BY run_time;


-- Static portfolio metadata for richer Grafana panels
CREATE TABLE IF NOT EXISTS portfolio_positions (
    symbol   String,
    sector   String,
    quantity Float64
)
ENGINE = MergeTree()
ORDER BY symbol;


-- Option-level Greeks output used by the recruiter dashboard
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
ORDER BY (run_time, symbol, option_type, strike);


-- Breach log table — stores every VaR limit breach permanently
CREATE TABLE IF NOT EXISTS breach_log (
    breach_time     DateTime,
    method          String,
    var_amount      Float64,
    limit_amount    Float64,
    breach_pct      Float64,
    portfolio_value Float64,
    severity        String
)
ENGINE = MergeTree()
ORDER BY breach_time;
