from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from kbd_auto_layout import __version__
from kbd_auto_layout.config import USER_CONFIG, init_user_config, load_config, save_user_config
from kbd_auto_layout.models import DeviceRule
from kbd_auto_layout.xinput import is_device_connected, list_keyboard_names
from kbd_auto_layout.xkb import (
    current_layout_query,
    is_valid_layout,
    is_valid_variant,
    list_layouts,
    list_variants,
)


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _rule_to_dict(rule: DeviceRule) -> dict[str, object]:
    return {
        "name": rule.name,
        "layout": rule.layout,
        "variant": rule.variant,
        "match": rule.match,
        "connected": is_device_connected(rule.name),
    }


def cmd_list(args: argparse.Namespace) -> int:
    devices = []
    for name in list_keyboard_names():
        connected = is_device_connected(name)
        if args.connected and not connected:
            continue
        devices.append({"name": name, "connected": connected})

    if args.json:
        _print_json(devices)
        return 0

    for device in devices:
        status = "connected" if device["connected"] else "disconnected"
        print(f"{device['name']}\t{status}")
    return 0


def cmd_layouts(_args: argparse.Namespace) -> int:
    for layout in list_layouts():
        print(layout)
    return 0


def cmd_variants(args: argparse.Namespace) -> int:
    for variant in list_variants(args.layout):
        print(variant)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    general, rules, files_read = load_config()
    detected_keyboards = list_keyboard_names()

    data = {
        "config_files": [str(path) for path in files_read],
        "general": {
            "default_layout": general.default_layout,
            "default_variant": general.default_variant,
            "poll_interval": general.poll_interval,
        },
        "detected_keyboards": detected_keyboards,
        "rules": [_rule_to_dict(rule) for rule in rules],
        "current_xkb": current_layout_query().rstrip(),
    }

    if args.json:
        _print_json(data)
        return 0

    print("Config files:")
    if files_read:
        for path in files_read:
            print(f"  - {path}")
    else:
        print("  - none")

    print("\nGeneral:")
    print(f"  default_layout={general.default_layout}")
    print(f"  default_variant={general.default_variant}")
    print(f"  poll_interval={general.poll_interval}")

    print("\nDetected keyboards:")
    for name in detected_keyboards:
        print(f"  - {name}")

    print("\nRules:")
    if not rules:
        print("  (none)")
    else:
        for rule in rules:
            connected = "yes" if is_device_connected(rule.name) else "no"
            print(
                f'  - name="{rule.name}" layout="{rule.layout}" '
                f'variant="{rule.variant}" match="{rule.match}" connected="{connected}"'
            )

    print("\nCurrent XKB:")
    print(current_layout_query().rstrip())
    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    if not is_valid_layout(args.layout):
        print(f'Invalid layout: "{args.layout}"', file=sys.stderr)
        print("Run: kbd-auto-layoutctl layouts", file=sys.stderr)
        return 2

    if not is_valid_variant(args.layout, args.variant):
        print(
            f'Invalid variant "{args.variant}" for layout "{args.layout}"',
            file=sys.stderr,
        )
        print(f'Run: kbd-auto-layoutctl variants "{args.layout}"', file=sys.stderr)
        return 2

    general, rules, _ = load_config()

    updated = False
    for rule in rules:
        if rule.name == args.device:
            rule.layout = args.layout
            rule.variant = args.variant or ""
            updated = True
            break

    if not updated:
        rules.append(
            DeviceRule(
                name=args.device,
                layout=args.layout,
                variant=args.variant or "",
                match="exact",
            )
        )

    path = save_user_config(general, rules)
    print(f"Saved rule in {path}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    general, rules, _ = load_config()
    filtered = [rule for rule in rules if rule.name != args.device]

    if len(filtered) == len(rules):
        print("No matching rule found.", file=sys.stderr)
        return 1

    path = save_user_config(general, filtered)
    print(f"Removed rule from {path}")
    return 0


def cmd_set_default(args: argparse.Namespace) -> int:
    if not is_valid_layout(args.layout):
        print(f'Invalid layout: "{args.layout}"', file=sys.stderr)
        print("Run: kbd-auto-layoutctl layouts", file=sys.stderr)
        return 2

    if not is_valid_variant(args.layout, args.variant):
        print(
            f'Invalid variant "{args.variant}" for layout "{args.layout}"',
            file=sys.stderr,
        )
        print(f'Run: kbd-auto-layoutctl variants "{args.layout}"', file=sys.stderr)
        return 2

    general, rules, _ = load_config()
    general.default_layout = args.layout
    general.default_variant = args.variant or ""

    path = save_user_config(general, rules)
    print(f"Saved default layout in {path}")
    return 0


def cmd_set_poll_interval(args: argparse.Namespace) -> int:
    if args.seconds < 1:
        print("poll interval must be >= 1", file=sys.stderr)
        return 2

    general, rules, _ = load_config()
    general.poll_interval = args.seconds
    path = save_user_config(general, rules)
    print(f"Saved poll_interval={args.seconds} in {path}")
    return 0


def cmd_reload(_args: argparse.Namespace) -> int:
    result = subprocess.run(
        ["systemctl", "--user", "kill", "-s", "HUP", "kbd-auto-layout.service"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        return result.returncode or 1

    print("Reload signal sent.")
    return 0


def cmd_edit(_args: argparse.Namespace) -> int:
    USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["code", str(USER_CONFIG)], check=False)
    return 0


def cmd_init_config(args: argparse.Namespace) -> int:
    path, created = init_user_config(force=args.force)
    if created:
        print(f"Initialized config at {path}")
    else:
        print(f"Config already exists at {path}")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    checks: list[tuple[str, bool, str]] = []

    checks.append(
        (
            "XDG_SESSION_TYPE is x11",
            os.environ.get("XDG_SESSION_TYPE") == "x11",
            os.environ.get("XDG_SESSION_TYPE", ""),
        )
    )
    checks.append(
        ("DISPLAY is set", bool(os.environ.get("DISPLAY")), os.environ.get("DISPLAY", ""))
    )
    checks.append(
        ("XAUTHORITY is set", bool(os.environ.get("XAUTHORITY")), os.environ.get("XAUTHORITY", ""))
    )
    checks.append(
        ("xinput available", shutil.which("xinput") is not None, shutil.which("xinput") or "")
    )
    checks.append(
        (
            "setxkbmap available",
            shutil.which("setxkbmap") is not None,
            shutil.which("setxkbmap") or "",
        )
    )
    checks.append(
        (
            "localectl available",
            shutil.which("localectl") is not None,
            shutil.which("localectl") or "",
        )
    )

    service_ok = False
    service_detail = ""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "kbd-auto-layout.service"],
            capture_output=True,
            text=True,
            check=False,
        )
        service_ok = result.stdout.strip() == "active"
        service_detail = result.stdout.strip() or result.stderr.strip()
    except Exception as exc:
        service_detail = str(exc)

    checks.append(("user service active", service_ok, service_detail))

    failed = False
    for label, ok, detail in checks:
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {label}")
        if detail:
            print(f"      {detail}")
        if not ok:
            failed = True

    return 1 if failed else 0


