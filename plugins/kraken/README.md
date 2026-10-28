# kraken

Query and act on Kraken (`kraken.kroger.com`), Kroger's internal network asset API --
store/device search, MAC/IP lookups, switch port actions, ECS compliance, config/firmware
jobs.

## Skills

- `kraken` -- see [skills/kraken/SKILL.md](skills/kraken/SKILL.md) for full usage.

## Required credentials

Reads from `~/.claude/.env`:

```
KRAKEN_EUID=<your EUID>
KRAKEN_PASSWORD_B64=<base64-encoded password>
```

These are **personal credentials** (your own Kraken login), not a service account.

## Installation

```
/plugin marketplace add alex-dick-kr/claude_skills
/plugin install kraken@claude-skills
```
