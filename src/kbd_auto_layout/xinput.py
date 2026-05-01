from __future__ import annotations

import re
import subprocess

from kbd_auto_layout.models import DeviceRule, KeyboardDevice

_KEYBOARD_LINE_RE = re.compile(
    r"^\s*↳?\s*(?P<name>.+?)\s+id=(?P<id>\d+)\s+\[slave\s+keyboard",
)
_PRODUCT_ID_RE = re.compile(r"Device Product ID:\s+(?P<vendor>\d+),\s+(?P<product>\d+)")

_EXCLUDED_EXACT = {
    "Video Bus",
    "Power Button",
    "Sleep Button",
    "Ideapad extra buttons",
    "Intel HID events",
}
_EXCLUDED_SUBSTRINGS = (
    "Audio CODEC",
    "Headphone",
    "Consumer Control",
    "System Control",
)


def _to_hex_id(value: str) -> str:
    return f"{int(value):04x}"


def _normalize_hex(value: str) -> str:
    value = (value or "").strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value.zfill(4) if value else ""


def list_device_names() -> list[str]:
    result = subprocess.run(
        ["xinput", "list", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_real_keyboard_name(name: str) -> bool:
    if name.startswith("Virtual core"):
        return False
    if name.endswith("XTEST keyboard"):
        return False
    if name in _EXCLUDED_EXACT:
        return False
    if any(part in name for part in _EXCLUDED_SUBSTRINGS):
        return False
    return True


def _device_product_ids(device_id: str) -> tuple[str, str]:
    result = subprocess.run(
        ["xinput", "list-props", device_id],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "", ""

    for line in result.stdout.splitlines():
        match = _PRODUCT_ID_RE.search(line)
        if match:
            return _to_hex_id(match.group("vendor")), _to_hex_id(match.group("product"))
    return "", ""


def list_keyboard_devices() -> list[KeyboardDevice]:
    result = subprocess.run(
        ["xinput", "list", "--long"],
        capture_output=True,
        text=True,
        check=True,
    )

    found: dict[tuple[str, str, str], KeyboardDevice] = {}
    for line in result.stdout.splitlines():
        match = _KEYBOARD_LINE_RE.search(line)
        if not match:
            continue

        name = match.group("name").strip()
        if not _is_real_keyboard_name(name):
            continue

        vendor_id, product_id = _device_product_ids(match.group("id"))
        device = KeyboardDevice(
            name=name,
            connected=True,
            vendor_id=vendor_id,
            product_id=product_id,
        )
        found[(device.name, device.vendor_id, device.product_id)] = device

    return sorted(found.values(), key=lambda device: (device.name, device.vendor_id, device.product_id))


def list_keyboard_names() -> list[str]:
    return sorted({device.name for device in list_keyboard_devices()})


def is_device_connected(name: str) -> bool:
    return name in list_keyboard_names()


def match_device_names(pattern: str, match_mode: str) -> list[str]:
    names = list_keyboard_names()

    if match_mode == "exact":
        return [name for name in names if name == pattern]

    if match_mode == "contains":
        needle = pattern.lower()
        return [name for name in names if needle in name.lower()]

    raise ValueError(f"unsupported match mode: {match_mode}")


def match_rule_devices(rule: DeviceRule) -> list[KeyboardDevice]:
    devices = list_keyboard_devices()

    if rule.vendor_id and rule.product_id:
        vendor_id = _normalize_hex(rule.vendor_id)
        product_id = _normalize_hex(rule.product_id)
        return [
            device
            for device in devices
            if device.vendor_id == vendor_id and device.product_id == product_id
        ]

    if rule.match == "exact":
        return [device for device in devices if device.name == rule.name]

    if rule.match == "contains":
        needle = rule.name.lower()
        return [device for device in devices if needle in device.name.lower()]

    raise ValueError(f"unsupported match mode: {rule.match}")
