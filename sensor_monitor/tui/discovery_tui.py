#!/usr/bin/env python3
"""Sensor discovery terminal UI (Textual)."""
from __future__ import annotations

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, Label
from textual import events

from sensor_monitor.core.discovery import SensorDiscovery
from sensor_monitor.utils.helpers import sanitize_variable_name, normalize_hardware_key

logger = logging.getLogger(__name__)

COL_ENABLED = "enabled"
COL_CONFIGURED = "configured"
COL_NUM = "num"
COL_VAR = "var"
COL_READ = "read"
COL_UNIT = "unit"
COL_CHIP = "chip"
COL_SENSOR = "sensor"
COL_LABEL = "label"

def _trunc(s: str, w: int) -> str:
    if len(s) <= w:
        return s
    return s[:max(1, w-1)] + "…"

class ClickableDataTable(DataTable):
    class CellClicked(events.Event, bubble=True):
        def __init__(self, row_key, column_key):
            super().__init__()
            self.row_key = row_key
            self.column_key = column_key
    
    def _on_click(self, event: events.Click) -> None:
        if not self.ordered_rows:
            return
        header_height = 1 if self.show_header else 0
        y_offset = event.y - header_height
        if y_offset < 0 or y_offset >= len(self.ordered_rows):
            return
        row_key = self.ordered_rows[y_offset]
        x_offset = event.x
        for col_key in self.ordered_columns:
            col_width = col_key.width
            if x_offset < col_width:
                self.post_message(self.CellClicked(row_key, col_key))
                return
            x_offset -= col_width

class RowState:
    def __init__(self, stable_id: int, sensor, default_var: str, in_config: bool,
                 variable: str = None, divide_by: int = None, custom_unit: str = None):
        self.stable_id = stable_id
        self.sensor = sensor
        self.default_var = default_var
        self.selected = False
        self.in_config = in_config
        self.variable = variable or default_var
        self.divide_by = divide_by
        self.custom_unit = custom_unit

    @property
    def display_unit(self) -> str:
        return self.custom_unit if self.custom_unit else self.sensor.unit

