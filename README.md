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

## Adding this marketplace and installing plugins [Claude Code]

Use the `/plugin` slash command inside Claude Code to register this repo as a
marketplace and install plugins from it.

> See the official [Discovering and using plugins](https://code.claude.com/docs/en/discover-plugins.md) docs for the full reference.

### 1. Register this repo as a marketplace

The marketplace must contain `.claude-plugin/marketplace.json` at its root (this repo
does).

**From the GitHub repo (recommended -- no clone needed):**

```
/plugin marketplace add alex-dick-kr/claude_skills
```

**From a local clone of this repo instead:**

```
/plugin marketplace add ./path/to/claude_skills
```

(Pass either the repo root or the `marketplace.json` path directly.)

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
| kraken | Personal EUID/password | Your own Kraken login |
| powerbi | None (uses `az login`) | Run `az login` once |
| servicenow | **Service account** | Not self-service -- reach out to your manager for service account information |

Credentials are never stored in this repo. Each plugin reads its own values from
`~/.claude/.env` on the machine where Claude Code runs -- create or edit that file
directly, following the variable names listed in the plugin's README.

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
