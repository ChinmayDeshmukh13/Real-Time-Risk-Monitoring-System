# End-to-End Verification

Use this checklist to confirm the full chain works:

1. yfinance can download NSE prices.
2. Cleaned OHLCV and returns are stored in ClickHouse `market_ticks`.
3. `main.py` reads `market_ticks`, calculates VaR and Greeks, and writes `var_results`.
4. Grafana reads ClickHouse tables and shows fresh data.

## One-command health check

From the project root:

```powershell
.\venv\Scripts\python.exe scripts\health_check.py
```

Expected result: all core checks should be `PASS`. Grafana is `SKIP` unless these optional variables are set in `.env`:

```text
GRAFANA_URL=https://your-grafana-host
GRAFANA_API_KEY=your-service-account-token
GRAFANA_DASHBOARD_UID=optional-dashboard-uid
```

Useful variants:

```powershell
.\venv\Scripts\python.exe scripts\health_check.py --skip-yfinance
.\venv\Scripts\python.exe scripts\health_check.py --skip-grafana
.\venv\Scripts\python.exe scripts\health_check.py --yfinance-sample-size 20
```

## Manual Pipeline Order

Run these commands in this order when you want a full smoke test:

```powershell
.\venv\Scripts\python.exe data\loader.py
.\venv\Scripts\python.exe main.py
.\venv\Scripts\python.exe scripts\health_check.py --skip-yfinance
```

`data\loader.py` refreshes `market_ticks`. `main.py` calculates risk and saves one row to `var_results`. The health check confirms the database has fresh market data and saved risk output.

## Grafana Query Checks

Run these in Grafana Explore with your ClickHouse datasource.

Fresh market data:

```sql
SELECT
    max(date) AS latest_market_date,
    count() AS rows,
    uniqExact(symbol) AS symbols
FROM market_ticks;
```

Rows per stock:

```sql
SELECT
    symbol,
    min(date) AS first_date,
    max(date) AS latest_date,
    count() AS rows
FROM market_ticks
GROUP BY symbol
ORDER BY symbol;
```

Latest VaR runs:

```sql
SELECT
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
FROM var_results
ORDER BY run_time DESC
LIMIT 20;
```

Duplicate market rows:

```sql
SELECT
    symbol,
    date,
    count() AS rows
FROM market_ticks
GROUP BY symbol, date
HAVING rows > 1
ORDER BY rows DESC;
```

If the first two queries are fresh and complete, yfinance to ClickHouse is working. If `var_results` has a recent `run_time`, the VaR engine and result saving are working. If Grafana panels use these same queries and show the latest dates, the dashboard path is working.
