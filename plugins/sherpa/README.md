# sherpa

Query Sherpa (`sherpa.kroger.com`), Kroger's NOE infrastructure management
framework -- location details, IP subnets, floor plans, GPS coordinates, MS
Teams GUIDs, AP/switch info, and circuit/asset data.

## Skills

- `sherpa` -- see [skills/sherpa/SKILL.md](skills/sherpa/SKILL.md) for full usage.

## Required credentials

Reads from `~/.claude/.env`:

```
KROGER_CLIENT_ID=<client id>
KROGER_CLIENT_SECRET=<client secret>
```

This is a **Kroger OAuth2 client-credentials client** (the same kind used by
other Kroger-hosted APIs, e.g. the DSL/ESL data API) -- it must be granted the
`urn:com:kroger:kr:sherpa:locations:read` and/or `urn:com:kroger:kr:sherpa:assets:read`
scopes (or their `:readwrite` counterparts) before Sherpa calls will succeed.

## Installation

```
/plugin marketplace add https://github.com/alex-dick-kr/claude_skills
/plugin install sherpa@claude-skills
```
