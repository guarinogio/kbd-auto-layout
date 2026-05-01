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


def default_config_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    general = default_general_config()
    parser["general"] = {
        "default_layout": general.default_layout,
        "default_variant": general.default_variant,
        "poll_interval": str(general.poll_interval),
        "apply_retries": str(general.apply_retries),
        "apply_retry_delay": str(general.apply_retry_delay),
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
    }

    for rule in rules:
        section = f'device "{rule.name}"'
        parser[section] = {
            "layout": rule.layout,
            "variant": rule.variant,
            "match": rule.match,
        }

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
