from __future__ import annotations

import subprocess


def list_layouts() -> list[str]:
    result = subprocess.run(
        ["localectl", "list-x11-keymap-layouts"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def list_variants(layout: str) -> list[str]:
    result = subprocess.run(
        ["localectl", "list-x11-keymap-variants", layout],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def set_layout(layout: str, variant: str = "") -> None:
    cmd = ["setxkbmap", "-layout", layout]
    if variant:
        cmd.extend(["-variant", variant])
    else:
        cmd.extend(["-variant", ""])
    cmd.extend(["-option", ""])
    subprocess.run(cmd, check=True)


def current_layout_query() -> str:
    result = subprocess.run(
        ["setxkbmap", "-query"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
