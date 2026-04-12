from kbd_auto_layout.xinput import match_device_names


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
