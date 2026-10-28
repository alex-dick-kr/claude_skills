# servicenow

ServiceNow ITSM operations: incidents, changes, problems, service catalog, CMDB, and
companies.

## Skills

- `servicenow-itsm` -- see [skills/servicenow-itsm/SKILL.md](skills/servicenow-itsm/SKILL.md)
  for full usage.

## Required credentials

Reads from `~/.claude/.env`:

```
SERVICENOW_INSTANCE=https://kroger.service-now.com
SERVICENOW_USERNAME=<service account username>
SERVICENOW_PASSWORD=<service account password>
```

**This is a service account, not a personal credential.** Reach out to your manager for
service account information -- do not use your own ServiceNow login.

### Python dependencies

Only `certifi` (SSL certificate handling, required on macOS):

```
python -m pip install certifi
```

## Installation

```
/plugin marketplace add alex-dick-kr/claude_skills
/plugin install servicenow@claude-skills
```
