from kbd_auto_layout.events import _is_relevant_input_event


def test_relevant_input_add_event():
    line = "UDEV  [123.0] add /devices/pci/input/input25 (input)"
    assert _is_relevant_input_event(line)


def test_relevant_input_remove_event():
    line = "UDEV  [123.0] remove /devices/pci/input/input25 (input)"
    assert _is_relevant_input_event(line)


def test_ignores_non_input_event():
    line = "UDEV  [123.0] add /devices/pci/block/sda (block)"
    assert not _is_relevant_input_event(line)


def test_ignores_input_line_without_action():
    line = "UDEV  [123.0] /devices/pci/input/input25 (input)"
    assert not _is_relevant_input_event(line)
