from pathlib import Path

from kbd_auto_layout.cli import (
    cmd_assign,
    cmd_init_config,
    cmd_remove,
    cmd_rules,
    cmd_set_poll_interval,
)
from kbd_auto_layout.models import DeviceRule, GeneralConfig, KeyboardDevice
from kbd_auto_layout.xinput import match_device_names


class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_match_device_names_contains_no_match(monkeypatch):
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_names",
        lambda: ["AT Translated Set 2 keyboard", "Keychron K2 Max Keyboard"],
    )
    assert match_device_names("Logitech", "contains") == []


def test_match_device_names_invalid_mode(monkeypatch):
    monkeypatch.setattr(
        "kbd_auto_layout.xinput.list_keyboard_names",
        lambda: ["Keychron K2 Max Keyboard"],
    )
    try:
        match_device_names("Keychron", "regex")
    except ValueError as exc:
        assert "unsupported match mode" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid match mode")


def test_set_poll_interval_rejects_zero(monkeypatch):
    args = Args(seconds=0)
    rc = cmd_set_poll_interval(args)
    assert rc == 2


def test_remove_returns_error_when_rule_missing(monkeypatch):
    monkeypatch.setattr(
        "kbd_auto_layout.cli.load_config",
        lambda: (GeneralConfig(), [DeviceRule(name="Keychron", layout="us", match="exact")], []),
    )
    monkeypatch.setattr(
        "kbd_auto_layout.cli.save_user_config", lambda general, rules: Path("/tmp/config.ini")
    )
    args = Args(device="Logitech", match=None)
    rc = cmd_remove(args)
    assert rc == 1


def test_assign_updates_existing_rule(monkeypatch):
    saved = {}

    general = GeneralConfig()
    rules = [DeviceRule(name="Keychron", layout="us", variant="", match="contains")]

    monkeypatch.setattr("kbd_auto_layout.cli.is_valid_layout", lambda layout: True)
    monkeypatch.setattr("kbd_auto_layout.cli.is_valid_variant", lambda layout, variant: True)
    monkeypatch.setattr("kbd_auto_layout.cli.load_config", lambda: (general, rules, []))

    def fake_save_user_config(general_cfg, rules_cfg):
        saved["general"] = general_cfg
        saved["rules"] = rules_cfg
        return Path("/tmp/config.ini")

    monkeypatch.setattr("kbd_auto_layout.cli.save_user_config", fake_save_user_config)

    args = Args(device="Keychron", layout="es", variant="nodeadkeys", match="contains")
    rc = cmd_assign(args)

    assert rc == 0
    assert len(saved["rules"]) == 1
    assert saved["rules"][0].layout == "es"
    assert saved["rules"][0].variant == "nodeadkeys"
    assert saved["rules"][0].match == "contains"


def test_remove_with_specific_match_only_removes_that_rule(monkeypatch):
    saved = {}

    general = GeneralConfig()
    rules = [
        DeviceRule(name="Keychron", layout="us", variant="", match="exact"),
        DeviceRule(name="Keychron", layout="us", variant="", match="contains"),
    ]

    monkeypatch.setattr("kbd_auto_layout.cli.load_config", lambda: (general, rules, []))

    def fake_save_user_config(general_cfg, rules_cfg):
        saved["rules"] = rules_cfg
        return Path("/tmp/config.ini")

    monkeypatch.setattr("kbd_auto_layout.cli.save_user_config", fake_save_user_config)

    args = Args(device="Keychron", match="contains")
    rc = cmd_remove(args)

    assert rc == 0
    assert len(saved["rules"]) == 1
    assert saved["rules"][0].match == "exact"


def test_init_config_does_not_overwrite_without_force(monkeypatch, tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text("[general]\ndefault_layout = us\n", encoding="utf-8")

    monkeypatch.setattr("kbd_auto_layout.config.USER_CONFIG", config_path)
    monkeypatch.setattr("kbd_auto_layout.cli.init_user_config", lambda force: (config_path, False))

    args = Args(force=False)
    rc = cmd_init_config(args)

    assert rc == 0
    assert "default_layout = us" in config_path.read_text(encoding="utf-8")


def test_remove_by_index_removes_selected_rule(monkeypatch):
    saved = {}

    general = GeneralConfig()
    rules = [
        DeviceRule(name="Keychron", layout="us", variant="", match="contains"),
        DeviceRule(name="Logitech", layout="gb", variant="", match="contains"),
    ]

    monkeypatch.setattr("kbd_auto_layout.cli.load_config", lambda: (general, rules, []))

    def fake_save_user_config(general_cfg, rules_cfg):
        saved["rules"] = rules_cfg
        return Path("/tmp/config.ini")

    monkeypatch.setattr("kbd_auto_layout.cli.save_user_config", fake_save_user_config)

    args = Args(device=None, match=None, index=1)
    rc = cmd_remove(args)

    assert rc == 0
    assert len(saved["rules"]) == 1
    assert saved["rules"][0].name == "Logitech"


def test_remove_without_device_or_index_returns_usage_error(monkeypatch):
    monkeypatch.setattr("kbd_auto_layout.cli.load_config", lambda: (GeneralConfig(), [], []))

    args = Args(device=None, match=None, index=None)
    rc = cmd_remove(args)

    assert rc == 2


def test_rules_lists_rules(monkeypatch, capsys):
    rules = [DeviceRule(name="Keychron", layout="us", variant="", match="contains")]

    monkeypatch.setattr("kbd_auto_layout.cli.load_config", lambda: (GeneralConfig(), rules, []))
    monkeypatch.setattr(
        "kbd_auto_layout.cli.match_rule_devices",
        lambda rule: [KeyboardDevice(name="Keychron K2")],
    )

    args = Args(json=False)
    rc = cmd_rules(args)

    out = capsys.readouterr().out
    assert rc == 0
    assert '1. name="Keychron"' in out
    assert 'connected="yes"' in out



def test_assign_sets_priority_and_hardware(monkeypatch):
    saved = {}
    general = GeneralConfig()
    rules = []

    monkeypatch.setattr("kbd_auto_layout.cli.is_valid_layout", lambda layout: True)
    monkeypatch.setattr("kbd_auto_layout.cli.is_valid_variant", lambda layout, variant: True)
    monkeypatch.setattr("kbd_auto_layout.cli.load_config", lambda: (general, rules, []))

    def fake_save_user_config(general_cfg, rules_cfg):
        saved["rules"] = rules_cfg
        return Path("/tmp/config.ini")

    monkeypatch.setattr("kbd_auto_layout.cli.save_user_config", fake_save_user_config)

    args = Args(
        device="Keychron hardware",
        layout="us",
        variant="",
        match="contains",
        vendor_id="0x3434",
        product_id="0260",
        priority=50,
    )

    rc = cmd_assign(args)

    assert rc == 0
    assert saved["rules"][0].vendor_id == "3434"
    assert saved["rules"][0].product_id == "0260"
    assert saved["rules"][0].priority == 50
