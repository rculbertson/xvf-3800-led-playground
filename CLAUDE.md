# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Textual TUI for testing/saving LED configurations on the ReSpeaker XVF-3800 USB mic array (VID 0x2886, PID 0x001A). Configs live in a JSON file (default `./config.json`); each one bundles a set of LED parameter values that can be cycled and pushed to the device live.

## Commands

```bash
uv sync                                  # install deps
uv run python -m led_playground          # run TUI
uv run python -m led_playground --config path/to/config.json --vid 0x2886 --pid 0x001A
uv run pytest                            # run tests
```

There is no test suite, linter, or build step beyond `hatchling` packaging.

## Architecture

All under `led_playground/`:

- **`params.py`** — single source of truth for the device's LED parameter table. Each `Param` declares `resid`, `cmdid`, element `count`, dtype (`uint8`/`uint16`/`uint32`), and access (`rw`/`ro`). `validate()` enforces per-parameter ranges (e.g. `LED_EFFECT` is 0–5, colors are 0x000000–0xFFFFFF). All other modules import `PARAMS` from here — to add or change a parameter, edit this table and the rest of the app picks it up automatically (UI rendering branches on specific names like `LED_EFFECT`/`LED_COLOR`/`LED_RING_COLOR` though).
- **`device.py`** — thin `pyusb` wrapper. Uses vendor-class control transfers: `wValue = cmdid` (OR 0x80 for reads), `wIndex = resid`. Read responses are prefixed with a status byte (`0x00` ok, `0x01` retry → sleep 10ms and retry up to 100 times, anything else → `IOError`). Writes pack values little-endian per dtype. This protocol mirrors `xvf_host.py` from the vendor SDK.
- **`config.py`** — `Config` (name + `settings: dict[str, list[int]]`) and `ConfigStore` (load/save JSON, add/duplicate/delete/rename/reorder, `update_setting` validates via `params.validate`). `from_json` silently drops unknown or read-only keys. File format is `{"version": 1, "configurations": [...]}`; saved with `dirty` flag tracking unsaved edits.
- **`app.py`** — the Textual `App` and top-level `MainScreen` (config list on the left, inline `EditorPane` on the right — there is no separate editor or color-picker modal screen). Module-level `apply_config_to_device` enforces a key invariant: write `LED_EFFECT` **last** so the effect engine on the device picks up the new color/brightness/etc. before switching mode. Every committed edit and every next/prev cycle pushes to the device immediately.
- **`widgets.py`** — reusable Textual widgets used by `app.py`: `EditorPane` (the right-hand parameter editor), `ConfigList`, `CommitInput` (Input that fires events on Enter/blur), `FieldSwitch`/`FieldSelect`, and the `TextPromptScreen` / `ConfirmQuitScreen` modal screens. Also exports `COLOR_RESTRICT` (regex used to mask color inputs).
- **`app.tcss`** — Textual stylesheet for the app.

Entry point is `__main__.py` → constructs `Device`, loads `ConfigStore`, hands both to `LedPlaygroundApp`. The device handle is shared (not re-opened per write).

## USB access

If `pyusb` raises "Access denied", install the udev rule from README.md (allows non-root access to VID 2886 / PID 001a).
