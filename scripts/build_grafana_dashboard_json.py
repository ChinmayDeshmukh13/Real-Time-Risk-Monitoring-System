"""Build a paste-ready Grafana JSON model for the recruiter dashboard."""

from __future__ import annotations

import json
from pathlib import Path


DATASOURCE_NAME = "efmifth80lon4e"
PLUGIN_GROUP = "grafana-clickhouse-datasource"
PLUGIN_VERSION = "4.17.0"
VIZ_VERSION = "13.1.0-25668120414"

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard" / "NSE_Portfolio_Risk_Command_Center.json"


def query(raw_sql: str) -> dict:
    return {
        "kind": "PanelQuery",
        "spec": {
            "hidden": False,
            "query": {
                "datasource": {"name": DATASOURCE_NAME},
                "group": PLUGIN_GROUP,
                "kind": "DataQuery",
                "spec": {
                    "editorType": "sql",
                    "format": 1,
                    "meta": {
                        "builderOptions": {
                            "columns": [],
                            "database": "",
                            "limit": 1000,
                            "mode": "list",
                            "queryType": "table",
                            "table": "",
                        }
                    },
                    "pluginVersion": PLUGIN_VERSION,
                    "queryType": "table",
                    "rawSql": raw_sql.strip(),
                },
                "version": "v0",
            },
            "refId": "A",
        },
    }


def query_group(raw_sql: str) -> dict:
    return {
        "kind": "QueryGroup",
        "spec": {
            "queries": [query(raw_sql)],
            "queryOptions": {},
            "transformations": [],
        },
    }


def thresholds(steps: list[tuple[str, float]]) -> dict:
    return {
        "mode": "absolute",
        "steps": [{"color": color, "value": value} for color, value in steps],
    }


def timeseries_viz(unit: str | None = None, fill: int = 0) -> dict:
    defaults = {
        "color": {"mode": "palette-classic"},
        "custom": {
            "axisBorderShow": False,
            "axisCenteredZero": False,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "barWidthFactor": 0.6,
            "drawStyle": "line",
            "fillOpacity": fill,
            "gradientMode": "opacity" if fill else "none",
            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
            "insertNulls": False,
            "lineInterpolation": "linear",
            "lineWidth": 2,
            "pointSize": 4,
            "scaleDistribution": {"type": "linear"},
            "showPoints": "auto",
            "showValues": False,
            "spanNulls": False,
            "stacking": {"group": "A", "mode": "none"},
            "thresholdsStyle": {"mode": "off"},
        },
        "thresholds": thresholds([("green", 0), ("red", 80)]),
    }
    if unit:
        defaults["unit"] = unit

    return {
        "group": "timeseries",
        "kind": "VizConfig",
        "spec": {
            "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {
                "annotations": {"clustering": -1, "multiLane": False},
                "legend": {
                    "calcs": ["lastNotNull"],
                    "displayMode": "table",
                    "placement": "bottom",
                    "showLegend": True,
                },
                "tooltip": {"hideZeros": False, "mode": "multi", "sort": "desc"},
            },
        },
        "version": VIZ_VERSION,
    }


def table_viz() -> dict:
    return {
        "group": "table",
        "kind": "VizConfig",
        "spec": {
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "custom": {
                        "align": "auto",
                        "cellOptions": {"type": "auto"},
                        "footer": {"reducers": []},
                        "inspect": False,
                    },
                    "thresholds": thresholds([("green", 0), ("red", 80)]),
                },
                "overrides": [],
            },
            "options": {"cellHeight": "sm", "showHeader": True},
        },
        "version": VIZ_VERSION,
    }


def barchart_viz(unit: str | None = None) -> dict:
    defaults = {
        "color": {"mode": "palette-classic"},
        "custom": {
            "axisBorderShow": False,
            "axisCenteredZero": False,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "fillOpacity": 82,
            "gradientMode": "opacity",
            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
            "lineWidth": 1,
            "scaleDistribution": {"type": "linear"},
            "thresholdsStyle": {"mode": "off"},
        },
        "thresholds": thresholds([("green", 0), ("red", 80)]),
    }
    if unit:
        defaults["unit"] = unit

    return {
        "group": "barchart",
        "kind": "VizConfig",
        "spec": {
            "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {
                "barRadius": 0,
                "barWidth": 0.82,
                "fullHighlight": False,
                "groupWidth": 0.72,
                "legend": {
                    "calcs": [],
                    "displayMode": "list",
                    "placement": "bottom",
                    "showLegend": True,
                },
                "orientation": "auto",
                "showValue": "auto",
                "stacking": "none",
                "tooltip": {"hideZeros": False, "mode": "single", "sort": "none"},
                "xTickLabelRotation": 0,
                "xTickLabelSpacing": 0,
            },
        },
        "version": VIZ_VERSION,
    }


