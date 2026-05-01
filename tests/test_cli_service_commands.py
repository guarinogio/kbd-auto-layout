from kbd_auto_layout.cli import cmd_disable, cmd_enable, cmd_restart


class Args:
    pass


def test_cmd_enable_runs_systemctl_when_not_enabled(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    def fake_output(args):
        if args[0] == "is-enabled":
            return 1, "disabled"
        if args[0] == "is-active":
            return 1, "inactive"
        return 0, ""

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)
    monkeypatch.setattr("kbd_auto_layout.cli._systemctl_user_output", fake_output)

    assert cmd_enable(Args()) == 0
    assert calls == [["daemon-reload"], ["enable", "--now", "kbd-auto-layout.service"]]


def test_cmd_enable_noops_when_already_enabled_and_active(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    def fake_output(args):
        if args[0] == "is-enabled":
            return 0, "enabled"
        if args[0] == "is-active":
            return 0, "active"
        return 0, ""

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)
    monkeypatch.setattr("kbd_auto_layout.cli._systemctl_user_output", fake_output)

    assert cmd_enable(Args()) == 0
    assert calls == [["daemon-reload"]]


def test_cmd_disable_runs_systemctl_when_enabled(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    def fake_output(args):
        if args[0] == "is-enabled":
            return 0, "enabled"
        if args[0] == "is-active":
            return 0, "active"
        return 0, ""

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)
    monkeypatch.setattr("kbd_auto_layout.cli._systemctl_user_output", fake_output)

    assert cmd_disable(Args()) == 0
    assert calls == [["disable", "--now", "kbd-auto-layout.service"]]


def test_cmd_disable_noops_when_already_disabled(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    def fake_output(args):
        if args[0] == "is-enabled":
            return 1, "disabled"
        if args[0] == "is-active":
            return 1, "inactive"
        return 0, ""

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)
    monkeypatch.setattr("kbd_auto_layout.cli._systemctl_user_output", fake_output)

    assert cmd_disable(Args()) == 0
    assert calls == []


def test_cmd_restart_runs_systemctl(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)

    assert cmd_restart(Args()) == 0
    assert calls == [["daemon-reload"], ["restart", "kbd-auto-layout.service"]]
