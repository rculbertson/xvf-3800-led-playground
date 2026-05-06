import json

import pytest

from led_playground.config import Config, ConfigStore, FILE_VERSION


def test_from_json_drops_unknown_keys():
    cfg = Config.from_json({
        "name": "x",
        "settings": {
            "LED_EFFECT": [1],
            "BOGUS_KEY": [42],
        },
    })
    assert "BOGUS_KEY" not in cfg.settings
    assert cfg.settings["LED_EFFECT"] == [1]


def test_from_json_drops_readonly_keys():
    cfg = Config.from_json({
        "name": "x",
        "settings": {
            "LED_EFFECT": [1],
            "DOA_VALUE": [180, 1],
        },
    })
    assert "DOA_VALUE" not in cfg.settings


def test_from_json_validates_values():
    with pytest.raises(ValueError):
        Config.from_json({"name": "x", "settings": {"LED_EFFECT": [99]}})


def test_from_json_coerces_to_int():
    cfg = Config.from_json({"name": "x", "settings": {"LED_BRIGHTNESS": [128.0]}})
    assert cfg.settings["LED_BRIGHTNESS"] == [128]
    assert isinstance(cfg.settings["LED_BRIGHTNESS"][0], int)


def test_store_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    store.load()
    assert store.configs == []

    cfg = store.add("first")
    cfg.settings["LED_EFFECT"] = [3]
    cfg.settings["LED_COLOR"] = [0xABCDEF]
    store.save()
    assert not store.dirty

    raw = json.loads(path.read_text())
    assert raw["version"] == FILE_VERSION
    assert raw["configurations"][0]["name"] == "first"

    store2 = ConfigStore(path)
    store2.load()
    assert len(store2.configs) == 1
    assert store2.configs[0].name == "first"
    assert store2.configs[0].settings["LED_COLOR"] == [0xABCDEF]
    assert not store2.dirty


def test_load_drops_unknown_and_readonly_from_disk(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "version": FILE_VERSION,
        "configurations": [
            {
                "name": "x",
                "settings": {
                    "LED_EFFECT": [2],
                    "DOA_VALUE": [180, 1],
                    "GHOST": [1],
                },
            }
        ],
    }))
    store = ConfigStore(path)
    store.load()
    settings = store.configs[0].settings
    assert "DOA_VALUE" not in settings
    assert "GHOST" not in settings
    assert settings["LED_EFFECT"] == [2]


def test_update_setting_validates(tmp_path):
    store = ConfigStore(tmp_path / "c.json")
    store.add("a")
    store.dirty = False
    with pytest.raises(ValueError):
        store.update_setting(0, "LED_EFFECT", [99])
    assert not store.dirty


def test_update_setting_marks_dirty(tmp_path):
    store = ConfigStore(tmp_path / "c.json")
    store.add("a")
    store.dirty = False
    store.update_setting(0, "LED_EFFECT", [4])
    assert store.dirty
    assert store.configs[0].settings["LED_EFFECT"] == [4]


def test_duplicate_inserts_after(tmp_path):
    store = ConfigStore(tmp_path / "c.json")
    store.add("a")
    store.add("b")
    store.duplicate(0)
    assert [c.name for c in store.configs] == ["a", "a copy", "b"]
    # deep copy: mutating original doesn't affect duplicate
    store.configs[0].settings["LED_EFFECT"] = [5]
    assert store.configs[1].settings["LED_EFFECT"] != [5]
