# Recruiter Dashboard Upgrade Pack

Use these panels on the same Grafana dashboard you already shared. Edit the existing dashboard instead of creating a new one, so the public URL stays unchanged.

## Recommended Layout

Row 1: Four Stat panels
- Portfolio Value
- 95% VaR
- VaR Budget Used
- Data Freshness

Row 2: Main story
- Portfolio Value Replay, last 2-3 years
- Rolling Portfolio VaR and Volatility

Row 3: What drives risk
- Sector Allocation
- Top Risk Contributors
- Stock Risk Rankings

Row 4: Model explanation
- Portfolio Return Distribution
- Correlation Heatmap or Correlation Table
- VaR vs CVaR Tail Gap

Row 5: Options and controls
- Latest Option Greeks
- Risk Limit Monitor
- Breach Log

## Panel Queries

### Portfolio Value Stat

```sql
SELECT
    run_time AS time,
    portfolio_value
FROM var_results
ORDER BY run_time DESC
LIMIT 1;
```

Visualization: Stat. Unit: Currency INR.

### 95% VaR Stat

```sql
SELECT
    run_time AS time,
    hist_var_inr
FROM var_results
ORDER BY run_time DESC
LIMIT 1;
```

Visualization: Stat. Unit: Currency INR.

### VaR Budget Used

```sql
SELECT
    run_time AS time,
    round(hist_var_pct / 0.02 * 100, 2) AS var_budget_used_pct
FROM var_results
ORDER BY run_time DESC
LIMIT 1;
```

Visualization: Gauge. Unit: percent. Thresholds: green 0, yellow 70, red 100.

### Data Freshness

```sql
SELECT
    max(date) AS latest_market_date,
    uniqExact(symbol) AS symbols,
    count() AS rows
FROM market_ticks;
```

Visualization: Stat or Table. This proves the cloud data is fresh.

### Portfolio Value Replay

```sql
SELECT
    toDateTime(mt.date) AS time,
    round(sum(mt.close * pp.quantity), 2) AS portfolio_value
FROM market_ticks mt
INNER JOIN portfolio_positions pp ON mt.symbol = pp.symbol
GROUP BY mt.date
ORDER BY time;
```

Visualization: Time series. This is more impressive than repeated `var_results` because it replays the portfolio through historical market moves.

### Rolling Portfolio VaR and Volatility

```sql
WITH
latest_prices AS (
    SELECT symbol, argMax(close, date) AS latest_close
    FROM market_ticks
    GROUP BY symbol
),
weights AS (
    SELECT
        pp.symbol,
        pp.quantity * lp.latest_close
            / sum(pp.quantity * lp.latest_close) OVER () AS weight
    FROM portfolio_positions pp
    INNER JOIN latest_prices lp ON pp.symbol = lp.symbol
),
portfolio_returns AS (
    SELECT
        mt.date,
        sum(mt.returns * w.weight) AS portfolio_return
    FROM market_ticks mt
    INNER JOIN weights w ON mt.symbol = w.symbol
    GROUP BY mt.date
)
SELECT
    toDateTime(date) AS time,
    round(stddevPop(portfolio_return)
        OVER (ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
        * sqrt(252) * 100, 2) AS rolling_vol_60d_pct,
    round(abs(quantileExact(0.05)(portfolio_return)
        OVER (ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW))
        * 100, 2) AS rolling_var_60d_pct
FROM portfolio_returns
ORDER BY time;
```

Visualization: Time series. This chart should move and look like a real risk monitor.

### Sector Allocation

```sql
WITH
latest_prices AS (
    SELECT symbol, argMax(close, date) AS latest_close
    FROM market_ticks
    GROUP BY symbol
),
sector_values AS (
    SELECT
        pp.sector,
        sum(pp.quantity * lp.latest_close) AS sector_value
    FROM portfolio_positions pp
    INNER JOIN latest_prices lp ON pp.symbol = lp.symbol
    GROUP BY pp.sector
)
SELECT
    sector,
    round(sector_value, 2) AS value_inr,
    round(sector_value / sum(sector_value) OVER () * 100, 2) AS weight_pct
FROM sector_values
ORDER BY value_inr DESC;
```

Visualization: Pie chart or Bar gauge. This tells the concentration story immediately.

### Top Risk Contributors

```sql
WITH
latest_prices AS (
    SELECT symbol, argMax(close, date) AS latest_close
    FROM market_ticks
    GROUP BY symbol
),
stock_stats AS (
    SELECT
        symbol,
        stddevPop(returns) * sqrt(252) AS annual_vol
    FROM market_ticks
    GROUP BY symbol
)
SELECT
    pp.symbol,
    pp.sector,
    round(pp.quantity * lp.latest_close, 2) AS position_value,
    round(ss.annual_vol * 100, 2) AS annual_vol_pct,
    round(pp.quantity * lp.latest_close * ss.annual_vol, 2) AS approx_risk_inr
FROM portfolio_positions pp
INNER JOIN latest_prices lp ON pp.symbol = lp.symbol
INNER JOIN stock_stats ss ON pp.symbol = ss.symbol
ORDER BY approx_risk_inr DESC
LIMIT 10;
```

Visualization: Horizontal bar chart. Use `approx_risk_inr` as the bar value.

### Stock Risk Rankings

