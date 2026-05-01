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
from kbd_auto_layout.backends import detect_backend
from kbd_auto_layout.models import DeviceRule
from kbd_auto_layout.xinput import list_keyboard_devices, match_rule_devices
from kbd_auto_layout.xinput import list_keyboard_names, match_device_names
from kbd_auto_layout.xkb import (
    current_layout_query,
    is_valid_layout,
    is_valid_variant,
    list_layouts,
    list_variants,
)

MATCH_CHOICES = ("exact", "contains")


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _rule_to_dict(rule: DeviceRule) -> dict[str, object]:
    matched_devices = match_rule_devices(rule)
    return {
        "name": rule.name,
        "layout": rule.layout,
        "variant": rule.variant,
        "match": rule.match,
        "vendor_id": rule.vendor_id,
        "product_id": rule.product_id,
        "connected": bool(matched_devices),
        "matched_devices": [device.name for device in matched_devices],
        "matched_hardware_ids": [device.hardware_id for device in matched_devices if device.hardware_id],
    }


def cmd_list(args: argparse.Namespace) -> int:
    devices = []
    for device in list_keyboard_devices():
        if args.connected and not device.connected:
            continue
        devices.append(
            {
                "name": device.name,
                "connected": device.connected,
                "vendor_id": device.vendor_id,
                "product_id": device.product_id,
                "hardware_id": device.hardware_id,
            }
        )

    if args.json:
        _print_json(devices)
        return 0

    for device in devices:
        status = "connected" if device["connected"] else "disconnected"
        hardware = f"\t{device['hardware_id']}" if device["hardware_id"] else ""
        print(f"{device['name']}\t{status}{hardware}")
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
            "apply_retries": general.apply_retries,
            "apply_retry_delay": general.apply_retry_delay,
            "backend": general.backend,
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
    print(f"  apply_retries={general.apply_retries}")
    print(f"  apply_retry_delay={general.apply_retry_delay}")
    print(f"  backend={general.backend}")

    print("\nDetected keyboards:")
    for name in detected_keyboards:
        print(f"  - {name}")

    print("\nRules:")
    if not rules:
        print("  (none)")
    else:
        for rule in rules:
            matched_devices = match_device_names(rule.name, rule.match)
            connected = "yes" if matched_devices else "no"
            matched_text = ", ".join(matched_devices) if matched_devices else "-"
            print(
                f'  - name="{rule.name}" layout="{rule.layout}" '
                f'variant="{rule.variant}" match="{rule.match}" '
                f'vendor_id="{rule.vendor_id}" product_id="{rule.product_id}" '
                f'connected="{connected}" matched_devices="{matched_text}"'
            )

    print("\nCurrent XKB:")
    print(current_layout_query().rstrip())
    return 0