class SensorDiscoveryTui(App[None]):
    TITLE = "Sensor discovery"
    SUB_TITLE = "lm-sensors → Companion"

    CSS = """
    Screen { height: 100%; }
    #main { height: 100%; layout: vertical; }
    #filter_row { height: 3; margin: 1 1; layout: horizontal; align: center middle; }
    #filter_label { width: 8; padding-right: 1; text-align: right; }
    #filter_in { border: solid $accent; background: $surface; width: 1fr; margin-right: 1; }
    #tbl_container { height: 1fr; margin: 0 1; border: solid $primary; }
    #tbl { height: 100%; }
    #loading_overlay { height: 100%; width: 100%; align: center middle; background: $panel; layer: overlay; }
    #loading_box { width: 50; height: auto; background: $surface; border: thick $accent; padding: 2 4; align: center middle; }
    #loading_title { width: 100%; text-align: center; color: $accent; text-style: bold; margin-bottom: 1; }
    #loading_message { width: 100%; text-align: center; color: $text; margin-bottom: 1; }
    #loading_subtitle { width: 100%; text-align: center; color: $text-muted; text-style: italic; margin-bottom: 1; }
    #loading_dots { width: 100%; text-align: center; color: $accent; text-style: bold; }
    #detail { height: auto; margin: 1 1; border: solid $primary; padding: 1; background: $panel; }
    #detail_content { layout: horizontal; height: 17; }
    #info_panel { width: 50%; padding-right: 2; }
    #edit_panel { width: 50%; }
    .field-row { height: 3; margin-bottom: 1; }
    .field-label { width: 12; padding-right: 1; text-align: right; }
    .field-input { width: 1fr; max-width: 30; }
    #btn_row { height: 3; margin-top: 0; align-horizontal: left; }
    #btn_row Button { margin-right: 1; }
    #meta { margin-bottom: 1; color: $text-muted; }
    #hints { margin-bottom: 1; color: $text-muted; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("/", "focus_filter", "Filter", show=True),
        Binding("space", "toggle_focused", "Toggle", show=True),
        Binding("a", "select_all", "All on"),
        Binding("z", "select_none", "All off"),
        Binding("o", "sort_enabled", "Sort enabled"),
        Binding("g", "sort_configured", "Sort configured"),
        Binding("c", "sort_chip", "Sort chip"),
        Binding("i", "sort_num", "Sort #"),
        Binding("p", "sort_sensor", "Sort sensor"),
        Binding("u", "sort_unit", "Sort unit"),
        Binding("v", "sort_value", "Sort value"),
        Binding("n", "sort_label", "Sort label"),
        Binding("b", "sort_var", "Sort variable"),
        Binding("r", "sort_reverse", "Reverse sort"),
        Binding("escape", "focus_table", "Table", show=False),
        Binding("enter", "focus_var", "Var / ÷ / unit", show=False),
    ]

    def __init__(self, config_file: str = "sm_config.yaml"):
        super().__init__()
        self.config_file = config_file
        self.discovery = SensorDiscovery()
        self.states: list[RowState] = []
        self.display_order: list[int] = []
        self.sort_key = COL_CHIP
        self.sort_reverse = False
        self.filter_text = ""
        self._active_idx: int | None = None
        self._suppress_var_sync = False
        self._suppress_divide_sync = False
        self._suppress_unit_sync = False
        self._config_divide_map = {}
        self._config_unit_map = {}
        self._row_keys = {}
        self._loading = True
        self._loading_dots = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main"):
            with Horizontal(id="filter_row"):
                yield Static("Filter:", id="filter_label")
                yield Input(placeholder="type to filter sensors...", id="filter_in", disabled=True)
            with Vertical(id="tbl_container"):
                yield ClickableDataTable(id="tbl", cursor_type="row", zebra_stripes=True)
                with Vertical(id="loading_overlay"):
                    with Vertical(id="loading_box"):
                        yield Static("🔍 Discovering Sensors", id="loading_title")
                        yield Static("Querying lm-sensors...", id="loading_message")
                        yield Static("This may take up to 30 seconds", id="loading_subtitle")
                        yield Static("⏳", id="loading_dots")
            with Vertical(id="detail"):
                with Horizontal(id="detail_content"):
                    with Vertical(id="info_panel"):
                        yield Static("Select a row.", id="meta")
                        yield Static("Click 'Enabled' to toggle. Edit fields, then Save & Reload.", id="hints")
                    with Vertical(id="edit_panel"):
                        with Horizontal(classes="field-row"):
                            yield Static("Variable name:", classes="field-label")
                            yield Input(placeholder="Companion variable name", id="var_in", classes="field-input", disabled=True)
                        with Horizontal(classes="field-row"):
                            yield Static("Divide by:", classes="field-label")
                            yield Input(placeholder="e.g. 10", id="divide_in", classes="field-input", disabled=True)
                        with Horizontal(classes="field-row"):
                            yield Static("Unit:", classes="field-label")
                            yield Input(placeholder="Override unit (e.g. 'C')", id="unit_in", classes="field-input", disabled=True)
                with Horizontal(id="btn_row"):
                    yield Button("Reset default", id="btn_reset", variant="default", disabled=True)
                    yield Button("Sanitize", id="btn_sanitize", variant="primary", disabled=True)
                    yield Button("Save changes", id="btn_save", variant="warning", disabled=True)
                    yield Button("Save & Reload", id="btn_save_reload", variant="success", disabled=True)
                    yield Button("Quit", id="btn_quit", variant="error", disabled=True)
        yield Footer()

    def on_mount(self):
        self.query_one("#tbl").display = False
        self.set_interval(0.5, self._animate_loading)
        self.run_worker(self._discover_sensors, thread=True)

    def _animate_loading(self):
        if not self._loading:
            return
        self._loading_dots = (self._loading_dots + 1) % 4
        symbols = ["⏳", "⌛", "⏳", "⌛"]
        try:
            self.query_one("#loading_dots", Static).update(symbols[self._loading_dots])
        except Exception:
            pass

    async def _discover_sensors(self):
        self._update_loading_message("Querying lm-sensors...")
        self.discovery.discover()
        flat = self.discovery.sorted_sensors()
        self._update_loading_message(f"Found {len(flat)} sensors")
        defaults = self.discovery.assign_default_variables(flat)
        hw_keys = self.discovery.load_config_hardware_keys(self.config_file)
        self._config_divide_map = self.discovery.load_config_divide_by(self.config_file)
        self._config_unit_map = self.discovery.load_config_unit_overrides(self.config_file)
        self._update_loading_message("Building display...")
        self.states = []
        for i, s in enumerate(flat):
            key = normalize_hardware_key(s.chip, s.sensor_group)
            in_c = key in hw_keys
            div = self._config_divide_map.get(key)
            unit = self._config_unit_map.get(key)
            self.states.append(RowState(i+1, s, defaults[i], in_c, defaults[i], div, unit))
        self._recompute_display_order()
        self._loading = False
        self.query_one("#filter_in").disabled = False
        self.query_one("#var_in").disabled = False
        self.query_one("#divide_in").disabled = False
        self.query_one("#unit_in").disabled = False
        for btn_id in ["btn_reset", "btn_sanitize", "btn_save", "btn_save_reload"]:
            self.query_one(f"#{btn_id}").disabled = False
        for btn_id in ["btn_reset", "btn_sanitize", "btn_save", "btn_save_reload", "btn_quit"]:
            self.query_one(f"#{btn_id}").disabled = False
        self.query_one("#loading_overlay").remove()
        self.query_one("#tbl").display = True
        self._setup_table()
        self._populate_table()
        self._update_sort_headers()
        self.query_one("#tbl").focus()
        if self.display_order:
            self._sync_detail_from_idx(self.display_order[0])

    def _update_loading_message(self, message: str):
        try:
            self.call_from_thread(self._set_loading_message, message)
        except Exception:
            pass
    
    def _set_loading_message(self, message: str):
        try:
            self.query_one("#loading_message", Static).update(message)
        except Exception:
            pass

    def _setup_table(self):
        table = self.query_one("#tbl", ClickableDataTable)
        table.clear(columns=True)
        table.add_column("Enabled", key=COL_ENABLED, width=8)
        table.add_column("Configured", key=COL_CONFIGURED, width=10)
        table.add_column("#", key=COL_NUM, width=4)
        table.add_column("variable", key=COL_VAR, width=26)
        table.add_column("reading", key=COL_READ, width=10)
        table.add_column("unit", key=COL_UNIT, width=5)
        table.add_column("chip", key=COL_CHIP, width=28)
        table.add_column("sensor", key=COL_SENSOR, width=22)
        table.add_column("label", key=COL_LABEL, width=22)

    def _populate_table(self):
        table = self.query_one("#tbl", ClickableDataTable)
        for idx in self.display_order:
            key = str(self.states[idx].stable_id)
            table.add_row(*self._row_cells(idx), key=key)
            self._row_keys[self.states[idx].stable_id] = key

    def _row_cells(self, idx: int):
        st = self.states[idx]
        s = st.sensor
        reading = f"{s.current_value:.1f}" if s.unit != "RPM" else f"{s.current_value:.0f}"
        enabled = "✓ Yes" if (st.in_config or st.selected) else "- No"
        configured = "✓ Yes" if st.in_config else "- No"
        return (enabled, configured, str(st.stable_id),
                _trunc(st.variable, 40), reading, st.display_unit or "—",
                _trunc(s.chip, 40), _trunc(s.sensor_group, 30), _trunc(s.simple_name, 30))

    def _refresh_row(self, idx: int):
        table = self.query_one("#tbl", ClickableDataTable)
        row_key = self._row_keys.get(self.states[idx].stable_id)
        if row_key:
            table.update_cell(row_key, COL_ENABLED, self._row_cells(idx)[0])
            table.update_cell(row_key, COL_CONFIGURED, self._row_cells(idx)[1])
            table.update_cell(row_key, COL_VAR, self._row_cells(idx)[3])
            table.update_cell(row_key, COL_UNIT, self._row_cells(idx)[5])

    def _reorder_table(self):
        if self._loading:
            return
        table = self.query_one("#tbl", ClickableDataTable)
        target_keys = [str(self.states[i].stable_id) for i in self.display_order]
        current_keys = [rk.value for rk in table.rows.keys()]
        if current_keys == target_keys:
            return
        cursor_key = None
        if table.cursor_coordinate.row is not None:
            cursor_key = table.get_row_at(table.cursor_coordinate.row)
        table.clear()
        for idx in self.display_order:
            key = str(self.states[idx].stable_id)
            table.add_row(*self._row_cells(idx), key=key)
            self._row_keys[self.states[idx].stable_id] = key
        if cursor_key:
            for row_idx, row_key in enumerate(table.rows.keys()):
                if row_key.value == cursor_key:
                    table.move_cursor(row=row_idx)
                    break
        elif self.display_order:
            table.move_cursor(row=0)

    def _recompute_display_order(self):
        indices = list(range(len(self.states)))
        ft = self.filter_text.strip().lower()
        if ft:
            indices = [i for i in indices if (
                ft in self.states[i].sensor.chip.lower() or
                ft in self.states[i].sensor.sensor_group.lower() or
                ft in self.states[i].sensor.simple_name.lower() or
                ft in self.states[i].variable.lower() or
                (self.states[i].custom_unit and ft in self.states[i].custom_unit.lower()))]
        def key_fn(i):
            st = self.states[i]
            if self.sort_key == COL_ENABLED:
                return (0 if (st.in_config or st.selected) else 1, st.sensor.chip.lower())
            if self.sort_key == COL_CONFIGURED:
                return (0 if st.in_config else 1, st.sensor.chip.lower())
            if self.sort_key == COL_NUM:
                return st.stable_id
            if self.sort_key == COL_VAR:
                return st.variable.lower()
            if self.sort_key == COL_READ:
                return st.sensor.current_value
            if self.sort_key == COL_UNIT:
                return st.display_unit.lower()
            if self.sort_key == COL_CHIP:
                return st.sensor.chip.lower()
            if self.sort_key == COL_SENSOR:
                return st.sensor.sensor_group.lower()
            if self.sort_key == COL_LABEL:
                return st.sensor.simple_name.lower()
            return st.sensor.chip.lower()
        indices.sort(key=key_fn, reverse=self.sort_reverse)
        self.display_order = indices

    def _sync_detail_from_idx(self, idx: int):
        self._active_idx = idx
        st = self.states[idx]
        s = st.sensor
        if st.in_config and st.selected:
            action = "Will be REMOVED on next save"
        elif not st.in_config and st.selected:
            action = "Will be ADDED on next save"
        else:
            action = "No pending changes"
        info_text = (
            f"#{st.stable_id}  {s.simple_name}\n"
            f"chip: {s.chip}\n"
            f"sensor: {s.sensor_group}\n"
            f"Enabled: {'Yes' if (st.in_config or st.selected) else 'No'}  |  Configured: {'Yes' if st.in_config else 'No'}\n"
            f"Status: {action}\n"
            f"{st.sensor.description}"
        )
        self.query_one("#meta", Static).update(info_text)
        self._suppress_var_sync = True
        self.query_one("#var_in", Input).value = st.variable
        self._suppress_var_sync = False
        self._suppress_divide_sync = True
        self.query_one("#divide_in", Input).value = str(st.divide_by) if st.divide_by and st.divide_by >= 2 else ""
        self._suppress_divide_sync = False
        self._suppress_unit_sync = True
        self.query_one("#unit_in", Input).value = st.custom_unit if st.custom_unit else ""
        self._suppress_unit_sync = False

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        if self._loading or not event.row_key:
            return
        stable_id = int(event.row_key.value)
        for i, st in enumerate(self.states):
            if st.stable_id == stable_id:
                self._sync_detail_from_idx(i)
                break

    def on_clickable_data_table_cell_clicked(self, event: ClickableDataTable.CellClicked):
        if self._loading:
            return
        column = event.column_key
        column_key_value = column.key.value if hasattr(column, 'key') else str(column.label)
        row = event.row_key
        row_key_value = row.key.value if hasattr(row, 'key') else str(row.label)
        if column_key_value == COL_ENABLED:
            stable_id = int(row_key_value)
            for i, st in enumerate(self.states):
                if st.stable_id == stable_id:
                    table = self.query_one("#tbl", ClickableDataTable)
                    try:
                        row_index = table.ordered_rows.index(event.row_key)
                        table.move_cursor(row=row_index)
                    except ValueError:
                        pass
                    self._toggle_sensor(i)
                    break
    
    def _toggle_sensor(self, idx: int):
        if self._loading or idx is None:
            return
        st = self.states[idx]
        st.selected = not st.selected
        self._refresh_row(idx)
        self._sync_detail_from_idx(idx)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected):
        if self._loading:
            return
        self._set_sort(event.column_key.value)

    def on_input_changed(self, event: Input.Changed):
        if self._loading:
            return
        if event.input.id == "filter_in":
            self.filter_text = event.value
            self._recompute_display_order()
            self._reorder_table()
        elif event.input.id == "var_in" and not self._suppress_var_sync and self._active_idx is not None:
            self.states[self._active_idx].variable = event.value
            self._refresh_row(self._active_idx)
        elif event.input.id == "divide_in" and not self._suppress_divide_sync and self._active_idx is not None:
            raw = event.value.strip()
            st = self.states[self._active_idx]
            if raw == "":
                st.divide_by = None
            else:
                try:
                    n = int(raw)
                    if n >= 2:
                        st.divide_by = n
                    else:
                        st.divide_by = None
                except:
                    st.divide_by = None
            self._refresh_row(self._active_idx)
        elif event.input.id == "unit_in" and not self._suppress_unit_sync and self._active_idx is not None:
            raw = event.value.strip()
            st = self.states[self._active_idx]
            st.custom_unit = raw if raw else None
            self._refresh_row(self._active_idx)

    def on_input_submitted(self, event: Input.Submitted):
        if self._loading:
            return
        if event.input.id == "var_in":
            self.query_one("#divide_in", Input).focus()
        elif event.input.id == "divide_in":
            self.query_one("#unit_in", Input).focus()
        elif event.input.id == "unit_in":
            self.query_one("#var_in", Input).focus()

    def on_button_pressed(self, event: Button.Pressed):
        if self._loading or self._active_idx is None:
            return
        bid = event.button.id
        st = self.states[self._active_idx]
        if bid == "btn_reset":
            st.variable = st.default_var
            st.divide_by = None
            st.custom_unit = None
            self._sync_detail_from_idx(self._active_idx)
            self._refresh_row(self._active_idx)
        elif bid == "btn_sanitize":
            st.variable = sanitize_variable_name(st.variable)
            self._sync_detail_from_idx(self._active_idx)
            self._refresh_row(self._active_idx)
        elif bid == "btn_save":
            self._save_config()
        elif bid == "btn_save_reload":
            self._save_config()
            self._reload_daemon()
            self._update_configuration_status()
        elif bid == "btn_quit":
            self.exit()

    def _save_config(self):
        selected = [st for st in self.states if st.selected]
        if not selected:
            return
        cfg = self.discovery._load_config(self.config_file)
        existing_sensors = cfg.get('sensors', [])
        to_remove = {normalize_hardware_key(st.sensor.chip, st.sensor.sensor_group) 
                     for st in selected if st.in_config}
        for st in selected:
            if st.in_config:
                continue
            key = normalize_hardware_key(st.sensor.chip, st.sensor.sensor_group)
            already_exists = False
            for entry in existing_sensors:
                if isinstance(entry, dict):
                    ec = entry.get('chip')
                    es = entry.get('sensor')
                    if ec and es and normalize_hardware_key(ec, es) == key:
                        entry['variable'] = sanitize_variable_name(st.variable)
                        if st.divide_by and st.divide_by >= 2:
                            entry['divide_by'] = st.divide_by
                        elif 'divide_by' in entry:
                            del entry['divide_by']
                        if st.custom_unit:
                            entry['unit'] = st.custom_unit
                        elif 'unit' in entry:
                            del entry['unit']
                        already_exists = True
                        break
            if not already_exists:
                entry = {
                    'variable': sanitize_variable_name(st.variable),
                    'chip': st.sensor.chip,
                    'sensor': st.sensor.sensor_group,
                    'name': st.sensor.simple_name,
                    'format': self.discovery.companion_format_yaml(st.sensor),
                }
                if st.divide_by and st.divide_by >= 2:
                    entry['divide_by'] = st.divide_by
                if st.custom_unit:
                    entry['unit'] = st.custom_unit
                existing_sensors.append(entry)
        if to_remove:
            new_sensors = []
            for entry in existing_sensors:
                if isinstance(entry, dict) and entry.get('chip') and entry.get('sensor'):
                    if normalize_hardware_key(entry['chip'], entry['sensor']) in to_remove:
                        continue
                new_sensors.append(entry)
            existing_sensors = new_sensors
        cfg['sensors'] = existing_sensors
        try:
            import yaml
            with open(self.config_file, 'w') as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except Exception:
            return
        hw_keys = self.discovery.load_config_hardware_keys(self.config_file)
        self._config_divide_map = self.discovery.load_config_divide_by(self.config_file)
        self._config_unit_map = self.discovery.load_config_unit_overrides(self.config_file)
        for st in self.states:
            key = normalize_hardware_key(st.sensor.chip, st.sensor.sensor_group)
            st.in_config = key in hw_keys
            st.selected = False
            self._refresh_row(self.states.index(st))
        self._reorder_table()
    
    def _update_configuration_status(self):
        hw_keys = self.discovery.load_config_hardware_keys(self.config_file)
        for i, st in enumerate(self.states):
            key = normalize_hardware_key(st.sensor.chip, st.sensor.sensor_group)
            st.in_config = key in hw_keys
            self._refresh_row(i)
        if self._active_idx is not None:
            self._sync_detail_from_idx(self._active_idx)
        self._reorder_table()

    def _reload_daemon(self):
        import subprocess
        subprocess.run(["sensor-monitor", "-c", self.config_file, "reload"], 
                      capture_output=True, text=True)

    def _update_sort_headers(self):
        table = self.query_one("#tbl", ClickableDataTable)
        for col_key in [COL_ENABLED, COL_CONFIGURED, COL_NUM, COL_VAR, COL_READ, COL_UNIT, COL_CHIP, COL_SENSOR, COL_LABEL]:
            label_obj = table.columns[col_key].label
            if hasattr(label_obj, 'plain'):
                label = label_obj.plain
            else:
                label = str(label_obj)
            if label.endswith(" ↑") or label.endswith(" ↓"):
                label = label[:-2]
            if col_key == self.sort_key:
                arrow = " ↓" if self.sort_reverse else " ↑"
                label += arrow
            table.columns[col_key].label = label

    def _set_sort(self, key):
        if self._loading:
            return
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = False
        self._recompute_display_order()
        self._reorder_table()
        self._update_sort_headers()

    def action_quit(self): self.exit()
    def action_focus_filter(self): self.query_one("#filter_in").focus()
    def action_toggle_focused(self):
        if self._loading or self._active_idx is None:
            return
        self._toggle_sensor(self._active_idx)
    def action_select_all(self):
        if self._loading: return
        for st in self.states:
            if not st.selected:
                st.selected = True
                self._refresh_row(self.states.index(st))
    def action_select_none(self):
        if self._loading: return
        for st in self.states:
            if st.selected:
                st.selected = False
                self._refresh_row(self.states.index(st))
    def action_sort_enabled(self): self._set_sort(COL_ENABLED)
    def action_sort_configured(self): self._set_sort(COL_CONFIGURED)
    def action_sort_chip(self): self._set_sort(COL_CHIP)
    def action_sort_num(self): self._set_sort(COL_NUM)
    def action_sort_sensor(self): self._set_sort(COL_SENSOR)
    def action_sort_unit(self): self._set_sort(COL_UNIT)
    def action_sort_value(self): self._set_sort(COL_READ)
    def action_sort_label(self): self._set_sort(COL_LABEL)
    def action_sort_var(self): self._set_sort(COL_VAR)
    def action_sort_reverse(self):
        if self._loading: return
        self.sort_reverse = not self.sort_reverse
        self._recompute_display_order()
        self._reorder_table()
        self._update_sort_headers()
    def action_focus_table(self):
        if not self._loading:
            self.query_one("#tbl").focus()
    def action_focus_var(self):
        if not self._loading:
            self.query_one("#var_in").focus()

def main():
    import argparse
    from pathlib import Path
    DEFAULT_CONFIG_DIR = Path.home() / '.config' / 'sensor-monitor'
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / 'sm_config.yaml'
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=str(DEFAULT_CONFIG_FILE))
    args = parser.parse_args()
    config_path = Path(args.config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    app = SensorDiscoveryTui(config_file=str(config_path))
    app.run()

if __name__ == "__main__":
    main()