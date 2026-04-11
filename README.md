# kbd-auto-layout

Automatic keyboard layout switching for X11 based on connected keyboards.

## Scope

- X11 only
- Per-device layout rules
- Default fallback layout
- User systemd service
- CLI for listing devices, layouts, variants, and assigning rules

## Planned commands

- `kbd-auto-layoutctl list`
- `kbd-auto-layoutctl layouts`
- `kbd-auto-layoutctl variants <layout>`
- `kbd-auto-layoutctl assign "<device>" <layout> [variant]`
- `kbd-auto-layoutctl remove "<device>"`
- `kbd-auto-layoutctl status`
- `kbd-auto-layoutctl reload`
- `kbd-auto-layoutctl doctor`

## Config locations

- User: `~/.config/kbd-auto-layout/config.ini`
- System: `/etc/kbd-auto-layout/config.ini`
