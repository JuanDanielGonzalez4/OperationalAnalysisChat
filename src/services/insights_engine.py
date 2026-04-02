"""Deterministic insights detectors — pure Pandas/NumPy, no LLM."""

from itertools import combinations

import numpy as np
import pandas as pd

METRIC_WEEK_COLS = [
    "L8W_ROLL",
    "L7W_ROLL",
    "L6W_ROLL",
    "L5W_ROLL",
    "L4W_ROLL",
    "L3W_ROLL",
    "L2W_ROLL",
    "L1W_ROLL",
    "L0W_ROLL",
]
ORDER_WEEK_COLS = [
    "L8W",
    "L7W",
    "L6W",
    "L5W",
    "L4W",
    "L3W",
    "L2W",
    "L1W",
    "L0W",
]
WEEK_LABELS = ["L8W", "L7W", "L6W", "L5W", "L4W", "L3W", "L2W", "L1W", "L0W"]

INVERTED_METRICS = {"Restaurants Markdowns / GMV"}


def _safe_weekly_values(row: pd.Series, cols: list[str]) -> list[float | None]:
    """Extract weekly values, converting NaN to None for JSON serialization."""
    return [None if pd.isna(row[c]) else round(float(row[c]), 6) for c in cols]


def detect_anomalies(df_metrics: pd.DataFrame, threshold: float = 0.10) -> list[dict]:
    """Zones where |WoW change| > threshold on L0W_ROLL vs L1W_ROLL."""
    df = df_metrics.copy()
    l0 = df["L0W_ROLL"]
    l1 = df["L1W_ROLL"]

    # Skip rows where denominator is 0 or NaN
    valid = l1.notna() & l0.notna() & (l1 != 0)
    df = df[valid].copy()
    l0 = df["L0W_ROLL"]
    l1 = df["L1W_ROLL"]

    pct_change = (l0 - l1) / l1.abs()
    df = df[pct_change.abs() > threshold].copy()
    pct_change = pct_change[df.index]

    findings = []
    for idx, row in df.iterrows():
        pc = float(pct_change[idx])
        metric = row["METRIC"]

        if metric in INVERTED_METRICS:
            direction = "improvement" if pc < 0 else "deterioration"
        else:
            direction = "deterioration" if pc < 0 else "improvement"

        findings.append(
            {
                "type": "anomaly",
                "zone": row["ZONE"],
                "country": row["COUNTRY"],
                "city": row["CITY"],
                "metric": metric,
                "direction": direction,
                "pct_change": round(pc, 4),
                "l0w_value": round(float(row["L0W_ROLL"]), 6),
                "l1w_value": round(float(row["L1W_ROLL"]), 6),
                "weekly_values": _safe_weekly_values(row, METRIC_WEEK_COLS),
                "severity": round(abs(pc), 4),
            }
        )

    findings.sort(key=lambda f: f["severity"], reverse=True)
    return findings


def detect_trends(df_metrics: pd.DataFrame, min_consecutive: int = 3) -> list[dict]:
    """Zones+metrics where values declined min_consecutive+ consecutive weeks ending at L0W."""
    df = df_metrics.copy()
    week_vals = df[METRIC_WEEK_COLS].values

    findings = []
    for i, row in df.iterrows():
        vals = week_vals[df.index.get_loc(i)]

        # Count consecutive declines from the end (L0W backwards)
        consecutive = 0
        for w in range(len(vals) - 1, 0, -1):
            if np.isnan(vals[w]) or np.isnan(vals[w - 1]):
                break
            if vals[w] < vals[w - 1]:
                consecutive += 1
            else:
                break

        if consecutive >= min_consecutive:
            start_idx = len(vals) - 1 - consecutive
            start_val = vals[start_idx]
            end_val = vals[-1]
            total_decline = (
                (end_val - start_val) / abs(start_val) if start_val != 0 else 0
            )

            findings.append(
                {
                    "type": "trend",
                    "zone": row["ZONE"],
                    "country": row["COUNTRY"],
                    "city": row["CITY"],
                    "metric": row["METRIC"],
                    "weeks_declining": consecutive,
                    "total_decline_pct": round(float(total_decline), 4),
                    "weekly_values": _safe_weekly_values(row, METRIC_WEEK_COLS),
                    "severity": round(consecutive * abs(float(total_decline)), 4),
                }
            )

    findings.sort(key=lambda f: f["severity"], reverse=True)
    return findings


