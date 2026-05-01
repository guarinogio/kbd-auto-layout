from __future__ import annotations

import subprocess

from kbd_auto_layout.backends import (
    SUBPROCESS_TIMEOUT_SECONDS,
    detect_backend,
    parse_setxkbmap_query,
)


def list_layouts() -> list[str]:
    result = subprocess.run(
        ["localectl", "list-x11-keymap-layouts"],
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def list_variants(layout: str) -> list[str]:
    result = subprocess.run(
        ["localectl", "list-x11-keymap-variants", layout],
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_valid_layout(layout: str) -> bool:
    return layout in list_layouts()


def is_valid_variant(layout: str, variant: str) -> bool:
    if variant == "":
        return True
    return variant in list_variants(layout)


def set_layout(layout: str, variant: str = "", backend: str = "auto") -> None:
    detect_backend(backend).set_layout(layout, variant)


def current_layout_query(backend: str = "auto") -> str:
    return detect_backend(backend).current_query()


def parse_current_xkb(query: str) -> tuple[str, str]:
    return parse_setxkbmap_query(query)


def current_layout(backend: str = "auto") -> tuple[str, str]:
    return detect_backend(backend).current_layout()


def layout_matches(layout: str, variant: str = "", backend: str = "auto") -> bool:
    return detect_backend(backend).layout_matches(layout, variant)
