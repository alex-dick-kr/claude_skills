#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["requests"]
# ///
"""
Kraken (Kroger Remote Asset Kit for Enterprise Networking) API client.

Auth is LDAP-backed, session-cookie based (no API keys). Credentials come from
env vars so this can be run non-interactively:

    KRAKEN_EUID
    KRAKEN_PASSWORD_B64   # base64-encoded password

The session cookie is cached on disk (.kraken_session.json, 0600) next to this
script, so repeated calls reuse the existing login instead of re-authenticating
every time. On a 401 the cache is invalidated and it logs in again automatically.

Usage as a library:

    from kraken_client import KrakenClient
    k = KrakenClient()
    k.login()
    print(k.user_perms())
    print(k.search(mode="standard", q="switches in ci907", env="retail"))

Usage from the CLI (thin wrapper around search, the workhorse endpoint):

    python3 kraken_client.py search --mode standard --q "switches in ci907" --env retail
    python3 kraken_client.py user_perms
    python3 kraken_client.py get /api/store_health --params store=ci907 env=retail
"""

import argparse
import base64
import json
import os
import stat
import sys

import requests

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass

KRAKEN_BASE = "https://kraken.kroger.com"

# Cached session cookie, reused across CLI invocations so we don't log in
# every call. Holds a live auth cookie, not the password - still sensitive,
# kept user-only (0600) next to the script.
SESSION_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".kraken_session.json")


class KrakenClient:
    def __init__(self, base_url=KRAKEN_BASE, euid=None, password=None):
        self.base_url = base_url
        self.euid = euid or os.environ.get("KRAKEN_EUID")
        self.password = password or self._password_from_env()
        self.session = requests.Session()
        # Kraken's cert isn't in this host's trust store.
        self.session.verify = False
        self._authenticated = False
        self._load_cached_session()

    @staticmethod
    def _password_from_env():
        b64 = os.environ.get("KRAKEN_PASSWORD_B64")
        if b64:
            # Strip trailing newline - a common artifact of `echo ... | base64` when
            # generating the value, which would otherwise corrupt the real password.
            return base64.b64decode(b64).decode("utf-8").rstrip("\n")
        return os.environ.get("KRAKEN_PASSWORD")

    def _load_cached_session(self):
        try:
            with open(SESSION_CACHE_PATH) as f:
                cached = json.load(f)
        except (FileNotFoundError, ValueError):
            return
        if cached.get("euid") != self.euid:
            return
        for name, value in cached.get("cookies", {}).items():
            self.session.cookies.set(name, value)
        if self.session.cookies:
            self._authenticated = True

    def _save_cached_session(self):
        data = {
            "euid": self.euid,
            "cookies": self.session.cookies.get_dict(),
        }
        with open(SESSION_CACHE_PATH, "w") as f:
            json.dump(data, f)
        os.chmod(SESSION_CACHE_PATH, stat.S_IRUSR | stat.S_IWUSR)

    def login(self):
        if not self.euid or not self.password:
            raise RuntimeError(
                "Missing credentials: set KRAKEN_EUID and KRAKEN_PASSWORD_B64 "
                "(base64-encoded password, e.g. in ~/.claude/.env) or pass "
                "euid/password to KrakenClient()."
            )
        resp = self.session.post(
            f"{self.base_url}/login",
            data={"euid": self.euid, "password": self.password},
            timeout=30,
        )
        resp.raise_for_status()
        if not self.session.cookies:
            # Some internal LDAP apps return 200 with an error page on bad
            # creds instead of a proper 4xx - don't claim success in that case.
            raise RuntimeError(
                "Kraken login did not return a session cookie - check credentials"
            )
        self._authenticated = True
        self._save_cached_session()
        return resp

    def _ensure_auth(self):
        if not self._authenticated:
            self.login()

    def _request(self, method, path, retried=False, **kwargs):
        self._ensure_auth()
        kwargs.setdefault("timeout", 30)
        resp = self.session.request(method, f"{self.base_url}{path}", **kwargs)
        if resp.status_code == 401 and not retried:
            # Cached cookie expired/invalid - force a fresh login and retry once.
            self._authenticated = False
            self.login()
            return self._request(method, path, retried=True, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def user_perms(self):
        return self._request("GET", "/api/user_perms")

    def search(self, mode="standard", q="", q2=None, div=None, env="retail",
               scope=None, page=None, all=None, field=None):
        params = {"mode": mode, "q": q, "env": env}
        for key, value in (
            ("q2", q2), ("div", div), ("scope", scope),
            ("page", page), ("all", all), ("field", field),
        ):
            if value is not None:
                params[key] = value
        return self._request("GET", "/api/search", params=params)

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, json_body=None):
        return self._request("POST", path, json=json_body)

    def poll_job(self, status_path, interval=3, timeout=600):
        import time
        elapsed = 0
        while elapsed < timeout:
            status = self.get(status_path)
            if status.get("status") in ("completed", "failed", "done", "error"):
                return status
            time.sleep(interval)
            elapsed += interval
        raise TimeoutError(f"Job at {status_path} did not finish within {timeout}s")


def rows_as_dicts(search_result):
    cols = search_result["columns"]
    return [dict(zip(cols, row)) for row in search_result["results"]]


def _main():
    parser = argparse.ArgumentParser(description="Kraken API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("user_perms")

    p_search = sub.add_parser("search")
    p_search.add_argument("--mode", default="standard")
    p_search.add_argument("--q", default="")
    p_search.add_argument("--q2")
    p_search.add_argument("--div")
    p_search.add_argument("--env", default="retail")
    p_search.add_argument("--scope")
    p_search.add_argument("--page")
    p_search.add_argument("--all")
    p_search.add_argument("--field")

    p_get = sub.add_parser("get")
    p_get.add_argument("path")
    p_get.add_argument("--params", nargs="*", default=[], help="key=value pairs")

    args = parser.parse_args()
    client = KrakenClient()

    if args.command == "user_perms":
        print(json.dumps(client.user_perms(), indent=2))
    elif args.command == "search":
        result = client.search(
            mode=args.mode, q=args.q, q2=args.q2, div=args.div,
            env=args.env, scope=args.scope, page=args.page, all=args.all,
            field=args.field,
        )
        print(json.dumps(result, indent=2))
    elif args.command == "get":
        params = dict(p.split("=", 1) for p in args.params)
        print(json.dumps(client.get(args.path, params=params), indent=2))


if __name__ == "__main__":
    sys.exit(_main())
