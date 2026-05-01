from __future__ import annotations

import re
import subprocess
import time

from kbd_auto_layout.backends import SUBPROCESS_TIMEOUT_SECONDS
from kbd_auto_layout.models import DeviceRule, KeyboardDevice

_KEYBOARD_LINE_RE = re.compile(
    r"^\s*↳?\s*(?P<name>.+?)\s+id=(?P<id>\d+)\s+\[slave\s+keyboard",
)
_PRODUCT_ID_RE = re.compile(r"Device Product ID:\s+(?P<vendor>\d+),\s+(?P<product>\d+)")
_UDEV_ID_RE = re.compile(r"ID_VENDOR_ID=(?P<vendor>[0-9a-fA-F]+).*?ID_MODEL_ID=(?P<product>[0-9a-fA-F]+)", re.S)

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

_CACHE_TS = 0.0
_CACHE_DATA: list[KeyboardDevice] = []


def _to_hex_id(value: str) -> str:
    return f"{int(value):04x}"


def _normalize_hex(value: str) -> str:
    value = (value or "").strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value.zfill(4) if value else ""


def clear_device_cache() -> None:
    global _CACHE_TS, _CACHE_DATA
    _CACHE_TS = 0.0
    _CACHE_DATA = []


def list_device_names() -> list[str]:
    result = subprocess.run(
        ["xinput", "list", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
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


def _device_product_ids_from_props(device_id: str) -> tuple[str, str]:
    result = subprocess.run(
        ["xinput", "list-props", device_id],
        capture_output=True,
        text=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return "", ""

    for line in result.stdout.splitlines():
        match = _PRODUCT_ID_RE.search(line)
        if match:
            return _to_hex_id(match.group("vendor")), _to_hex_id(match.group("product"))
    return "", ""


def _device_node_from_props(device_id: str) -> str:
    result = subprocess.run(
        ["xinput", "list-props", device_id],
        capture_output=True,
        text=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return ""

    for line in result.stdout.splitlines():
        if "Device Node" in line and '"' in line:
            return line.split('"', 1)[1].split('"', 1)[0]
    return ""


def _device_product_ids_from_udev(device_id: str) -> tuple[str, str]:
    node = _device_node_from_props(device_id)
    if not node:
        return "", ""

    result = subprocess.run(
        ["udevadm", "info", "--query=property", f"--name={node}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return "", ""

    vendor = ""
    product = ""
    for line in result.stdout.splitlines():
        if line.startswith("ID_VENDOR_ID="):
            vendor = _normalize_hex(line.split("=", 1)[1])
        elif line.startswith("ID_MODEL_ID="):
            product = _normalize_hex(line.split("=", 1)[1])

    return vendor, product


def _device_product_ids(device_id: str) -> tuple[str, str]:
    vendor, product = _device_product_ids_from_props(device_id)
    if vendor or product:
        return vendor, product

    return _device_product_ids_from_udev(device_id)


def list_keyboard_devices() -> list[KeyboardDevice]:
    result = subprocess.run(
        ["xinput", "list", "--long"],
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
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


def list_keyboard_devices_cached(ttl: float = 2.0) -> list[KeyboardDevice]:
    global _CACHE_TS, _CACHE_DATA
    now = time.time()
    if _CACHE_DATA and ttl > 0 and now - _CACHE_TS < ttl:
        return list(_CACHE_DATA)

    _CACHE_DATA = list_keyboard_devices()
    _CACHE_TS = now
    return list(_CACHE_DATA)


def list_keyboard_names() -> list[str]:
    return sorted({device.name for device in list_keyboard_devices_cached()})


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


def match_rule_devices(rule: DeviceRule, cache_ttl: float = 2.0) -> list[KeyboardDevice]:
    devices = list_keyboard_devices_cached(cache_ttl)

    if rule.vendor_id or rule.product_id:
        vendor_id = _normalize_hex(rule.vendor_id)
        product_id = _normalize_hex(rule.product_id)
        return [
            device
            for device in devices
            if (not vendor_id or device.vendor_id == vendor_id)
            and (not product_id or device.product_id == product_id)
        ]

    if rule.match == "exact":
        return [device for device in devices if device.name == rule.name]

    if rule.match == "contains":
        needle = rule.name.lower()
        return [device for device in devices if needle in device.name.lower()]

    raise ValueError(f"unsupported match mode: {rule.match}")
