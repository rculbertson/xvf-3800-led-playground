"""Textual TUI for editing and cycling XVF-3800 LED configurations."""

from __future__ import annotations

import logging

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    Switch,
)

from .config import Config, ConfigStore
from .device import Device
from .params import (
    EFFECTS,
    PARAMS,
    WRITABLE,
    format_color,
    parse_color,
    validate,
)
from .widgets import (
    COLOR_RESTRICT,
    CommitInput,
    ConfigList,
    ConfirmQuitScreen,
    EditorPane,
    FieldSelect,
    FieldSwitch,
    TextPromptScreen,
)

log = logging.getLogger(__name__)


def apply_config_to_device(device: Device, cfg: Config) -> list[str]:
    """Push every setting in `cfg` to the device. Returns list of error messages."""
    errors: list[str] = []
    # Apply non-effect first, then LED_EFFECT last so the effect picks up new params.
    keys = [k for k in cfg.settings if k != "LED_EFFECT"]
    if "LED_EFFECT" in cfg.settings:
        keys.append("LED_EFFECT")
    for key in keys:
        try:
            device.write(key, cfg.settings[key])
        except Exception as e:
            errors.append(f"{key}: {e}")
    return errors



class MainScreen(Screen):
    """Unified screen: list of configs on the left, editor for the selected config on the right."""

    BINDINGS = [
        Binding("up", "field_prev", "Navigate", key_display="↑/↓"),
        Binding("down", "field_next", "Navigate", show=False),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+q", "app.quit", "Quit", priority=True),
        Binding("tab", "noop", show=False, priority=True),
        Binding("shift+tab", "noop", show=False, priority=True),
    ]

    def action_noop(self) -> None:
        pass


    def __init__(self, store: ConfigStore, device: Device) -> None:
        super().__init__()
        self.store = store
        self.device = device
        self.current_index: int = 0

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action in ("field_prev", "field_next"):
            focused = self.focused
            if isinstance(focused, CommitInput) and focused._is_dirty():
                return None
        return True

    @property
    def cfg(self) -> Config | None:
        if not self.store.configs or not (0 <= self.current_index < len(self.store.configs)):
            return None
        return self.store.configs[self.current_index]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            yield ConfigList(id="config-list")
            with EditorPane(id="editor"):

                with Horizontal(id="group-effect", classes="field-row"):
                    yield Label("LED_EFFECT", classes="field-label")
                    yield FieldSelect(
                        options=[(name, value) for value, name in EFFECTS.items()],
                        value=0,
                        allow_blank=False,
                        id="led-effect",
                        compact=True,
                    )

                with Horizontal(id="group-brightness", classes="field-row"):
                    yield Label("LED_BRIGHTNESS", classes="field-label")
                    yield CommitInput(value="128", id="led-brightness", type="integer", compact=True)

                with Horizontal(id="group-speed", classes="field-row"):
                    yield Label("LED_SPEED", classes="field-label")
                    yield CommitInput(value="30", id="led-speed", type="integer", compact=True)

                with Horizontal(id="group-gammify", classes="field-row"):
                    yield Label("LED_GAMMIFY", classes="field-label")
                    yield FieldSwitch(value=False, id="led-gammify")

                with Horizontal(id="group-color", classes="field-row"):
                    yield Label("LED_COLOR", classes="field-label")
                    yield CommitInput(value=format_color(0xFF8800), id="led-color", restrict=COLOR_RESTRICT, compact=True)

                with Vertical(id="group-doa", classes="field-group"):
                    with Horizontal(classes="field-row"):
                        yield Label("LED_DOA (base)", classes="field-label")
                        yield CommitInput(value=format_color(0x00FF00), id="led-doa-0", restrict=COLOR_RESTRICT, compact=True)
                    with Horizontal(classes="field-row"):
                        yield Label("LED_DOA (direction)", classes="field-label")
                        yield CommitInput(value=format_color(0xFF0000), id="led-doa-1", restrict=COLOR_RESTRICT, compact=True)

                with Vertical(id="group-ring", classes="field-group"):
                    yield Label("LED_RING_COLOR — 12 LEDs (#RRGGBB)")
                    for i in range(12):
                        with Horizontal(classes="ring-row"):
                            yield Label(f"{i + 1}.", classes="ring-num")
                            yield CommitInput(
                                value=format_color(0xFF0000),
                                id=f"led-ring-{i}",
                                restrict=COLOR_RESTRICT,
                                compact=True,
                            )

        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Header).icon = ""
        self.query_one("#config-list").border_title = "Configurations"
        self.query_one("#editor").border_title = "Editor"
        self._refresh_list()
        self._populate_editor()
        self._apply_current()

    # ---- List management ------------------------------------------------

    def _refresh_list(self, select_index: int | None = None) -> None:
        listview = self.query_one("#config-list", ListView)
        listview.clear()
        for i, cfg in enumerate(self.store.configs):
            listview.append(ListItem(Static(f"{i + 1}. {cfg.name}")))
        if self.store.configs:
            target = (
                select_index
                if select_index is not None
                else min(self.current_index, len(self.store.configs) - 1)
            )
            listview.index = target
            self.current_index = target
        else:
            self.current_index = 0

    def _set_status(self, text: str, error: bool = False) -> None:
        node = self.query_one("#status", Static)
        node.update(f"[red]{text}[/red]" if error else text)

    @on(ListView.Highlighted, "#config-list")
    def _highlight(self, event: ListView.Highlighted) -> None:
        if event.list_view.index is None:
            return
        if event.list_view.index == self.current_index:
            return
        self.current_index = event.list_view.index
        self._populate_editor()
        self._apply_current()

    @on(ListView.Selected, "#config-list")
    def _selected(self, event: ListView.Selected) -> None:
        self.action_focus_editor()

    # ---- Editor population ---------------------------------------------

    _EDITOR_GROUP_IDS = (
        "#group-effect",
        "#group-brightness",
        "#group-speed",
        "#group-gammify",
        "#group-color",
        "#group-doa",
        "#group-ring",
    )

    def _populate_editor(self) -> None:
        cfg = self.cfg
        if cfg is None:
            for gid in self._EDITOR_GROUP_IDS:
                self.query_one(gid).display = False
            return
        for gid in self._EDITOR_GROUP_IDS:
            self.query_one(gid).display = True

        effect_select = self.query_one("#led-effect", Select)
        effect = int(cfg.settings.get("LED_EFFECT", [0])[0])
        with effect_select.prevent(Select.Changed):
            effect_select.value = effect

        self._set_input_value("#led-brightness", str(cfg.settings.get("LED_BRIGHTNESS", [128])[0]))
        self._set_input_value("#led-speed", str(cfg.settings.get("LED_SPEED", [30])[0]))

        gammify = self.query_one("#led-gammify", Switch)
        with gammify.prevent(Switch.Changed):
            gammify.value = bool(cfg.settings.get("LED_GAMMIFY", [0])[0])

        self._set_input_value("#led-color", format_color(cfg.settings.get("LED_COLOR", [0xFF8800])[0]))

        doa = cfg.settings.get("LED_DOA_COLOR", [0x00FF00, 0xFF0000])
        self._set_input_value("#led-doa-0", format_color(doa[0]))
        self._set_input_value("#led-doa-1", format_color(doa[1]))

        ring = cfg.settings.get("LED_RING_COLOR", [0xFF0000] * 12)
        for i in range(12):
            self._set_input_value(f"#led-ring-{i}", format_color(ring[i]))

    def _set_input_value(self, selector: str, value: str) -> None:
        node = self.query_one(selector, Input)
        if node.value != value:
            with node.prevent(Input.Changed):
                node.value = value

    # ---- Device-pushing helpers ----------------------------------------

    def _read_all_from_device(self) -> dict[str, list[int]]:
        result: dict[str, list[int]] = {}
        for key in WRITABLE:
            try:
                result[key] = list(self.device.read(key))
            except Exception:
                pass
        return result

    def _push(self, key: str, values: list[int]) -> bool:
        if self.cfg is None:
            return False
        try:
            validate(key, values)
        except ValueError as e:
            self._set_status(str(e), error=True)
            return False
        self.store.update_setting(self.current_index, key, values)
        self._refresh_list_item(self.current_index)
        try:
            self.device.write(key, values)
            self._set_status(f"applied {key}")
        except Exception as e:
            self._set_status(f"{key} write failed: {e}", error=True)
            return False
        settings = self._read_all_from_device()
        if settings and self.cfg is not None:
            self.cfg.settings.update(settings)
            self._populate_editor()
        return True

    def _refresh_list_item(self, index: int) -> None:
        """Update the list row text in place so the summary follows live edits."""
        listview = self.query_one("#config-list", ListView)
        if not (0 <= index < len(listview.children)):
            return
        cfg = self.store.configs[index]
        item = listview.children[index]
        # ListItem's first child is the Static we yielded.
        statics = item.query(Static)
        if statics:
            statics.first().update(f"{index + 1}. {cfg.name}")

    def _apply_current(self) -> None:
        cfg = self.cfg
        if cfg is None:
            return
        errors = apply_config_to_device(self.device, cfg)
        if errors:
            self._set_status(f"applied with errors: {'; '.join(errors)}", error=True)

    # ---- Editor event handlers -----------------------------------------

    def _is_stale_change(self, event_value: object, selector: str) -> bool:
        """True if the widget's current value no longer matches the event's value.
        Filters out mount-time events that fire after _populate_editor has already
        synced the widget to the active config."""
        return event_value != self.query_one(selector).value  # type: ignore[attr-defined]

    @on(Select.Changed, "#led-effect")
    def _effect(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK or self.cfg is None:
            return
        if self._is_stale_change(event.value, "#led-effect"):
            return
        self._push("LED_EFFECT", [int(event.value)])

    @on(Switch.Changed, "#led-gammify")
    def _gammify(self, event: Switch.Changed) -> None:
        if self._is_stale_change(event.value, "#led-gammify"):
            return
        self._push("LED_GAMMIFY", [1 if event.value else 0])

    def _commit_int(self, event: Input.Submitted, key: str, label: str) -> None:
        try:
            value = int(event.value)
        except ValueError:
            self._set_status(f"{label} must be an integer", error=True)
            return
        if self._push(key, [value]):
            event.input.mark_committed()

    def _commit_colors(self, key: str, input_ids: list[str]) -> None:
        try:
            values = [parse_color(self.query_one(f"#{i}", Input).value) for i in input_ids]
        except ValueError as e:
            self._set_status(str(e), error=True)
            return
        if not self._push(key, values):
            return
        for input_id, value in zip(input_ids, values):
            inp = self.query_one(f"#{input_id}", CommitInput)
            inp.value = format_color(value)
            inp.mark_committed()

    @on(Input.Submitted, "#led-brightness")
    def _brightness(self, event: Input.Submitted) -> None:
        self._commit_int(event, "LED_BRIGHTNESS", "brightness")

    @on(Input.Submitted, "#led-speed")
    def _speed(self, event: Input.Submitted) -> None:
        self._commit_int(event, "LED_SPEED", "speed")

    @on(Input.Submitted, "#led-color")
    def _color(self, event: Input.Submitted) -> None:
        self._commit_colors("LED_COLOR", ["led-color"])

    @on(Input.Submitted, "#led-doa-0")
    @on(Input.Submitted, "#led-doa-1")
    def _doa_color(self, event: Input.Submitted) -> None:
        self._commit_colors("LED_DOA_COLOR", ["led-doa-0", "led-doa-1"])

    @on(Input.Submitted)
    def _ring_input(self, event: Input.Submitted) -> None:
        if not (event.input.id and event.input.id.startswith("led-ring-")):
            return
        self._commit_colors("LED_RING_COLOR", [f"led-ring-{i}" for i in range(12)])

    # ---- Pane focus & field traversal ----------------------------------

    def _editor_focusables(self) -> list:
        def visible(w) -> bool:
            for a in w.ancestors_with_self:
                if not a.display:
                    return False
            return True
        return [
            w for w in self.query("#editor *")
            if w.can_focus and visible(w) and not getattr(w, "disabled", False)
        ]

    def action_focus_list(self) -> None:
        self.query_one("#config-list", ListView).focus()

    def action_focus_editor(self) -> None:
        for w in self._editor_focusables():
            w.focus()
            return

    def action_field_prev(self) -> None:
        if isinstance(self.focused, CommitInput) and self.focused._is_dirty():
            self.app.bell()
            self._set_status("press Enter to apply or Esc to cancel", error=True)
            return
        self._move_field(-1)

    def action_field_next(self) -> None:
        if isinstance(self.focused, CommitInput) and self.focused._is_dirty():
            self.app.bell()
            self._set_status("press Enter to apply or Esc to cancel", error=True)
            return
        self._move_field(1)

    def _move_field(self, delta: int) -> None:
        widgets = self._editor_focusables()
        if not widgets:
            return
        try:
            idx = widgets.index(self.focused)
        except ValueError:
            widgets[0].focus()
            return
        widgets[(idx + delta) % len(widgets)].focus()

    # ---- List-level actions --------------------------------------------

    def action_add(self) -> None:
        def after(name: str | None) -> None:
            if not name:
                return
            self.store.add(name)
            new_index = len(self.store.configs) - 1
            cfg = self.store.configs[new_index]
            listview = self.query_one("#config-list", ListView)
            listview.append(ListItem(Static(f"{new_index + 1}. {cfg.name}")))
            self.current_index = new_index
            self.call_after_refresh(setattr, listview, "index", new_index)
            self._populate_editor()

        self.app.push_screen(TextPromptScreen("Name for new config:"), after)

    def action_delete(self) -> None:
        if not self.store.configs:
            return
        self.store.delete(self.current_index)
        self._refresh_list()
        self._populate_editor()

    def action_rename(self) -> None:
        if not self.store.configs:
            return
        idx = self.current_index
        current_name = self.store.configs[idx].name

        def after(name: str | None) -> None:
            if not name:
                return
            self.store.rename(idx, name)
            self._refresh_list(select_index=idx)
            self._populate_editor()

        self.app.push_screen(
            TextPromptScreen("Rename config:", initial=current_name), after
        )

    def action_move_up(self) -> None:
        if not self.store.configs:
            return
        old_index = self.current_index
        new_index = self.store.move_up(old_index)
        if new_index == old_index:
            return
        self._refresh_list_item(old_index)
        self._refresh_list_item(new_index)
        listview = self.query_one("#config-list", ListView)
        listview.index = new_index
        self.current_index = new_index

    def action_move_down(self) -> None:
        if not self.store.configs:
            return
        old_index = self.current_index
        new_index = self.store.move_down(old_index)
        if new_index == old_index:
            return
        self._refresh_list_item(old_index)
        self._refresh_list_item(new_index)
        listview = self.query_one("#config-list", ListView)
        listview.index = new_index
        self.current_index = new_index

    def action_save(self) -> None:
        try:
            self.store.save()
            self._set_status(f"saved {self.store.path}")
        except Exception as e:
            self._set_status(f"save failed: {e}", error=True)


class LedPlaygroundApp(App):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "app.tcss"

    TITLE = "XVF-3800 LED Playground"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, store: ConfigStore, device: Device) -> None:
        super().__init__()
        self.store = store
        self.device = device

    def on_mount(self) -> None:
        self.push_screen(MainScreen(self.store, self.device))

    def _finish_quit(self, choice: str | None) -> None:
        if choice == "cancel" or choice is None:
            return
        if choice == "save":
            try:
                self.store.save()
            except Exception:
                log.exception("save on quit failed")
                return
        self.device.close()
        self.exit()

    def action_quit(self) -> None:
        if not self.store.dirty:
            self.device.close()
            self.exit()
            return
        self.push_screen(ConfirmQuitScreen(), self._finish_quit)
