---
name: sherpa
description: Query Sherpa (sherpa.kroger.com), Kroger's NOE infrastructure management framework - location details, IP subnets, floor plans, GPS coordinates, MS Teams GUIDs, AP/switch info, circuit/asset data. Use when the user asks about a store/location's network/facility details, IP subnet-to-location mapping, floor info, or circuit assets, or about Sherpa itself.
---

# Sherpa API Skill

Sherpa is Kroger's NOE (Network Operations Engineering) infrastructure management
framework, a REST API at `https://sherpa.kroger.com/api/public` (staging:
`https://sherpa-stage.kroger.com/api/public`, has test data). It covers three
areas: **location** (address, status, GPS, floor, MS Teams GUID, IP subnets),
**asset** (facility code lookup, circuits), and **monitor** (OpenNMS requisition
XML for all monitored assets).

Full spec: `reference/sherpa-openapi.json` (every path, parameter, and schema).
Read it when a task needs a field or endpoint not covered below.

## Auth

OAuth2 client-credentials, same flow as other Kroger-hosted APIs. Credentials
come from `~/.claude/.env` - reuses the same `KROGER_CLIENT_ID`/`KROGER_CLIENT_SECRET`
already configured for other Kroger API clients (e.g. the DSL/ESL data API), as
long as that client has been granted the relevant scope(s):

```
KROGER_CLIENT_ID=<client id>
KROGER_CLIENT_SECRET=<client secret>
```

Scopes (requested per endpoint, see the OpenAPI spec's `security` blocks):
- `urn:com:kroger:kr:sherpa:locations:read` / `:readwrite`
- `urn:com:kroger:kr:sherpa:assets:read` / `:readwrite`

If a call 401s/403s, the client likely lacks the needed scope - that's a
credential-provisioning issue, not something this skill can work around.

## Using it

Prefer calling `scripts/sherpa_client.py` via Bash rather than writing fresh
`requests` calls - it already handles the OAuth token fetch/cache/refresh.

```bash
# Location details for a facility code, short name, or "all"/"active"
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py location_detail --value go905 --status active

# All IP subnets for every location, or scoped to one facility
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py all_ip_subnets
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py all_ip_subnets_by_facility --facility_code go905

# Floor info by IP address, subnet (ip+cidr), or facility code
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py floor_by_ip_address --ip_address 192.168.100.1
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py floor_by_location --facility_code go905

# GPS coordinates, MS Teams GUID, AP/switch info
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py coordinates --facility_code go905
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py ms_guid --facility_code go905
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py ap_switch_by_location --facility_code go905

# Asset -> facility code, circuit info
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py facility_code_by_asset --asset_name go905osna1u
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py circuit_by_facility_code --facility_code go905
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py active_circuits_by_location --facility_code go905 --type all

# Arbitrary GET endpoint not covered by a subcommand
python3 ~/.claude/skills/sherpa/scripts/sherpa_client.py get /location/detail --params value=go905 status=active
```

For the two write endpoints (`update_ms_guid`, `update_coordinates`,
`tag_lab_location`, `update_notification`), import the client directly:

```python
import sys
sys.path.insert(0, "/Users/ad87019/.claude/skills/sherpa/scripts")
from sherpa_client import SherpaClient

s = SherpaClient()
s.update_coordinates(facility_code="go905", latitude="39.1", longitude="-84.5")
```

## Key things to know before acting

- **`facility_code`** accepts either the 8-digit format (`06000905`) or the
  short-name format (two letters + three digits, `go905`) - same convention as
  Kraken store codes but Sherpa calls the field `facility_code`, not `store`.
- **`value`** on `location_detail` is overloaded: `"all"`, a status keyword
  (`"active"`), a facility code, or a short name - check which one the user
  means before calling.
- **Response envelope**: every endpoint returns `{"status", "error", "results"}`
  (or `"requisition"`/`"foreign_source"` for the two `/monitor` endpoints) - the
  payload schema varies by endpoint, see the OpenAPI spec's `components.schemas`.
- **This is location/facility/circuit metadata, not live device health** - for
  switch/port status or MAC/IP device lookups, use the `kraken` skill instead;
  Sherpa is the complementary "where is this and what's its address/subnet/GUID"
  source. They correlate well by `facility_code`/store code.
- **Read-only by default for investigation use.** `update_ms_guid`,
  `update_coordinates`, `tag_lab_location`, and `update_notification` are
  write/notify endpoints - never call them during read-only investigation
  (e.g. from `investigatinator`) unless the user explicitly asks to correct a
  record.
