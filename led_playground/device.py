"""Minimal pyusb wrapper for the XVF-3800 LED control endpoints.

Mirrors the protocol used by xvf_host.py: vendor-class control transfers where
wValue = cmdid (with 0x80 set for reads), wIndex = resid. Read responses begin
with a 1-byte status (0x00 = ok, 0x01 = retry, anything else = error).
"""

from __future__ import annotations

import logging
import struct
import time

import usb.core
import usb.util

from .params import PARAMS, validate

log = logging.getLogger(__name__)

VENDOR_ID = 0x2886
PRODUCT_ID = 0x001A

_STATUS_OK = 0x00
_STATUS_RETRY = 0x01
_TIMEOUT_MS = 2_000
_MAX_RETRIES = 100


class DeviceNotFound(RuntimeError):
    pass


class Device:
    def __init__(self, vid: int = VENDOR_ID, pid: int = PRODUCT_ID):
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise DeviceNotFound(
                f"No USB device with VID=0x{vid:04x} PID=0x{pid:04x}"
            )
        self._dev = dev

    def write(self, name: str, values: list[int]) -> None:
        p = PARAMS[name]
        if p.access == "ro":
            raise ValueError(f"{name} is read-only")
        validate(name, values)
        if p.dtype == "uint8":
            payload = bytes(v & 0xFF for v in values)
        elif p.dtype == "uint16":
            payload = b"".join(struct.pack("<H", v & 0xFFFF) for v in values)
        elif p.dtype == "uint32":
            payload = b"".join(struct.pack("<I", v & 0xFFFFFFFF) for v in values)
        else:
            raise ValueError(f"writing {p.dtype} not supported")
        log.debug(
            "WRITE %s resid=0x%02x cmdid=0x%02x dtype=%s values=%s payload=%s",
            name, p.resid, p.cmdid, p.dtype, values, payload.hex(),
        )
        self._dev.ctrl_transfer(
            usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0,  # bRequest
            p.cmdid,  # wValue
            p.resid,  # wIndex
            payload,
            _TIMEOUT_MS,
        )

    def read(self, name: str) -> tuple[int, ...]:
        p = PARAMS[name]
        wvalue = 0x80 | p.cmdid
        if p.dtype == "uint8":
            unit = 1
        elif p.dtype == "uint16":
            unit = 2
        elif p.dtype == "uint32":
            unit = 4
        else:
            raise ValueError(f"reading {p.dtype} not supported")
        length = p.count * unit + 1  # +1 status byte

        bm_request_type = (
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
        )
        log.debug(
            "READ  %s resid=0x%02x cmdid=0x%02x wValue=0x%02x length=%d",
            name, p.resid, p.cmdid, wvalue, length,
        )
        for _ in range(_MAX_RETRIES):
            response = self._dev.ctrl_transfer(
                bm_request_type, 0, wvalue, p.resid, length, _TIMEOUT_MS
            )
            status = response[0]
            if status == _STATUS_OK:
                break
            if status == _STATUS_RETRY:
                time.sleep(0.01)
                continue
            raise IOError(f"{name} read failed, status={status:#x}")
        else:
            raise IOError(f"{name} read exceeded {_MAX_RETRIES} retries")

        body = bytes(response[1:])
        if p.dtype == "uint8":
            fmt = "<" + "B" * p.count
        elif p.dtype == "uint16":
            fmt = "<" + "H" * p.count
        else:
            fmt = "<" + "I" * p.count
        result = struct.unpack(fmt, body)
        log.debug("READ  %s -> %s", name, result)
        return result

    def close(self) -> None:
        usb.util.dispose_resources(self._dev)
