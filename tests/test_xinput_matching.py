from kbd_auto_layout.xinput import match_device_names, match_rule_devices
from kbd_auto_layout.models import DeviceRule
from kbd_auto_layout.xinput import KeyboardDevice


def test_match_device_names_exact(monkeypatch):
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_names",
        lambda: ["AT Translated Set 2 keyboard", "Keychron K2 Max Keyboard"],
    )
    result = match_device_names("Keychron K2 Max Keyboard", "exact")
    assert result == ["Keychron K2 Max Keyboard"]


def test_match_device_names_contains(monkeypatch):
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_names",
        lambda: ["AT Translated Set 2 keyboard", "Keychron K2 Max Keyboard"],
    )
    result = match_device_names("Keychron", "contains")
    assert result == ["Keychron K2 Max Keyboard"]


def test_bluetooth_device_no_hardware_matches_name_only(monkeypatch):
    """Bluetooth devices with empty VID/PID should match by name."""
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_devices",
        lambda: [KeyboardDevice(name="Keychron K2 Max", vendor_id="", product_id="")],
    )
    rule = DeviceRule(name="Keychron K2 Max", layout="us", match="contains")
    result = match_rule_devices(rule, cache_ttl=0)
    assert len(result) == 1
    assert result[0].name == "Keychron K2 Max"


def test_bluetooth_device_excluded_by_hardware_rule(monkeypatch):
    """Rule with vendor_id should NOT match Bluetooth device with empty VID."""
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_devices",
        lambda: [KeyboardDevice(name="Keychron K2 Max", vendor_id="", product_id="")],
    )
    rule = DeviceRule(
        name="Keychron K2 Max", layout="us", match="contains",
        vendor_id="3434", product_id="0a20",
    )
    result = match_rule_devices(rule, cache_ttl=0)
    assert len(result) == 0
