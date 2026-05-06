"""LED parameter table, validators, and color helpers for the XVF-3800."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    name: str
    resid: int
    cmdid: int
    count: int
    dtype: str  # "uint8" | "uint16" | "uint32"
    access: str  # "rw" | "ro"
    description: str


PARAMS: dict[str, Param] = {
    p.name: p
    for p in [
        Param("LED_EFFECT", 20, 12, 1, "uint8", "rw",
              "0=off, 1=breath, 2=rainbow, 3=single color, 4=doa, 5=ring"),
        Param("LED_BRIGHTNESS", 20, 13, 1, "uint8", "rw", "0-255"),
        Param("LED_GAMMIFY", 20, 14, 1, "uint8", "rw", "0=off, 1=on"),
        Param("LED_SPEED", 20, 15, 1, "uint8", "rw", "1-10"),
        Param("LED_COLOR", 20, 16, 1, "uint32", "rw", "RGB hex 0x000000-0xFFFFFF"),
        Param("LED_DOA_COLOR", 20, 17, 2, "uint32", "rw",
              "two RGB hex values (base, doa)"),
        Param("DOA_VALUE", 20, 18, 2, "uint16", "ro",
              "read-only: [doa angle 0-359, speech 0|1]"),
        Param("LED_RING_COLOR", 20, 19, 12, "uint32", "rw",
              "twelve RGB hex values, one per LED"),
    ]
}


EFFECTS = {
    0: "off",
    1: "breath",
    2: "rainbow",
    3: "single color",
    4: "doa",
    5: "ring",
}
EFFECT_NAME_TO_VALUE = {v: k for k, v in EFFECTS.items()}


WRITABLE = [name for name, p in PARAMS.items() if p.access == "rw"]

DEFAULTS: dict[str, list[int]] = {
    "LED_EFFECT":    [0],
    "LED_BRIGHTNESS": [255],
    "LED_GAMMIFY":   [1],
    "LED_SPEED":     [5],
    "LED_COLOR":     [0xFFFFFF],
    "LED_DOA_COLOR": [0xFFFFFF, 0xFF0000],
    "LED_RING_COLOR": [0xFFFFFF] * 12,
}


def parse_color(text: str) -> int:
    """Parse '#RRGGBB', '0xRRGGBB', '$RRGGBB', or 'RRGGBB' into a uint32 RGB int."""
    s = text.strip()
    if not s:
        raise ValueError("empty color")
    if s.startswith("#"):
        s = s[1:]
    elif s.startswith("$"):
        s = s[1:]
    elif s.lower().startswith("0x"):
        s = s[2:]
    if len(s) != 6 or any(c not in "0123456789abcdefABCDEF" for c in s):
        raise ValueError(f"not a 6-digit hex color: {text!r}")
    value = int(s, 16)
    if not 0 <= value <= 0xFFFFFF:
        raise ValueError(f"color out of range: {text!r}")
    return value


def format_color(value: int) -> str:
    return f"#{value & 0xFFFFFF:06X}"


def validate(name: str, values: list[int]) -> None:
    """Raise ValueError if values aren't legal for the named parameter."""
    p = PARAMS[name]
    if len(values) != p.count:
        raise ValueError(f"{name} expects {p.count} value(s), got {len(values)}")
    if p.dtype == "uint8":
        lo, hi = 0, 255
        if name == "LED_EFFECT":
            lo, hi = 0, 5
        elif name == "LED_GAMMIFY":
            lo, hi = 0, 1
        elif name == "LED_SPEED":
            lo, hi = 1, 10
        for v in values:
            if not lo <= v <= hi:
                raise ValueError(f"{name} value {v} out of range [{lo}, {hi}]")
    elif p.dtype == "uint32":
        for v in values:
            if not 0 <= v <= 0xFFFFFF:
                raise ValueError(f"{name} color {v:#x} out of range 0x000000-0xFFFFFF")
    elif p.dtype == "uint16":
        for v in values:
            if not 0 <= v <= 0xFFFF:
                raise ValueError(f"{name} value {v} out of uint16 range")
