import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from Reto_7.ci.scripts.go_cover_to_cobertura import convert as convert_coverage
from Reto_7.ci.scripts.go_test_json_to_junit import convert as convert_junit
from Reto_7.ci.scripts.junit_status import main as junit_status_main, summarize
from Reto_7.ci.scripts.normalize_dotnet_coverage import normalize
from Reto_7.ci.scripts.normalize_node_junit import normalize as normalize_node_junit
from Reto_7.ci.scripts.run_e2e import positive_number, wait_for_gateway
from Reto_7.ci.scripts.validate_reports import (
    validate_coverage,
    validate_cucumber,
    validate_cucumber_html,
    validate_junit,
    validate_lcov,
)
from Reto_7.ci.scripts.verify_ci_config import verify


class GoConvertersTests(unittest.TestCase):
    def test_missing_converter_inputs_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing input"
            with self.assertRaises(FileNotFoundError):
                convert_junit(missing, Path(directory) / "junit.xml")
            with self.assertRaises(FileNotFoundError):
                convert_coverage(missing, Path(directory) / "coverage.xml")

    def test_go_json_preserves_failures_skips_and_names(self):
        events = [
            {"Action": "run", "Package": "reto/perfiles", "Test": "TestOK"},
            {"Action": "pass", "Package": "reto/perfiles", "Test": "TestOK", "Elapsed": 0.01},
            {"Action": "run", "Package": "reto/perfiles", "Test": "TestFailure"},
            {"Action": "output", "Package": "reto/perfiles", "Test": "TestFailure", "Output": "expected 200\n"},
            {"Action": "fail", "Package": "reto/perfiles", "Test": "TestFailure", "Elapsed": 0.02},
            {"Action": "run", "Package": "reto/perfiles", "Test": "TestSkipped"},
            {"Action": "skip", "Package": "reto/perfiles", "Test": "TestSkipped"},
            {"Action": "fail", "Package": "reto/perfiles", "Elapsed": 0.03},
        ]
        with tempfile.TemporaryDirectory(prefix="reto 7 ") as directory:
            source = Path(directory) / "entrada go.json"
            target = Path(directory) / "salida junit.xml"
            source.write_text("\n".join(json.dumps(item) for item in events), encoding="utf-8")
            totals = convert_junit(source, target)
            root = ET.parse(target).getroot()
            self.assertEqual({"tests": 3, "failures": 1, "errors": 0, "skipped": 1}, totals)
            self.assertEqual(
                ["TestFailure", "TestOK", "TestSkipped"],
                [item.get("name") for item in root.findall(".//testcase")],
            )
            self.assertIn("expected 200", root.findtext(".//failure", default=""))

    def test_go_json_rejects_empty_malformed_and_unknown_action(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "go.json"
            target = Path(directory) / "junit.xml"
            for content in ("", "{malformed", json.dumps({"Action": "mystery", "Package": "p"})):
                source.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(ValueError):
                    convert_junit(source, target)

    def test_incomplete_go_test_becomes_junit_error(self):
        event = {"Action": "run", "Package": "reto/perfiles", "Test": "TestInterrupted"}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "go.json"
            target = Path(directory) / "junit.xml"
            source.write_text(json.dumps(event), encoding="utf-8")
            totals = convert_junit(source, target)
            self.assertEqual(1, totals["errors"])
            self.assertIsNotNone(ET.parse(target).find(".//error"))

    def test_go_coverprofile_becomes_cobertura_and_accepts_zero_coverage(self):
        content = "\n".join([
            "mode: atomic",
            r"C:\workspace with spaces\perfiles\main.go:10.1,12.2 2 0",
            r"C:\workspace with spaces\perfiles\main.go:14.1,14.9 1 0",
        ])
        with tempfile.TemporaryDirectory(prefix="reto 7 ") as directory:
            source = Path(directory) / "coverage input.out"
            target = Path(directory) / "coverage output.xml"
            source.write_text(content, encoding="utf-8")
            totals = convert_coverage(source, target, "Reto_4/perfiles")
            self.assertEqual({"lines-valid": 4, "lines-covered": 0}, totals)
            self.assertEqual("coverage", ET.parse(target).getroot().tag)
            self.assertEqual("coverage", validate_coverage(target))

    def test_go_coverprofile_rejects_header_without_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "coverage.out"
            source.write_text("mode: atomic\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                convert_coverage(source, Path(directory) / "coverage.xml")


class NormalizerTests(unittest.TestCase):
    def test_dotnet_normalizes_both_complete_coverage_formats(self):
        cobertura_xml = """<coverage lines-valid="1" lines-covered="0" line-rate="0"><packages><package><classes><class><lines><line number="1" hits="0"/></lines></class></classes></package></packages></coverage>"""
        opencover_xml = """<CoverageSession><Summary numSequencePoints="1" visitedSequencePoints="0"/><Modules/></CoverageSession>"""
        with tempfile.TemporaryDirectory(prefix="reto 7 ") as directory:
            results = Path(directory) / "resultados con espacio"
            generated = results / "run-id"
            generated.mkdir(parents=True)
            (generated / "coverage.cobertura.xml").write_text(cobertura_xml, encoding="utf-8")
            (generated / "coverage.opencover.xml").write_text(opencover_xml, encoding="utf-8")
            cobertura = results / "coverage.xml"
            opencover = results / "coverage.opencover.xml"
            normalize(results, cobertura, opencover)
            self.assertEqual("coverage", ET.parse(cobertura).getroot().tag)
            self.assertEqual("CoverageSession", ET.parse(opencover).getroot().tag)

    def test_dotnet_rejects_wrong_or_empty_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory)
            (results / "coverage.cobertura.xml").write_text("<coverage/>", encoding="utf-8")
            (results / "coverage.opencover.xml").write_text("<coverage/>", encoding="utf-8")
            with self.assertRaises(ValueError):
                normalize(results, results / "out-c.xml", results / "out-o.xml")

    def test_node_wraps_direct_testcases_and_preserves_states(self):
        raw = """<testsuites>
          <testcase name="works" time="0.01" classname="test"/>
          <testcase name="fails" time="0.02" classname="test"><failure>detalle</failure></testcase>
          <testcase name="skip" classname="test"><skipped/></testcase>
        </testsuites>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            path.write_text(raw, encoding="utf-8")
            totals = normalize_node_junit(path, path)
            root = ET.parse(path).getroot()
            self.assertEqual({"tests": 3, "failures": 1, "errors": 0, "skipped": 1}, totals)
            self.assertEqual("node:test", root.find("testsuite").get("name"))
            self.assertEqual("detalle", root.findtext(".//failure"))

    def test_node_rejects_empty_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            path.write_text("<testsuites/>", encoding="utf-8")
            with self.assertRaises(ValueError):
                normalize_node_junit(path, path)


class ReportValidationTests(unittest.TestCase):
    def test_junit_counts_failures_errors_and_skips(self):
        raw = """<testsuite tests="4" failures="1" errors="1" skipped="1">
          <testcase name="ok"/><testcase name="bad"><failure/></testcase>
          <testcase name="broken"><error/></testcase><testcase name="skip"><skipped/></testcase>
        </testsuite>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TEST-sample.xml"
            path.write_text(raw, encoding="utf-8")
            self.assertEqual((4, 1, 1), validate_junit(path))
            self.assertEqual(
                {"tests": 4, "failures": 1, "errors": 1, "skipped": 1}, summarize([path])
            )

    def test_junit_rejects_empty_corrupt_and_inconsistent_reports(self):
        samples = (
            "<testsuites/>",
            "<testsuite tests='2'><testcase name='only-one'/></testsuite>",
            "<testsuite><testcase/></testsuite>",
            "<testsuite>",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.xml"
            for raw in samples:
                path.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw), self.assertRaises((ValueError, ET.ParseError)):
                    validate_junit(path)

    def test_junit_status_exit_codes_distinguish_missing_failure_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TEST-result.xml"
            with patch("sys.argv", ["junit_status", "--glob", str(Path(directory) / "missing-*.xml")]):
                self.assertEqual(2, junit_status_main())
            path.write_text(
                '<testsuite><testcase name="bad"><failure/></testcase></testsuite>', encoding="utf-8"
            )
            with patch("sys.argv", ["junit_status", "--glob", str(path)]):
                self.assertEqual(1, junit_status_main())
            path.write_text("<testsuite>", encoding="utf-8")
            with patch("sys.argv", ["junit_status", "--glob", str(path)]):
                self.assertEqual(3, junit_status_main())

    def test_coverage_rejects_malformed_metrics_but_accepts_real_zero(self):
        valid_zero = """<coverage lines-valid="1" lines-covered="0" line-rate="0"><packages><package><classes><class><lines><line number="1" hits="0"/></lines></class></classes></package></packages></coverage>"""
        invalid = """<coverage lines-valid="2" lines-covered="1" line-rate="0.9"><line number="1" hits="1"/></coverage>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.xml"
            path.write_text(valid_zero, encoding="utf-8")
            self.assertEqual("coverage", validate_coverage(path))
            path.write_text(invalid, encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_coverage(path)

    def test_cucumber_validates_step_results_and_malformed_json(self):
        valid = [{"name": "f", "elements": [{"type": "scenario", "name": "s", "steps": [
            {"name": "x", "result": {"status": "failed", "duration": 0.1}}
        ]}]}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cucumber.json"
            path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual((1, 1), validate_cucumber(path))
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                validate_cucumber(path)

    def test_lcov_validates_counts_and_rejects_incomplete_records(self):
        valid = "TN:\nSF:src/app.js\nDA:1,0\nDA:2,3\nLF:2\nLH:1\nend_of_record\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lcov.info"
            path.write_text(valid, encoding="utf-8")
            self.assertEqual((1, 2, 1), validate_lcov(path))
            path.write_text(valid.replace("LH:1", "LH:2"), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_lcov(path)

    def test_cucumber_html_requires_document_and_scenario_cards(self):
        valid = "<html><head><title>BDD</title></head><body><article class='scenario passed'></article></body></html>"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cucumber.html"
            path.write_text(valid, encoding="utf-8")
            self.assertEqual(1, validate_cucumber_html(path))
            path.write_text("<html><body>sin escenarios</body></html>", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_cucumber_html(path)


class RunnerAndConfigurationTests(unittest.TestCase):
    def test_gateway_health_requires_the_expected_json_contract(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read():
                return b'{"status":"ok","service":"api-gateway"}'

        with patch("Reto_7.ci.scripts.run_e2e.urlopen", return_value=Response()):
            wait_for_gateway("http://gateway.example", "/health", 1, 0.01, 0.1)

    def test_positive_number_rejects_nan_and_infinity(self):
        for value in ("nan", "inf", "0", "-1"):
            with self.subTest(value=value), patch.dict(os.environ, {"LIMIT": value}):
                with self.assertRaises(ValueError):
                    positive_number("LIMIT", "1")

    def test_gateway_url_requires_http_absolute_url(self):
        with self.assertRaises(ValueError):
            wait_for_gateway("file:///tmp/gateway", "/health", 1, 0.01, 0.01)

    def test_repository_ci_contract_is_consistent(self):
        root = Path(__file__).resolve().parents[2]
        self.assertEqual([], verify(root))


if __name__ == "__main__":
    unittest.main()
