from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

SUBPROCESS_TIMEOUT_SECONDS = 2


@dataclass
class KeyboardBackend:
    name: str

    def set_layout(self, layout: str, variant: str = "") -> None:
        raise NotImplementedError

    def current_query(self) -> str:
        raise NotImplementedError

    def current_layout(self) -> tuple[str, str]:
        raise NotImplementedError

    def layout_matches(self, layout: str, variant: str = "") -> bool:
        return self.current_layout() == (layout, variant)


class X11Backend(KeyboardBackend):
    def __init__(self) -> None:
        super().__init__("x11")

    def set_layout(self, layout: str, variant: str = "") -> None:
        subprocess.run(
            ["setxkbmap", "-layout", layout, "-variant", variant or "", "-option", ""],
            check=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )

    def current_query(self) -> str:
        result = subprocess.run(
            ["setxkbmap", "-query"],
            capture_output=True,
            text=True,
            check=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
        return result.stdout

    def current_layout(self) -> tuple[str, str]:
        return parse_setxkbmap_query(self.current_query())


class GnomeWaylandBackend(KeyboardBackend):
    def __init__(self) -> None:
        super().__init__("gnome-wayland")

    def set_layout(self, layout: str, variant: str = "") -> None:
        source = f"xkb:{layout}+{variant}" if variant else f"xkb:{layout}"
        subprocess.run(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.input-sources",
                "sources",
                f"[('xkb', '{source}')]",
            ],
            check=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )

    def current_query(self) -> str:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.input-sources", "sources"],
            capture_output=True,
            text=True,
            check=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
        return result.stdout

    def current_layout(self) -> tuple[str, str]:
        return parse_gnome_sources(self.current_query())


class WaylandBackend(KeyboardBackend):
    def __init__(self) -> None:
        super().__init__("wayland")

    def set_layout(self, layout: str, variant: str = "") -> None:
        raise NotImplementedError("Generic Wayland backend is not implemented yet")

    def current_query(self) -> str:
        return "Generic Wayland backend is not implemented yet"

    def current_layout(self) -> tuple[str, str]:
        return "", ""

    def layout_matches(self, layout: str, variant: str = "") -> bool:
        return False


class UnsupportedBackend(KeyboardBackend):
    def __init__(self, reason: str) -> None:
        super().__init__("unsupported")
        self.reason = reason

    def set_layout(self, layout: str, variant: str = "") -> None:
        raise RuntimeError(self.reason)

    def current_query(self) -> str:
        return self.reason

    def current_layout(self) -> tuple[str, str]:
        return "", ""


def parse_setxkbmap_query(query: str) -> tuple[str, str]:
    values: dict[str, str] = {}
    for line in query.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values.get("layout", ""), values.get("variant", "")


def parse_gnome_sources(value: str) -> tuple[str, str]:
    marker = "'xkb', '"
    if marker not in value:
        return "", ""
    source = value.split(marker, 1)[1].split("'", 1)[0]
    if source.startswith("xkb:"):
        source = source[4:]
    if "+" in source:
        layout, variant = source.split("+", 1)
        return layout, variant
    return source, ""


def detect_backend(configured_backend: str = "auto") -> KeyboardBackend:
    configured_backend = (configured_backend or "auto").lower()
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    if configured_backend in {"x11", "setxkbmap"}:
        return X11Backend()

    if configured_backend in {"gnome-wayland", "gnome"}:
        return GnomeWaylandBackend()

    if configured_backend == "wayland":
        return WaylandBackend()

    if configured_backend != "auto":
        return UnsupportedBackend(f"Unsupported backend: {configured_backend}")

    if session_type == "x11":
        return X11Backend()

    if session_type == "wayland" and "gnome" in desktop:
        return GnomeWaylandBackend()

    if session_type == "wayland":
        return WaylandBackend()

    return X11Backend()