```sql
WITH
latest_prices AS (
    SELECT symbol, argMax(close, date) AS latest_close
    FROM market_ticks
    GROUP BY symbol
)
SELECT
    pp.symbol,
    pp.sector,
    pp.quantity,
    round(lp.latest_close, 2) AS latest_close,
    round(pp.quantity * lp.latest_close, 2) AS position_value,
    round(stddevPop(mt.returns) * sqrt(252) * 100, 2) AS annual_vol_pct,
    round(avg(mt.returns) * 252 * 100, 2) AS annual_return_pct,
    round(min(mt.returns) * 100, 2) AS worst_day_pct
FROM market_ticks mt
INNER JOIN portfolio_positions pp ON mt.symbol = pp.symbol
INNER JOIN latest_prices lp ON mt.symbol = lp.symbol
GROUP BY
    pp.symbol,
    pp.sector,
    pp.quantity,
    lp.latest_close
ORDER BY annual_vol_pct DESC;
```

Visualization: Table. Add conditional coloring to annual volatility and worst day.

### Portfolio Return Distribution

```sql
WITH
latest_prices AS (
    SELECT symbol, argMax(close, date) AS latest_close
    FROM market_ticks
    GROUP BY symbol
),
weights AS (
    SELECT
        pp.symbol,
        pp.quantity * lp.latest_close
            / sum(pp.quantity * lp.latest_close) OVER () AS weight
    FROM portfolio_positions pp
    INNER JOIN latest_prices lp ON pp.symbol = lp.symbol
),
portfolio_returns AS (
    SELECT
        mt.date,
        sum(mt.returns * w.weight) AS portfolio_return
    FROM market_ticks mt
    INNER JOIN weights w ON mt.symbol = w.symbol
    GROUP BY mt.date
)
SELECT
    round(portfolio_return * 100, 1) AS return_bucket_pct,
    count() AS days
FROM portfolio_returns
GROUP BY return_bucket_pct
ORDER BY return_bucket_pct;
```

Visualization: Bar chart. This explains why VaR exists.

### Correlation Table

```sql
SELECT
    a.symbol AS stock_a,
    b.symbol AS stock_b,
    round(corr(a.returns, b.returns), 2) AS correlation
FROM market_ticks a
INNER JOIN market_ticks b
    ON a.date = b.date
   AND a.symbol < b.symbol
GROUP BY a.symbol, b.symbol
ORDER BY abs(correlation) DESC
LIMIT 30;
```

Visualization: Table, or Heatmap if your Grafana plugin maps `stock_a`, `stock_b`, `correlation`.

### Latest Option Greeks

```sql
SELECT
    run_time,
    symbol,
    option_type,
    strike,
    expiry_days,
    round(price, 2) AS price,
    round(delta, 4) AS delta,
    round(gamma, 6) AS gamma,
    round(vega, 4) AS vega,
    round(theta, 4) AS theta,
    round(position_delta, 2) AS position_delta,
    round(position_theta, 2) AS position_theta,
    round(position_vega, 2) AS position_vega,
    moneyness
FROM option_greeks_results
WHERE run_time = (SELECT max(run_time) FROM option_greeks_results)
ORDER BY symbol;
```

Visualization: Table. This fixes the boring aggregate Greeks panel.

### Risk Limit Monitor

```sql
WITH latest AS (
    SELECT *
    FROM var_results
    ORDER BY run_time DESC
    LIMIT 1
)
SELECT
    metric,
    used_pct,
    current_value,
    limit_value,
    if(used_pct >= 100, 'BREACH', if(used_pct >= 80, 'WARNING', 'OK')) AS status
FROM (
    SELECT 'VaR Budget' AS metric,
           round(hist_var_pct / 0.02 * 100, 2) AS used_pct,
           round(hist_var_inr, 2) AS current_value,
           round(portfolio_value * 0.02, 2) AS limit_value
    FROM latest
    UNION ALL
    SELECT 'CVaR Budget',
           round(hist_cvar_inr / (portfolio_value * 0.03) * 100, 2),
           round(hist_cvar_inr, 2),
           round(portfolio_value * 0.03, 2)
    FROM latest
    UNION ALL
    SELECT 'Delta',
           round(abs(net_delta) / 50 * 100, 2),
           round(net_delta, 2),
           50
    FROM latest
    UNION ALL
    SELECT 'Theta',
           round(abs(net_theta) / 500 * 100, 2),
           round(net_theta, 2),
           500
    FROM latest
    UNION ALL
    SELECT 'Vega',
           round(abs(net_vega) / 2000 * 100, 2),
           round(net_vega, 2),
           2000
    FROM latest
);
```

Visualization: Table or Bar gauge. Use this instead of a huge empty breach-log panel.

### Breach Log

```sql
SELECT
    breach_time,
    method,
    round(var_amount, 2) AS breach_amount,
    round(limit_amount, 2) AS limit_amount,
    round(breach_pct * 100, 2) AS pct_of_limit,
    severity
FROM breach_log
ORDER BY breach_time DESC
LIMIT 20;
```

Visualization: Table. Keep it in the bottom row; empty breach log is a good sign, not the hero panel.

## Visual Settings That Matter

- Rename dashboard title to `NSE Portfolio Risk Command Center`.
- Set dashboard time range to `Last 90 days` for historical panels and keep auto-refresh at `1m`.
- Use Stat panels for KPIs, Time series for portfolio replay and rolling risk, Bar gauge for risk contributors, Table for holdings and Greeks.
- Put the VaR gauge beside `Risk Limit Monitor`, not alone in a large empty row.
- Add a text panel at the top: `20-stock NSE portfolio, 5 option overlays, ClickHouse Cloud, GitHub Actions, Grafana Cloud`.
