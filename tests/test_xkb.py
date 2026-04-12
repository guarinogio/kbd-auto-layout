from kbd_auto_layout.xkb import is_valid_variant


def test_empty_variant_is_valid():
    assert is_valid_variant("es", "")
