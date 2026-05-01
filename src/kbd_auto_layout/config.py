from __future__ import annotations

import configparser
from pathlib import Path

from kbd_auto_layout.models import DeviceRule, GeneralConfig

APP_NAME = "kbd-auto-layout"
USER_CONFIG = Path.home() / ".config" / APP_NAME / "config.ini"
SYSTEM_CONFIG = Path("/etc") / APP_NAME / "config.ini"


def ensure_user_config_dir() -> Path:
    USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    return USER_CONFIG.parent


def default_general_config() -> GeneralConfig:
    return GeneralConfig()


def _normalize_hex(value: str) -> str:
    value = (value or "").strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value.zfill(4) if value else ""


def default_config_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    general = default_general_config()
    parser["general"] = {
        "default_layout": general.default_layout,
        "default_variant": general.default_variant,
        "poll_interval": str(general.poll_interval),
        "apply_retries": str(general.apply_retries),
        "apply_retry_delay": str(general.apply_retry_delay),
        "backend": general.backend,
        "device_cache_ttl": str(general.device_cache_ttl),
        "event_mode": general.event_mode,
        "event_timeout": str(general.event_timeout),
    }
    return parser


def load_config() -> tuple[GeneralConfig, list[DeviceRule], list[Path]]:
    parser = configparser.ConfigParser()
    files_read = parser.read([str(SYSTEM_CONFIG), str(USER_CONFIG)])

    general = GeneralConfig()
    if parser.has_section("general"):
        general.default_layout = parser.get("general", "default_layout", fallback="es")
        general.default_variant = parser.get("general", "default_variant", fallback="nodeadkeys")
        general.poll_interval = parser.getint("general", "poll_interval", fallback=2)
        general.apply_retries = parser.getint("general", "apply_retries", fallback=5)
        general.apply_retry_delay = parser.getfloat("general", "apply_retry_delay", fallback=1.0)
        general.backend = parser.get("general", "backend", fallback="auto")
        general.device_cache_ttl = parser.getfloat("general", "device_cache_ttl", fallback=2.0)
        general.event_mode = parser.get("general", "event_mode", fallback="auto")
        general.event_timeout = parser.getfloat("general", "event_timeout", fallback=30.0)

    rules: list[DeviceRule] = []
    for section in parser.sections():
        if not section.startswith('device "') or not section.endswith('"'):
            continue
        device_name = section[len('device "') : -1]
        rules.append(
            DeviceRule(
                name=device_name,
                layout=parser.get(section, "layout", fallback="us"),
                variant=parser.get(section, "variant", fallback=""),
                match=parser.get(section, "match", fallback="exact"),
                vendor_id=_normalize_hex(parser.get(section, "vendor_id", fallback="")),
                product_id=_normalize_hex(parser.get(section, "product_id", fallback="")),
                priority=parser.getint(section, "priority", fallback=0),
            )
        )

    return general, rules, [Path(p) for p in files_read]


def save_user_config(general: GeneralConfig, rules: list[DeviceRule]) -> Path:
    ensure_user_config_dir()

    parser = configparser.ConfigParser()
    parser["general"] = {
        "default_layout": general.default_layout,
        "default_variant": general.default_variant,
        "poll_interval": str(general.poll_interval),
        "apply_retries": str(general.apply_retries),
        "apply_retry_delay": str(general.apply_retry_delay),
        "backend": general.backend,
        "device_cache_ttl": str(general.device_cache_ttl),
        "event_mode": general.event_mode,
        "event_timeout": str(general.event_timeout),
    }

    for rule in rules:
        section = f'device "{rule.name}"'
        parser[section] = {
            "layout": rule.layout,
            "variant": rule.variant,
            "match": rule.match,
            "priority": str(rule.priority),
        }
        if rule.vendor_id:
            parser[section]["vendor_id"] = rule.vendor_id
        if rule.product_id:
            parser[section]["product_id"] = rule.product_id

    with USER_CONFIG.open("w", encoding="utf-8") as fh:
        parser.write(fh)

    return USER_CONFIG


def init_user_config(force: bool = False) -> tuple[Path, bool]:
    ensure_user_config_dir()

    if USER_CONFIG.exists() and not force:
        return USER_CONFIG, False

    parser = default_config_parser()
    with USER_CONFIG.open("w", encoding="utf-8") as fh:
        parser.write(fh)

    return USER_CONFIG, True
