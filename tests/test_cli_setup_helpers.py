from kbd_auto_layout.cli import _find_device_by_query
from kbd_auto_layout.models import KeyboardDevice


def test_find_device_by_query_unique_match():
    devices = [
        KeyboardDevice(name="AT Translated Set 2 keyboard"),
        KeyboardDevice(name="Keychron K2 Max"),
    ]

    assert _find_device_by_query(devices, "keychron").name == "Keychron K2 Max"


def test_find_device_by_query_ambiguous_returns_none():
    devices = [
        KeyboardDevice(name="Keychron K2 Max"),
        KeyboardDevice(name="Keychron K2 Max Keyboard"),
    ]

    assert _find_device_by_query(devices, "keychron") is None


def test_find_device_by_query_no_match_returns_none():
    devices = [KeyboardDevice(name="AT Translated Set 2 keyboard")]

    assert _find_device_by_query(devices, "logitech") is None
