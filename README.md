# XVF-3800 LED Playground

Terminal UI for testing LED settings on the ReSpeaker XVF-3800 USB mic array.

The XVF-3800 dev kit has a 12-LED ring controlled over USB via vendor control transfers. This app lets you preview effects, tweak parameters live, and save named presets to a JSON file without writing any code against the vendor SDK.

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
SUBSYSTEM=="usb", ATTR{idVendor}=="2886", ATTR{idProduct}=="001a", MODE="0666"
```

Save to `/etc/udev/rules.d/99-respeaker.rules`, then `sudo udevadm control --reload-rules && sudo udevadm trigger`.

## License

MIT — see [LICENSE](LICENSE).
