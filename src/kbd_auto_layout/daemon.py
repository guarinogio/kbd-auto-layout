from __future__ import annotations

import argparse
import logging
import time

from kbd_auto_layout.config import load_config
from kbd_auto_layout.logging_utils import setup_logging
from kbd_auto_layout.xinput import is_device_connected
from kbd_auto_layout.xkb import set_layout

log = logging.getLogger("kbd_auto_layout.daemon")


def find_active_rule():
    general, rules, _ = load_config()
    for rule in rules:
        if is_device_connected(rule.name):
            return general, rule
    return general, None


def run_loop() -> None:
    last_state: tuple[str, str] | None = None

    while True:
        general, rule = find_active_rule()

        if rule is not None:
            state = (rule.layout, rule.variant)
            if state != last_state:
                set_layout(rule.layout, rule.variant)
                log.info("Applied device rule: %s -> %s %s", rule.name, rule.layout, rule.variant)
                last_state = state
        else:
            state = (general.default_layout, general.default_variant)
            if state != last_state:
                set_layout(general.default_layout, general.default_variant)
                log.info(
                    "Applied default layout: %s %s",
                    general.default_layout,
                    general.default_variant,
                )
                last_state = state

        time.sleep(general.poll_interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kbd-auto-layoutd")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)
    run_loop()
