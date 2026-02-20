#!/usr/bin/env python3
"""CLI Configuration Profile Manager.

A tool for creating, validating, listing, and switching between
named configuration profiles stored as JSON files.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".cli-config-manager"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
ACTIVE_FILE = CONFIG_DIR / "active_profile"

REQUIRED_SCHEMA_KEYS: list[str] = []

VALIDATION_RULES = {
    "database_url": lambda v: v.startswith(("postgres://", "mysql://", "sqlite://", "mongodb://")),
    "timeout": lambda v: isinstance(v, (int, float)) and v > 0,
    "retries": lambda v: isinstance(v, int) and 0 <= v <= 10,
    "log_level": lambda v: v.upper() in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
    "max_connections": lambda v: isinstance(v, int) and v > 0,
    "enable_cache": lambda v: isinstance(v, bool),
    "api_endpoint": lambda v: v.startswith(("http://", "https://")),
    "port": lambda v: isinstance(v, int) and 1 <= v <= 65535,
}


def ensure_config_dir():
    """Create the configuration directory and profiles file if they don't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILES_FILE.exists():
        PROFILES_FILE.write_text(json.dumps({"profiles": {}}, indent=2))


def load_profiles():
    """Load all profiles from disk."""
    ensure_config_dir()
    data = json.loads(PROFILES_FILE.read_text())
    return data["profiles"]


def save_profiles(profiles):
    """Persist profiles to disk."""
    data = {"profiles": profiles, "last_updated": datetime.now().isoformat()}
    PROFILES_FILE.write_text(json.dumps(data, indent=2))


def get_active_profile():
    """Return the name of the currently active profile, or None."""
    if ACTIVE_FILE.exists():
        return ACTIVE_FILE.read_text().strip()
    return None


def set_active_profile(name):
    """Write the active profile marker."""
    ACTIVE_FILE.write_text(name)


def validate_profile(profile_data, strict=False):
    """Validate a profile's configuration values.

    Args:
        profile_data: dict of key-value pairs for the profile.
        strict: if True, fail on any unknown keys without a rule.

    Returns:
        (bool, list[str]) — validity and a list of error messages.
    """
    errors = []

    for required_key in REQUIRED_SCHEMA_KEYS:
        if required_key not in profile_data:
            errors.append(f"Missing required key: {required_key}")

    if errors:
        return False, errors

    for key, value in profile_data.items():
        if key in REQUIRED_SCHEMA_KEYS:
            continue
        if key in VALIDATION_RULES:
            rule = VALIDATION_RULES[key]
            try:
                if not rule(value):
                    errors.append(f"Validation failed for '{key}': value '{value}' does not satisfy the rule")
            except Exception as exc:
                errors.append(f"Validation error for '{key}': {exc}")
        elif strict:
            errors.append(f"Unknown key '{key}' not in validation rules (strict mode)")

    return len(errors) == 0, errors


