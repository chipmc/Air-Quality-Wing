import copy
import importlib.util
import json
import os
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pm25_function", ROOT / "function/main.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
FIXTURE = json.loads((ROOT / "tests/fixtures/pm25.json").read_text())
NOW = m.parse_time("2026-10-12T16:20:00+08:00")
CONFIG = ("central", "existing-monitor", "live", 10800)


class FakeHTTP:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def __call__(self, method, url, headers, payload=None):
        self.calls.append((method, url, headers, payload))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def request_for(last_response=(404, None), write=(200, {m.VARIABLE: [{"status_code": 201}]})):
    return FakeHTTP([(200, FIXTURE), (200, {"label": "existing-monitor"}), last_response, write])


class ObservationTests(unittest.TestCase):
    def select(self, data=FIXTURE, now=NOW):
        return m.select_observation(data, "central", now, 10800)

    def test_region_unit_and_source_timestamp(self):
        dot = self.select()
        self.assertEqual(dot["value"], 15)
        self.assertEqual(dot["timestamp"], 1791792000000)
        self.assertEqual(dot["context"]["region"], "central")
        self.assertEqual(dot["context"]["averaging_period"], "1h")

    def test_numeric_zero_is_valid(self):
        data = copy.deepcopy(FIXTURE)
        data["data"]["items"][0]["readings"]["pm25_one_hourly"]["central"] = 0
        self.assertEqual(self.select(data)["value"], 0)

    def test_invalid_or_missing_reading_rejected(self):
        for bad in [None, True, "15", -1, float("nan"), float("inf")]:
            with self.subTest(value=bad):
                data = copy.deepcopy(FIXTURE)
                data["data"]["items"][0]["readings"]["pm25_one_hourly"]["central"] = bad
                with self.assertRaises(m.IngestionError): self.select(data)

    def test_unsorted_items_choose_newest_and_latest_revision(self):
        data = copy.deepcopy(FIXTURE)
        older = copy.deepcopy(data["data"]["items"][0])
        older.update(timestamp="2026-10-12T15:00:00+08:00", updatedTimestamp="2026-10-12T15:15:00+08:00")
        older["readings"]["pm25_one_hourly"]["central"] = 99
        revised = copy.deepcopy(data["data"]["items"][0])
        revised["updatedTimestamp"] = "2026-10-12T16:19:00+08:00"
        revised["readings"]["pm25_one_hourly"]["central"] = 16
        data["data"]["items"] = [revised, older, data["data"]["items"][0]]
        self.assertEqual(self.select(data)["value"], 16)

    def test_latest_missing_region_never_falls_back_to_old(self):
        data = copy.deepcopy(FIXTURE)
        latest = copy.deepcopy(data["data"]["items"][0])
        latest.update(timestamp="2026-10-12T16:15:00+08:00", updatedTimestamp="2026-10-12T16:16:00+08:00")
        latest["readings"]["pm25_one_hourly"].pop("central")
        data["data"]["items"].append(latest)
        with self.assertRaises(m.IngestionError): self.select(data)

    def test_stale_and_future_rejected(self):
        for now in [NOW + timedelta(hours=4), NOW - timedelta(hours=2)]:
            with self.subTest(now=now), self.assertRaises(m.IngestionError): self.select(now=now)

    def test_timezone_required_and_offset_conversion(self):
        self.assertEqual(m.parse_time("2026-10-12T16:00:00+08:00"), m.parse_time("2026-10-12T08:00:00Z"))
        for value in [None, "invalid", "2026-10-12T16:00:00"]:
            with self.assertRaises(m.IngestionError): m.parse_time(value)

    def test_invalid_shape_or_api_error(self):
        for data in [{"code": 1}, {"code": False}, {"code": 0, "data": {"items": []}}, {"code": 0, "data": None}]:
            with self.assertRaises(m.IngestionError): self.select(data)


