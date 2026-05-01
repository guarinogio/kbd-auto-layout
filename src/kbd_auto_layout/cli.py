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
from kbd_auto_layout.events import event_monitor_available
from kbd_auto_layout.daemon import find_active_rule, rule_specificity, sorted_rules
from kbd_auto_layout.models import DeviceRule, KeyboardDevice
from kbd_auto_layout.xinput import list_keyboard_devices, match_rule_devices, clear_device_cache
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
            "event_mode": general.event_mode,
            "event_timeout": general.event_timeout,
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
    print(f"  event_mode={general.event_mode}")
    print(f"  event_timeout={general.event_timeout}")

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


def cmd_set_event_mode(args: argparse.Namespace) -> int:
    general, rules, _ = load_config()
    general.event_mode = args.mode
    path = save_user_config(general, rules)
    print(f"Saved event_mode={args.mode} in {path}")
    return 0


def cmd_set_event_timeout(args: argparse.Namespace) -> int:
    if args.seconds < 1:
        print("event timeout must be >= 1", file=sys.stderr)
        return 2

    general, rules, _ = load_config()
    general.event_timeout = args.seconds
    path = save_user_config(general, rules)
    print(f"Saved event_timeout={args.seconds} in {path}")
    return 0



def _choose_device_interactively(devices):
    if not devices:
        print("No keyboards detected.", file=sys.stderr)
        return None

    print("Detected keyboards:")
    for idx, device in enumerate(devices, start=1):
        hardware = f" ({device.hardware_id})" if device.hardware_id else ""
        print(f"  {idx}. {device.name}{hardware}")

    raw = input("Select keyboard number: ").strip()
    try:
        index = int(raw)
    except ValueError:
        print("Invalid selection.", file=sys.stderr)
        return None

    if index < 1 or index > len(devices):
        print("Invalid selection.", file=sys.stderr)
        return None

    return devices[index - 1]


def _find_device_by_query(devices, query: str):
    query = query.lower()
    matches = [device for device in devices if query in device.name.lower()]
    if len(matches) == 1:
        return matches[0]
    return None


def _matching_devices_by_query(devices, query: str):
    query = query.lower()
    return [device for device in devices if query in device.name.lower()]


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _suggest_rule_command(device, layout: str, variant: str = "", priority: int = 10) -> str:
    args = [
        "kbd-auto-layoutctl",
        "use-current-keyboard",
        layout,
    ]
    if variant:
        args.append(variant)

    args.extend(
        [
            "--device",
            _shell_quote(device.name),
            "--exact",
            "--priority",
            str(priority),
        ]
    )

    if device.hardware_id:
        args.append("--hardware")

    return " ".join(args)


def cmd_detect(args: argparse.Namespace) -> int:
    clear_device_cache()
    devices = list_keyboard_devices()

    if not devices:
        print("No keyboards detected.")
        print()
        print("Check:")
        print("  kbd-auto-layoutctl doctor")
        return 1

    if args.json:
        data = []
        for device in devices:
            data.append(
                {
                    "name": device.name,
                    "vendor_id": device.vendor_id,
                    "product_id": device.product_id,
                    "hardware_id": device.hardware_id,
                    "suggested_command": _suggest_rule_command(
                        device,
                        args.layout,
                        args.variant,
                        args.priority,
                    ),
                }
            )
        _print_json(data)
        return 0

    print("Detected keyboards:")
    print()

    for idx, device in enumerate(devices, start=1):
        print(f"{idx}. {device.name}")
        if device.hardware_id:
            print(f"   hardware: {device.hardware_id}")
        else:
            print("   hardware: unavailable")
        print("   suggested:")
        print(f"     {_suggest_rule_command(device, args.layout, args.variant, args.priority)}")
        print()

    print("Tip:")
    print("  Use the suggested command for the external keyboard you want to map.")
    print("  Then run: kbd-auto-layoutctl reload")
    return 0


