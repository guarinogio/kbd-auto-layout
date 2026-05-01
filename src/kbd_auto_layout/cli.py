from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from kbd_auto_layout import __version__
from kbd_auto_layout.backends import detect_backend
from kbd_auto_layout.config import USER_CONFIG, init_user_config, load_config, save_user_config
from kbd_auto_layout.daemon import find_active_rule, sorted_rules
from kbd_auto_layout.models import DeviceRule, KeyboardDevice
from kbd_auto_layout.xinput import list_keyboard_devices, match_rule_devices
from kbd_auto_layout.xkb import (
    current_layout_query,
    is_valid_layout,
    is_valid_variant,
    list_layouts,
    list_variants,
)

MATCH_CHOICES = ("exact", "contains")
BACKEND_CHOICES = ("auto", "x11", "wayland", "gnome-wayland")


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _normalize_hex(value: str | None) -> str:
    value = (value or "").strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value.zfill(4) if value else ""


def _device_to_dict(device: KeyboardDevice) -> dict[str, object]:
    return {
        "name": device.name,
        "connected": device.connected,
        "vendor_id": device.vendor_id,
        "product_id": device.product_id,
        "hardware_id": device.hardware_id,
    }


def _rule_to_dict(rule: DeviceRule) -> dict[str, object]:
    matched_devices = match_rule_devices(rule)
    return {
        "name": rule.name,
        "layout": rule.layout,
        "variant": rule.variant,
        "match": rule.match,
        "vendor_id": rule.vendor_id,
        "product_id": rule.product_id,
        "priority": rule.priority,
        "connected": bool(matched_devices),
        "matched_devices": [device.name for device in matched_devices],
        "matched_hardware_ids": [device.hardware_id for device in matched_devices if device.hardware_id],
    }


def cmd_list(args: argparse.Namespace) -> int:
    devices = []
    for device in list_keyboard_devices():
        if args.connected and not device.connected:
            continue
        devices.append(_device_to_dict(device))

    if args.json:
        _print_json(devices)
        return 0

    for device in devices:
        status = "connected" if device["connected"] else "disconnected"
        hardware = f"\t{device['hardware_id']}" if device["hardware_id"] else ""
        print(f"{device['name']}\t{status}{hardware}")
    return 0


def cmd_layouts(args: argparse.Namespace) -> int:
    layouts = list_layouts()
    if getattr(args, "json", False):
        _print_json(layouts)
        return 0
    for layout in layouts:
        print(layout)
    return 0


