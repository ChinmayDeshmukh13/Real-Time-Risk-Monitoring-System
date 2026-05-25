# Real-Time Market Risk Monitor
## Methodology & Technical Documentation

**Author:** [Chinmay Deshmukh]  
**Date:** May 2026  
**Version:** 1.2.22  
**Stack:** Python 3.11 · QuantLib · ClickHouse · Grafana · AWS Lambda

---

## 1. Executive Summary

This system provides real-time market risk monitoring for a 
multi-asset portfolio comprising equity positions and European 
options. It computes Value at Risk (VaR) using three independent 
methodologies, prices option Greeks via Black-Scholes using 
QuantLib, monitors risk limits automatically, and validates 
model accuracy using Kupiec's Proportion of Failures test.

**Portfolio monitored:** 5 Nifty 50 stocks + 3 European options  
**Update frequency:** Every 15 minutes (AWS Lambda)  
**Data history:** 495 trading days (May 2024 – May 2026)  
**Confidence level:** 95% (regulatory standard)

---

## 2. Data Architecture

### 2.1 Data Source
Historical OHLCV data sourced from Yahoo Finance via `yfinance` 
for 5 NSE-listed equities: RELIANCE, INFY, HDFCBANK, TCS, ICICIBANK.

### 2.2 Storage
ClickHouse columnar database — chosen for sub-millisecond query 
latency on time-series financial data. Schema optimised with 
MergeTree engine sorted by (symbol, date) for O(log n) range 
queries.

**Tables:**
- `market_ticks` — OHLCV + daily returns (2,475 rows)
- `var_results` — Risk calculation output per run
- `breach_log` — Permanent regulatory breach record

---

## 3. VaR Methodology

### 3.1 Historical Simulation
Replays 495 actual trading days on the current portfolio weights. 
VaR = return at the 5th percentile of the empirical distribution.

**Formula:** VaR = |P(α)| × Portfolio Value  
**Advantage:** No distributional assumptions  
**Result:** ₹15,945.51 (1.55% of portfolio)

### 3.2 Parametric (Normal Distribution)
Assumes returns follow a normal distribution parameterised by 
historical mean (μ) and standard deviation (σ).

**Formula:** VaR = Portfolio Value × (μ − Z_α × σ)  
**Z-score at 95%:** 1.645  
**Result:** ₹16,190.55 (1.58%)

### 3.3 Monte Carlo Simulation
Generates 10,000 random return scenarios using historical μ and σ 
as inputs. VaR = 500th worst simulated loss.

**Seed:** 42 (reproducible results)  
**Result:** ₹16,288.48 (1.59%)

### 3.4 CVaR (Expected Shortfall)
Average portfolio loss on the worst 5% of days beyond VaR threshold.

**Result:** ₹22,558.89 — 41.5% above VaR  
**Interpretation:** On the 5% worst days, losses average ₹6,613 
more than the VaR threshold predicts.

---

## 4. Options Greeks — QuantLib Implementation

European options priced using Black-Scholes-Merton via 
`ql.AnalyticEuropeanEngine`. Historical volatility calculated 
from 252-day rolling standard deviation of log returns, 
annualised by √252.

| Option | Spot | Strike | Expiry | Vol | Delta | Vega |
|---|---|---|---|---|---|---|
| RELIANCE CALL | ₹1,336 | ₹1,400 | 30d | 19.8% | 0.24 | 1.20 |
| INFY PUT | ₹1,119 | ₹1,050 | 45d | 25.2% | −0.20 | 1.09 |
| TCS CALL | ₹2,264 | ₹2,300 | 60d | 21.9% | 0.49 | 3.66 |

**Portfolio Greeks:**
- Net Delta: +9.76 (mildly long market)
- Net Theta: −₹140.74/day (daily time decay cost)
- Net Vega: +₹520.84 per 1% vol spike (long volatility)

---

## 5. Model Validation — Kupiec POF Test

### 5.1 Methodology
Rolling 252-day window backtest over 243 test days. For each day, 
VaR predicted using prior 252 days only — no look-ahead bias.

### 5.2 Results

| Metric | Value |
|---|---|
| Test period | 243 trading days |
| Expected breaches (5%) | 12.2 |
| Actual breaches | 14 |
| Observed breach rate | 5.76% |
| Kupiec LR statistic | 0.2833 |
| Critical value (95%) | 3.8415 |
| Decision | Fail to reject H₀ |
| Verdict | **PASS — Model acceptable** |
| Basel III zone | 🟡 Yellow (Investigate) |

### 5.3 Interpretation
The LR statistic of 0.28 falls well below the critical value of 
3.84, indicating no statistical reason to reject the model. The 
Yellow Basel zone (14.4 scaled breaches) reflects slightly elevated 
recent volatility — the 5 worst breach days (Days 457–491) cluster 
in the most recent trading period, suggesting a volatility regime 
shift warranting monitoring.

### 5.4 Worst Breach Days
| Day | Actual Loss | VaR Predicted | Excess |
|---|---|---|---|
| Day 457 | 3.326% | 1.371% | 1.955% |
| Day 479 | 3.116% | 1.446% | 1.670% |
| Day 491 | 2.532% | 1.504% | 1.028% |

---

## 6. Risk Limits & Alert System

Five metrics monitored continuously:

| Metric | Limit | Current | Status |
|---|---|---|---|
| VaR % | 2.00% | 1.55% | ✅ Green |
| CVaR % | 3.00% | 2.20% | ✅ Green |
| Net Delta | ±50 | 9.76 | ✅ Green |
| Net Theta | ₹500/day | ₹140/day | ✅ Green |
| Net Vega | ₹2,000 | ₹520 | ✅ Green |

Breaches logged permanently to `breach_log` table for 
regulatory reporting (Basel III compliance).

---

## 7. System Architecture

NSE Data (Yahoo Finance)
↓
data/fetcher.py  →  ClickHouse (market_ticks)
↓
engine/portfolio.py       (Portfolio weights)
engine/var_calculator.py  (3 VaR methods + CVaR)
engine/greeks_calculator.py (QuantLib Black-Scholes)
engine/alert_engine.py    (Limit monitoring)
engine/backtester.py      (Kupiec validation)
engine/result_saver.py    (Persist to DB)
↓
ClickHouse (var_results, breach_log)
↓
Grafana Dashboard (live panels, 1-min refresh)
↑
AWS Lambda + EventBridge (runs every 15 minutes)

---

## 8. Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11 | Core language |
| QuantLib | 1.42 | Options pricing |
| pandas | 3.0.3 | Data manipulation |
| numpy | 2.4.5 | Numerical computing |
| scipy | 1.17 | Statistics (Kupiec) |
| yfinance | 1.3.0 | Market data |
| ClickHouse | 26.4 | Time-series database |
| Grafana | Latest | Live dashboard |
| AWS Lambda | — | Scheduled execution |

---

## 9. Limitations & Future Work

1. **Black-Scholes assumption:** Constant volatility assumption 
   violated in practice. Next step: implement Heston stochastic 
   volatility model.

2. **American options:** Current implementation uses European 
   exercise. NSE stock options are American — binomial tree 
   engine (ql.BinomialVanillaEngine) needed.

3. **Correlation stress:** Portfolio VaR uses historical 
   correlation. During crises, correlations converge to 1.0. 
   Implement stressed correlation matrices.

4. **Intraday data:** Current system uses daily OHLCV. 
   For intraday risk, integrate NSE tick data feed.

---

*This document describes a risk monitoring system built as a 
portfolio project replicating institutional-grade methodologies 
used in investment banking risk management.*