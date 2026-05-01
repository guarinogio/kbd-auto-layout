from kbd_auto_layout.cli import cmd_disable, cmd_enable, cmd_restart


class Args:
    pass


def test_cmd_enable_runs_systemctl(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)

    assert cmd_enable(Args()) == 0
    assert calls == [["daemon-reload"], ["enable", "--now", "kbd-auto-layout.service"]]


def test_cmd_disable_runs_systemctl(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)

    assert cmd_disable(Args()) == 0
    assert calls == [["disable", "--now", "kbd-auto-layout.service"]]


def test_cmd_restart_runs_systemctl(monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return 0

    monkeypatch.setattr("kbd_auto_layout.cli._run_systemctl_user", fake_run)

    assert cmd_restart(Args()) == 0
    assert calls == [["daemon-reload"], ["restart", "kbd-auto-layout.service"]]
