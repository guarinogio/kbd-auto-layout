from kbd_auto_layout.models import DeviceRule, KeyboardDevice
from kbd_auto_layout.xinput import clear_device_cache, list_keyboard_devices_cached, match_rule_devices


def test_match_rule_devices_by_vid_pid(monkeypatch):
    clear_device_cache()
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_devices",
        lambda: [
            KeyboardDevice(name="Keychron K2", vendor_id="3434", product_id="0260"),
            KeyboardDevice(name="AT Keyboard", vendor_id="0001", product_id="0001"),
        ],
    )

    rule = DeviceRule(
        name="external",
        layout="us",
        vendor_id="3434",
        product_id="0260",
    )

    result = match_rule_devices(rule)

    assert [device.name for device in result] == ["Keychron K2"]


def test_match_rule_devices_by_partial_vid(monkeypatch):
    clear_device_cache()
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_devices",
        lambda: [
            KeyboardDevice(name="Keychron K2", vendor_id="3434", product_id="0260"),
            KeyboardDevice(name="Other", vendor_id="3434", product_id="9999"),
        ],
    )

    rule = DeviceRule(name="external", layout="us", vendor_id="3434")

    result = match_rule_devices(rule)

    assert [device.name for device in result] == ["Keychron K2", "Other"]


def test_match_rule_devices_by_name_contains(monkeypatch):
    clear_device_cache()
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_devices",
        lambda: [
            KeyboardDevice(name="Keychron K2", vendor_id="3434", product_id="0260"),
            KeyboardDevice(name="AT Keyboard", vendor_id="0001", product_id="0001"),
        ],
    )

    rule = DeviceRule(name="Keychron", layout="us", match="contains")

    result = match_rule_devices(rule)

    assert [device.name for device in result] == ["Keychron K2"]


def test_list_keyboard_devices_cached(monkeypatch):
    clear_device_cache()
    calls = {"count": 0}

    def fake_list_keyboard_devices():
        calls["count"] += 1
        return [KeyboardDevice(name="Keychron K2")]

    monkeypatch.setattr("kbd_auto_layout.xinput.list_keyboard_devices", fake_list_keyboard_devices)

    assert list_keyboard_devices_cached(ttl=10)[0].name == "Keychron K2"
    assert list_keyboard_devices_cached(ttl=10)[0].name == "Keychron K2"
    assert calls["count"] == 1
