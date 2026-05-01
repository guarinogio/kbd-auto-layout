# kbd-auto-layout

[![CI](https://img.shields.io/github/actions/workflow/status/guarinogio/kbd-auto-layout/ci.yml?branch=main&label=CI)](https://github.com/guarinogio/kbd-auto-layout/actions)
[![Latest
Release](https://img.shields.io/github/v/release/guarinogio/kbd-auto-layout?label=release)](https://github.com/guarinogio/kbd-auto-layout/releases)
[![APT
Repository](https://img.shields.io/badge/APT-stable-blue)](https://guarinogio.github.io/kbd-auto-layout-apt/)
[![License:
MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Automatic keyboard layout switching for Linux based on connected
keyboards.

`kbd-auto-layout` is for setups where your built-in laptop keyboard uses
one layout, such as Spanish, and your external keyboard uses another
layout, such as US English.

------------------------------------------------------------------------

## Why this exists

Linux desktop environments usually let you switch keyboard layouts
globally, but they do not always make it easy to bind a layout to a
specific physical keyboard.

This tool solves that problem by watching connected keyboards and
applying the right XKB layout automatically.

Example:

-   Laptop keyboard → `es nodeadkeys`
-   Keychron external keyboard → `us`

------------------------------------------------------------------------

## Features

-   Per-keyboard layout switching
-   Hardware-aware matching using vendor/product IDs
-   Rule priority and specificity scoring
-   Event-driven hotplug handling via `udevadm`
-   Polling fallback
-   User-level systemd service
-   JSON output for automation
-   APT repository installation
-   No GUI by design: simple daemon + CLI

------------------------------------------------------------------------

## Install from APT

Add the repository:

``` bash
curl -fsSL https://guarinogio.github.io/kbd-auto-layout-apt/public.key \
  | sudo gpg --dearmor --yes -o /usr/share/keyrings/kbd-auto-layout.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/kbd-auto-layout.gpg] https://guarinogio.github.io/kbd-auto-layout-apt stable main" \
  | sudo tee /etc/apt/sources.list.d/kbd-auto-layout.list

sudo apt update
sudo apt install kbd-auto-layout
```

Enable the daemon:

``` bash
kbd-auto-layoutctl enable
```

------------------------------------------------------------------------

## Quick start

Detect keyboards:

``` bash
kbd-auto-layoutctl detect
```

Create a rule from a connected keyboard:

``` bash
kbd-auto-layoutctl use-current-keyboard us \
  --device "Keychron Keychron K2 Max Keyboard" \
  --exact \
  --hardware \
  --priority 20
```

Reload the daemon:

``` bash
kbd-auto-layoutctl reload
```

Inspect what is happening:

``` bash
kbd-auto-layoutctl explain
```

------------------------------------------------------------------------

## Example: Spanish laptop + US Keychron

Set the default layout for the laptop keyboard:

``` bash
kbd-auto-layoutctl set-default es nodeadkeys
```

Assign US layout to the external Keychron:

``` bash
kbd-auto-layoutctl use-current-keyboard us \
  --device "Keychron Keychron K2 Max Keyboard" \
  --exact \
  --hardware \
  --priority 20
```

Reload:

``` bash
kbd-auto-layoutctl reload
```

Expected behavior:

-   Keychron connected → `us`
-   Keychron disconnected → `es nodeadkeys`

------------------------------------------------------------------------

## Rule matching

Rules are evaluated by:

1.  Highest priority
2.  Highest specificity
3.  First matching rule

Specificity order:

  Match type      Specificity
  ------------- -------------
  Hardware ID         Highest
  Exact name           Medium
  Contains             Lowest

Example:

``` bash
kbd-auto-layoutctl explain
```

Example output:

``` text
Active: Keychron Keychron K2 Max Keyboard -> us
Reason: hardware match 3434:0a20 (priority=20)
Matched: Keychron Keychron K2 Max, Keychron Keychron K2 Max Keyboard
```

------------------------------------------------------------------------

## CLI reference

### Detect devices

``` bash
kbd-auto-layoutctl detect
kbd-auto-layoutctl detect --json
```

### Create rules

``` bash
kbd-auto-layoutctl assign "Keychron" us --match contains
kbd-auto-layoutctl use-current-keyboard us --interactive --hardware
```

### Inspect

``` bash
kbd-auto-layoutctl list
kbd-auto-layoutctl rules
kbd-auto-layoutctl status
kbd-auto-layoutctl explain
kbd-auto-layoutctl doctor
```

### Service control

``` bash
kbd-auto-layoutctl enable
kbd-auto-layoutctl disable
kbd-auto-layoutctl restart
kbd-auto-layoutctl reload
```

------------------------------------------------------------------------

## Configuration

User config:

``` text
~/.config/kbd-auto-layout/config.ini
```

System config:

``` text
/etc/kbd-auto-layout/config.ini
```

Example:

``` ini
[general]
default_layout = es
default_variant = nodeadkeys
poll_interval = 2
apply_retries = 5
apply_retry_delay = 1.0
backend = auto
device_cache_ttl = 2.0
event_mode = auto
event_timeout = 30.0

[device "Keychron Keychron K2 Max Keyboard"]
layout = us
variant =
match = exact
vendor_id = 3434
product_id = 0a20
priority = 20
```

------------------------------------------------------------------------

## Backend support

  -----------------------------------------------------------------------
  Session/backend         Status                  Notes
  ----------------------- ----------------------- -----------------------
  X11                     Full                    Primary supported
                                                  backend

  GNOME Wayland           Partial                 Experimental backend

  Other Wayland           Limited                 Detection may work;
                                                  layout switching may
                                                  not
  -----------------------------------------------------------------------

Check your session:

``` bash
echo $XDG_SESSION_TYPE
kbd-auto-layoutctl doctor
```

------------------------------------------------------------------------

## Troubleshooting

### Check everything

``` bash
kbd-auto-layoutctl doctor
```

### Explain rule selection

``` bash
kbd-auto-layoutctl explain
```

### Check daemon logs

``` bash
journalctl --user -u kbd-auto-layout.service -f
```

### Restart the service

``` bash
kbd-auto-layoutctl restart
```

### No layout change

Check:

``` bash
kbd-auto-layoutctl explain
setxkbmap -query
```

Common causes:

-   Rule does not match the keyboard
-   Service is not running
-   Session is not X11
-   Desktop environment overrides keyboard layout after login

------------------------------------------------------------------------

# Release Notes v1.6.1

## Summary

`v1.6.1` is the first release that feels like a complete CLI-first
product. It includes hardware matching, event-driven switching, rule
explanation, service control, APT publishing, and lintian-clean Debian
builds.

------------------------------------------------------------------------

## Highlights since v1.0

### Hardware-aware matching

Rules can now match keyboards using vendor/product IDs, not only device
names.

``` text
3434:0a20
```

This is more stable than matching only by display name.

### Rule priority and specificity

Rules now support priority and automatic specificity scoring:

``` text
hardware > exact > contains
```

### Event-driven daemon

The daemon can react to keyboard plug/unplug events using `udevadm`,
with polling fallback.

### Better CLI UX

New commands make first-time setup and debugging easier:

``` bash
kbd-auto-layoutctl detect
kbd-auto-layoutctl explain
kbd-auto-layoutctl enable
kbd-auto-layoutctl disable
kbd-auto-layoutctl restart
```

### APT repository

The package is installable from a public APT repository.

### Packaging cleanup

`v1.6.1` uses an Ubuntu Noble changelog distribution for lintian-clean
local builds.

------------------------------------------------------------------------

## New commands

### `detect`

Shows connected keyboards and suggested commands.

``` bash
kbd-auto-layoutctl detect
```

### `explain`

Explains why a rule is active.

``` bash
kbd-auto-layoutctl explain
```

### `enable`

Enables and starts the user service.

``` bash
kbd-auto-layoutctl enable
```

### `disable`

Stops and disables the user service.

``` bash
kbd-auto-layoutctl disable
```

### `restart`

Restarts the user service.

``` bash
kbd-auto-layoutctl restart
```

------------------------------------------------------------------------

## Known limitations

-   X11 is the primary supported target.
-   Wayland support is partial.
-   Hardware detection depends on `xinput` and `udevadm`.
-   Some keyboards expose multiple logical devices with the same
    hardware ID.
-   Desktop environments may override keyboard layout at session
    startup.

------------------------------------------------------------------------

## License

MIT License

------------------------------------------------------------------------

Generated: 2026-05-01T14:01:05