def cmd_use_current_keyboard(args: argparse.Namespace) -> int:
    clear_device_cache()
    devices = list_keyboard_devices()

    if args.device:
        matches = _matching_devices_by_query(devices, args.device)
        if len(matches) == 1:
            device = matches[0]
        elif not matches:
            print(f'No keyboard matched: "{args.device}"', file=sys.stderr)
            print("Run: kbd-auto-layoutctl list", file=sys.stderr)
            return 1
        else:
            print(f'Ambiguous keyboard query: "{args.device}"', file=sys.stderr)
            print("Matching keyboards:", file=sys.stderr)
            for match in matches:
                hardware = f" ({match.hardware_id})" if match.hardware_id else ""
                print(f"  - {match.name}{hardware}", file=sys.stderr)
            print("Use a more specific --device value or --interactive.", file=sys.stderr)
            return 2
    elif args.interactive:
        device = _choose_device_interactively(devices)
        if device is None:
            return 1
    elif len(devices) == 1:
        device = devices[0]
    else:
        print("Multiple keyboards detected. Use --device or --interactive.", file=sys.stderr)
        for device in devices:
            hardware = f" ({device.hardware_id})" if device.hardware_id else ""
            print(f"  - {device.name}{hardware}", file=sys.stderr)
        return 2

    if not is_valid_layout(args.layout):
        print(f'Invalid layout: "{args.layout}"', file=sys.stderr)
        return 2

    if not is_valid_variant(args.layout, args.variant):
        print(f'Invalid variant "{args.variant}" for layout "{args.layout}"', file=sys.stderr)
        return 2

    general, rules, _ = load_config()

    vendor_id = device.vendor_id if args.hardware and device.vendor_id else ""
    product_id = device.product_id if args.hardware and device.product_id else ""
    match = "exact" if args.exact else "contains"
    name = device.name if args.exact else args.pattern or device.name.split()[0]

    new_rule = DeviceRule(
        name=name,
        layout=args.layout,
        variant=args.variant or "",
        match=match,
        vendor_id=vendor_id,
        product_id=product_id,
        priority=args.priority,
    )

    updated = False
    for rule in rules:
        if rule.name == new_rule.name and rule.match == new_rule.match:
            rule.layout = new_rule.layout
            rule.variant = new_rule.variant
            rule.vendor_id = new_rule.vendor_id
            rule.product_id = new_rule.product_id
            rule.priority = new_rule.priority
            updated = True
            break

    if not updated:
        rules.append(new_rule)

    path = save_user_config(general, rules)
    print(f"Saved rule in {path}")
    print(f'Rule: name="{new_rule.name}" match="{new_rule.match}" layout="{new_rule.layout}" priority={new_rule.priority}')
    if new_rule.vendor_id or new_rule.product_id:
        print(f"Hardware: {new_rule.vendor_id}:{new_rule.product_id}")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    clear_device_cache()
    devices = list_keyboard_devices()

    print("kbd-auto-layout setup")
    print()

    default_layout = input(f"Default layout [{args.default_layout}]: ").strip() or args.default_layout
    default_variant = input(f"Default variant [{args.default_variant}]: ").strip() or args.default_variant

    device = _choose_device_interactively(devices)
    if device is None:
        return 1

    layout = input(f"Layout for {device.name} [{args.layout}]: ").strip() or args.layout
    variant = input("Variant for this keyboard []: ").strip()
    use_hardware = input("Use hardware ID if available? [Y/n]: ").strip().lower() not in {"n", "no"}

    general, rules, _ = load_config()
    general.default_layout = default_layout
    general.default_variant = default_variant

    rule = DeviceRule(
        name=device.name if not args.contains else args.contains,
        layout=layout,
        variant=variant,
        match="contains" if args.contains else "exact",
        vendor_id=device.vendor_id if use_hardware else "",
        product_id=device.product_id if use_hardware else "",
        priority=args.priority,
    )
    rules.append(rule)

    path = save_user_config(general, rules)
    print()
    print(f"Saved config in {path}")
    print("Run:")
    print("  kbd-auto-layoutctl reload")
    print("  kbd-auto-layoutctl status")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    general, rules, files = load_config()
    devices = list_keyboard_devices()
    _general, active_rule, active_matches = find_active_rule()

    if args.json:
        matched_rules = []
        for rule in sorted_rules(rules):
            matches = match_rule_devices(rule, general.device_cache_ttl)
            matched_rules.append(
                {
                    "name": rule.name,
                    "layout": rule.layout,
                    "variant": rule.variant,
                    "match": rule.match,
                    "priority": rule.priority,
                    "specificity": rule_specificity(rule),
                    "vendor_id": rule.vendor_id,
                    "product_id": rule.product_id,
                    "matched_devices": [device.name for device in matches],
                }
            )

        _print_json(
            {
                "config_files": [str(path) for path in files],
                "default": {
                    "layout": general.default_layout,
                    "variant": general.default_variant,
                    "backend": general.backend,
                    "event_mode": general.event_mode,
                },
                "detected_keyboards": [
                    {
                        "name": device.name,
                        "vendor_id": device.vendor_id,
                        "product_id": device.product_id,
                        "hardware_id": device.hardware_id,
                    }
                    for device in devices
                ],
                "active_rule": None
                if active_rule is None
                else {
                    "name": active_rule.name,
                    "layout": active_rule.layout,
                    "variant": active_rule.variant,
                    "match": active_rule.match,
                    "priority": active_rule.priority,
                    "specificity": rule_specificity(active_rule),
                    "matched_devices": [device.name for device in active_matches],
                },
                "rules": matched_rules,
            }
        )
        return 0

    if active_rule:
        layout_text = f"{active_rule.layout} {active_rule.variant}".strip()
        print(f"Active: {active_rule.name} -> {layout_text}")
        if active_rule.vendor_id or active_rule.product_id:
            print(
                f"Reason: hardware match {active_rule.vendor_id}:{active_rule.product_id} "
                f"(priority={active_rule.priority})"
            )
        else:
            print(
                f"Reason: {active_rule.match} match "
                f"(priority={active_rule.priority}, specificity={rule_specificity(active_rule)})"
            )
        print(f"Matched: {', '.join(device.name for device in active_matches)}")
    else:
        default_text = f"{general.default_layout} {general.default_variant}".strip()
        print(f"Active: default -> {default_text}")
        print("Reason: no configured rule matched.")

    print()

    if not rules:
        print("No rules configured.")
        print()
        print("Use:")
        print('  kbd-auto-layoutctl assign "My Keyboard" us')
        print("or:")
        print("  kbd-auto-layoutctl detect")
        return 0

    matched_rules = []
    unmatched_rules = []
    for rule in sorted_rules(rules):
        matches = match_rule_devices(rule, general.device_cache_ttl)
        if matches:
            matched_rules.append((rule, matches))
        else:
            unmatched_rules.append(rule)

    if len(matched_rules) > 1:
        print(f"Warning: {len(matched_rules)} rules match. Using highest priority/specificity:")
        for rule, matches in matched_rules:
            marker = "*" if active_rule is rule else "-"
            print(
                f"  {marker} {rule.name} -> {rule.layout} "
                f"(priority={rule.priority}, specificity={rule_specificity(rule)}, "
                f"matched={len(matches)})"
            )
        print()

    print("Rules:")
    for idx, rule in enumerate(sorted_rules(rules), start=1):
        matches = match_rule_devices(rule, general.device_cache_ttl)
        status = "MATCH" if matches else "no match"
        layout_text = f"{rule.layout} {rule.variant}".strip()
        hardware = ""
        if rule.vendor_id or rule.product_id:
            hardware = f" hardware={rule.vendor_id}:{rule.product_id}"
        print(
            f"  {idx}. {rule.name} -> {layout_text} "
            f"[{status}, priority={rule.priority}, specificity={rule_specificity(rule)}{hardware}]"
        )

    print()
    print("Detected keyboards:")
    for device in devices:
        hardware = f" ({device.hardware_id})" if device.hardware_id else ""
        print(f"  - {device.name}{hardware}")

    return 0

