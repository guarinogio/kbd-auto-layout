from __future__ import annotations

import subprocess


def list_device_names() -> list[str]:
    result = subprocess.run(
        ["xinput", "list", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def list_keyboard_names() -> list[str]:
    ignored_prefixes = {
        "Virtual core",
    }
    ignored_exact = {
        "Video Bus",
        "Power Button",
        "Sleep Button",
        "Ideapad extra buttons",
        "Intel HID events",
    }

    devices = list_device_names()
    keyboards: list[str] = []

    for name in devices:
        if any(name.startswith(prefix) for prefix in ignored_prefixes):
            continue
        if name in ignored_exact:
            continue
        if "Mouse" in name or "Touchpad" in name or "Trackball" in name:
            continue
        keyboards.append(name)

    return sorted(set(keyboards))


def is_device_connected(name: str) -> bool:
    return name in list_device_names()
