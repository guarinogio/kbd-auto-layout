from kbd_auto_layout.xkb import is_valid_variant, parse_current_xkb


def test_empty_variant_is_valid():
    assert is_valid_variant("es", "")


def test_parse_current_xkb_with_variant():
    query = """rules:      evdev
model:      pc105
layout:     es
variant:    nodeadkeys
"""
    assert parse_current_xkb(query) == ("es", "nodeadkeys")


def test_parse_current_xkb_without_variant():
    query = """rules:      evdev
model:      pc105
layout:     us
"""
    assert parse_current_xkb(query) == ("us", "")
