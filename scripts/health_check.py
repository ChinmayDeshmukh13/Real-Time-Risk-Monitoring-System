from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")


@dataclass
class Result:
    name: str
    status: str
    detail: str


class CheckFailure(Exception):
    pass


def pass_result(name: str, detail: str) -> Result:
    return Result(name, "PASS", detail)


def warn_result(name: str, detail: str) -> Result:
    return Result(name, "WARN", detail)


def skip_result(name: str, detail: str) -> Result:
    return Result(name, "SKIP", detail)


def fail(name: str, detail: str) -> None:
    raise CheckFailure(f"{name}: {detail}")


def run_check(name: str, check: Callable[[], Result]) -> Result:
    try:
        return check()
    except CheckFailure as exc:
        return Result(name, "FAIL", str(exc).split(": ", 1)[-1])
    except Exception as exc:
        return Result(name, "FAIL", f"{type(exc).__name__}: {exc}")


def check_environment() -> Result:
    required = [
        "CLICKHOUSE_HOST",
        "CLICKHOUSE_PORT",
        "CLICKHOUSE_USER",
        "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_SECURE",
    ]
    missing = [key for key in required if os.getenv(key) in (None, "")]
    if missing:
        fail("Environment", "missing " + ", ".join(missing))

    secure = os.getenv("CLICKHOUSE_SECURE", "").lower()
    if secure not in {"true", "false"}:
        fail("Environment", "CLICKHOUSE_SECURE must be true or false")

    return pass_result(
        "Environment",
        f"ClickHouse env is set for host {os.getenv('CLICKHOUSE_HOST')}",
    )


def expected_symbols() -> list[str]:
    from data.fetcher import STOCKS

    return [symbol.replace(".NS", "") for symbol in STOCKS]


def check_yfinance(sample_size: int) -> Result:
    import yfinance as yf
    from data.fetcher import STOCKS

    symbols = STOCKS[:sample_size]
    failures: list[str] = []
    latest_dates: list[date] = []

    for symbol in symbols:
        df = yf.Ticker(symbol).history(period="10d", auto_adjust=True)
        if df.empty:
            failures.append(f"{symbol}: no rows")
            continue
        if "Close" not in df.columns:
            failures.append(f"{symbol}: missing Close column")
            continue
        if float(df["Close"].iloc[-1]) <= 0:
            failures.append(f"{symbol}: latest close is not positive")
            continue
        latest_dates.append(df.index.max().date())

    if failures:
        fail("yfinance", "; ".join(failures))

    latest = max(latest_dates).isoformat() if latest_dates else "unknown"
    return pass_result(
        "yfinance",
        f"downloaded {len(symbols)} sample symbols; latest date {latest}",
    )


def client():
    from engine.config import get_client

    return get_client()


def table_exists(ch_client, table: str) -> bool:
    rows = ch_client.execute(
        """
        SELECT count()
        FROM system.tables
        WHERE database = currentDatabase()
          AND name = %(table)s
        """,
        {"table": table},
    )
    return int(rows[0][0]) > 0


def check_clickhouse_connection() -> Result:
    ch_client = client()
    rows = ch_client.execute("SELECT 1")
    if rows != [(1,)]:
        fail("ClickHouse connection", f"unexpected SELECT 1 result: {rows}")
    database = ch_client.execute("SELECT currentDatabase()")[0][0]
    return pass_result("ClickHouse connection", f"connected to database {database}")


def check_tables() -> Result:
    ch_client = client()
    required = ["market_ticks", "var_results", "breach_log"]
    missing = [table for table in required if not table_exists(ch_client, table)]
    if missing:
        fail("ClickHouse tables", "missing " + ", ".join(missing))
    return pass_result("ClickHouse tables", "market_ticks, var_results, breach_log exist")


def check_market_data(max_age_days: int) -> Result:
    from engine.config import Config

    ch_client = client()
    if not table_exists(ch_client, "market_ticks"):
        fail("market_ticks data", "market_ticks table is missing")

    rows = ch_client.execute(
        """
        SELECT
            symbol,
            count() AS rows,
            min(date) AS first_date,
            max(date) AS latest_date,
            countIf(close <= 0) AS bad_close,
            countIf(isNaN(returns)) AS bad_returns
        FROM market_ticks
        GROUP BY symbol
        ORDER BY symbol
        """
    )
    if not rows:
        fail("market_ticks data", "table has zero rows")

    found = {row[0] for row in rows}
    missing_symbols = sorted(set(expected_symbols()) - found)
    if missing_symbols:
        fail("market_ticks data", "missing symbols " + ", ".join(missing_symbols))

    min_required_rows = Config.VAR_WINDOW_DAYS + 1
    shallow = [f"{row[0]}={row[1]}" for row in rows if int(row[1]) < min_required_rows]
    if shallow:
        fail(
            "market_ticks data",
            f"not enough rows for {Config.VAR_WINDOW_DAYS}-day VaR: "
            + ", ".join(shallow),
        )

    bad_values = [
        f"{row[0]} close={row[4]} returns={row[5]}"
        for row in rows
        if int(row[4]) > 0 or int(row[5]) > 0
    ]
    if bad_values:
        fail("market_ticks data", "bad values: " + "; ".join(bad_values))

    latest_date = max(row[3] for row in rows)
    if latest_date < date.today() - timedelta(days=max_age_days):
        fail(
            "market_ticks data",
            f"latest date {latest_date} is older than {max_age_days} days",
        )

    duplicates = ch_client.execute(
        """
        SELECT count()
        FROM (
            SELECT symbol, date, count() AS c
            FROM market_ticks
            GROUP BY symbol, date
            HAVING c > 1
        )
        """
    )[0][0]
    if int(duplicates) > 0:
        fail("market_ticks data", f"{duplicates} duplicate symbol/date rows")

    return pass_result(
        "market_ticks data",
        f"{len(rows)} symbols; latest date {latest_date}; no duplicate dates",
    )


