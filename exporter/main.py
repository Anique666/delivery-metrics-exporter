"""Command-line entry point for the Delivery Metrics Exporter.

Usage
-----
    python -m exporter.main
    python -m exporter.main --config config/metrics.json --output-dir output

Exit codes
----------
0   report generated successfully
1   invalid configuration / metric data, or the report could not be written
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .metrics import MetricError, build_report, load_config, write_report

# Repository root = parent of the ``exporter`` package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "metrics.json"
DEFAULT_OUTPUT_DIR = "output"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="delivery-metrics-exporter",
        description="Export delivery metrics (DORA style) as a JSON report.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=str(DEFAULT_CONFIG),
        help=f"path to the metrics configuration file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"directory that receives the JSON report (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "-f",
        "--filename",
        default="metrics-report.json",
        help="name of the generated JSON report (default: metrics-report.json)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the exporter and return a process exit code."""
    args = parse_args(argv)

    try:
        config = load_config(args.config)
        report = build_report(config)
        target = write_report(report, args.output_dir, args.filename)
    except MetricError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Service      : {report['service']}")
    print(f"Window (days): {report['window_days']}")
    print(f"Metrics      : {report['metric_count']}")
    print(f"Report       : {target.resolve()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
