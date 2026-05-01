from kbd_auto_layout.daemon import find_active_rule, sorted_rules
from kbd_auto_layout.models import DeviceRule, GeneralConfig, KeyboardDevice


def test_sorted_rules_uses_priority_descending():
    rules = [
        DeviceRule(name="A", layout="us", priority=1),
        DeviceRule(name="B", layout="es", priority=10),
    ]

    assert [rule.name for rule in sorted_rules(rules)] == ["B", "A"]


def test_find_active_rule_returns_highest_priority_match(monkeypatch):
    general = GeneralConfig()
    rules = [
        DeviceRule(name="Keychron", layout="us", variant="", match="contains", priority=1),
        DeviceRule(
            name="Keychron K2 Max Keyboard",
            layout="es",
            variant="nodeadkeys",
            match="exact",
            priority=10,
        ),
    ]

    monkeypatch.setattr("kbd_auto_layout.daemon.load_config", lambda: (general, rules, []))

    def fake_match_rule_devices(rule, cache_ttl=2.0):
        if rule.name in ("Keychron", "Keychron K2 Max Keyboard"):
            return [KeyboardDevice(name="Keychron K2 Max Keyboard")]
        return []

    monkeypatch.setattr("kbd_auto_layout.daemon.match_rule_devices", fake_match_rule_devices)

    found_general, found_rule, matches = find_active_rule()

    assert found_general is general
    assert found_rule is rules[1]
    assert [device.name for device in matches] == ["Keychron K2 Max Keyboard"]


def test_find_active_rule_returns_default_when_no_match(monkeypatch):
    general = GeneralConfig()
    rules = [DeviceRule(name="Keychron", layout="us", variant="", match="contains")]

    monkeypatch.setattr("kbd_auto_layout.daemon.load_config", lambda: (general, rules, []))
    monkeypatch.setattr("kbd_auto_layout.daemon.match_rule_devices", lambda rule, cache_ttl=2.0: [])

    found_general, found_rule, matches = find_active_rule()

    assert found_general is general
    assert found_rule is None
    assert matches == []
