from kbd_auto_layout.cli import _shell_quote, _suggest_rule_command
from kbd_auto_layout.models import KeyboardDevice


def test_shell_quote_quotes_spaces():
    assert _shell_quote("Keychron K2") == "'Keychron K2'"


def test_shell_quote_escapes_single_quote():
    assert _shell_quote("Bob's Keyboard") == "'Bob'\\''s Keyboard'"


def test_suggest_rule_command_uses_hardware_when_available():
    device = KeyboardDevice(name="Keychron K2", vendor_id="3434", product_id="0a20")

    command = _suggest_rule_command(device, "us", "", 10)

    assert "kbd-auto-layoutctl use-current-keyboard us" in command
    assert "--device 'Keychron K2'" in command
    assert "--exact" in command
    assert "--hardware" in command
    assert "--priority 10" in command


def test_suggest_rule_command_omits_hardware_when_unavailable():
    device = KeyboardDevice(name="AT Keyboard")

    command = _suggest_rule_command(device, "es", "nodeadkeys", 5)

    assert "kbd-auto-layoutctl use-current-keyboard es nodeadkeys" in command
    assert "--hardware" not in command
