---
name: kraken
description: Query and act on Kraken (kraken.kroger.com), Kroger's internal network asset API - store/device search, MAC/IP lookups, switch port actions, ECS compliance, config/firmware jobs. Use when the user asks about store network devices, switches, ports, VLANs, MAC addresses, or Kraken itself.
---

# Kraken API Skill

Kraken (Kroger Remote Asset Kit for Enterprise Networking) is an internal REST API at
`https://kraken.kroger.com` covering store/DC/lab network inventory: devices, switches,
ports, VLANs, MAC/IP lookups, ECS port compliance, config deploy, and firmware jobs.

Full reference: `reference/KRAKEN_API_Guide.pdf` (auth, conventions, every endpoint family,
worked examples). Read it when a task needs an endpoint not covered below.

## Auth

LDAP-backed, session-cookie based - no API keys or bearer tokens. Credentials come from
`~/.claude/.env`:

```
KRAKEN_EUID=<your EUID>
KRAKEN_PASSWORD_B64=<base64-encoded password>
```

`scripts/kraken_client.py` reads these automatically and caches the resulting session
cookie on disk (`scripts/.kraken_session.json`, mode 0600) so it does NOT log in on every
call - only on first use or after the cached cookie is rejected (401), when it
re-authenticates automatically.

## Using it

Prefer calling `scripts/kraken_client.py` via Bash rather than writing fresh `requests`
calls - it already handles auth, cert verification (Kraken's cert isn't in the trust
store), and session caching.

```bash
# Confirm role/scope before doing real work
python3 ~/.claude/skills/kraken/scripts/kraken_client.py user_perms

# The workhorse: GET /api/search, 13 modes + natural-language "ai" mode
python3 ~/.claude/skills/kraken/scripts/kraken_client.py search --mode standard --q "switches in ci907" --env retail
python3 ~/.claude/skills/kraken/scripts/kraken_client.py search --mode mac --q "BCCA$" --div ci
python3 ~/.claude/skills/kraken/scripts/kraken_client.py search --mode stale --q "" --q2 30 --div ci

# Arbitrary GET endpoint
python3 ~/.claude/skills/kraken/scripts/kraken_client.py get /api/store_health --params store=ci907 env=retail
```

For POST/PUT actions (switch port toggle, notes, issues, job kickoff) or anything not
exposed by the CLI subcommands, import the client directly:

```python
import sys
sys.path.insert(0, "/Users/ad87019/.claude/skills/kraken/scripts")
from kraken_client import KrakenClient, rows_as_dicts

k = KrakenClient()
result = k.search(mode="standard", q="switches in ci907", env="retail")
rows = rows_as_dicts(result)

k.post("/api/switch/toggle_port", json_body={
    "store": "ci907", "device": "ar6405sw1", "ip": "10.x.x.x",
    "port": "1/3/13", "action": "disable",
})
```

## Key things to know before acting

- **Role matters.** `login` / `operator` / `superuser` / `admin` are enforced per-route.
  Write/action endpoints (port toggle, ECS enable/disable, config, firmware) need
  `operator+`. Check `user_perms` first if a call 403s.
- **Search envelope**: `{"results": [[...row...]], "columns": [...], "total", "returned",
  "page", "pages"}`. Map rows positionally against `columns`, or use `rows_as_dicts()`.
- **Store codes** are two letters + three digits (`ci907`). Numeric `DIV00STR` codes are
  auto-normalized on search endpoints.
- **Long-running jobs** (config deploy, firmware, ECS scan, cable diag, GDC route test)
  return `{"job_id": ...}` - poll the matching `.../job/<id>` endpoint until
  `status` is `completed`/`failed`, per the guide's §7 table.
- **Streaming endpoints** (`/api/fresh`, `/api/ping_stream`) are Server-Sent Events, not
  plain JSON - consume with `stream=True` and parse `data: ` lines.
- Confirm scope with `POST /api/scope/parse` before passing a raw multi-store `scope`
  string to search.
