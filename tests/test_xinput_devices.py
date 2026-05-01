from kbd_auto_layout.models import DeviceRule, KeyboardDevice
from kbd_auto_layout.xinput import match_rule_devices


def test_match_rule_devices_by_vid_pid(monkeypatch):
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


def test_match_rule_devices_by_name_contains(monkeypatch):
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
