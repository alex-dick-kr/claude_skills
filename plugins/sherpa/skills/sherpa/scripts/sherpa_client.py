#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["requests"]
# ///
"""
Sherpa (Kroger NOE infrastructure management framework) API client.

Sherpa is a REST API at https://sherpa.kroger.com/api/public covering location
data (address/GPS/floor/MS Teams GUID), IP subnets, and network asset/circuit
info. Auth is Kroger's standard OAuth2 client-credentials flow, scoped per
endpoint (e.g. urn:com:kroger:kr:sherpa:locations:read).

Credentials come from env vars so this can be run non-interactively. Sherpa
reuses the same Kroger API client already configured for other Kroger-hosted
APIs (e.g. the DSL/ESL data API) if that client has been granted sherpa scopes:

    KROGER_CLIENT_ID
    KROGER_CLIENT_SECRET

The access token is cached in memory only (per-process) and refetched once
expired - client_credentials tokens aren't worth persisting to disk the way
Kraken's session cookie is.

Usage as a library:

    from sherpa_client import SherpaClient
    s = SherpaClient()
    print(s.location_detail(value="6000905", status="active"))
    print(s.all_ip_subnets_by_facility(facility_code="06000905"))

Usage from the CLI (thin wrapper, one subcommand per endpoint):

    python3 sherpa_client.py location_detail --value 6000905 --status active
    python3 sherpa_client.py all_ip_subnets
    python3 sherpa_client.py all_ip_subnets_by_facility --facility_code go905
    python3 sherpa_client.py floor_by_ip_address --ip_address 192.168.100.1
    python3 sherpa_client.py ms_guid --facility_code go905
    python3 sherpa_client.py coordinates --facility_code go905
    python3 sherpa_client.py ap_switch_by_location --facility_code go905
    python3 sherpa_client.py facility_code_by_asset --asset_name go905osna1u
    python3 sherpa_client.py circuit_by_facility_code --facility_code go905
    python3 sherpa_client.py active_circuits_by_location --facility_code go905 --location_type store --type all
    python3 sherpa_client.py ktv_satellite_by_location --facility_code go905
    # Arbitrary GET endpoint not covered above
    python3 sherpa_client.py get /location/detail --params value=6000905 status=active
"""

import argparse
import json
import os
import sys
import time

import requests

PROD_BASE = "https://sherpa.kroger.com/api/public"
STAGE_BASE = "https://sherpa-stage.kroger.com/api/public"
TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"


