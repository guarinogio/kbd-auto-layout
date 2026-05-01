from kbd_auto_layout.daemon import rule_specificity, sorted_rules
from kbd_auto_layout.models import DeviceRule


def test_rule_specificity_hardware_beats_exact_and_contains():
    hardware = DeviceRule(name="A", layout="us", vendor_id="3434")
    exact = DeviceRule(name="B", layout="us", match="exact")
    contains = DeviceRule(name="C", layout="us", match="contains")

    assert rule_specificity(hardware) > rule_specificity(exact)
    assert rule_specificity(exact) > rule_specificity(contains)


def test_sorted_rules_uses_priority_then_specificity():
    rules = [
        DeviceRule(name="contains", layout="us", match="contains", priority=10),
        DeviceRule(name="exact", layout="us", match="exact", priority=10),
        DeviceRule(name="hardware", layout="us", vendor_id="3434", priority=10),
        DeviceRule(name="low-priority-hardware", layout="us", vendor_id="3434", priority=1),
    ]

    ordered = sorted_rules(rules)

    assert [rule.name for rule in ordered] == [
        "hardware",
        "exact",
        "contains",
        "low-priority-hardware",
    ]
