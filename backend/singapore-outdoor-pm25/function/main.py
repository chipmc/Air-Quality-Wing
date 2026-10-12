"""Scheduled NEA regional PM2.5 ingestion; Python 3.11, standard library only."""
import json
import math
import os
import re
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

DGS_URL = "https://api-open.data.gov.sg/v2/real-time/api/pm25"
UBIDOTS_URL = "https://industrial.api.ubidots.com"
VARIABLE = "outdoor_pm25_1h"
REGIONS = {"north", "south", "east", "west", "central"}
MAX_RESPONSE_BYTES = 1024 * 1024


class IngestionError(Exception):
    """Only fixed, credential-free messages are returned to callers."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward credentials to a redirected host.
        return None


def request_json(method, url, headers, payload=None):
    body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with build_opener(NoRedirects()).open(req, timeout=4) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
    except HTTPError as exc:
        # Response bodies and exception messages can echo credentials; discard them.
        status = exc.code
        exc.close()
        return status, None
    except (URLError, OSError, socket.timeout, ssl.SSLError):
        raise IngestionError("network_request_failed") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise IngestionError("response_too_large")
    try:
        return status, json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise IngestionError("invalid_json_response") from None


def parse_time(value):
    if not isinstance(value, str):
        raise IngestionError("invalid_source_timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise IngestionError("invalid_source_timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IngestionError("timestamp_requires_timezone")
    return parsed.astimezone(timezone.utc)


def select_observation(response, region, now, max_age_seconds):
    if not isinstance(response, dict) or type(response.get("code")) is not int or response["code"] != 0:
        raise IngestionError("source_api_error")
    items = response.get("data", {}).get("items") if isinstance(response.get("data"), dict) else None
    if not isinstance(items, list) or not items:
        raise IngestionError("source_has_no_observations")
    # Do not assume array order or fall back to an older region value if newest is missing.
    if any(not isinstance(item, dict) for item in items):
        raise IngestionError("invalid_source_items")
    latest = max(items, key=lambda item: (parse_time(item.get("timestamp")),
                                         parse_time(item.get("updatedTimestamp"))))
    observed = parse_time(latest.get("timestamp"))
    updated = parse_time(latest.get("updatedTimestamp"))
    age = (now - observed).total_seconds()
    if age < -300 or (updated - now).total_seconds() > 300:
        raise IngestionError("source_timestamp_in_future")
    if updated < observed:
        raise IngestionError("source_update_precedes_observation")
    if age > max_age_seconds:
        raise IngestionError("source_observation_stale")
    readings = latest.get("readings")
    regional = readings.get("pm25_one_hourly") if isinstance(readings, dict) else None
    value = regional.get(region) if isinstance(regional, dict) else None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise IngestionError("source_region_value_missing_or_invalid")
    return {
        "value": value,
        "timestamp": int(observed.timestamp() * 1000),
        "context": {
            "source": "NEA/data.gov.sg", "region": region, "unit": "ug/m3",
            "averaging_period": "1h", "source_timestamp": latest["timestamp"],
            "source_updated_timestamp": latest["updatedTimestamp"],
            "dataset_id": "d_e1058d6974c877257e32048ab128ad83",
        },
    }


def load_config():
    try:
        config = json.loads(Path(__file__).with_name("config.json").read_text())
    except (OSError, ValueError):
        raise IngestionError("invalid_configuration_file") from None
    if not isinstance(config, dict):
        raise IngestionError("invalid_configuration_file")
    region = config.get("region", "central")
    label = os.environ.get("UBIDOTS_DEVICE_LABEL") or config.get("device_label", "")
    mode = config.get("mode", "preview")
    max_age = config.get("max_age_seconds", 10800)
    if (not isinstance(region, str) or region not in REGIONS
            or not isinstance(mode, str) or mode not in {"preview", "live"}):
        raise IngestionError("invalid_region_or_mode")
    if type(max_age) is not int or not 900 <= max_age <= 86400:
        raise IngestionError("invalid_max_age_seconds")
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", label):
        raise IngestionError("configure_device_api_label")
    if label.lower() in {"your-device-label", "configure-device-label"} or label.startswith("BBFF"):
        raise IngestionError("configure_device_api_label")
    return region, label, mode, max_age


def newest_dot(response):
    if not isinstance(response, dict) or not isinstance(response.get("results"), list):
        raise IngestionError("invalid_existing_dots_response")
    dots = response["results"]
    if not dots:
        return None
    if any(not isinstance(dot, dict) or type(dot.get("timestamp")) is not int for dot in dots):
        raise IngestionError("invalid_existing_dot_timestamp")
    return max(dots, key=lambda dot: dot["timestamp"])


def ingest(config, dgs_key, token, request=request_json, now=None):
    region, label, mode, max_age = config
    now = now or datetime.now(timezone.utc)
    if not isinstance(dgs_key, str) or not dgs_key.strip() or "{{" in dgs_key:
        raise IngestionError("configure_datagovsg_api_key")
    if mode == "live" and (not isinstance(token, str) or not token.strip() or "{{" in token):
        raise IngestionError("configure_function_account_token")
    status, source = request("GET", DGS_URL,
                             {"x-api-key": dgs_key, "Accept": "application/json"})
    if status != 200:
        raise IngestionError("source_http_error")
    dot = select_observation(source, region, now, max_age)
    if mode == "preview":
        return {"status": "preview", "variable": VARIABLE, "dot": dot}

    headers = {"X-Auth-Token": token, "Accept": "application/json",
               "Content-Type": "application/json"}
    encoded = quote(label, safe="")
    # The ingestion API auto-creates devices. Verify this existing device first.
    status, device = request("GET", f"{UBIDOTS_URL}/api/v2.0/devices/~{encoded}/", headers)
    if status != 200 or not isinstance(device, dict) or device.get("label") != label:
        raise IngestionError("destination_device_not_verified")
    status, existing = request("GET", f"{UBIDOTS_URL}/api/v1.6/devices/{encoded}/{VARIABLE}/values/?page_size=1", headers)
    if status == 404:
        last = None  # Device verified above; the outdoor variable is not created yet.
    elif status == 200:
        last = newest_dot(existing)
    else:
        raise IngestionError("existing_dot_read_failed")
    if last is not None:
        if last["timestamp"] > dot["timestamp"]:
            return {"status": "skipped", "reason": "older_than_stored_observation"}
        old_context = last.get("context") or {}
        if not isinstance(old_context, dict):
            raise IngestionError("invalid_existing_dot_context")
        if last["timestamp"] == dot["timestamp"]:
            old_updated = old_context.get("source_updated_timestamp")
            if old_updated and parse_time(old_updated) > parse_time(dot["context"]["source_updated_timestamp"]):
                return {"status": "skipped", "reason": "older_source_revision"}
            if (last.get("value") == dot["value"] and old_context.get("region") == region
                    and old_updated and parse_time(old_updated) == parse_time(dot["context"]["source_updated_timestamp"])):
                return {"status": "skipped", "reason": "unchanged_observation"}
    status, result = request("POST", f"{UBIDOTS_URL}/api/v1.6/devices/{encoded}/", headers, {VARIABLE: dot})
    entries = result.get(VARIABLE) if isinstance(result, dict) else None
    if (status not in (200, 201) or not isinstance(entries, list) or len(entries) != 1
            or not isinstance(entries[0], dict) or type(entries[0].get("status_code")) is not int
            or entries[0]["status_code"] not in (200, 201)):
        raise IngestionError("outdoor_dot_write_not_confirmed")
    return {"status": "written", "variable": VARIABLE, "timestamp": dot["timestamp"],
            "value": dot["value"], "region": region}


def main(args):
    """Ubidots injects its selected account token as _auth_token. Never log args."""
    try:
        config = load_config()
        # Ignore caller-supplied device/region/mode/token; destination comes from configuration.
        token = args.get("_auth_token") if isinstance(args, dict) else None
        token = token or os.environ.get("UBIDOTS_TOKEN")  # local/private environment fallback
        return ingest(config, os.environ.get("DATAGOVSG_API_KEY", ""), token)
    except IngestionError as exc:
        return {"status": "error", "reason": str(exc)}
    except Exception:
        # Do not expose unexpected exception text, URLs, request bodies or secrets.
        return {"status": "error", "reason": "unexpected_error"}
