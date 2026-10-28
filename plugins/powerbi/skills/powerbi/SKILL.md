---
name: powerbi
description: Query Power BI workspaces, datasets, reports, and dataset refresh status via the Power BI REST API. Use when the user asks about Power BI reports/dashboards, dataset refresh health, DAX queries, or embedded Power BI content referenced by another app (e.g. Metrics That Matter).
---

# Power BI Skill

Wraps the Power BI REST API (`https://api.powerbi.com/v1.0/myorg`). Auth uses the
Azure CLI's signed-in session (`az login`) rather than a dedicated app registration -
no client secret to manage. Works as long as the signed-in Azure AD user
(`alex.dick@kroger.com`) has access to the relevant workspace(s).

## Prerequisite

Must already be signed in via `az login` (same session used elsewhere for Application
Insights / Azure Spring Apps queries in the sat-dashboard project). If a call fails with
"Not signed in to Azure," tell the user to run `az login` in a terminal.

## Using it

Prefer `scripts/powerbi_client.py` via Bash over hand-rolled `requests` calls - it
already handles token acquisition/caching and retry-on-401.

```bash
# List workspaces (groups) the signed-in user can see
python3 ~/.claude/skills/powerbi/scripts/powerbi_client.py workspaces

# Datasets/reports in one workspace (or omit --workspace for "My workspace")
python3 ~/.claude/skills/powerbi/scripts/powerbi_client.py datasets --workspace <group_id>
python3 ~/.claude/skills/powerbi/scripts/powerbi_client.py reports --workspace <group_id>

# Refresh history for a dataset
python3 ~/.claude/skills/powerbi/scripts/powerbi_client.py refreshes --workspace <group_id> --dataset <dataset_id>

# Kick off a refresh
python3 ~/.claude/skills/powerbi/scripts/powerbi_client.py trigger_refresh --workspace <group_id> --dataset <dataset_id>

# Run a DAX query directly against a dataset (needs Viewer/Build access, not XMLA)
python3 ~/.claude/skills/powerbi/scripts/powerbi_client.py dax --workspace <group_id> --dataset <dataset_id> \
    --query "EVALUATE TOPN(10, 'Table')"
```

For anything not exposed as a CLI subcommand, import the client directly:

```python
import sys
sys.path.insert(0, "/Users/ad87019/.claude/skills/powerbi/scripts")
from powerbi_client import PowerBIClient

pbi = PowerBIClient()
for ws in pbi.workspaces():
    print(ws["id"], ws["name"])
```

## Known workspaces (found via `workspaces`, 2026-10-16)

- **Store Health Dashboard - Dev/Test/Prod** - contains dataset+report both named
  `StoreHealthDashboard`, owned by the signed-in user. Prod workspace id:
  `8a651c65-ff45-45f9-b394-e5870ee7b45d`, dataset id `dc4ec83e-5b65-4c5a-9485-a60a203592e5`.
- 23 workspaces total are visible to this account; run `workspaces` for the current list
  rather than trusting this snapshot, since membership changes over time.

## Relevant context: Metrics That Matter (MTM)

The MTM Android app (see `~/Claude/reports/MI605_MTM_Slowness_Investigation_Report.md` and
the `project_mi605_mtm_slowness_investigation` memory) embeds a Power BI report via
`https://api.powerbi.com/v1.0/myorg/reports/{reportId}/pages`. If investigating MTM
"report slowness," this skill can check the underlying dataset's refresh history/failures
rather than guessing from app-side telemetry alone - that was an open lead in the prior
investigation (Azure connectivity to management.azure.com was blocked, but this API uses
`api.powerbi.com`/`analysis.windows.net`, a different audience, so it may not be
blocked the same way - worth testing if resuming that investigation).

## Admin-level calls

`activity_events(start_iso, end_iso)` hits `/admin/activityevents` (tenant-wide activity
log) - requires the signed-in user to hold a Power BI/Fabric admin role. Expect a 403 if
the account is not an admin; fall back to per-workspace calls instead.

## Limits / things to check before relying on results

- DAX query execution (`executeQueries`) needs the signed-in user to have dataset
  Build/Viewer permission - it is NOT the same as XMLA endpoint access, and some
  dataset/workspace configurations disable it.
- Token comes from `az account get-access-token --resource
  https://analysis.windows.net/powerbi/api` - if the CLI session expires, re-run
  `az login` interactively; this skill cannot do that itself.