def detect_benchmark_outliers(df_metrics: pd.DataFrame) -> list[dict]:
    """Zones >1 std dev below peer group (COUNTRY, ZONE_TYPE) mean on L0W_ROLL."""
    df = df_metrics.dropna(subset=["L0W_ROLL"]).copy()
    findings = []

    grouped = df.groupby(["COUNTRY", "ZONE_TYPE", "METRIC"])
    for (country, zone_type, metric), group in grouped:
        if len(group) < 3:
            continue

        mean_val = group["L0W_ROLL"].mean()
        std_val = group["L0W_ROLL"].std()
        if std_val == 0 or np.isnan(std_val):
            continue

        cutoff = mean_val - std_val
        outliers = group[group["L0W_ROLL"] < cutoff]

        for _, row in outliers.iterrows():
            z_score = (row["L0W_ROLL"] - mean_val) / std_val

            findings.append(
                {
                    "type": "benchmark",
                    "zone": row["ZONE"],
                    "country": row["COUNTRY"],
                    "city": row["CITY"],
                    "zone_type": zone_type,
                    "metric": metric,
                    "value": round(float(row["L0W_ROLL"]), 6),
                    "peer_mean": round(float(mean_val), 6),
                    "peer_std": round(float(std_val), 6),
                    "z_score": round(float(z_score), 4),
                    "weekly_values": _safe_weekly_values(row, METRIC_WEEK_COLS),
                    "severity": round(abs(float(z_score)), 4),
                }
            )

    findings.sort(key=lambda f: f["severity"], reverse=True)
    return findings


def detect_correlations(df_metrics: pd.DataFrame, threshold: float = 0.7) -> list[dict]:
    """Per zone, Pearson r between metric pairs across 9 weeks. Flag |r| > threshold."""
    findings = []

    grouped = df_metrics.groupby(["COUNTRY", "CITY", "ZONE"])

    for (country, city, zone), group in grouped:
        if len(group) < 2:
            continue

        metrics = group["METRIC"].values
        values_matrix = group[METRIC_WEEK_COLS].values  # shape (n_metrics, 9)

        for i, j in combinations(range(len(metrics)), 2):
            a = values_matrix[i]
            b = values_matrix[j]

            # Skip if either has NaN
            valid = ~np.isnan(a) & ~np.isnan(b)
            if valid.sum() < 4:
                continue

            a_valid = a[valid]
            b_valid = b[valid]

            # Skip constant series
            if np.std(a_valid) == 0 or np.std(b_valid) == 0:
                continue

            r = float(np.corrcoef(a_valid, b_valid)[0, 1])
            if np.isnan(r) or abs(r) <= threshold:
                continue

            findings.append(
                {
                    "type": "correlation",
                    "zone": zone,
                    "country": country,
                    "city": city,
                    "metric_a": metrics[i],
                    "metric_b": metrics[j],
                    "correlation": round(r, 4),
                    "metric_a_values": _safe_weekly_values(
                        group.iloc[i], METRIC_WEEK_COLS
                    ),
                    "metric_b_values": _safe_weekly_values(
                        group.iloc[j], METRIC_WEEK_COLS
                    ),
                    "severity": round(abs(r), 4),
                }
            )

    findings.sort(key=lambda f: f["severity"], reverse=True)
    return findings


def run_all_detectors(
    df_metrics: pd.DataFrame,
    df_orders: pd.DataFrame,
) -> dict:
    """Run all detectors, merge findings, sort by severity."""
    anomalies = detect_anomalies(df_metrics)
    trends = detect_trends(df_metrics)
    benchmarks = detect_benchmark_outliers(df_metrics)
    correlations = detect_correlations(df_metrics)

    all_findings = anomalies + trends + benchmarks + correlations
    all_findings.sort(key=lambda f: f["severity"], reverse=True)

    return {
        "anomalies": anomalies,
        "trends": trends,
        "benchmarks": benchmarks,
        "correlations": correlations,
        "top_critical": all_findings[:5],
        "all_findings_ranked": all_findings,
    }