class SherpaClient:
    def __init__(self, base_url=None, client_id=None, client_secret=None, token_url=TOKEN_URL):
        self.base_url = base_url or (STAGE_BASE if os.environ.get("SHERPA_STAGE") else PROD_BASE)
        self.client_id = client_id or os.environ.get("KROGER_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("KROGER_CLIENT_SECRET")
        self.token_url = os.environ.get("KROGER_TOKEN_URL", token_url)
        self.scope = os.environ.get("KROGER_OAUTH_SCOPE", "").strip()
        self.session = requests.Session()
        self._token = None
        self._token_exp = 0

    def _get_token(self):
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Missing credentials: set KROGER_CLIENT_ID and KROGER_CLIENT_SECRET "
                "(e.g. in ~/.claude/.env) or pass client_id/client_secret to SherpaClient(). "
                "The Kroger OAuth client must be granted the relevant "
                "urn:com:kroger:kr:sherpa:*:read scope(s)."
            )
        data = {"grant_type": "client_credentials"}
        if self.scope:
            data["scope"] = self.scope
        resp = requests.post(
            self.token_url,
            auth=(self.client_id, self.client_secret),
            data=data,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_exp = time.time() + int(body.get("expires_in", 1800))
        return self._token

    def _request(self, method, path, retried=False, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._get_token()}"
        headers.setdefault("Accept", "application/json")
        kwargs.setdefault("timeout", 30)
        resp = self.session.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        if resp.status_code == 401 and not retried:
            # Cached token rejected (e.g. revoked) - force a fresh one and retry once.
            self._token = None
            return self._request(method, path, retried=True, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get(self, path, params=None):
        return self._request("GET", path, params={k: v for k, v in (params or {}).items() if v is not None})

    def post(self, path, params=None):
        return self._request("POST", path, params={k: v for k, v in (params or {}).items() if v is not None})

    # ---- location ----------------------------------------------------------

    def location_detail(self, value, status=None, location_type=None):
        return self.get("/location/detail", {"value": value, "status": status, "location_type": location_type})

    def all_ip_subnets(self):
        return self.get("/location/all_ip_subnets")

    def all_ip_subnets_by_facility(self, facility_code):
        return self.get("/location/all_ip_subnets_by_facility", {"facility_code": facility_code})

    def floor_by_subnet(self, ip_address, cidr=None):
        return self.get("/location/floor_by_subnet", {"ip_address": ip_address, "cidr": cidr})

    def floor_by_ip_address(self, ip_address):
        return self.get("/location/floor_by_ip_address", {"ip_address": ip_address})

    def floor_by_location(self, facility_code):
        return self.get("/location/floor_by_location", {"facility_code": facility_code})

    def ms_guid(self, facility_code):
        return self.get("/location/ms_guid", {"facility_code": facility_code})

    def update_ms_guid(self, facility_code, guid):
        return self.post("/location/update_ms_guid", {"facility_code": facility_code, "guid": guid})

    def coordinates(self, facility_code):
        return self.get("/location/coordinates", {"facility_code": facility_code})

    def update_coordinates(self, facility_code, latitude, longitude):
        return self.post("/location/update_coordinates",
                          {"facility_code": facility_code, "latitude": latitude, "longitude": longitude})

    def ap_switch_by_location(self, facility_code):
        return self.get("/location/ap_switch_by_location", {"facility_code": facility_code})

    def update_notification(self, facility_code, field, flag, description):
        return self.post("/location/update_notification",
                          {"facility_code": facility_code, "field": field, "flag": flag, "description": description})

    def tag_lab_location(self, facility_code):
        return self.post("/location/tag_lab_location", {"facility_code": facility_code})

    # ---- asset ---------------------------------------------------------------

    def facility_code_by_asset(self, asset_name):
        return self.get("/asset/facility_code_by_asset", {"asset_name": asset_name})

    def circuit_by_facility_code(self, facility_code):
        return self.get("/asset/circuit_by_facility_code", {"facility_code": facility_code})

    def active_circuits_by_location(self, facility_code, type, location_type=None):
        return self.get("/asset/active_circuits_by_location",
                         {"facility_code": facility_code, "location_type": location_type, "type": type})

    def ktv_satellite_by_location(self, facility_code, location_type=None):
        return self.get("/asset/ktv_satellite_by_location", {"facility_code": facility_code, "location_type": location_type})

    # ---- monitor (OpenNMS) -----------------------------------------------------

    def monitor_assets(self):
        return self.get("/monitor/assets")

    def monitor_foreign_source(self):
        return self.get("/monitor/foreign_source")


def _main():
    parser = argparse.ArgumentParser(description="Sherpa API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("location_detail")
    p.add_argument("--value", required=True)
    p.add_argument("--status")
    p.add_argument("--location_type")

    sub.add_parser("all_ip_subnets")

    p = sub.add_parser("all_ip_subnets_by_facility")
    p.add_argument("--facility_code", required=True)

    p = sub.add_parser("floor_by_subnet")
    p.add_argument("--ip_address", required=True)
    p.add_argument("--cidr", type=int)

    p = sub.add_parser("floor_by_ip_address")
    p.add_argument("--ip_address", required=True)

    p = sub.add_parser("floor_by_location")
    p.add_argument("--facility_code", required=True)

    p = sub.add_parser("ms_guid")
    p.add_argument("--facility_code", required=True)

    p = sub.add_parser("coordinates")
    p.add_argument("--facility_code", required=True)

    p = sub.add_parser("ap_switch_by_location")
    p.add_argument("--facility_code", required=True)

    p = sub.add_parser("facility_code_by_asset")
    p.add_argument("--asset_name", required=True)

    p = sub.add_parser("circuit_by_facility_code")
    p.add_argument("--facility_code", required=True)

    p = sub.add_parser("active_circuits_by_location")
    p.add_argument("--facility_code", required=True)
    p.add_argument("--location_type")
    p.add_argument("--type", required=True)

    p = sub.add_parser("ktv_satellite_by_location")
    p.add_argument("--facility_code", required=True)
    p.add_argument("--location_type")

    sub.add_parser("monitor_assets")
    sub.add_parser("monitor_foreign_source")

    p_get = sub.add_parser("get")
    p_get.add_argument("path")
    p_get.add_argument("--params", nargs="*", default=[], help="key=value pairs")

    args = parser.parse_args()
    client = SherpaClient()
    ns = vars(args)
    cmd = ns.pop("command")

    if cmd == "get":
        params = dict(p.split("=", 1) for p in ns["params"])
        result = client.get(ns["path"], params=params)
    else:
        ns.pop("params", None)
        result = getattr(client, cmd)(**ns)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    sys.exit(_main())
