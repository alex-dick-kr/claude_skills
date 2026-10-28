# claude_skills

Claude Code plugins marketplace for **SAT Support** custom skills. This repo contains
shared skills that aren't part of Claude Code's official plugin marketplace --
Kraken, Power BI, and ServiceNow ITSM -- packaged the same way official plugins are, so
installing them is a single command instead of copying files by hand.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [kraken](plugins/kraken) | Query/act on Kraken (kraken.kroger.com) -- network asset search, switch port actions, ECS compliance, config/firmware jobs |
| [powerbi](plugins/powerbi) | Query Power BI workspaces, datasets, reports, and refresh status |
| [servicenow](plugins/servicenow) | ServiceNow ITSM: incidents, changes, problems, catalog, CMDB, companies |

## Prerequisites

Works on both macOS and Windows. Before installing, each person needs:

- **Claude Code** installed.
- **`uv`** -- the kraken and powerbi scripts use it to auto-install their Python
  dependencies on first run.
  ```
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Python 3 + `certifi`** -- only needed for the servicenow plugin (its scripts run on
  plain `python3`, not `uv`).
  ```
  python -m pip install certifi
  ```

> **No admin rights on your machine?** None of the above require it:
> - `uv`'s install script installs to your user profile (`~/.local/bin` or
>   `%USERPROFILE%\.local\bin`) -- no elevation needed.
> - Add `--user` to the pip command: `python -m pip install --user certifi`.
> - For Power BI's Azure CLI (see [Credentials](#credentials) below), skip the
>   Homebrew/winget install -- which can require admin -- and use
>   `pip install --user azure-cli` instead.

Per-plugin account/credential prerequisites are in [Credentials](#credentials) below.

## Adding this marketplace and installing plugins [Claude Code]

Use the `/plugin` slash command inside Claude Code to register this repo as a
marketplace and install plugins from it.

> See the official [Discovering and using plugins](https://code.claude.com/docs/en/discover-plugins.md) docs for the full reference.

### 1. Register this repo as a marketplace

```
/plugin marketplace add https://github.com/alex-dick-kr/claude_skills
```

> **If `/plugin marketplace add` was run before with the `owner/repo` shorthand**
> (e.g. `alex-dick-kr/claude_skills`) and failed with an SSH error, remove it first:
> ```
> /plugin marketplace remove claude-skills
> ```
> then re-run the `add` command above with the full `https://` URL -- the shorthand
> clones over SSH (port 22), which some corporate networks block.

### 2. Browse and install plugins

Open the interactive plugin browser:

```
/plugin
```

Tab to the **Discover** tab to see plugins available from registered marketplaces, then
select one to install.

Or install directly with a single command (format: `<plugin-name>@<marketplace-name>`):

```
/plugin install kraken@claude-skills
/plugin install powerbi@claude-skills
/plugin install servicenow@claude-skills
```

### 3. Other useful plugin commands

```
/plugin marketplace list                      # List configured marketplaces
/plugin                                       # Open the TUI (Discover / Installed / Marketplaces / Errors tabs)
/plugin disable kraken@claude-skills          # Disable a plugin without uninstalling
/plugin uninstall kraken@claude-skills
/reload-plugins                               # Reload after install/disable changes without restarting
```

### Scope (where the plugin is installed)

Append `--scope user|project|local` to install/enable commands to control whether the
plugin applies globally, to the current project, or only to your local checkout.

## Credentials

Each plugin's own README documents what it needs. Summary:

| Plugin | Credential type | Where to get it |
|--------|------------------|------------------|
| kraken | Personal EUID/password | Your own Kraken login. Don't have one? Go to [kraken.kroger.com](https://kraken.kroger.com) and request access -- it's not granted through this plugin. |
| powerbi | None (uses your existing Azure session) | Install the Azure CLI, then run `az login` once on your machine |
| servicenow | **Service account** | Not self-service -- reach out to your manager for service account information |

Credentials are never stored in this repo. Each plugin reads its own values from
`~/.claude/.env` on the machine where Claude Code runs (same path on macOS and Windows)
-- create or edit that file directly, following the variable names listed in the
plugin's README.

### Power BI: installing the Azure CLI and signing in

```
# macOS (Homebrew)
brew update && brew install azure-cli

# Windows (winget)
winget install -e --id Microsoft.AzureCLI
# or download/run the MSI: https://aka.ms/installazurecliwindows
```

No admin rights? Both of the above can require elevation. Install into your user
Python environment instead -- works on macOS and Windows:

```
pip install --user azure-cli
```

Then, on either OS:

```
az login
```

This opens a browser to sign in with your Kroger Azure AD account. The session it
creates is what the powerbi plugin reuses -- no separate credentials to store. Re-run
`az login` whenever the session expires (you'll see an auth error from the plugin when
that happens).

## Repository Structure

```
claude_skills/
├── README.md
├── .claude-plugin/
│   └── marketplace.json           # Central registry of all plugins
└── plugins/
    └── <plugin-name>/
        ├── README.md                  # Plugin overview, usage, and credentials
        ├── .claude-plugin/
        │   └── plugin.json          # Plugin-level manifest required by Claude Code's plugin loader
        └── skills/
            └── <skill-name>/
                ├── SKILL.md           # Required - skill definition (frontmatter + instructions)
                └── scripts/           # Helper scripts the skill invokes
```

Each **plugin** is a self-contained directory under `plugins/`. A skill is invoked as a
slash command in Claude Code using the format `/<plugin-name>:<skill-name>`.

## Adding a new skill to this marketplace

1. `mkdir -p plugins/<your-plugin>/skills/<your-skill>`
2. Write `skills/<your-skill>/SKILL.md` with YAML frontmatter (`name`, `description`) and
   markdown instructions.
3. Add `plugins/<your-plugin>/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "your-plugin",
     "version": "0.1.0",
     "description": "What your plugin does.",
     "author": { "name": "SAT Support" }
   }
   ```
4. Add a `plugins/<your-plugin>/README.md` documenting usage and credentials.
5. Register it in `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "your-plugin",
     "source": "./plugins/your-plugin",
     "description": "What your plugin does."
   }
   ```

Skills, commands, agents, hooks, and MCP servers are auto-discovered from each plugin's
conventional folders -- they do not need to be listed in `plugin.json`.