def _run_systemctl_user(args: list[str]) -> int:
    result = subprocess.run(
        ["systemctl", "--user", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def _systemctl_user_output(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        ["systemctl", "--user", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    output = result.stdout.strip() or result.stderr.strip()
    return result.returncode, output


def cmd_enable(_args: argparse.Namespace) -> int:
    rc = _run_systemctl_user(["daemon-reload"])
    if rc != 0:
        return rc

    _enabled_rc, enabled = _systemctl_user_output(["is-enabled", "kbd-auto-layout.service"])
    _active_rc, active = _systemctl_user_output(["is-active", "kbd-auto-layout.service"])

    if enabled == "enabled" and active == "active":
        print("kbd-auto-layout.service already enabled and running.")
        return 0

    rc = _run_systemctl_user(["enable", "--now", "kbd-auto-layout.service"])
    if rc == 0:
        print("kbd-auto-layout.service enabled and started.")
    return rc


def cmd_disable(_args: argparse.Namespace) -> int:
    _enabled_rc, enabled = _systemctl_user_output(["is-enabled", "kbd-auto-layout.service"])
    _active_rc, active = _systemctl_user_output(["is-active", "kbd-auto-layout.service"])

    if enabled != "enabled" and active != "active":
        print("kbd-auto-layout.service already stopped and disabled.")
        return 0

    rc = _run_systemctl_user(["disable", "--now", "kbd-auto-layout.service"])
    if rc == 0:
        print("kbd-auto-layout.service stopped and disabled.")
    return rc


def cmd_restart(_args: argparse.Namespace) -> int:
    rc = _run_systemctl_user(["daemon-reload"])
    if rc != 0:
        return rc
    rc = _run_systemctl_user(["restart", "kbd-auto-layout.service"])
    if rc == 0:
        print("kbd-auto-layout.service restarted.")
    return rc

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
                    "udevadm": shutil.which("udevadm"),
                },
                "event_monitor_available": event_monitor_available(),
            }
        )
        return 0 if backend_ok else 1

    detail = backend.name
    if backend.name == "wayland":
        detail = "generic Wayland detected; set backend=gnome-wayland for GNOME or use X11"
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
    checks.append(
        (
            "udevadm available",
            event_monitor_available(),
            shutil.which("udevadm") or "event-driven mode will fall back to polling",
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

    service_enabled = False
    service_enabled_detail = ""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", "kbd-auto-layout.service"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        service_enabled = result.stdout.strip() == "enabled"
        service_enabled_detail = result.stdout.strip() or result.stderr.strip()
    except Exception as exc:
        service_enabled_detail = str(exc)

    checks.append(("user service enabled", service_enabled, service_enabled_detail))

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

    p_set_event_mode = sub.add_parser("set-event-mode", help="Set event monitoring mode")
    p_set_event_mode.add_argument("mode", choices=("auto", "udev", "poll"))
    p_set_event_mode.set_defaults(func=cmd_set_event_mode)

    p_set_event_timeout = sub.add_parser("set-event-timeout", help="Set event wait timeout")
    p_set_event_timeout.add_argument("seconds", type=float)
    p_set_event_timeout.set_defaults(func=cmd_set_event_timeout)

    p_watch = sub.add_parser("watch", help="Watch detected devices and active rule")
    p_watch.add_argument("--interval", type=float, default=2.0)
    p_watch.add_argument("--once", action="store_true")
    p_watch.add_argument("--json", action="store_true")
    p_watch.set_defaults(func=cmd_watch)

    p_setup = sub.add_parser("setup", help="Interactive first-time setup wizard")
    p_setup.add_argument("--default-layout", default="es")
    p_setup.add_argument("--default-variant", default="nodeadkeys")
    p_setup.add_argument("--layout", default="us")
    p_setup.add_argument("--contains", help="Use contains matching with this pattern")
    p_setup.add_argument("--priority", type=int, default=10)
    p_setup.set_defaults(func=cmd_setup)

    p_use_current = sub.add_parser("use-current-keyboard", help="Create a rule from a connected keyboard")
    p_use_current.add_argument("layout")
    p_use_current.add_argument("variant", nargs="?", default="")
    p_use_current.add_argument("--device", help="Substring to select a connected keyboard")
    p_use_current.add_argument("--interactive", action="store_true")
    p_use_current.add_argument("--exact", action="store_true", help="Use exact name matching")
    p_use_current.add_argument("--pattern", help="Pattern to save when using contains matching")
    p_use_current.add_argument("--hardware", action="store_true", help="Prefer vendor/product matching")
    p_use_current.add_argument("--priority", type=int, default=10)
    p_use_current.set_defaults(func=cmd_use_current_keyboard)

    p_detect = sub.add_parser("detect", help="Detect keyboards and suggest rules")
    p_detect.add_argument("--layout", default="us", help="Layout to use in suggested commands")
    p_detect.add_argument("--variant", default="", help="Variant to use in suggested commands")
    p_detect.add_argument("--priority", type=int, default=10)
    p_detect.add_argument("--json", action="store_true", help="Output as JSON")
    p_detect.set_defaults(func=cmd_detect)

    p_explain = sub.add_parser("explain", help="Explain rule evaluation and active layout")
    p_explain.add_argument("--json", action="store_true", help="Output as JSON")
    p_explain.set_defaults(func=cmd_explain)

    p_enable = sub.add_parser("enable", help="Enable and start the user service")
    p_enable.set_defaults(func=cmd_enable)

    p_disable = sub.add_parser("disable", help="Stop and disable the user service")
    p_disable.set_defaults(func=cmd_disable)

    p_restart = sub.add_parser("restart", help="Restart the user service")
    p_restart.set_defaults(func=cmd_restart)

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