def cmd_rules(args: argparse.Namespace) -> int:
    _general, rules, _files_read = load_config()

    data = []
    for index, rule in enumerate(rules, start=1):
        item = _rule_to_dict(rule)
        item["index"] = index
        data.append(item)

    if args.json:
        _print_json(data)
        return 0

    if not rules:
        print("(no rules)")
        return 0

    for item in data:
        matched = ", ".join(item["matched_devices"]) if item["matched_devices"] else "-"
        connected = "yes" if item["connected"] else "no"
        hardware = ""
        if item["vendor_id"] or item["product_id"]:
            hardware = f' vendor_id="{item["vendor_id"]}" product_id="{item["product_id"]}"'
        print(
            f'{item["index"]}. name="{item["name"]}" '
            f'layout="{item["layout"]}" variant="{item["variant"]}" '
            f'match="{item["match"]}"{hardware} connected="{connected}" '
            f'matched_devices="{matched}"'
        )
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
        if rule.name == args.device and rule.match == args.match:
            rule.layout = args.layout
            rule.variant = args.variant or ""
            rule.vendor_id = (
                (getattr(args, "vendor_id", "") or "").lower().replace("0x", "").zfill(4)
                if getattr(args, "vendor_id", "")
                else rule.vendor_id
            )
            rule.product_id = (
                (getattr(args, "product_id", "") or "").lower().replace("0x", "").zfill(4)
                if getattr(args, "product_id", "")
                else rule.product_id
            )
            updated = True
            break

    if not updated:
        rules.append(
            DeviceRule(
                name=args.device,
                layout=args.layout,
                variant=args.variant or "",
                match=args.match,
                vendor_id=(getattr(args, "vendor_id", "") or "").lower().replace("0x", "").zfill(4)
                if getattr(args, "vendor_id", "")
                else "",
                product_id=(getattr(args, "product_id", "") or "").lower().replace("0x", "").zfill(4)
                if getattr(args, "product_id", "")
                else "",
            )
        )

    path = save_user_config(general, rules)
    print(f"Saved rule in {path}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    general, rules, _ = load_config()

    index = getattr(args, "index", None)

    if index is not None:
        if index < 1 or index > len(rules):
            print(f"No rule at index {index}.", file=sys.stderr)
            return 1
        filtered = [rule for idx, rule in enumerate(rules, start=1) if idx != index]
    else:
        if not args.device:
            print("Provide a device name or --index.", file=sys.stderr)
            return 2

        if args.match is None:
            filtered = [rule for rule in rules if rule.name != args.device]
        else:
            filtered = [
                rule
                for rule in rules
                if not (rule.name == args.device and rule.match == args.match)
            ]

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

    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    session_detail = session_type or "not set"
    if session_type == "wayland":
        session_detail = "wayland detected; kbd-auto-layout currently supports X11 only"

    backend = detect_backend("auto")
    checks.append(
        (
            "keyboard backend detected",
            backend.name != "unsupported",
            f"{backend.name}: {getattr(backend, 'reason', session_detail)}",
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


def cmd_watch(args: argparse.Namespace) -> int:
    import time

    previous = None
    while True:
        general, rules, _ = load_config()
        backend = detect_backend(general.backend)
        devices = list_keyboard_devices()

        active_rule = None
        active_matches = []
        for rule in rules:
            matches = match_rule_devices(rule)
            if matches:
                active_rule = rule
                active_matches = matches
                break

        target_layout = active_rule.layout if active_rule else general.default_layout
        target_variant = active_rule.variant if active_rule else general.default_variant
        state = (
            tuple((device.name, device.hardware_id) for device in devices),
            active_rule.name if active_rule else "default",
            target_layout,
            target_variant,
            backend.current_layout(),
        )

        if state != previous:
            print("Detected keyboards:")
            for device in devices:
                hardware = f" ({device.hardware_id})" if device.hardware_id else ""
                print(f"  - {device.name}{hardware}")

            if active_rule:
                print(
                    f'Active rule: "{active_rule.name}" '
                    f"layout={target_layout} variant={target_variant} "
                    f"matched={', '.join(device.name for device in active_matches)}"
                )
            else:
                print(f"Active rule: default layout={target_layout} variant={target_variant}")

            print(f"Backend: {backend.name}")
            print(f"Current layout: {backend.current_layout()}")
            print("")
            previous = state

        if args.once:
            return 0

        time.sleep(args.interval)


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

    p_rules = sub.add_parser("rules", help="List configured device rules")
    p_rules.add_argument("--json", action="store_true", help="Output as JSON")
    p_rules.set_defaults(func=cmd_rules)

    p_assign = sub.add_parser("assign", help="Assign layout to a device")
    p_assign.add_argument("device")
    p_assign.add_argument("layout")
    p_assign.add_argument("variant", nargs="?", default="")
    p_assign.add_argument("--match", choices=MATCH_CHOICES, default="exact")
    p_assign.add_argument("--vendor-id", help="USB/input vendor id, for example 05ac")
    p_assign.add_argument("--product-id", help="USB/input product id, for example 024f")
    p_assign.set_defaults(func=cmd_assign)

    p_remove = sub.add_parser("remove", help="Remove a device rule")
    p_remove.add_argument("device", nargs="?")
    p_remove.add_argument("--match", choices=MATCH_CHOICES)
    p_remove.add_argument("--index", type=int, help="Remove rule by index from `rules` output")
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

    p_watch = sub.add_parser("watch", help="Watch detected devices and active rule")
    p_watch.add_argument("--interval", type=float, default=2.0)
    p_watch.add_argument("--once", action="store_true")
    p_watch.set_defaults(func=cmd_watch)

    p_completion = sub.add_parser("completion-zsh", help="Print zsh completion script")
    p_completion.set_defaults(func=cmd_completion_zsh)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
