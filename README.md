# kbd-auto-layout

Automatic keyboard layout switching for X11 based on connected keyboards.

## Overview

`kbd-auto-layout` is a lightweight daemon and CLI tool that automatically switches your keyboard layout depending on which keyboard is connected.

It is designed for setups where you use:
- a laptop keyboard with one layout, such as Spanish
- an external keyboard with another layout, such as English

The daemon monitors connected input devices and applies the appropriate layout automatically.

## Features

- Automatic layout switching based on connected keyboards
- Per-device rules with `exact` or `contains` matching
- Default fallback layout
- User-level systemd service
- CLI for configuration and inspection
- JSON output for inspection commands
- Zsh completion
- Debian package support
- Man pages

## Requirements

- Linux with X11
- `xinput`
- `setxkbmap`
- `localectl`
- `systemd --user`

## Install from GitHub Releases

```bash
wget https://github.com/guarinogio/kbd-auto-layout/releases/download/v1.0.0/kbd-auto-layout_1.0.0_all.deb
sudo apt install ./kbd-auto-layout_1.0.0_all.deb
systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Install from a local `.deb`

```bash
sudo dpkg -i ./kbd-auto-layout_1.0.0_all.deb
systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Basic usage

### List detected keyboards

```bash
kbd-auto-layoutctl list
```

### List available layouts

```bash
kbd-auto-layoutctl layouts
```

### List variants for a layout

```bash
kbd-auto-layoutctl variants es
```

### Assign a layout to a specific keyboard

```bash
kbd-auto-layoutctl assign "Keychron K2 Max Keyboard" us
```

### Assign a layout using substring matching

```bash
kbd-auto-layoutctl assign "Keychron" us --match contains
```

### Set default layout

```bash
kbd-auto-layoutctl set-default es nodeadkeys
```

### Reload daemon configuration

```bash
kbd-auto-layoutctl reload
```

### Show current status

```bash
kbd-auto-layoutctl status
```

### Run diagnostics

```bash
kbd-auto-layoutctl doctor
```

## Configuration

Configuration files:

- User config: `~/.config/kbd-auto-layout/config.ini`
- System config: `/etc/kbd-auto-layout/config.ini`

Example:

```ini
[general]
default_layout = es
default_variant = nodeadkeys
poll_interval = 2

[device "Keychron K2 Max Keyboard"]
layout = us
variant =
match = exact
```

## How it works

- The daemon polls connected input devices
- It matches them against configured rules in order
- The first matching rule is applied
- If no rule matches, the default layout is used

## Service management

Start:

```bash
systemctl --user start kbd-auto-layout.service
```

Stop:

```bash
systemctl --user stop kbd-auto-layout.service
```

Restart:

```bash
systemctl --user restart kbd-auto-layout.service
```

Logs:

```bash
journalctl --user -u kbd-auto-layout.service -f
```

## Troubleshooting

Check the environment:

```bash
kbd-auto-layoutctl doctor
```

Common issues:
- Not running X11
- Missing `xinput` or `setxkbmap`
- Service not enabled
- A stale user unit overriding the packaged unit

Check which unit is active:

```bash
systemctl --user status kbd-auto-layout.service --no-pager -l
```

## Development

```bash
python -m venv ~/.venvs/kbd-auto-layout
source ~/.venvs/kbd-auto-layout/bin/activate
pip install -e ".[dev]"
```

Run checks:

```bash
make format
make lint
make test
```

Build the Debian package:

```bash
debuild -us -uc
```

## License

MIT License

## Author

Giovanni Guarino
