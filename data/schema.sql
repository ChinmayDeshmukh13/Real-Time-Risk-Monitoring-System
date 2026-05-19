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