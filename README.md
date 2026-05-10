# XVF-3800 LED Playground

Terminal UI for testing LED settings on the ReSpeaker XVF-3800 USB mic array.

<img width="696" height="468" alt="image" src="https://github.com/user-attachments/assets/0326b844-9972-4818-9bd4-4dc385d96f85" />

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- A ReSpeaker XVF-3800 connected over USB (VID `0x2886`, PID `0x001A`)
- Linux (tested); macOS/Windows untested — `pyusb` should work but the udev step below is Linux-only

## Run

```bash
uv sync
uv run python -m led_playground
```

Optional flags: `--config PATH` (default `./config.json`), `--vid 0x2886`, `--pid 0x001A`.

## USB permissions

If pyusb raises `Access denied`, add a udev rule:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="2886", ATTRS{idProduct}=="001a", MODE="0660", GROUP="plugdev"
```

Save to `/etc/udev/rules.d/99-respeaker.rules`, then `sudo udevadm control --reload && sudo udevadm trigger`.

## License

MIT — see [LICENSE](LICENSE).
