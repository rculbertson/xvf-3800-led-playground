"""Saved-config model and JSON store."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .params import DEFAULTS, PARAMS, validate

FILE_VERSION = 1


@dataclass
class Config:
    name: str
    settings: dict[str, list[int]] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"name": self.name, "settings": self.settings}

    @classmethod
    def from_json(cls, data: dict) -> "Config":
        name = data["name"]
        raw = data.get("settings", {})
        settings: dict[str, list[int]] = {}
        for key, values in raw.items():
            if key not in PARAMS or PARAMS[key].access == "ro":
                continue
            values = [int(v) for v in values]
            validate(key, values)
            settings[key] = values
        return cls(name=name, settings=settings)


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self.configs: list[Config] = []
        self.dirty: bool = False

    def load(self) -> None:
        if not self.path.exists():
            self.configs = []
            self.dirty = False
            return
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        configs = [Config.from_json(c) for c in data.get("configurations", [])]
        self.configs = configs
        self.dirty = False

    def save(self) -> None:
        payload = {
            "version": FILE_VERSION,
            "configurations": [c.to_json() for c in self.configs],
        }
        text = json.dumps(payload, indent=2, sort_keys=False)
        self.path.write_text(text + "\n", encoding="utf-8")
        self.dirty = False

    def add(self, name: str) -> Config:
        cfg = Config(name=name, settings={k: list(v) for k, v in DEFAULTS.items()})
        self.configs.append(cfg)
        self.dirty = True
        return cfg

    def duplicate(self, index: int) -> Config:
        src = self.configs[index]
        cfg = Config(name=f"{src.name} copy", settings={k: list(v) for k, v in src.settings.items()})
        self.configs.insert(index + 1, cfg)
        self.dirty = True
        return cfg

    def delete(self, index: int) -> None:
        del self.configs[index]
        self.dirty = True

    def rename(self, index: int, name: str) -> None:
        self.configs[index].name = name
        self.dirty = True

    def move_up(self, index: int) -> int:
        if index <= 0:
            return index
        self.configs[index - 1], self.configs[index] = self.configs[index], self.configs[index - 1]
        self.dirty = True
        return index - 1

    def move_down(self, index: int) -> int:
        if index >= len(self.configs) - 1:
            return index
        self.configs[index + 1], self.configs[index] = self.configs[index], self.configs[index + 1]
        self.dirty = True
        return index + 1

    def update_setting(self, index: int, key: str, values: list[int]) -> None:
        validate(key, values)
        self.configs[index].settings[key] = values
        self.dirty = True
