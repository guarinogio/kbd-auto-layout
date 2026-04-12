from __future__ import annotations

import re
import subprocess


_KEYBOARD_LINE_RE = re.compile(r"^\s*↳?\s*(?P<name>.+?)\s+id=\d+\s+\[slave\s+keyboard")


def list_device_names() -> list[str]:
    result = subprocess.run(
        ["xinput", "list", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


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
        if name.startswith("Virtual core"):
            continue
        if name.endswith("XTEST keyboard"):
            continue
        keyboards.append(name)

    return sorted(set(keyboards))


def is_device_connected(name: str) -> bool:
    return name in list_keyboard_names()
