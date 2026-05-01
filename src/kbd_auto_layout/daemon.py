from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import time

from kbd_auto_layout.config import load_config
from kbd_auto_layout.logging_utils import setup_logging
from kbd_auto_layout.xinput import match_device_names
from kbd_auto_layout.xkb import layout_matches, set_layout

log = logging.getLogger("kbd_auto_layout.daemon")

_reload_requested = False
APPLY_RETRIES = 5
APPLY_RETRY_DELAY_SECONDS = 1


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


def apply_layout_verified(layout: str, variant: str, reason: str) -> bool:
    for attempt in range(1, APPLY_RETRIES + 1):
        try:
            if layout_matches(layout, variant):
                return True

            set_layout(layout, variant)

            if layout_matches(layout, variant):
                return True

        except (OSError, subprocess.CalledProcessError) as exc:
            log.warning(
                "Failed to apply layout=%s variant=%s for %s, attempt %s/%s: %s",
                layout,
                variant,
                reason,
                attempt,
                APPLY_RETRIES,
                exc,
            )

        if attempt < APPLY_RETRIES:
            time.sleep(APPLY_RETRY_DELAY_SECONDS)

    log.warning(
        "Layout=%s variant=%s for %s was not active after %s attempts",
        layout,
        variant,
        reason,
        APPLY_RETRIES,
    )
    return False


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
            if state != last_state or not layout_matches(rule.layout, rule.variant):
                if apply_layout_verified(rule.layout, rule.variant, f"rule {rule.name}"):
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
                    last_state = None
        else:
            state = (general.default_layout, general.default_variant, "default", ())
            if state != last_state or not layout_matches(
                general.default_layout,
                general.default_variant,
            ):
                if apply_layout_verified(
                    general.default_layout,
                    general.default_variant,
                    "default layout",
                ):
                    log.info(
                        "Applied default layout: %s %s",
                        general.default_layout,
                        general.default_variant,
                    )
                    last_state = state
                else:
                    last_state = None

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
