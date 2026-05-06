"""CLI entry: `python -m led_playground`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .app import LedPlaygroundApp
from .config import ConfigStore
from .device import Device, DeviceNotFound


def _hex_int(s: str) -> int:
    return int(s, 0)


def main() -> int:
    parser = argparse.ArgumentParser(prog="led_playground")
    parser.add_argument("--config", type=Path, default=Path("config.json"),
                        help="path to config JSON file (default: ./config.json)")
    parser.add_argument("--vid", type=_hex_int, default=0x2886)
    parser.add_argument("--pid", type=_hex_int, default=0x001A)
    parser.add_argument("--debug", action="store_true",
                        help="log every USB command to --log-file")
    parser.add_argument("--log-file", type=Path, default=Path("led_playground.log"),
                        help="debug log destination (default: ./led_playground.log)")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            filename=args.log_file,
            filemode="w",
            level=logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )

    try:
        device = Device(vid=args.vid, pid=args.pid)
    except DeviceNotFound as e:
        print(e, file=sys.stderr)
        return 1

    store = ConfigStore(args.config)
    try:
        store.load()
    except Exception as e:
        print(f"failed to load {args.config}: {e}", file=sys.stderr)
        device.close()
        return 1

    app = LedPlaygroundApp(store, device)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