def check_var_results(max_age_days: int) -> Result:
    ch_client = client()
    if not table_exists(ch_client, "var_results"):
        fail("var_results data", "var_results table is missing")

    rows = ch_client.execute(
        """
        SELECT
            count(),
            max(run_time),
            countIf(portfolio_value <= 0),
            countIf(hist_var_inr < 0 OR hist_var_pct < 0)
        FROM var_results
        """
    )
    count, latest_run, bad_portfolio, bad_var = rows[0]

    if int(count) == 0:
        fail("var_results data", "table has zero rows; run python main.py")
    if int(bad_portfolio) > 0 or int(bad_var) > 0:
        fail(
            "var_results data",
            f"bad rows: portfolio={bad_portfolio}, var={bad_var}",
        )

    if isinstance(latest_run, datetime):
        latest_date = latest_run.date()
        if latest_date < date.today() - timedelta(days=max_age_days):
            fail(
                "var_results data",
                f"latest run {latest_run} is older than {max_age_days} days",
            )

    return pass_result("var_results data", f"{count} saved risk runs; latest {latest_run}")


def check_grafana() -> Result:
    grafana_url = os.getenv("GRAFANA_URL")
    api_key = os.getenv("GRAFANA_API_KEY")
    dashboard_uid = os.getenv("GRAFANA_DASHBOARD_UID")

    if not grafana_url or not api_key:
        return skip_result(
            "Grafana API",
            "set GRAFANA_URL and GRAFANA_API_KEY to verify Grafana automatically",
        )

    base_url = grafana_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}

    def get_json(path: str) -> dict:
        request = Request(base_url + path, headers=headers)
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        health = get_json("/api/health")
        if health.get("database") not in {None, "ok"}:
            fail("Grafana API", f"Grafana health is not ok: {health}")

        datasource_count = "unknown"
        try:
            datasources = get_json("/api/datasources")
            datasource_count = str(len(datasources))
            clickhouse_sources = [
                ds.get("name", "")
                for ds in datasources
                if "clickhouse" in str(ds.get("type", "")).lower()
            ]
            if not clickhouse_sources:
                return warn_result(
                    "Grafana API",
                    f"connected, but no ClickHouse datasource found among {datasource_count}",
                )
        except Exception:
            pass

        if dashboard_uid:
            dashboard = get_json(f"/api/dashboards/uid/{dashboard_uid}")
            title = dashboard.get("dashboard", {}).get("title", dashboard_uid)
            return pass_result("Grafana API", f"dashboard reachable: {title}")

        return pass_result(
            "Grafana API",
            f"Grafana reachable; datasources visible: {datasource_count}",
        )
    except HTTPError as exc:
        fail("Grafana API", f"HTTP {exc.code}: {exc.reason}")
    except URLError as exc:
        fail("Grafana API", f"connection failed: {exc.reason}")


def print_results(results: list[Result]) -> None:
    width = max(len(result.name) for result in results)
    print("\nRisk monitor health check")
    print("=" * 80)
    for result in results:
        print(f"{result.status:<5} {result.name:<{width}}  {result.detail}")
    print("=" * 80)
    failures = [result for result in results if result.status == "FAIL"]
    warnings = [result for result in results if result.status == "WARN"]
    skipped = [result for result in results if result.status == "SKIP"]
    print(
        f"Summary: {len(failures)} failed, "
        f"{len(warnings)} warnings, {len(skipped)} skipped"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify yfinance, ClickHouse, saved VaR results, and Grafana wiring."
    )
    parser.add_argument("--skip-yfinance", action="store_true")
    parser.add_argument("--skip-clickhouse", action="store_true")
    parser.add_argument("--skip-grafana", action="store_true")
    parser.add_argument("--yfinance-sample-size", type=int, default=3)
    parser.add_argument("--market-max-age-days", type=int, default=10)
    parser.add_argument("--results-max-age-days", type=int, default=3)
    args = parser.parse_args()

    checks: list[tuple[str, Callable[[], Result]]] = [
        ("Environment", check_environment),
    ]

    if args.skip_yfinance:
        checks.append(
            (
                "yfinance",
                lambda: skip_result("yfinance", "skipped by command-line flag"),
            )
        )
    else:
        checks.append(
            (
                "yfinance",
                lambda: check_yfinance(args.yfinance_sample_size),
            )
        )

    if args.skip_clickhouse:
        checks.extend(
            [
                (
                    "ClickHouse connection",
                    lambda: skip_result(
                        "ClickHouse connection", "skipped by command-line flag"
                    ),
                ),
                (
                    "ClickHouse tables",
                    lambda: skip_result("ClickHouse tables", "skipped by command-line flag"),
                ),
                (
                    "market_ticks data",
                    lambda: skip_result("market_ticks data", "skipped by command-line flag"),
                ),
                (
                    "var_results data",
                    lambda: skip_result("var_results data", "skipped by command-line flag"),
                ),
            ]
        )
    else:
        checks.extend(
            [
                ("ClickHouse connection", check_clickhouse_connection),
                ("ClickHouse tables", check_tables),
                (
                    "market_ticks data",
                    lambda: check_market_data(args.market_max_age_days),
                ),
                (
                    "var_results data",
                    lambda: check_var_results(args.results_max_age_days),
                ),
            ]
        )

    if args.skip_grafana:
        checks.append(
            (
                "Grafana API",
                lambda: skip_result("Grafana API", "skipped by command-line flag"),
            )
        )
    else:
        checks.append(("Grafana API", check_grafana))

    results = [run_check(name, check) for name, check in checks]
    print_results(results)
    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
