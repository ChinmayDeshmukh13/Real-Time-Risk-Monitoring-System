# 📊 NSE Portfolio Risk Command Center

[![Pipeline Status](https://github.com/ChinmayDeshmukh13/Real-Time-Risk-Monitoring-ystem/actions/workflows/risk_pipeline.yml/badge.svg)](https://github.com/ChinmayDeshmukh13/Real-Time-Risk-Monitoring-ystem/actions)

> Live institutional-grade risk monitoring for 20 Nifty 50 stocks

## 🔴 Live Dashboard
**[→ Open Live Dashboard](https://chinmaydeshmukh13.grafana.net/public-dashboards/10e2e3b4ac7a4403aa3ab91b4df4a67d)**

## What It Shows
- Real-time VaR (3 methods: Historical, Parametric, Monte Carlo)
- CVaR / Expected Shortfall
- Option Greeks via QuantLib Black-Scholes
- Kupiec POF backtesting (Basel III validation)
- Sector allocation & risk contribution
- Return distribution with fat tails
- Automated breach detection & alert logging (JSON + ClickHouse `breach_log`)

## Stack
Python · QuantLib · ClickHouse Cloud · Grafana Cloud · GitHub Actions

## Auto-Updates
Pipeline runs every 15 minutes during NSE market hours
via GitHub Actions cron scheduling
