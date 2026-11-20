"""Test suite for the Delivery Metrics Exporter.

Runs with the standard library (``python -m unittest discover -s tests -v``)
and with pytest (``pytest -v tests``), which is what the Jenkins pipeline uses
because pytest can emit a JUnit XML report with ``--junitxml``.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from exporter import main as cli
from exporter.metrics import (
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "metrics.json"

# Fixed timestamp keeps the generated report fully deterministic.
FIXED_TIME = datetime(2026, 1, 15, 9, 30, tzinfo=timezone.utc)


def sample_config() -> dict:
    """Deterministic in-memory configuration used by most tests."""
    return {
        "service": "checkout-api",
        "window_days": 30,
        "metrics": {
            "deployment_frequency_per_day": 3.4,
            "lead_time_hours": 18.5,
            "change_failure_rate_percent": 8.0,
            "mttr_hours": 2.25,
        },
    }


class TestConfiguration(unittest.TestCase):
    def test_shipped_config_file_loads(self):
        config = load_config(CONFIG_PATH)
        self.assertEqual(config["service"], "checkout-api")
        self.assertIn("metrics", config)
        for name in REQUIRED_METRICS:
            self.assertIn(name, config["metrics"])

    def test_missing_config_file_raises_metric_error(self):
        with self.assertRaises(MetricError):
            load_config(PROJECT_ROOT / "config" / "does-not-exist.json")

    def test_invalid_json_raises_metric_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken.json"
            broken.write_text("{not valid json", encoding="utf-8")
            with self.assertRaises(MetricError):
                load_config(broken)

    def test_config_without_metrics_section_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"service": "x"}), encoding="utf-8")
            with self.assertRaises(MetricError):
                load_config(path)


class TestMetricValidation(unittest.TestCase):
    def test_valid_metric_returns_float(self):
        self.assertEqual(validate_metric("mttr_hours", 2), 2.0)
        self.assertIsInstance(validate_metric("mttr_hours", 2), float)

    def test_unknown_metric_is_rejected(self):
        with self.assertRaises(MetricError):
            validate_metric("not_a_metric", 1.0)

    def test_negative_value_is_rejected(self):
        with self.assertRaises(MetricError):
            validate_metric("lead_time_hours", -1.0)

    def test_percentage_above_100_is_rejected(self):
        with self.assertRaises(MetricError):
            validate_metric("change_failure_rate_percent", 101.0)

    def test_non_numeric_values_are_rejected(self):
        for bad in ("3.4", None, [1], {"value": 1}, True):
            with self.subTest(bad=bad):
                with self.assertRaises(MetricError):
                    validate_metric("deployment_frequency_per_day", bad)

    def test_nan_is_rejected(self):
        with self.assertRaises(MetricError):
            validate_metric("deployment_frequency_per_day", float("nan"))

    def test_missing_metric_is_reported(self):
        metrics = sample_config()["metrics"]
        del metrics["mttr_hours"]
        with self.assertRaisesRegex(MetricError, "Missing required metric"):
            validate_metrics(metrics)

    def test_unknown_metric_is_reported(self):
        metrics = sample_config()["metrics"]
        metrics["velocity_points"] = 12
        with self.assertRaisesRegex(MetricError, "Unknown metric"):
            validate_metrics(metrics)

    def test_non_mapping_metrics_are_rejected(self):
        with self.assertRaises(MetricError):
            validate_metrics(["deployment_frequency_per_day"])

    def test_validate_metrics_returns_all_required_keys(self):
        result = validate_metrics(sample_config()["metrics"])
        self.assertEqual(set(result), set(REQUIRED_METRICS))
        self.assertTrue(all(isinstance(value, float) for value in result.values()))


class TestReportGeneration(unittest.TestCase):
    def test_report_structure_is_predictable(self):
        report = build_report(sample_config(), generated_at=FIXED_TIME)

        self.assertEqual(
            set(report),
            {"service", "window_days", "generated_at", "metric_count", "metrics"},
        )
        self.assertEqual(report["service"], "checkout-api")
        self.assertEqual(report["window_days"], 30)
        self.assertEqual(report["metric_count"], len(REQUIRED_METRICS))
        self.assertEqual(report["generated_at"], "2026-01-15T09:30:00+00:00")

        for name in REQUIRED_METRICS:
            entry = report["metrics"][name]
            self.assertEqual(set(entry), {"label", "value", "unit", "description"})
            self.assertEqual(entry["label"], METRIC_SPECS[name]["label"])
            self.assertEqual(entry["unit"], METRIC_SPECS[name]["unit"])

    def test_report_values_match_input(self):
        report = build_report(sample_config(), generated_at=FIXED_TIME)
        self.assertEqual(report["metrics"]["deployment_frequency_per_day"]["value"], 3.4)
        self.assertEqual(report["metrics"]["lead_time_hours"]["value"], 18.5)
        self.assertEqual(report["metrics"]["change_failure_rate_percent"]["value"], 8.0)
        self.assertEqual(report["metrics"]["mttr_hours"]["value"], 2.25)

    def test_report_is_deterministic_for_fixed_timestamp(self):
        first = to_json(build_report(sample_config(), generated_at=FIXED_TIME))
        second = to_json(build_report(sample_config(), generated_at=FIXED_TIME))
        self.assertEqual(first, second)

    def test_invalid_metric_value_prevents_report(self):
        config = sample_config()
        config["metrics"]["change_failure_rate_percent"] = 150
        with self.assertRaises(MetricError):
            build_report(config)

    def test_invalid_window_days_is_rejected(self):
        for bad in (0, -5, "30", 2.5, True):
            with self.subTest(bad=bad):
                config = sample_config()
                config["window_days"] = bad
                with self.assertRaises(MetricError):
                    build_report(config)


class TestJsonSerialisation(unittest.TestCase):
    def test_json_round_trip(self):
        report = build_report(sample_config(), generated_at=FIXED_TIME)
        restored = json.loads(to_json(report))
        self.assertEqual(restored, report)

    def test_json_is_pretty_printed(self):
        text = to_json(build_report(sample_config(), generated_at=FIXED_TIME))
        self.assertIn('\n  "service": "checkout-api"', text)

    def test_write_report_creates_directory_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "report.json"
            written = write_report(
                build_report(sample_config(), generated_at=FIXED_TIME),
                target.parent,
                target.name,
            )
            self.assertTrue(written.is_file())
            data = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(data["service"], "checkout-api")

    def test_write_report_rejects_non_json_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MetricError):
                write_report(build_report(sample_config()), tmp, "report.txt")


class TestCommandLine(unittest.TestCase):
    def test_cli_generates_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = cli.main(
                ["--config", str(CONFIG_PATH), "--output-dir", tmp, "--filename", "report.json"]
            )
            self.assertEqual(exit_code, 0)
            data = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(data["service"], "checkout-api")
            self.assertEqual(data["metric_count"], 4)

    def test_cli_returns_1_on_bad_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = cli.main(
                ["--config", str(Path(tmp) / "missing.json"), "--output-dir", tmp]
            )
            self.assertEqual(exit_code, 1)


class TestControlledFailureDemo(unittest.TestCase):
    """Controlled failure mechanism used for the Jenkins demonstration.

    The pipeline passes ``DEMO_FORCE_TEST_FAILURE=true`` as a build parameter
    to prove that Jenkins turns a failing test into a FAILURE build. The flag
    is disabled (absent/false) during normal execution, so this test passes.
    """

    def test_controlled_failure_flag_is_respected(self):
        flag = os.environ.get("DEMO_FORCE_TEST_FAILURE", "").strip().lower()
        if flag in {"1", "true", "yes", "on"}:
            self.fail(
                "CONTROLLED FAILURE: DEMO_FORCE_TEST_FAILURE="
                f"{flag!r} is enabled. This failure is intentional and exists "
                "only to demonstrate Jenkins test-failure detection."
            )
        self.assertIn(flag, {"", "0", "false", "no", "off"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
