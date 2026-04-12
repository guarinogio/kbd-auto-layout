from __future__ import annotations

import re
import subprocess


_KEYBOARD_LINE_RE = re.compile(r"^\s*↳?\s*(?P<name>.+?)\s+id=\d+\s+\[slave\s+keyboard")
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


def list_keyboard_names() -> list[str]:
    result = subprocess.run(
        ["xinput", "list", "--long"],
        capture_output=True,
        text=True,
        check=True,
    )

    keyboards: list[str] = []
    for line in result.stdout.splitlines():
        match = _KEYBOARD_LINE_RE.search(line)
        if not match:
            continue
        name = match.group("name").strip()
        if not _is_real_keyboard_name(name):
            continue
        keyboards.append(name)

    return sorted(set(keyboards))


def is_device_connected(name: str) -> bool:
    return name in list_keyboard_names()
