# kbd-auto-layout

[![CI](https://github.com/guarinogio/kbd-auto-layout/actions/workflows/ci.yml/badge.svg)](https://github.com/guarinogio/kbd-auto-layout/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/guarinogio/kbd-auto-layout)](https://github.com/guarinogio/kbd-auto-layout/releases/latest)
[![APT Repository](https://img.shields.io/badge/APT-stable-blue)](https://guarinogio.github.io/kbd-auto-layout-apt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Automatic keyboard layout switching for X11 based on connected keyboards.

## Overview

`kbd-auto-layout` is a lightweight daemon and CLI tool that automatically switches your keyboard layout depending on which keyboard is connected.

It is designed for setups where you use:
- a laptop keyboard with one layout, such as Spanish
- an external keyboard with another layout, such as English

The daemon monitors connected input devices and applies the appropriate layout automatically.

## Features

- Automatic keyboard layout switching based on connected keyboards
- Per-device rules with `exact` or `contains` matching
- Default fallback layout
- User-level systemd service
- CLI for configuration and inspection
- JSON output for inspection commands
- Zsh completion
- Debian package support
- Man pages
- Public APT repository

## Install from APT repository

```bash
curl -fsSL https://guarinogio.github.io/kbd-auto-layout-apt/public.key \
  | sudo gpg --dearmor --yes -o /usr/share/keyrings/kbd-auto-layout.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/kbd-auto-layout.gpg] https://guarinogio.github.io/kbd-auto-layout-apt stable main" \
  | sudo tee /etc/apt/sources.list.d/kbd-auto-layout.list

sudo apt update
sudo apt install kbd-auto-layout

systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Install from GitHub Releases

```bash
wget https://github.com/guarinogio/kbd-auto-layout/releases/download/v1.0.5/kbd-auto-layout_1.0.5_all.deb
sudo apt install ./kbd-auto-layout_1.0.5_all.deb
systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Basic usage

### List detected keyboards

```bash
kbd-auto-layoutctl list
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

## Troubleshooting

Check the environment:

```bash
kbd-auto-layoutctl doctor
systemctl --user status kbd-auto-layout.service --no-pager -l
journalctl --user -u kbd-auto-layout.service -f
```

## Development

```bash
python -m venv ~/.venvs/kbd-auto-layout
source ~/.venvs/kbd-auto-layout/bin/activate
pip install -e ".[dev]"

make format
make lint
make test
debuild -us -uc
```

## License

MIT License

## Author

Giovanni Guarino
