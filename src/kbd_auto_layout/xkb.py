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


def is_valid_layout(layout: str) -> bool:
    return layout in list_layouts()


def is_valid_variant(layout: str, variant: str) -> bool:
    if variant == "":
        return True
    return variant in list_variants(layout)


def set_layout(layout: str, variant: str = "") -> None:
    subprocess.run(
        ["setxkbmap", "-layout", layout, "-variant", variant or "", "-option", ""],
        check=True,
    )


def current_layout_query() -> str:
    result = subprocess.run(
        ["setxkbmap", "-query"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_current_xkb(query: str) -> tuple[str, str]:
    values: dict[str, str] = {}
    for line in query.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values.get("layout", ""), values.get("variant", "")


def current_layout() -> tuple[str, str]:
    return parse_current_xkb(current_layout_query())


def layout_matches(layout: str, variant: str = "") -> bool:
    return current_layout() == (layout, variant)
