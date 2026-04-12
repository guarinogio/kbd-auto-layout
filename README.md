# kbd-auto-layout

Automatic keyboard layout switching for X11 based on connected keyboards.

## Overview

`kbd-auto-layout` is a lightweight daemon and CLI tool that automatically switches your keyboard layout depending on which keyboard is connected.

It is designed for setups where you use:
- a laptop keyboard (for example, Spanish)
- an external keyboard (for example, English)

The daemon monitors connected input devices and applies the appropriate layout automatically.

## Features

- Automatic layout switching based on connected keyboards
- Per-device rules with `exact` and `contains` matching
- Default fallback layout
- User-level systemd service
- CLI for configuration and inspection
- Zsh completion
- Debian package support
- Manual pages for the CLI and daemon

## Requirements

- Linux with X11
- `xinput`
- `setxkbmap`
- `systemd --user`

## Install from a GitHub Release

Download the latest `.deb` from the repository's Releases page, then install it with:

```bash
sudo apt install ./kbd-auto-layout_0.1.1_all.deb
```

Then enable the user service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Usage

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

### Assign a layout to a keyboard

```bash
kbd-auto-layoutctl assign "Keychron K2 Max Keyboard" us
```

### Assign using partial match

```bash
kbd-auto-layoutctl assign "Keychron" us --match contains
```

### Set default layout

```bash
kbd-auto-layoutctl set-default es nodeadkeys
```

### Reload configuration

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

Check environment:

```bash
kbd-auto-layoutctl doctor
```

Common issues:

- Not running X11
- Missing `xinput` or `setxkbmap`
- User service not enabled

## Development

Create a virtual environment outside the repository:

```bash
python3 -m venv ~/.venvs/kbd-auto-layout
source ~/.venvs/kbd-auto-layout/bin/activate
pip install -e ".[dev]"
```

Run checks:

```bash
make format
make lint
make test
```

Build Debian package:

```bash
debuild -us -uc
```

## License

MIT License

## Author

Giovanni Guarino
