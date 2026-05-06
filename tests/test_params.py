import pytest

from led_playground.params import parse_color, format_color, validate


class TestValidate:
    def test_led_effect_range(self):
        for v in range(6):
            validate("LED_EFFECT", [v])
        with pytest.raises(ValueError):
            validate("LED_EFFECT", [6])
        with pytest.raises(ValueError):
            validate("LED_EFFECT", [-1])

    def test_led_brightness_range(self):
        validate("LED_BRIGHTNESS", [0])
        validate("LED_BRIGHTNESS", [255])
        with pytest.raises(ValueError):
            validate("LED_BRIGHTNESS", [256])

    def test_led_gammify_range(self):
        validate("LED_GAMMIFY", [0])
        validate("LED_GAMMIFY", [1])
        with pytest.raises(ValueError):
            validate("LED_GAMMIFY", [2])

    def test_led_speed_range(self):
        validate("LED_SPEED", [1])
        validate("LED_SPEED", [10])
        with pytest.raises(ValueError):
            validate("LED_SPEED", [0])
        with pytest.raises(ValueError):
            validate("LED_SPEED", [11])

    def test_led_color_range(self):
        validate("LED_COLOR", [0x000000])
        validate("LED_COLOR", [0xFFFFFF])
        with pytest.raises(ValueError):
            validate("LED_COLOR", [0x1000000])
        with pytest.raises(ValueError):
            validate("LED_COLOR", [-1])

    def test_led_doa_color_count(self):
        validate("LED_DOA_COLOR", [0xFFFFFF, 0xFF0000])
        with pytest.raises(ValueError):
            validate("LED_DOA_COLOR", [0xFFFFFF])
        with pytest.raises(ValueError):
            validate("LED_DOA_COLOR", [0xFFFFFF, 0xFF0000, 0])

    def test_led_ring_color_count(self):
        validate("LED_RING_COLOR", [0xFFFFFF] * 12)
        with pytest.raises(ValueError):
            validate("LED_RING_COLOR", [0xFFFFFF] * 11)
        with pytest.raises(ValueError):
            validate("LED_RING_COLOR", [0x1000000] * 12)

    def test_doa_value_uint16(self):
        validate("DOA_VALUE", [0, 0])
        validate("DOA_VALUE", [0xFFFF, 1])
        with pytest.raises(ValueError):
            validate("DOA_VALUE", [0x10000, 0])


class TestParseColor:
    @pytest.mark.parametrize("text,expected", [
        ("#FF0000", 0xFF0000),
        ("0xff0000", 0xFF0000),
        ("$00ff00", 0x00FF00),
        ("0000FF", 0x0000FF),
        ("  #abcdef  ", 0xABCDEF),
    ])
    def test_valid(self, text, expected):
        assert parse_color(text) == expected

    @pytest.mark.parametrize("text", ["", "#FFF", "#GGGGGG", "0xFFFFFFF", "not-a-color"])
    def test_invalid(self, text):
        with pytest.raises(ValueError):
            parse_color(text)

    def test_format_roundtrip(self):
        assert format_color(0xABCDEF) == "#ABCDEF"
        assert parse_color(format_color(0x123456)) == 0x123456