def cmd_create(args):
    """Create a new configuration profile from provided key=value pairs."""
    profiles = load_profiles()

    if args.name in profiles:
        if not args.force:
            print(f"Error: profile '{args.name}' already exists. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)

    config = {"name": args.name}
    for pair in args.entries:
        if "=" not in pair:
            print(f"Error: entry '{pair}' is not in key=value format.", file=sys.stderr)
            sys.exit(1)
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Attempt type coercion for common types
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.lstrip("-").isdigit():
            value = int(value)
        else:
            try:
                value = float(value)
            except ValueError:
                pass

        config[key] = value

    is_valid, errors = validate_profile(config)
    if not is_valid:
        print("Profile validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        if not args.skip_validation:
            sys.exit(1)
        print("Continuing because --skip-validation was provided.")

    profiles[args.name] = config
    save_profiles(profiles)
    print(f"Profile '{args.name}' created successfully with {len(config)} entries.")


def cmd_list(args):
    """List all stored configuration profiles."""
    profiles = load_profiles()
    active = get_active_profile()

    if not profiles:
        print("No profiles found.")
        return

    print(f"{'Name':<25} {'Entries':<10} {'Status'}")
    print("-" * 50)
    for name, config in sorted(profiles.items()):
        marker = " (active)" if name == active else ""
        print(f"  {name:<23} {len(config):<10} {marker}")


def cmd_show(args):
    """Display the contents of a specific profile."""
    profiles = load_profiles()

    if args.name not in profiles:
        print(f"Error: profile '{args.name}' does not exist.", file=sys.stderr)
        sys.exit(1)

    config = profiles[args.name]
    print(f"Profile: {args.name}")
    print(f"{'Key':<25} {'Value'}")
    print("-" * 50)
    for key, value in sorted(config.items()):
        print(f"  {key:<23} {value}")


def cmd_validate(args):
    """Validate one or all profiles against built-in rules."""
    profiles = load_profiles()
    has_errors = False

    target_names = [args.name] if args.name else list(profiles.keys())

    for pname in target_names:
        if pname not in profiles:
            print(f"Error: profile '{pname}' does not exist.", file=sys.stderr)
            has_errors = True
            continue

        is_valid, errors = validate_profile(profiles[pname], strict=args.strict)
        if is_valid:
            print(f"Profile '{pname}': PASS")
        else:
            print(f"Profile '{pname}': FAIL")
            for err in errors:
                print(f"    - {err}")
            has_errors = True

    if has_errors:
        sys.exit(1)
    else:
        print("All profiles passed validation.")


def cmd_activate(args):
    """Switch the active configuration profile."""
    profiles = load_profiles()

    if args.name not in profiles:
        print(f"Error: profile '{args.name}' does not exist. Create it first.", file=sys.stderr)
        sys.exit(1)

    is_valid, errors = validate_profile(profiles[args.name])
    if not is_valid:
        print(f"Warning: profile '{args.name}' has validation issues:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        if not args.force:
            print("Use --force to activate anyway.", file=sys.stderr)
            sys.exit(1)

    set_active_profile(args.name)
    print(f"Active profile switched to '{args.name}'.")


def cmd_delete(args):
    """Remove a configuration profile."""
    profiles = load_profiles()
    active = get_active_profile()

    if args.name not in profiles:
        print(f"Error: profile '{args.name}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if args.name == active:
        print(f"Error: cannot delete the active profile '{args.name}'. Switch first.", file=sys.stderr)
        sys.exit(1)

    del profiles[args.name]
    save_profiles(profiles)
    print(f"Profile '{args.name}' deleted.")


def cmd_export(args):
    """Export a profile to a JSON file for sharing or backup."""
    profiles = load_profiles()

    if args.name not in profiles:
        print(f"Error: profile '{args.name}' does not exist.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(f"Error: output file '{output_path}' exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    export_data = {"profile_name": args.name, "config": profiles[args.name]}
    output_path.write_text(json.dumps(export_data, indent=2))
    print(f"Profile '{args.name}' exported to '{output_path}'.")


def cmd_import(args):
    """Import a profile from a previously exported JSON file."""
    source = Path(args.file)
    if not source.exists():
        print(f"Error: file '{source}' does not exist.", file=sys.stderr)
        sys.exit(1)

    import_data = json.loads(source.read_text())
    profile_name = import_data.get("profile_name")
    config = import_data.get("config")

    if not profile_name or not config:
        print("Error: imported file is missing 'profile_name' or 'config' fields.", file=sys.stderr)
        sys.exit(1)

    profiles = load_profiles()

    if profile_name in profiles and not args.force:
        print(f"Error: profile '{profile_name}' already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    profiles[profile_name] = config
    save_profiles(profiles)
    print(f"Profile '{profile_name}' imported successfully.")


def main():
    parser = argparse.ArgumentParser(
        prog="cli-config-manager",
        description="Manage, validate, and switch between configuration profiles.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create
    p_create = subparsers.add_parser("create", help="Create a new profile")
    p_create.add_argument("name", help="Profile name")
    p_create.add_argument("entries", nargs="+", help="key=value pairs")
    p_create.add_argument("--force", action="store_true", help="Overwrite existing profile")
    p_create.add_argument("--skip-validation", action="store_true", help="Skip validation on creation")
    p_create.set_defaults(func=cmd_create)

    # list
    p_list = subparsers.add_parser("list", help="List all profiles")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subparsers.add_parser("show", help="Show profile contents")
    p_show.add_argument("name", help="Profile name")
    p_show.set_defaults(func=cmd_show)

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate profile(s)")
    p_validate.add_argument("name", nargs="?", default=None, help="Profile name (all if omitted)")
    p_validate.add_argument("--strict", action="store_true", help="Fail on unknown keys")
    p_validate.set_defaults(func=cmd_validate)

    # activate
    p_activate = subparsers.add_parser("activate", help="Switch active profile")
    p_activate.add_argument("name", help="Profile name")
    p_activate.add_argument("--force", action="store_true", help="Activate even if validation fails")
    p_activate.set_defaults(func=cmd_activate)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a profile")
    p_delete.add_argument("name", help="Profile name")
    p_delete.set_defaults(func=cmd_delete)

    # export
    p_export = subparsers.add_parser("export", help="Export a profile to file")
    p_export.add_argument("name", help="Profile name")
    p_export.add_argument("output", help="Output file path")
    p_export.add_argument("--force", action="store_true", help="Overwrite output file")
    p_export.set_defaults(func=cmd_export)

    # import
    p_import = subparsers.add_parser("import", help="Import a profile from file")
    p_import.add_argument("file", help="JSON file to import")
    p_import.add_argument("--force", action="store_true", help="Overwrite existing profile")
    p_import.set_defaults(func=cmd_import)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
