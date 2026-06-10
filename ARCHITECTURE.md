# Architecture: kbd-auto-layout

## Overview

Daemon that watches connected keyboards and auto-switches XKB layouts per device.
Example: laptop keyboard → Spanish, external Keychron → US English.

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                    kbd-auto-layoutd                  │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ config  │  │  xinput  │  │     backends        │ │
│  │ loader  │  │ enumerat │  │  X11 | Wayland+GNOME│ │
│  │ (INI)   │  │ devices  │  │  Wayland | Unsupp   │ │
│  └────┬────┘  └────┬─────┘  └─────────┬──────────┘ │
│       │            │                  │             │
│  ┌────▼────────────▼──────────────────▼──────────┐  │
│  │              find_active_rule()               │  │
│  │  Load rules → Match devices → Return winner   │  │
│  └──────────────────────┬────────────────────────┘  │
│                         │                           │
│  ┌──────────────────────▼────────────────────────┐  │
│  │            apply_layout_verified()            │  │
│  │  setxkbmap → verify → retry (configurable)   │  │
│  └──────────────────────┬────────────────────────┘  │
│                         │                           │
│  ┌──────────────────────▼────────────────────────┐  │
│  │           _wait_for_next_check()              │  │
│  │  Udev events OR polling (configurable)       │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `cli.py` | User-facing CLI: detect, rules, setup, doctor |
| `daemon.py` | Event loop, rule matching, layout application |
| `config.py` | INI config loading/saving (user + system paths) |
| `xinput.py` | Device enumeration via xinput, name/VID matching |
| `backends.py` | XKB backends: X11 (setxkbmap), Wayland+GNOME |
| `models.py` | Dataclasses: GeneralConfig, DeviceRule, KeyboardDevice |
| `events.py` | Udev monitor for hotplug events |

## Device Matching Flow

```
1. Load rules from ~/.config/kbd-auto-layout/config.ini
2. Enumerate keyboards via xinput
3. For each rule (sorted by priority DESC, specificity DESC):
   a. If rule has vendor_id/product_id → match by hardware ID
   b. Otherwise → match by device name (exact or contains)
4. First matching rule wins
5. If no rule matches → use default_layout from [general]
```

## Bluetooth Caveat

Bluetooth keyboards often report `hardware: unavailable` (no VID/PID).
Rules should use `match = contains` without hardware IDs for Bluetooth.
Example: `[device "Keychron K2 Max"]` with empty vendor_id/product_id.

## Error Recovery

- **Daemon loop**: all exceptions caught, logged, retried after poll_interval
- **xinput failure**: daemon sleeps and retries instead of crashing
- **Config reload**: SIGHUP triggers re-read without restart
- **Layout apply**: retries up to `apply_retries` times before falling back to default
