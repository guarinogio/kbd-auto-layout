from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import time

from kbd_auto_layout.backends import detect_backend
from kbd_auto_layout.config import load_config
from kbd_auto_layout.logging_utils import setup_logging
from kbd_auto_layout.models import DeviceRule, GeneralConfig, KeyboardDevice
from kbd_auto_layout.xinput import clear_device_cache, match_rule_devices

log = logging.getLogger("kbd_auto_layout.daemon")

_reload_requested = False


def _handle_sighup(_signum, _frame) -> None:
    global _reload_requested
    _reload_requested = True


def sorted_rules(rules: list[DeviceRule]) -> list[DeviceRule]:
    return sorted(rules, key=lambda rule: rule.priority, reverse=True)


def find_active_rule() -> tuple[GeneralConfig, DeviceRule | None, list[KeyboardDevice]]:
    general, rules, _ = load_config()
    for rule in sorted_rules(rules):
        matches = match_rule_devices(rule, general.device_cache_ttl)
        if matches:
            return general, rule, matches
    return general, None, []


def apply_layout_verified(
    layout: str,
    variant: str,
    reason: str,
    general: GeneralConfig,
) -> bool:
    retries = max(1, general.apply_retries)
    delay = max(0.0, general.apply_retry_delay)
    backend = detect_backend(general.backend)

    for attempt in range(1, retries + 1):
        try:
            if backend.layout_matches(layout, variant):
                return True

            log.info(
                "Applying layout=%s variant=%s backend=%s reason=%s attempt=%s/%s",
                layout,
                variant,
                backend.name,
                reason,
                attempt,
                retries,
            )
            backend.set_layout(layout, variant)

            if backend.layout_matches(layout, variant):
                return True

        except (
            OSError,
            RuntimeError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            NotImplementedError,
        ) as exc:
            log.warning(
                "Failed to apply layout=%s variant=%s backend=%s for %s, attempt %s/%s: %s",
                layout,
                variant,
                backend.name,
                reason,
                attempt,
                retries,
                exc,
            )

        if attempt < retries:
            time.sleep(delay)

    log.warning(
        "Layout=%s variant=%s for %s was not active after %s attempts",
        layout,
        variant,
        reason,
        retries,
    )
    return False


def _device_names(devices: list[KeyboardDevice]) -> str:
    return ",".join(device.name for device in devices)


def _device_state(devices: list[KeyboardDevice]) -> tuple[str, ...]:
    return tuple(f"{device.name}:{device.hardware_id}" for device in devices)


def run_loop() -> None:
    global _reload_requested
    last_state: tuple[str, str, int, str, tuple[str, ...]] | None = None

    signal.signal(signal.SIGHUP, _handle_sighup)

    while True:
        if _reload_requested:
            log.info("Reloading configuration after SIGHUP")
            _reload_requested = False
            last_state = None
            clear_device_cache()

        general, rule, matches = find_active_rule()
        backend = detect_backend(general.backend)

        if rule is not None:
            state = (rule.layout, rule.variant, rule.priority, rule.match, _device_state(matches))
            if state != last_state or not backend.layout_matches(rule.layout, rule.variant):
                log.info(
                    "Active rule selected: name=%s priority=%s match=%s vid=%s pid=%s matched=%s",
                    rule.name,
                    rule.priority,
                    rule.match,
                    rule.vendor_id,
                    rule.product_id,
                    _device_names(matches),
                )
                if apply_layout_verified(rule.layout, rule.variant, f"rule {rule.name}", general):
                    log.info(
                        "Applied device rule: pattern=%s priority=%s match=%s vid=%s pid=%s "
                        "layout=%s variant=%s matched=%s",
                        rule.name,
                        rule.priority,
                        rule.match,
                        rule.vendor_id,
                        rule.product_id,
                        rule.layout,
                        rule.variant,
                        _device_names(matches),
                    )
                    last_state = state
                else:
                    last_state = None
        else:
            state = (general.default_layout, general.default_variant, 0, "default", ())
            if state != last_state or not backend.layout_matches(
                general.default_layout,
                general.default_variant,
            ):
                if apply_layout_verified(
                    general.default_layout,
                    general.default_variant,
                    "default layout",
                    general,
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
