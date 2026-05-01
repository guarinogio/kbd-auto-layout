from __future__ import annotations

import logging
import select
import shutil
import subprocess
import time
from dataclasses import dataclass

log = logging.getLogger("kbd_auto_layout.events")

UDEVADM_TIMEOUT_SECONDS = 2


@dataclass
class InputEvent:
    source: str
    line: str


class UdevInputMonitor:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None

    @property
    def available(self) -> bool:
        return shutil.which("udevadm") is not None

    def start(self) -> bool:
        if self.process and self.process.poll() is None:
            return True

        if not self.available:
            return False

        try:
            self.process = subprocess.Popen(
                ["udevadm", "monitor", "--udev", "--subsystem-match=input"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            return True
        except OSError as exc:
            log.warning("Failed to start udevadm monitor: %s", exc)
            self.process = None
            return False

    def stop(self) -> None:
        if not self.process:
            return

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=UDEVADM_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=UDEVADM_TIMEOUT_SECONDS)

        self.process = None

    def wait(self, timeout: float) -> InputEvent | None:
        if not self.start() or not self.process or not self.process.stdout:
            return None

        deadline = time.monotonic() + max(0.0, timeout)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            if self.process.poll() is not None:
                log.warning("udevadm monitor exited unexpectedly")
                self.process = None
                return None

            readable, _writable, _error = select.select(
                [self.process.stdout],
                [],
                [],
                remaining,
            )

            if not readable:
                return None

            line = self.process.stdout.readline()
            if not line:
                continue

            line = line.strip()
            if _is_relevant_input_event(line):
                return InputEvent(source="udev", line=line)


def _is_relevant_input_event(line: str) -> bool:
    lower = line.lower()
    if "/input/" not in lower:
        return False
    return any(action in lower for action in ("add", "remove", "change", "bind", "unbind"))


def event_monitor_available() -> bool:
    return shutil.which("udevadm") is not None
