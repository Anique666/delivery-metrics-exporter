"""Delivery Metrics Exporter package.

A tiny, dependency-free exporter that turns a small set of delivery
metrics (DORA-style) into a JSON report on disk.
"""

from .metrics import (
    METRIC_SPECS,
    REQUIRED_METRICS,
    MetricError,
    build_report,
    load_config,
    to_json,
    validate_metric,
    validate_metrics,
    write_report,
)

__all__ = [
    "METRIC_SPECS",
    "REQUIRED_METRICS",
    "MetricError",
    "build_report",
    "load_config",
    "to_json",
    "validate_metric",
    "validate_metrics",
    "write_report",
]

__version__ = "1.0.0"