def gauge_viz(unit: str = "percent", max_value: float = 120) -> dict:
    return {
        "group": "gauge",
        "kind": "VizConfig",
        "spec": {
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "continuous-GrYlRd"},
                    "max": max_value,
                    "min": 0,
                    "thresholds": thresholds(
                        [("green", 0), ("#EAB839", 70), ("red", 100)]
                    ),
                    "unit": unit,
                },
                "overrides": [],
            },
            "options": {
                "barShape": "flat",
                "barWidthFactor": 0.5,
                "effects": {
                    "barGlow": False,
                    "centerGlow": False,
                    "gradient": True,
                },
                "endpointMarker": "point",
                "minVizHeight": 75,
                "minVizWidth": 75,
                "orientation": "auto",
                "reduceOptions": {
                    "calcs": ["lastNotNull"],
                    "fields": "",
                    "values": False,
                },
                "segmentCount": 1,
                "segmentSpacing": 0.3,
                "shape": "circle",
                "showThresholdLabels": True,
                "showThresholdMarkers": True,
                "sizing": "auto",
                "sparkline": True,
                "textMode": "auto",
            },
        },
        "version": VIZ_VERSION,
    }


def panel(
    panel_id: int,
    title: str,
    raw_sql: str,
    viz: dict,
    description: str = "",
) -> dict:
    return {
        "kind": "Panel",
        "spec": {
            "data": query_group(raw_sql),
            "description": description,
            "id": panel_id,
            "links": [],
            "title": title,
            "vizConfig": viz,
        },
    }


