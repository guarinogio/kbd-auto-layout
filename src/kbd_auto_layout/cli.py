from __future__ import annotations

import argparse
import subprocess
import sys

from kbd_auto_layout import __version__
from kbd_auto_layout.config import USER_CONFIG, load_config, save_user_config
from kbd_auto_layout.models import DeviceRule
from kbd_auto_layout.xinput import list_keyboard_names
from kbd_auto_layout.xkb import current_layout_query, list_layouts, list_variants


def cmd_list(_args: argparse.Namespace) -> int:
    for name in list_keyboard_names():
        print(name)
    return 0


def cmd_layouts(_args: argparse.Namespace) -> int:
    for layout in list_layouts():
        print(layout)
    return 0


def cmd_variants(args: argparse.Namespace) -> int:
    for variant in list_variants(args.layout):
        print(variant)
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    general, rules, files_read = load_config()

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

    print("\nRules:")
    if not rules:
        print("  (none)")
    else:
        for rule in rules:
            print(
                f'  - name="{rule.name}" layout="{rule.layout}" '
                f'variant="{rule.variant}" match="{rule.match}"'
            )

    print("\nCurrent XKB:")
    print(current_layout_query().rstrip())
    return 0


def cmd_assign(args: argparse.Namespace) -> int:
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


def cmd_edit(_args: argparse.Namespace) -> int:
    subprocess.run(["code", str(USER_CONFIG)], check=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kbd-auto-layoutctl")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List detected keyboard devices")
    p_list.set_defaults(func=cmd_list)

    p_layouts = sub.add_parser("layouts", help="List available X11 keyboard layouts")
    p_layouts.set_defaults(func=cmd_layouts)

    p_variants = sub.add_parser("variants", help="List variants for a layout")
    p_variants.add_argument("layout")
    p_variants.set_defaults(func=cmd_variants)

    p_status = sub.add_parser("status", help="Show config and current layout")
    p_status.set_defaults(func=cmd_status)

    p_assign = sub.add_parser("assign", help="Assign layout to a device")
    p_assign.add_argument("device")
    p_assign.add_argument("layout")
    p_assign.add_argument("variant", nargs="?", default="")
    p_assign.set_defaults(func=cmd_assign)

    p_remove = sub.add_parser("remove", help="Remove a device rule")
    p_remove.add_argument("device")
    p_remove.set_defaults(func=cmd_remove)

    p_edit = sub.add_parser("edit", help="Open user config in editor")
    p_edit.set_defaults(func=cmd_edit)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))
