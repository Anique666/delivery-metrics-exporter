"""Delivery metric validation, collection and JSON serialisation.

The module deliberately uses only the Python standard library so the
packaged exporter can be run on any machine with a stock Python 3
installation (no third-party runtime dependencies).

Public API
----------
load_config(path)            -> dict   read + parse the JSON configuration
validate_metric(name, value) -> float  validate a single metric value
validate_metrics(mapping)    -> dict   validate the complete metric set
build_report(config)         -> dict   build the report data structure
to_json(report)              -> str    serialise the report to JSON text
write_report(report, dir)    -> Path   persist the report as a JSON file
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Metric catalogue
# ---------------------------------------------------------------------------
# Each metric carries the metadata needed for validation *and* for building a
# self-describing JSON report. ``maximum=None`` means "no upper bound".
METRIC_SPECS: dict[str, dict[str, Any]] = {
    "deployment_frequency_per_day": {
        "label": "Deployment Frequency",
        "unit": "deployments/day",
        "minimum": 0.0,
        "maximum": None,
        "description": "How often the service is deployed to production per day.",
    },
    "lead_time_hours": {
        "label": "Lead Time for Changes",
        "unit": "hours",
        "minimum": 0.0,
        "maximum": None,
        "description": "Time from commit to running in production.",
    },
    "change_failure_rate_percent": {
        "label": "Change Failure Rate",
        "unit": "%",
        "minimum": 0.0,
        "maximum": 100.0,
        "description": "Percentage of deployments that cause a degradation.",
    },
    "mttr_hours": {
        "label": "Mean Time to Recovery (MTTR)",
        "unit": "hours",
        "minimum": 0.0,
        "maximum": None,
        "description": "Average time to restore service after an incident.",
    },
}

# The report is only complete when every metric in this tuple is present.
REQUIRED_METRICS: tuple[str, ...] = tuple(METRIC_SPECS)


class MetricError(ValueError):
    """Raised when configuration or metric data is invalid."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_metric(name: str, value: Any) -> float:
    """Validate a single metric and return it as a float.

    Raises ``MetricError`` for unknown metric names, non-numeric values,
    NaN/infinity, or values outside the metric's allowed range.
    """
    if name not in METRIC_SPECS:
        raise MetricError(
            f"Unknown metric {name!r}. Expected one of: {', '.join(REQUIRED_METRICS)}"
        )

    # bool is a subclass of int; True/False is almost certainly a config typo.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MetricError(
            f"Metric {name!r} must be a number, got {type(value).__name__}: {value!r}"
        )

    number = float(value)

    if math.isnan(number) or math.isinf(number):
        raise MetricError(f"Metric {name!r} must be a finite number, got {value!r}")

    spec = METRIC_SPECS[name]
    if number < spec["minimum"]:
        raise MetricError(
            f"Metric {name!r} must be >= {spec['minimum']}, got {number}"
        )
    if spec["maximum"] is not None and number > spec["maximum"]:
        raise MetricError(
            f"Metric {name!r} must be <= {spec['maximum']}, got {number}"
        )

    return number


def validate_metrics(metrics: Any) -> dict[str, float]:
    """Validate a mapping of metric name -> value and return clean floats."""
    if not isinstance(metrics, Mapping):
        raise MetricError(
            f"'metrics' must be a JSON object, got {type(metrics).__name__}"
        )

    missing = [name for name in REQUIRED_METRICS if name not in metrics]
    if missing:
        raise MetricError("Missing required metric(s): " + ", ".join(missing))

    unknown = sorted(set(metrics) - set(REQUIRED_METRICS))
    if unknown:
        raise MetricError("Unknown metric(s): " + ", ".join(unknown))

    return {name: validate_metric(name, metrics[name]) for name in REQUIRED_METRICS}


# ---------------------------------------------------------------------------
# Configuration and report generation
# ---------------------------------------------------------------------------
def load_config(path: str | Path) -> dict[str, Any]:
    """Read and parse a JSON configuration file."""
    config_path = Path(path)
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MetricError(f"Cannot read configuration file {config_path}: {exc}") from exc

    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MetricError(
            f"Configuration file {config_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise MetricError(
            f"Configuration file {config_path} must contain a JSON object"
        )
    if "metrics" not in config:
        raise MetricError(f"Configuration file {config_path} has no 'metrics' section")

    return config


def build_report(
    config: Mapping[str, Any],
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a predictable report dictionary from a configuration mapping."""
    metrics = validate_metrics(config.get("metrics"))

    window_days = config.get("window_days", 30)
    if isinstance(window_days, bool) or not isinstance(window_days, int) or window_days <= 0:
        raise MetricError(f"'window_days' must be a positive integer, got {window_days!r}")

    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    service = config.get("service", "unnamed-service")
    if not isinstance(service, str) or not service.strip():
        raise MetricError("'service' must be a non-empty string")

    report_metrics = {
        name: {
            "label": METRIC_SPECS[name]["label"],
            "value": metrics[name],
            "unit": METRIC_SPECS[name]["unit"],
            "description": METRIC_SPECS[name]["description"],
        }
        for name in REQUIRED_METRICS
    }

    return {
        "service": service,
        "window_days": window_days,
        "generated_at": timestamp.isoformat(timespec="seconds"),
        "metric_count": len(report_metrics),
        "metrics": report_metrics,
    }


def to_json(report: Mapping[str, Any], indent: int = 2) -> str:
    """Serialise a report dictionary to pretty-printed JSON text."""
    try:
        return json.dumps(report, indent=indent, sort_keys=False)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise MetricError(f"Report cannot be serialised to JSON: {exc}") from exc


def write_report(
    report: Mapping[str, Any],
    output_dir: str | Path = "output",
    filename: str = "metrics-report.json",
) -> Path:
    """Write the report JSON to ``output_dir/filename`` and return the path."""
    if not filename.endswith(".json"):
        raise MetricError(f"Report filename must end with '.json', got {filename!r}")

    directory = Path(output_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / filename
        target.write_text(to_json(report) + "\n", encoding="utf-8")
    except OSError as exc:
        raise MetricError(f"Cannot write report to {directory}: {exc}") from exc

    return target
