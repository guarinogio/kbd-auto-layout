from kbd_auto_layout.daemon import find_active_rule
from kbd_auto_layout.models import DeviceRule, GeneralConfig


def test_find_active_rule_returns_first_match(monkeypatch):
    general = GeneralConfig()
    rules = [
        DeviceRule(name="Keychron", layout="us", variant="", match="contains"),
        DeviceRule(
            name="Keychron K2 Max Keyboard", layout="es", variant="nodeadkeys", match="exact"
        ),
    ]

    monkeypatch.setattr("kbd_auto_layout.daemon.load_config", lambda: (general, rules, []))
    monkeypatch.setattr(
        "kbd_auto_layout.daemon.match_device_names",
        lambda pattern, match: (
            ["Keychron K2 Max Keyboard"]
            if pattern in ("Keychron", "Keychron K2 Max Keyboard")
            else []
        ),
    )

    returned_general, rule, matches = find_active_rule()

    assert returned_general is general
    assert rule is not None
    assert rule.name == "Keychron"
    assert rule.match == "contains"
    assert matches == ["Keychron K2 Max Keyboard"]


def test_find_active_rule_returns_default_when_no_match(monkeypatch):
    general = GeneralConfig()
    rules = [DeviceRule(name="Keychron", layout="us", variant="", match="contains")]

    monkeypatch.setattr("kbd_auto_layout.daemon.load_config", lambda: (general, rules, []))
    monkeypatch.setattr("kbd_auto_layout.daemon.match_device_names", lambda pattern, match: [])

    returned_general, rule, matches = find_active_rule()

    assert returned_general is general
    assert rule is None
    assert matches == []
