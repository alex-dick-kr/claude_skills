# powerbi

Query Power BI workspaces, datasets, reports, and dataset refresh status via the Power BI
REST API.

## Skills

- `powerbi` -- see [skills/powerbi/SKILL.md](skills/powerbi/SKILL.md) for full usage.

## Required credentials

None stored by this skill. Auth uses your existing Azure CLI session (`az login`) --
no client secret to manage.

If you don't have the Azure CLI installed yet:

```
# macOS (Homebrew)
brew update && brew install azure-cli

# Windows (winget)
winget install -e --id Microsoft.AzureCLI
```

No admin rights? Both can require elevation -- install into your user Python
environment instead:

```
pip install --user azure-cli
```

Then run `az login` once per machine (signs in via browser with your Kroger Azure AD
account). Re-run it if the session expires later.

## Installation

```
/plugin marketplace add https://github.com/alex-dick-kr/claude_skills
/plugin install powerbi@claude-skills
```