PANELS = [
    (
        1,
        "VaR Budget Used",
        """
        WITH latest AS (
            SELECT *
            FROM var_results
            ORDER BY run_time DESC
            LIMIT 1
        )
        SELECT
            round(hist_var_inr / (portfolio_value * 0.02) * 100, 2) AS value
        FROM latest
        """,
        gauge_viz(),
        "Current VaR as a percentage of the 2 percent risk budget.",
        0,
        0,
        5,
        6,
    ),
    (
        2,
        "Risk Limit Monitor",
        """
        WITH latest AS (
            SELECT *
            FROM var_results
            ORDER BY run_time DESC
            LIMIT 1
        )
        SELECT 'VaR Budget' AS metric,
               round(hist_var_inr / (portfolio_value * 0.02) * 100, 2) AS used_pct,
               round(hist_var_inr, 2) AS current_value,
               round(portfolio_value * 0.02, 2) AS limit_value,
               if(used_pct >= 100, 'BREACH', if(used_pct >= 80, 'WARNING', 'OK')) AS status
        FROM latest
        UNION ALL
        SELECT 'CVaR Budget',
               round(hist_cvar_inr / (portfolio_value * 0.03) * 100, 2) AS used_pct,
               round(hist_cvar_inr, 2),
               round(portfolio_value * 0.03, 2),
               if(used_pct >= 100, 'BREACH', if(used_pct >= 80, 'WARNING', 'OK'))
        FROM latest
        UNION ALL
        SELECT 'Delta',
               round(abs(net_delta) / 50 * 100, 2) AS used_pct,
               round(net_delta, 2),
               50,
               if(used_pct >= 100, 'BREACH', if(used_pct >= 80, 'WARNING', 'OK'))
        FROM latest
        UNION ALL
        SELECT 'Theta',
               round(abs(net_theta) / 500 * 100, 2) AS used_pct,
               round(net_theta, 2),
               500,
               if(used_pct >= 100, 'BREACH', if(used_pct >= 80, 'WARNING', 'OK'))
        FROM latest
        UNION ALL
        SELECT 'Vega',
               round(abs(net_vega) / 2000 * 100, 2) AS used_pct,
               round(net_vega, 2),
               2000,
               if(used_pct >= 100, 'BREACH', if(used_pct >= 80, 'WARNING', 'OK'))
        FROM latest
        ORDER BY used_pct DESC
        """,
        table_viz(),
        "Single screen risk controls across VaR, CVaR, Delta, Theta and Vega.",
        5,
        0,
        10,
        6,
    ),
    (
        3,
        "Data Freshness",
        """
        SELECT
            'Market Data' AS feed,
            toString(max(date)) AS latest_date,
            countDistinct(symbol) AS symbols,
            count() AS rows
        FROM market_ticks
        UNION ALL
        SELECT
            'Risk Runs',
            toString(max(run_time)),
            1,
            count()
        FROM var_results
        UNION ALL
        SELECT
            'Option Greeks',
            toString(max(run_time)),
            countDistinct(symbol),
            count()
        FROM option_greeks_results
        """,
        table_viz(),
        "Shows recruiters that the cloud pipeline is refreshing data and risk outputs.",
        15,
        0,
        9,
        6,
    ),
    (
        4,
        "Portfolio Value Replay",
        """
        WITH weights AS (
            SELECT symbol, quantity
            FROM portfolio_positions
        )
        SELECT
            date AS time,
            sum(close * quantity) AS portfolio_value
        FROM market_ticks
        INNER JOIN weights USING symbol
        GROUP BY date
        ORDER BY time
        """,
        timeseries_viz("currencyINR", fill=18),
        "Reconstructs portfolio value across the full historical window.",
        0,
        6,
        12,
        8,
    ),
    (
        5,
        "Rolling Portfolio Risk",
        """
        WITH weights AS (
            SELECT
                symbol,
                quantity,
                quantity * price AS position_value
            FROM portfolio_positions
        ),
        total AS (
            SELECT sum(position_value) AS total_value
            FROM weights
        ),
        daily AS (
            SELECT
                m.date,
                sum(m.returns * w.position_value / t.total_value) AS portfolio_return
            FROM market_ticks m
            INNER JOIN weights w ON m.symbol = w.symbol
            CROSS JOIN total t
            GROUP BY m.date
        )
        SELECT
            date AS time,
            round(stddevPop(portfolio_return) OVER (
                ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) * sqrt(252) * 100, 2) AS rolling_vol_60d_pct,
            round(1.645 * stddevPop(portfolio_return) OVER (
                ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) * 100, 2) AS rolling_var_60d_pct
        FROM daily
        ORDER BY time
        """,
        timeseries_viz("percent", fill=10),
        "60-day rolling volatility and 95 percent VaR. This creates a real curve, not a flat monitor line.",
        12,
        6,
        12,
        8,
    ),
    (
        6,
        "Sector Allocation",
        """
        SELECT
            sector,
            round(sum(quantity * price), 2) AS exposure_inr
        FROM portfolio_positions
        GROUP BY sector
        ORDER BY exposure_inr DESC
        """,
        barchart_viz("currencyINR"),
        "Exposure concentration across banking, IT, energy, consumer and pharma.",
        0,
        14,
        8,
        7,
    ),
    (
        7,
        "Top Risk Contributors",
        """
        SELECT
            p.symbol,
            p.sector,
            round(p.quantity * p.price, 2) AS exposure_inr,
            round(stddevPop(m.returns) * sqrt(252) * 100, 2) AS annual_vol_pct,
            round((p.quantity * p.price) * stddevPop(m.returns) * sqrt(252), 2) AS risk_score
        FROM portfolio_positions p
        INNER JOIN market_ticks m ON p.symbol = m.symbol
        GROUP BY p.symbol, p.sector, p.quantity, p.price
        ORDER BY risk_score DESC
        LIMIT 10
        """,
        barchart_viz("currencyINR"),
        "Ranks positions by exposure times annualized volatility.",
        8,
        14,
        8,
        7,
    ),
    (
        8,
        "Portfolio Return Distribution",
        """
        WITH weights AS (
            SELECT
                symbol,
                quantity * price AS position_value
            FROM portfolio_positions
        ),
        total AS (
            SELECT sum(position_value) AS total_value
            FROM weights
        ),
        daily AS (
            SELECT
                m.date,
                sum(m.returns * w.position_value / t.total_value) AS portfolio_return
            FROM market_ticks m
            INNER JOIN weights w ON m.symbol = w.symbol
            CROSS JOIN total t
            GROUP BY m.date
        )
        SELECT
            round(portfolio_return * 100, 1) AS daily_return_bucket_pct,
            count() AS frequency
        FROM daily
        GROUP BY daily_return_bucket_pct
        ORDER BY daily_return_bucket_pct
        """,
        barchart_viz(),
        "Shows the empirical distribution that drives Historical VaR and CVaR.",
        16,
        14,
        8,
        7,
    ),
    (
        9,
        "Stock Risk Rankings",
        """
        SELECT
            m.symbol,
            any(p.sector) AS sector,
            round(any(p.quantity * p.price), 2) AS exposure_inr,
            round(stddevPop(m.returns) * sqrt(252) * 100, 2) AS annual_vol_pct,
            round(avg(m.returns) * 252 * 100, 2) AS annual_return_pct,
            round(min(m.returns) * 100, 2) AS worst_day_pct
        FROM market_ticks m
        INNER JOIN portfolio_positions p ON m.symbol = p.symbol
        GROUP BY m.symbol
        ORDER BY annual_vol_pct DESC
        """,
        table_viz(),
        "20-stock risk table: volatility, return, exposure and worst day.",
        0,
        21,
        12,
        8,
    ),
    (
        10,
        "Latest Option Greeks",
        """
        SELECT
            symbol,
            option_type,
            strike,
            expiry_days,
            quantity,
            round(delta, 4) AS delta,
            round(gamma, 6) AS gamma,
            round(theta, 2) AS theta,
            round(vega, 2) AS vega,
            round(position_delta, 2) AS position_delta,
            round(position_theta, 2) AS position_theta,
            round(position_vega, 2) AS position_vega
        FROM option_greeks_results
        WHERE run_time = (SELECT max(run_time) FROM option_greeks_results)
        ORDER BY abs(position_vega) DESC
        """,
        table_viz(),
        "Per-option Black-Scholes Greeks from the most recent cloud run.",
        12,
        21,
        12,
        8,
    ),
    (
        11,
        "VaR vs CVaR Tail Gap",
        """
        SELECT
            run_time AS time,
            hist_var_inr AS VaR,
            hist_cvar_inr AS CVaR,
            hist_cvar_inr - hist_var_inr AS Tail_Gap
        FROM var_results
        ORDER BY time
        """,
        timeseries_viz("currencyINR", fill=20),
        "Compares the VaR threshold with expected shortfall beyond that threshold.",
        0,
        29,
        12,
        8,
    ),
    (
        12,
        "Correlation Radar",
        """
        SELECT
            a.symbol AS stock_a,
            b.symbol AS stock_b,
            round(corr(a.returns, b.returns), 3) AS correlation
        FROM market_ticks a
        INNER JOIN market_ticks b ON a.date = b.date AND a.symbol < b.symbol
        WHERE a.symbol IN (
            SELECT symbol
            FROM portfolio_positions
            ORDER BY quantity * price DESC
            LIMIT 8
        )
        AND b.symbol IN (
            SELECT symbol
            FROM portfolio_positions
            ORDER BY quantity * price DESC
            LIMIT 8
        )
        GROUP BY stock_a, stock_b
        ORDER BY abs(correlation) DESC
        LIMIT 25
        """,
        table_viz(),
        "Top pairwise correlations across the largest positions.",
        12,
        29,
        12,
        8,
    ),
    (
        13,
        "Breach Log",
        """
        SELECT
            breach_time,
            method,
            round(var_amount, 2) AS current_value,
            round(limit_amount, 2) AS limit_value,
            round(breach_pct * 100, 1) AS pct_of_limit,
            severity
        FROM breach_log
        ORDER BY breach_time DESC
        LIMIT 30
        """,
        table_viz(),
        "Permanent regulatory-style event log for limit breaches.",
        0,
        37,
        24,
        7,
    ),
]


