from kbd_auto_layout.backends import (
    WaylandBackend,
    detect_backend,
    parse_gnome_sources,
    parse_setxkbmap_query,
)


def test_parse_setxkbmap_query():
    query = """rules:      evdev
model:      pc105
layout:     es
variant:    nodeadkeys
"""
    assert parse_setxkbmap_query(query) == ("es", "nodeadkeys")


def test_parse_gnome_sources_simple():
    assert parse_gnome_sources("[('xkb', 'us')]") == ("us", "")


def test_parse_gnome_sources_variant():
    assert parse_gnome_sources("[('xkb', 'es+nodeadkeys')]") == ("es", "nodeadkeys")


def test_parse_gnome_sources_prefixed():
    assert parse_gnome_sources("[('xkb', 'xkb:es+nodeadkeys')]") == ("es", "nodeadkeys")


def test_detect_backend_generic_wayland(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "sway")
    assert isinstance(detect_backend("auto"), WaylandBackend)