def cmd_completion_zsh(_args: argparse.Namespace) -> int:
    completion_path = (
        Path(__file__).resolve().parents[2]
        / "packaging"
        / "completions"
        / "zsh"
        / "_kbd-auto-layoutctl"
    )
    print(completion_path.read_text(encoding="utf-8"), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kbd-auto-layoutctl")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List detected keyboard devices")
    p_list.add_argument("--connected", action="store_true", help="Show only connected devices")
    p_list.add_argument("--json", action="store_true", help="Output as JSON")
    p_list.set_defaults(func=cmd_list)

    p_layouts = sub.add_parser("layouts", help="List available X11 keyboard layouts")
    p_layouts.set_defaults(func=cmd_layouts)

    p_variants = sub.add_parser("variants", help="List variants for a layout")
    p_variants.add_argument("layout")
    p_variants.set_defaults(func=cmd_variants)

    p_status = sub.add_parser("status", help="Show config and current layout")
    p_status.add_argument("--json", action="store_true", help="Output as JSON")
    p_status.set_defaults(func=cmd_status)

    p_assign = sub.add_parser("assign", help="Assign layout to a device")
    p_assign.add_argument("device")
    p_assign.add_argument("layout")
    p_assign.add_argument("variant", nargs="?", default="")
    p_assign.set_defaults(func=cmd_assign)

    p_remove = sub.add_parser("remove", help="Remove a device rule")
    p_remove.add_argument("device")
    p_remove.set_defaults(func=cmd_remove)

    p_set_default = sub.add_parser("set-default", help="Set fallback default layout")
    p_set_default.add_argument("layout")
    p_set_default.add_argument("variant", nargs="?", default="")
    p_set_default.set_defaults(func=cmd_set_default)

    p_set_poll = sub.add_parser("set-poll-interval", help="Set polling interval in seconds")
    p_set_poll.add_argument("seconds", type=int)
    p_set_poll.set_defaults(func=cmd_set_poll_interval)

    p_reload = sub.add_parser("reload", help="Reload daemon config")
    p_reload.set_defaults(func=cmd_reload)

    p_edit = sub.add_parser("edit", help="Open user config in editor")
    p_edit.set_defaults(func=cmd_edit)

    p_init = sub.add_parser("init-config", help="Create default user config")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config")
    p_init.set_defaults(func=cmd_init_config)

    p_doctor = sub.add_parser("doctor", help="Run environment checks")
    p_doctor.set_defaults(func=cmd_doctor)

    p_completion = sub.add_parser("completion-zsh", help="Print zsh completion script")
    p_completion.set_defaults(func=cmd_completion_zsh)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