def cmd_variants(args: argparse.Namespace) -> int:
    variants = list_variants(args.layout)
    if getattr(args, "json", False):
        _print_json(variants)
        return 0
    for variant in variants:
        print(variant)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    general, rules, files_read = load_config()
    detected_keyboards = list_keyboard_devices()
    backend = detect_backend(general.backend)

    data = {
        "config_files": [str(path) for path in files_read],
        "general": {
            "default_layout": general.default_layout,
            "default_variant": general.default_variant,
            "poll_interval": general.poll_interval,
            "apply_retries": general.apply_retries,
            "apply_retry_delay": general.apply_retry_delay,
            "backend": general.backend,
            "device_cache_ttl": general.device_cache_ttl,
        },
        "backend": backend.name,
        "detected_keyboards": [_device_to_dict(device) for device in detected_keyboards],
        "rules": [_rule_to_dict(rule) for rule in sorted_rules(rules)],
        "current_xkb": current_layout_query(general.backend).rstrip(),
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
    print(f"  device_cache_ttl={general.device_cache_ttl}")

    print(f"\nBackend: {backend.name}")

    print("\nDetected keyboards:")
    for device in detected_keyboards:
        hardware = f" ({device.hardware_id})" if device.hardware_id else ""
        print(f"  - {device.name}{hardware}")

    print("\nRules:")
    if not rules:
        print("  (none)")
    else:
        for rule in sorted_rules(rules):
            matched_devices = match_rule_devices(rule)
            connected = "yes" if matched_devices else "no"
            matched_text = ", ".join(device.name for device in matched_devices) if matched_devices else "-"
            print(
                f'  - name="{rule.name}" layout="{rule.layout}" '
                f'variant="{rule.variant}" match="{rule.match}" priority="{rule.priority}" '
                f'vendor_id="{rule.vendor_id}" product_id="{rule.product_id}" '
                f'connected="{connected}" matched_devices="{matched_text}"'
            )

    print("\nCurrent XKB:")
    print(current_layout_query(general.backend).rstrip())
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    _general, rules, _files_read = load_config()

    data = []
    for index, rule in enumerate(sorted_rules(rules), start=1):
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
            f'match="{item["match"]}" priority="{item["priority"]}"{hardware} '
            f'connected="{connected}" matched_devices="{matched}"'
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
    vendor_id = _normalize_hex(getattr(args, "vendor_id", ""))
    product_id = _normalize_hex(getattr(args, "product_id", ""))
    priority = getattr(args, "priority", 0)

    updated = False
    for rule in rules:
        if rule.name == args.device and rule.match == args.match:
            rule.layout = args.layout
            rule.variant = args.variant or ""
            rule.priority = priority
            if vendor_id:
                rule.vendor_id = vendor_id
            if product_id:
                rule.product_id = product_id
            updated = True
            break

    if not updated:
        rules.append(
            DeviceRule(
                name=args.device,
                layout=args.layout,
                variant=args.variant or "",
                match=args.match,
                vendor_id=vendor_id,
                product_id=product_id,
                priority=priority,
            )
        )

    path = save_user_config(general, rules)
    print(f"Saved rule in {path}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    general, rules, _ = load_config()

    index = getattr(args, "index", None)

    if index is not None:
        ordered = sorted_rules(rules)
        if index < 1 or index > len(ordered):
            print(f"No rule at index {index}.", file=sys.stderr)
            return 1
        target = ordered[index - 1]
        removed = False
        filtered = []
        for rule in rules:
            if not removed and rule is target:
                removed = True
                continue
            filtered.append(rule)
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


def cmd_set_backend(args: argparse.Namespace) -> int:
    general, rules, _ = load_config()
    general.backend = args.backend
    path = save_user_config(general, rules)
    print(f"Saved backend={args.backend} in {path}")
    return 0


def cmd_set_device_cache_ttl(args: argparse.Namespace) -> int:
    if args.seconds < 0:
        print("device cache ttl must be >= 0", file=sys.stderr)
        return 2

    general, rules, _ = load_config()
    general.device_cache_ttl = args.seconds
    path = save_user_config(general, rules)
    print(f"Saved device_cache_ttl={args.seconds} in {path}")
    return 0


def cmd_reload(_args: argparse.Namespace) -> int:
    result = subprocess.run(
        ["systemctl", "--user", "kill", "-s", "HUP", "kbd-auto-layout.service"],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        return result.returncode or 1

    print("Reload signal sent.")
    return 0


def cmd_edit(_args: argparse.Namespace) -> int:
    USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    editor = os.environ.get("EDITOR") or "code"
    subprocess.run([editor, str(USER_CONFIG)], check=False, timeout=10)
    return 0


def cmd_init_config(args: argparse.Namespace) -> int:
    path, created = init_user_config(force=args.force)
    if created:
        print(f"Initialized config at {path}")
    else:
        print(f"Config already exists at {path}")
    return 0


def _watch_state() -> dict[str, object]:
    general, active_rule, matches = find_active_rule()
    backend = detect_backend(general.backend)
    devices = list_keyboard_devices()

    target_layout = active_rule.layout if active_rule else general.default_layout
    target_variant = active_rule.variant if active_rule else general.default_variant

    return {
        "backend": backend.name,
        "devices": [_device_to_dict(device) for device in devices],
        "active_rule": _rule_to_dict(active_rule) if active_rule else None,
        "matched_devices": [_device_to_dict(device) for device in matches],
        "target_layout": target_layout,
        "target_variant": target_variant,
        "current_layout": backend.current_layout(),
    }


def cmd_watch(args: argparse.Namespace) -> int:
    previous: dict[str, object] | None = None

    while True:
        state = _watch_state()

        if state != previous:
            if args.json:
                _print_json(state)
            else:
                if state["active_rule"]:
                    rule = state["active_rule"]
                    matched = ", ".join(device["name"] for device in state["matched_devices"])
                    print(
                        f'[+] {rule["name"]} priority={rule["priority"]} '
                        f'→ {state["target_layout"]} {state["target_variant"]} '
                        f'matched={matched}'
                    )
                else:
                    print(f'[~] default → {state["target_layout"]} {state["target_variant"]}')

                print(f'    backend={state["backend"]} current={state["current_layout"]}')

            previous = state

        if args.once:
            return 0

        time.sleep(args.interval)


def cmd_doctor(args: argparse.Namespace) -> int:
    checks: list[tuple[str, bool, str]] = []

    general, _rules, _files = load_config()
    backend = detect_backend(general.backend)
    backend_ok = backend.name not in {"unsupported", "wayland"}
    if args.json:
        _print_json(
            {
                "backend": backend.name,
                "backend_ok": backend_ok,
                "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
                "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
                "display": os.environ.get("DISPLAY", ""),
                "xauthority": os.environ.get("XAUTHORITY", ""),
                "tools": {
                    "xinput": shutil.which("xinput"),
                    "setxkbmap": shutil.which("setxkbmap"),
                    "localectl": shutil.which("localectl"),
                    "gsettings": shutil.which("gsettings"),
                },
            }
        )
        return 0 if backend_ok else 1

    detail = backend.name
    if backend.name == "wayland":
        detail = "generic Wayland detected; partial support only"
    if backend.name == "unsupported":
        detail = getattr(backend, "reason", "unsupported backend")

    checks.append(("keyboard backend detected", backend_ok, detail))
    checks.append(("DISPLAY is set", bool(os.environ.get("DISPLAY")), os.environ.get("DISPLAY", "")))
    checks.append(
        ("XAUTHORITY is set", bool(os.environ.get("XAUTHORITY")), os.environ.get("XAUTHORITY", ""))
    )
    checks.append(("xinput available", shutil.which("xinput") is not None, shutil.which("xinput") or ""))
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
            timeout=2,
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
    p_layouts.add_argument("--json", action="store_true", help="Output as JSON")
    p_layouts.set_defaults(func=cmd_layouts)

    p_variants = sub.add_parser("variants", help="List variants for a layout")
    p_variants.add_argument("layout")
    p_variants.add_argument("--json", action="store_true", help="Output as JSON")
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
    p_assign.add_argument("--vendor-id", help="USB/input vendor id, for example 3434")
    p_assign.add_argument("--product-id", help="USB/input product id, for example 0260")
    p_assign.add_argument("--priority", type=int, default=0)
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

    p_set_backend = sub.add_parser("set-backend", help="Set keyboard backend")
    p_set_backend.add_argument("backend", choices=BACKEND_CHOICES)
    p_set_backend.set_defaults(func=cmd_set_backend)

    p_set_cache = sub.add_parser("set-device-cache-ttl", help="Set device cache TTL in seconds")
    p_set_cache.add_argument("seconds", type=float)
    p_set_cache.set_defaults(func=cmd_set_device_cache_ttl)

    p_watch = sub.add_parser("watch", help="Watch detected devices and active rule")
    p_watch.add_argument("--interval", type=float, default=2.0)
    p_watch.add_argument("--once", action="store_true")
    p_watch.add_argument("--json", action="store_true")
    p_watch.set_defaults(func=cmd_watch)

    p_reload = sub.add_parser("reload", help="Reload daemon config")
    p_reload.set_defaults(func=cmd_reload)

    p_edit = sub.add_parser("edit", help="Open user config in editor")
    p_edit.set_defaults(func=cmd_edit)

    p_init = sub.add_parser("init-config", help="Create default user config")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config")
    p_init.set_defaults(func=cmd_init_config)

    p_doctor = sub.add_parser("doctor", help="Run environment checks")
    p_doctor.add_argument("--json", action="store_true", help="Output as JSON")
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
