#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["requests"]
# ///
"""
Power BI REST API client, authenticated via the Azure CLI's signed-in session
(`az login`) rather than a dedicated app registration - no client secret to manage,
works as long as the signed-in Azure AD user has Power BI workspace access.

Prereq: `az login` once, interactively, outside this script.

Usage as a library:

    from powerbi_client import PowerBIClient
    pbi = PowerBIClient()
    for ws in pbi.workspaces():
        print(ws["id"], ws["name"])

Usage from the CLI:

    python3 powerbi_client.py workspaces
    python3 powerbi_client.py datasets --workspace <group_id>
    python3 powerbi_client.py reports --workspace <group_id>
    python3 powerbi_client.py refreshes --workspace <group_id> --dataset <dataset_id>
    python3 powerbi_client.py dax --workspace <group_id> --dataset <dataset_id> --query "EVALUATE TOPN(10, 'Table')"
"""

import argparse
import json
import subprocess
import sys
import time

import requests

POWERBI_BASE = "https://api.powerbi.com/v1.0/myorg"
POWERBI_RESOURCE = "https://analysis.windows.net/powerbi/api"


class PowerBIClient:
    def __init__(self, base_url=POWERBI_BASE):
        self.base_url = base_url
        self._token = None
        self._token_exp = 0

    def _token_value(self):
        if self._token and time.time() < self._token_exp - 120:
            return self._token
        try:
            out = subprocess.run(
                ["az", "account", "get-access-token", "--resource", POWERBI_RESOURCE, "-o", "json"],
                capture_output=True, text=True, timeout=30,
            )
        except FileNotFoundError:
            raise RuntimeError("Azure CLI not found; install it and run `az login`")
        if out.returncode != 0:
            raise RuntimeError(f"Not signed in to Azure: run `az login` in a terminal, then retry.\n{out.stderr}")
        body = json.loads(out.stdout)
        self._token = body["accessToken"]
        # az returns expires_on as a unix timestamp string
        self._token_exp = int(body.get("expires_on", time.time() + 3300))
        return self._token

    def _request(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token_value()}"
        resp = requests.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        if resp.status_code == 401:
            # Token might have been invalidated early; force a refresh once and retry.
            self._token = None
            headers["Authorization"] = f"Bearer {self._token_value()}"
            resp = requests.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def workspaces(self):
        return self._request("GET", "/groups").get("value", [])

    def datasets(self, workspace_id=None):
        path = f"/groups/{workspace_id}/datasets" if workspace_id else "/datasets"
        return self._request("GET", path).get("value", [])

    def reports(self, workspace_id=None):
        path = f"/groups/{workspace_id}/reports" if workspace_id else "/reports"
        return self._request("GET", path).get("value", [])

    def dataset_refreshes(self, dataset_id, workspace_id=None, top=10):
        path = (f"/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
                if workspace_id else f"/datasets/{dataset_id}/refreshes")
        return self._request("GET", path, params={"$top": top}).get("value", [])

    def trigger_refresh(self, dataset_id, workspace_id=None):
        path = (f"/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
                if workspace_id else f"/datasets/{dataset_id}/refreshes")
        return self._request("POST", path)

    def execute_dax(self, dataset_id, dax_query, workspace_id=None):
        """Run a DAX query against a dataset. Requires the signed-in user to have
        at least Viewer/Build access to the dataset (XMLA endpoint not required)."""
        path = (f"/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
                if workspace_id else f"/datasets/{dataset_id}/executeQueries")
        body = {"queries": [{"query": dax_query}], "serializerSettings": {"includeNulls": True}}
        return self._request("POST", path, json=body)

    def activity_events(self, start_iso, end_iso):
        """Admin-level tenant activity log (requires Fabric/Power BI admin role)."""
        return self._request("GET", "/admin/activityevents",
                              params={"startDateTime": f"'{start_iso}'", "endDateTime": f"'{end_iso}'"})


def _main():
    parser = argparse.ArgumentParser(description="Power BI API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("workspaces")

    p_ds = sub.add_parser("datasets")
    p_ds.add_argument("--workspace")

    p_rp = sub.add_parser("reports")
    p_rp.add_argument("--workspace")

    p_rf = sub.add_parser("refreshes")
    p_rf.add_argument("--workspace")
    p_rf.add_argument("--dataset", required=True)
    p_rf.add_argument("--top", type=int, default=10)

    p_trigger = sub.add_parser("trigger_refresh")
    p_trigger.add_argument("--workspace")
    p_trigger.add_argument("--dataset", required=True)

    p_dax = sub.add_parser("dax")
    p_dax.add_argument("--workspace")
    p_dax.add_argument("--dataset", required=True)
    p_dax.add_argument("--query", required=True)

    args = parser.parse_args()
    client = PowerBIClient()

    if args.command == "workspaces":
        print(json.dumps(client.workspaces(), indent=2))
    elif args.command == "datasets":
        print(json.dumps(client.datasets(args.workspace), indent=2))
    elif args.command == "reports":
        print(json.dumps(client.reports(args.workspace), indent=2))
    elif args.command == "refreshes":
        print(json.dumps(client.dataset_refreshes(args.dataset, args.workspace, args.top), indent=2))
    elif args.command == "trigger_refresh":
        client.trigger_refresh(args.dataset, args.workspace)
        print("Refresh triggered.")
    elif args.command == "dax":
        print(json.dumps(client.execute_dax(args.dataset, args.query, args.workspace), indent=2))


if __name__ == "__main__":
    sys.exit(_main())
