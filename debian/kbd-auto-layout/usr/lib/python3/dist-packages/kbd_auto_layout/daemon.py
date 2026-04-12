from __future__ import annotations

import argparse
import logging
import signal
import time

from kbd_auto_layout.config import load_config
from kbd_auto_layout.logging_utils import setup_logging
from kbd_auto_layout.xinput import match_device_names
from kbd_auto_layout.xkb import set_layout

log = logging.getLogger("kbd_auto_layout.daemon")

_reload_requested = False


def _handle_sighup(_signum, _frame) -> None:
    global _reload_requested
    _reload_requested = True


def find_active_rule():
    general, rules, _ = load_config()
    for rule in rules:
        matches = match_device_names(rule.name, rule.match)
        if matches:
            return general, rule, matches
    return general, None, []


def run_loop() -> None:
    global _reload_requested
    last_state: tuple[str, str, str, tuple[str, ...]] | None = None

    signal.signal(signal.SIGHUP, _handle_sighup)

    while True:
        if _reload_requested:
            log.info("Reloading configuration after SIGHUP")
            _reload_requested = False
            last_state = None

        general, rule, matches = find_active_rule()

        if rule is not None:
            state = (rule.layout, rule.variant, rule.match, tuple(matches))
            if state != last_state:
                set_layout(rule.layout, rule.variant)
                log.info(
                    "Applied device rule: pattern=%s match=%s layout=%s variant=%s matched=%s",
                    rule.name,
                    rule.match,
                    rule.layout,
                    rule.variant,
                    ",".join(matches),
                )
                last_state = state
        else:
            state = (general.default_layout, general.default_variant, "default", ())
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


if __name__ == "__main__":
    main()
