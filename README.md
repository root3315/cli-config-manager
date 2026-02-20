# CLI Configuration Profile Manager

A command-line tool for creating, validating, listing, and switching between named configuration profiles. Profiles are stored as JSON in `~/.cli-config-manager/` and support built-in validation rules for common configuration keys.

## Installation

No external dependencies are required. The tool uses only the Python standard library.

```bash
chmod +x cli_config_manager.py
sudo cp cli_config_manager.py /usr/local/bin/config-manager
```

Or run directly:

```bash
python3 cli_config_manager.py <command>
```

## Quick Start

```bash
# Create a profile with configuration values
python3 cli_config_manager.py create production \
  database_url=postgres://db.example.com/myapp \
  timeout=30 \
  retries=3 \
  log_level=WARNING \
  max_connections=100 \
  enable_cache=true \
  api_endpoint=https://api.example.com \
  port=443

# List all profiles
python3 cli_config_manager.py list

# Activate a profile
python3 cli_config_manager.py activate production

# Validate all profiles
python3 cli_config_manager.py validate

# Export a profile for sharing
python3 cli_config_manager.py export production ./production.json

# Import a profile from a file
python3 cli_config_manager.py import ./production.json
```

## Commands

| Command | Description |
|---------|-------------|
| `create <name> <key=value>...` | Create a new profile from key-value pairs |
| `list` | List all stored profiles and show which is active |
| `show <name>` | Display the contents of a specific profile |
| `validate [name]` | Validate one profile or all profiles against built-in rules |
| `activate <name>` | Switch the active configuration profile |
| `delete <name>` | Remove a profile (cannot delete the active one) |
| `export <name> <file>` | Export a profile to a JSON file |
| `import <file>` | Import a profile from an exported JSON file |

## Global Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--force` | create, activate, export, import | Override safety checks (overwrite, activate invalid, etc.) |
| `--skip-validation` | create | Allow profile creation even if validation fails |
| `--strict` | validate | Fail validation on keys not in the built-in ruleset |

## Built-in Validation Rules

The following configuration keys have automatic validation:

| Key | Rule |
|-----|------|
| `database_url` | Must start with `postgres://`, `mysql://`, `sqlite://`, or `mongodb://` |
| `timeout` | Must be a positive number |
| `retries` | Must be an integer between 0 and 10 |
| `log_level` | Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `max_connections` | Must be a positive integer |
| `enable_cache` | Must be a boolean |
| `api_endpoint` | Must start with `http://` or `https://` |
| `port` | Must be an integer between 1 and 65535 |

Values entered as `true`/`false` are coerced to booleans, numeric strings are coerced to integers or floats automatically.

## Storage

All profiles are stored in `~/.cli-config-manager/profiles.json` as a single JSON file. The currently active profile is tracked in `~/.cli-config-manager/active_profile`.

## Example Session

```bash
$ python3 cli_config_manager.py create dev database_url=sqlite:///dev.db log_level=DEBUG timeout=10
Profile 'dev' created successfully with 3 entries.

$ python3 cli_config_manager.py create staging database_url=postgres://staging.db/myapp log_level=INFO retries=3 timeout=15
Profile 'staging' created successfully with 4 entries.

$ python3 cli_config_manager.py list
Name                      Entries    Status
--------------------------------------------------
  dev                       3
  staging                   4

$ python3 cli_config_manager.py activate dev
Active profile switched to 'dev'.

$ python3 cli_config_manager.py list
Name                      Entries    Status
--------------------------------------------------
  dev                       3           (active)
  staging                   4

$ python3 cli_config_manager.py validate
Profile 'dev': PASS
Profile 'staging': PASS
All profiles passed validation.

$ python3 cli_config_manager.py show dev
Profile: dev
Key                       Value
--------------------------------------------------
  database_url              sqlite:///dev.db
  log_level                 DEBUG
  timeout                   10

$ python3 cli_config_manager.py export dev ./dev-profile.json
Profile 'dev' exported to './dev-profile.json'.

$ python3 cli_config_manager.py delete staging
Profile 'staging' deleted.
```