def build() -> dict:
    elements = {}
    layout_items = []

    for panel_id, title, sql, viz, description, x, y, width, height in PANELS:
        name = f"panel-{panel_id}"
        elements[name] = panel(panel_id, title, sql, viz, description)
        layout_items.append(
            {
                "kind": "GridLayoutItem",
                "spec": {
                    "element": {"kind": "ElementReference", "name": name},
                    "height": height,
                    "width": width,
                    "x": x,
                    "y": y,
                },
            }
        )

    return {
        "annotations": [
            {
                "kind": "AnnotationQuery",
                "spec": {
                    "builtIn": True,
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "query": {
                        "datasource": {"name": "-- Grafana --"},
                        "group": "grafana",
                        "kind": "DataQuery",
                        "spec": {},
                        "version": "v0",
                    },
                },
            }
        ],
        "cursorSync": "Off",
        "editable": True,
        "elements": elements,
        "layout": {"kind": "GridLayout", "spec": {"items": layout_items}},
        "links": [],
        "liveNow": False,
        "preferences": {"layout": {"kind": "GridLayout", "spec": {"items": []}}},
        "preload": False,
        "tags": ["risk", "portfolio", "clickhouse", "grafana-cloud"],
        "timeSettings": {
            "autoRefresh": "1m",
            "autoRefreshIntervals": [
                "5s",
                "10s",
                "30s",
                "1m",
                "5m",
                "15m",
                "30m",
                "1h",
                "2h",
                "1d",
            ],
            "fiscalYearStartMonth": 0,
            "from": "now-1y",
            "hideTimepicker": False,
            "timezone": "browser",
            "to": "now",
        },
        "title": "NSE Portfolio Risk Command Center",
        "variables": [],
    }


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    dashboard = build()
    OUTPUT.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
