from kbd_auto_layout.models import DeviceRule, GeneralConfig


def test_general_defaults():
    cfg = GeneralConfig()
    assert cfg.default_layout == "es"
    assert cfg.default_variant == "nodeadkeys"


def test_device_rule_defaults():
    rule = DeviceRule(name="Keychron K2 Max Keyboard", layout="us")
    assert rule.variant == ""
    assert rule.match == "exact"
