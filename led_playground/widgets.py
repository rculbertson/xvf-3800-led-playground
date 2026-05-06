"""Reusable widgets for the LED Playground TUI."""

from __future__ import annotations

from dataclasses import replace

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    ListView,
    Select,
    Switch,
)


COLOR_RESTRICT = r"(#|0x|0X)?[0-9A-Fa-f]{0,6}"


class TextPromptScreen(ModalScreen[str | None]):
    """Modal that asks for a single line of text."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("left", "focus_prev_button", show=False),
        Binding("right", "focus_next_button", show=False),
    ]

    def action_focus_prev_button(self) -> None:
        if isinstance(self.focused, Button):
            self.focus_previous()

    def action_focus_next_button(self) -> None:
        if isinstance(self.focused, Button):
            self.focus_next()

    def __init__(self, prompt: str, initial: str = "") -> None:
        super().__init__()
        self.prompt = prompt
        self.initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(id="prompt-box"):
            yield Label(self.prompt)
            yield Input(value=self.initial, id="prompt-input", select_on_focus=False)
            with Horizontal(id="prompt-buttons"):
                yield Button("OK", id="ok", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    @on(Input.Submitted, "#prompt-input")
    def _submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        self.dismiss(self.query_one("#prompt-input", Input).value.strip() or None)

    @on(Button.Pressed, "#cancel")
    def _cancel_btn(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmQuitScreen(ModalScreen[str]):
    """Modal asking whether to save, discard, or cancel a quit."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("left", "focus_previous", show=False),
        Binding("right", "focus_next", show=False),
    ]

    def action_focus_previous(self) -> None:
        self.focus_previous()

    def action_focus_next(self) -> None:
        self.focus_next()

    def compose(self) -> ComposeResult:
        with Vertical(id="prompt-box"):
            yield Label("Save changes before quitting?")
            with Horizontal(id="prompt-buttons"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Discard", id="discard")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#save", Button).focus()

    @on(Button.Pressed, "#save")
    def _save(self) -> None:
        self.dismiss("save")

    @on(Button.Pressed, "#discard")
    def _discard(self) -> None:
        self.dismiss("discard")

    @on(Button.Pressed, "#cancel")
    def _cancel_btn(self) -> None:
        self.dismiss("cancel")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class CommitInput(Input):
    """Input that commits only on Enter. Arrow navigation is blocked while dirty."""

    BINDINGS = [
        Binding("up", "screen.field_prev", "Navigate", key_display="↑/↓"),
        Binding("down", "screen.field_next", "Navigate", show=False),
        Binding("enter", "submit", "Apply", priority=True),
        Binding("escape", "escape_pressed", "Back"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        # Must be set before super().__init__ — Textual fires watch_value during
        # base init, which calls _sync_escape_label and reads _original_value.
        self._original_value: str = ""
        kwargs.setdefault("select_on_focus", False)
        super().__init__(*args, **kwargs)
        self._original_value = self.value

    def _is_dirty(self) -> bool:
        return self.value != self._original_value

    def _sync_escape_label(self) -> None:
        bindings = self._bindings.key_to_bindings.get("escape", [])
        for i, b in enumerate(bindings):
            if b.action == "escape_pressed":
                desc = "Cancel" if self._is_dirty() else "Back"
                if b.description != desc:
                    bindings[i] = replace(b, description=desc)
        self.refresh_bindings()

    def on_focus(self, event: events.Focus) -> None:
        self._original_value = self.value
        self._sync_escape_label()

    def watch_value(self, value: str) -> None:
        self._sync_escape_label()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action in ("screen.field_prev", "screen.field_next"):
            return True if not self._is_dirty() else None
        return True

    def mark_committed(self) -> None:
        """Clear the dirty flag — call from the screen's submit handler on success."""
        self._original_value = self.value
        self._sync_escape_label()

    def action_escape_pressed(self) -> None:
        if self._is_dirty():
            with self.prevent(Input.Changed):
                self.value = self._original_value
            self._sync_escape_label()
        else:
            self.screen.action_focus_list()


class FieldSwitch(Switch, inherit_bindings=False):
    """Switch that surfaces Enter→toggle in the footer."""

    BINDINGS = [Binding("enter,space", "toggle_switch", "Toggle", show=True)]


class FieldSelect(Select, inherit_bindings=False):
    """Select that doesn't open its overlay on up/down — those navigate fields instead."""

    BINDINGS = [Binding("enter,space", "show_overlay", "Open", show=True)]


class ConfigList(ListView):
    """ListView with action bindings scoped to list focus."""

    BINDINGS = [
        Binding("enter", "screen.focus_editor", "Edit", key_display="↵"),
        Binding("a", "screen.add", "Add"),
        Binding("d", "screen.delete", "Delete"),
        Binding("r", "screen.rename", "Rename"),
        Binding("shift+up", "screen.move_up", "Move up"),
        Binding("shift+down", "screen.move_down", "Move down"),
    ]


class EditorPane(VerticalScroll, inherit_bindings=False):
    """Editor scroll container with bindings scoped to editor focus."""

    BINDINGS = [
        Binding("escape", "screen.focus_list", "Back", key_display="esc"),
        Binding("enter", "noop", "Commit"),
    ]

    def action_noop(self) -> None:
        """Footer-only binding; inner widgets handle Enter natively."""
        pass