class IngestionTests(unittest.TestCase):
    def ingest(self, request, config=CONFIG):
        return m.ingest(config, "test-dgs-credential", "test-ubidots-credential", request, NOW)

    def test_write_only_outdoor_with_timestamp_and_headers(self):
        request = request_for()
        result = self.ingest(request)
        self.assertEqual(result["status"], "written")
        self.assertEqual(len(request.calls), 4)
        self.assertEqual(request.calls[0][2]["x-api-key"], "test-dgs-credential")
        self.assertEqual(request.calls[-1][2]["X-Auth-Token"], "test-ubidots-credential")
        self.assertEqual(set(request.calls[-1][3]), {m.VARIABLE})
        self.assertEqual(request.calls[-1][3][m.VARIABLE]["timestamp"], 1791792000000)
        self.assertNotIn("token=", request.calls[-1][1])

    def test_source_request_identifies_project_instead_of_default_python_client(self):
        request = FakeHTTP([(200, FIXTURE)])
        self.ingest(request, ("central", "existing-monitor", "preview", 10800))
        self.assertEqual(request.calls[0][2]["User-Agent"], "Air-Quality-Wing/1.0")
        self.assertEqual(request.calls[0][2]["x-api-key"], "test-dgs-credential")
        self.assertEqual(len(request.calls), 1)

    def test_preview_never_contacts_ubidots(self):
        request = FakeHTTP([(200, FIXTURE)])
        self.assertEqual(self.ingest(request, ("central", "existing-monitor", "preview", 10800))["status"], "preview")
        self.assertEqual(len(request.calls), 1)

    def test_existing_device_must_match(self):
        for reply in [(404, None), (200, {"label": "another-device"}), (403, {})]:
            request = FakeHTTP([(200, FIXTURE), reply])
            with self.assertRaises(m.IngestionError): self.ingest(request)
            self.assertEqual(len(request.calls), 2)

    def test_unchanged_observation_skips_post(self):
        dot = m.select_observation(FIXTURE, "central", NOW, 10800)
        request = request_for((200, {"results": [dot]}))
        self.assertEqual(self.ingest(request)["reason"], "unchanged_observation")
        self.assertEqual(len(request.calls), 3)

    def test_corrected_same_timestamp_written(self):
        dot = m.select_observation(FIXTURE, "central", NOW, 10800)
        dot["value"] = 14
        dot["context"]["source_updated_timestamp"] = "2026-10-12T16:10:00+08:00"
        request = request_for((200, {"results": [dot]}))
        self.assertEqual(self.ingest(request)["status"], "written")

    def test_older_observation_or_revision_skips_post(self):
        for delta, revision in [(1000, "2026-10-12T16:15:00+08:00"), (0, "2026-10-12T16:19:00+08:00")]:
            dot = m.select_observation(FIXTURE, "central", NOW, 10800)
            dot["timestamp"] += delta
            dot["context"]["source_updated_timestamp"] = revision
            request = request_for((200, {"results": [dot]}))
            self.assertEqual(self.ingest(request)["status"], "skipped")
            self.assertEqual(len(request.calls), 3)

    def test_failures_never_write(self):
        for replies in [[(429, None)], [m.IngestionError("network_request_failed")],
                        [(200, FIXTURE), (200, {"label": "existing-monitor"}), (403, None)],
                        [(200, FIXTURE), (200, {"label": "existing-monitor"}), (200, {"results": "bad"})]]:
            request = FakeHTTP(replies)
            with self.assertRaises(m.IngestionError): self.ingest(request)
            self.assertTrue(all(call[0] != "POST" for call in request.calls))

    def test_top_level_success_with_rejected_dot_is_failure(self):
        for result in [(200, {m.VARIABLE: [{"status_code": 400}]}), (200, {}), (401, None),
                       (200, {m.VARIABLE: [{"status_code": True}]})]:
            with self.assertRaises(m.IngestionError): self.ingest(request_for(write=result))

    def test_required_secrets_fail_before_requests(self):
        request = FakeHTTP([])
        for dgs, token in [("", "token"), ("key", ""), ("{{key}}", "token")]:
            with self.assertRaises(m.IngestionError): m.ingest(CONFIG, dgs, token, request, NOW)
        self.assertFalse(request.calls)

    def test_main_uses_platform_account_token_not_request_token(self):
        with patch.object(m, "load_config", return_value=CONFIG), patch.dict(os.environ, {"DATAGOVSG_API_KEY": "private-key"}, clear=True), patch.object(m, "ingest", return_value={"status": "written"}) as ingest:
            m.main({"_auth_token": "platform-token", "token": "caller-token", "device": "wrong", "region": "west"})
            self.assertEqual(ingest.call_args.args, (CONFIG, "private-key", "platform-token"))

    def test_main_reads_global_property_label_and_preserves_uppercase_fallback(self):
        for environment, expected in [
            ({"datagovsg_api_key": "lowercase-key"}, "lowercase-key"),
            ({"DATAGOVSG_API_KEY": "uppercase-key"}, "uppercase-key"),
            ({"datagovsg_api_key": "preferred-key", "DATAGOVSG_API_KEY": "other-key"}, "preferred-key"),
            ({}, ""),
        ]:
            with self.subTest(environment_names=list(environment)):
                with patch.object(m, "load_config", return_value=CONFIG), patch.dict(os.environ, environment, clear=True), patch.object(m, "ingest", return_value={"status": "preview"}) as ingest:
                    m.main({"_auth_token": "platform-token"})
                    self.assertEqual(ingest.call_args.args, (CONFIG, expected, "platform-token"))

    def test_source_http_diagnostics_expose_only_valid_status(self):
        for status in (401, 403, 429, 503):
            with self.subTest(status=status):
                with self.assertRaises(m.IngestionError) as caught:
                    self.ingest(FakeHTTP([(status, {"message": "SECRET_VALUE"})]))
                self.assertEqual(caught.exception.http_status, status)
                with patch.object(m, "load_config", return_value=CONFIG), patch.object(m, "ingest", side_effect=caught.exception):
                    self.assertEqual(m.main({}), {"status": "error", "reason": "source_http_error", "http_status": status})
        for invalid in (True, "SECRET_VALUE", 999, None):
            self.assertIsNone(m.IngestionError("source_http_error", http_status=invalid).http_status)

    def test_main_does_not_expose_unexpected_exception_or_args(self):
        with patch.object(m, "load_config", side_effect=RuntimeError("SECRET_VALUE")):
            result = m.main({"_auth_token": "SECRET_VALUE"})
            self.assertEqual(result, {"status": "error", "reason": "unexpected_error"})

    def test_placeholder_label_rejected(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(m.IngestionError): m.load_config()


class TransportTests(unittest.TestCase):
    def test_http_errors_discard_response_body(self):
        opener = unittest.mock.MagicMock()
        opener.open.side_effect = HTTPError(m.DGS_URL, 401, "SECRET", {}, None)
        with patch.object(m, "build_opener", return_value=opener):
            self.assertEqual(m.request_json("GET", m.DGS_URL, {}), (401, None))

    def test_transport_errors_are_sanitized(self):
        opener = unittest.mock.MagicMock()
        opener.open.side_effect = URLError("SECRET")
        with patch.object(m, "build_opener", return_value=opener), self.assertRaisesRegex(m.IngestionError, "^network_request_failed$"):
            m.request_json("GET", m.DGS_URL, {})

    def test_redirects_are_disabled(self):
        self.assertIsNone(m.NoRedirects().redirect_request(None, None, 302, "", {}, "https://another.example"))

    def test_malformed_and_oversize_json_rejected(self):
        for data in [b"not json", b"x" * (m.MAX_RESPONSE_BYTES + 1)]:
            opener = unittest.mock.MagicMock()
            response = opener.open.return_value.__enter__.return_value
            response.status, response.read.return_value = 200, data
            with patch.object(m, "build_opener", return_value=opener), self.assertRaises(m.IngestionError):
                m.request_json("GET", m.DGS_URL, {})


if __name__ == "__main__": unittest.main()
