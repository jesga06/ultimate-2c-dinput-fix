"""
Controller Wrapper Configuration GUI (gui.py)
This script provides the CustomTkinter GUI interface.
It allows users to monitor wrapper connection status and configure button
mappings interactively (with keyboard combo / mouse click & scroll recorders).
"""
import customtkinter as ctk
import configparser
import json
import os
import pynput
import argparse
from logger_setup import setup_logger

logger = None

ctk.set_appearance_mode("Dark")
script_dir = os.path.dirname(os.path.abspath(__file__))
theme_path = os.path.join(script_dir, "purple_theme.json")
ctk.set_default_color_theme(theme_path)


class App(ctk.CTk):
    """
    Main Tkinter application class for the Configuration GUI.
    Manages layout tabs (Dashboard and Remapping), listens to status.json,
    and saves user remappings directly to config.ini.
    """

    def __init__(self):
        super().__init__()

        self.title("Controller Wrapper Configuration")
        self.geometry("900x700")

        self.config_file = 'config.ini'
        self.config = configparser.ConfigParser()
        self.load_config()

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_remapping = self.tabview.add("Remapping")

        self.setup_dashboard()
        self.setup_remapping()

        self.update_status_loop()

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        if not self.config.has_section('extra_buttons'):
            self.config.add_section('extra_buttons')
        if not self.config.has_section('settings'):
            self.config.add_section('settings')
        if not self.config.has_option('settings', 'layout'):
            self.config.set('settings', 'layout', 'xbox')
        if not self.config.has_option('settings', 'digital_lt'):
            self.config.set('settings', 'digital_lt', 'false')
        if not self.config.has_option('settings', 'digital_rt'):
            self.config.set('settings', 'digital_rt', 'false')
        if not self.config.has_section('block_xinput'):
            self.config.add_section('block_xinput')

    def save_config(self):
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def setup_dashboard(self):
        self.status_label = ctk.CTkLabel(
            self.tab_dashboard,
            text="Status: Unknown",
            font=ctk.CTkFont(
                size=20,
                weight="bold"))
        self.status_label.pack(pady=40)

        self.device_label = ctk.CTkLabel(
            self.tab_dashboard,
            text="Device: -",
            font=ctk.CTkFont(
                size=16))
        self.device_label.pack(pady=10)

        self.layout_var = ctk.StringVar(
            value=self.config.get(
                'settings', 'layout', fallback='xbox'))
        layout_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        layout_frame.pack(pady=20)

        layout_lbl = ctk.CTkLabel(
            layout_frame,
            text="Visual Layout:",
            font=ctk.CTkFont(
                weight="bold"))
        layout_lbl.pack(side="left", padx=10)

        layout_dropdown = ctk.CTkOptionMenu(
            layout_frame,
            values=["xbox", "playstation", "nintendo"],
            variable=self.layout_var,
            command=self.on_layout_changed
        )
        layout_dropdown.pack(side="left")

        info = ctk.CTkLabel(
            self.tab_dashboard,
            text="The background wrapper reloads configuration automatically.",
            text_color="gray")
        info.pack(pady=40)

    def on_layout_changed(self, new_layout):
        self.config.set('settings', 'layout', new_layout)
        self.save_config()
        self.refresh_labels()

    def get_layout_labels(self):
        layout = self.config.get('settings', 'layout', fallback='xbox')
        labels = {}
        if layout == 'playstation':
            labels = {
                'a': 'Cross (X)',
                'b': 'Circle (O)',
                'x': 'Square (■)',
                'y': 'Triangle (▲)',
                'lb': 'L1',
                'rb': 'R1',
                'lt': 'L2',
                'rt': 'R2',
                'l3': 'L3',
                'r3': 'R3',
                'select': 'Share',
                'start': 'Options'
            }
        elif layout == 'nintendo':
            labels = {
                'a': 'B',
                'b': 'A',
                'x': 'Y',
                'y': 'X',
                'lb': 'L',
                'rb': 'R',
                'lt': 'ZL',
                'rt': 'ZR',
                'l3': 'LS',
                'r3': 'RS',
                'select': '-',
                'start': '+'
            }
        else:
            labels = {
                'l3': 'LS',
                'r3': 'RS'
            }
        return labels

    def get_btn_display_name(self, btn):
        labels = self.get_layout_labels()
        return labels.get(btn, btn.upper())

    def refresh_labels(self):
        if hasattr(self, 'label_widgets'):
            for btn, lbl in self.label_widgets.items():
                lbl.configure(text=self.get_btn_display_name(btn))

    def setup_remapping(self):
        # Configure columns and rows in tab_remapping for expansion
        self.tab_remapping.grid_columnconfigure(0, weight=1)
        self.tab_remapping.grid_columnconfigure(1, weight=1)
        self.tab_remapping.grid_rowconfigure(0, weight=1)
        self.tab_remapping.grid_rowconfigure(1, weight=1)

        # Create 4 quadrants using normal Frames to avoid resize lag
        self.frame_face = ctk.CTkFrame(self.tab_remapping)
        self.frame_dpad = ctk.CTkFrame(self.tab_remapping)
        self.frame_sticks = ctk.CTkFrame(self.tab_remapping)
        self.frame_system = ctk.CTkFrame(self.tab_remapping)

        # Labels for the frames since CTkFrame doesn't have label_text
        for f, title in [(self.frame_face, "Face Buttons"), (self.frame_dpad, "D-Pad"),
                         (self.frame_sticks, "Shoulders & Sticks"), (self.frame_system, "System & Extras")]:
            lbl = ctk.CTkLabel(
                f, text=title, font=ctk.CTkFont(
                    size=14, weight="bold"))
            lbl.grid(row=0, column=0, columnspan=5, pady=(5, 5))

        self.frame_face.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.frame_dpad.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.frame_sticks.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
            sticky="nsew")
        self.frame_system.grid(
            row=1,
            column=1,
            padx=10,
            pady=10,
            sticky="nsew")

        self.entries = {}
        self.label_widgets = {}
        self.block_checkboxes = {}
        self.block_vars = {}
        self.digital_checkboxes = {}
        self.digital_vars = {}

        # Add headers helper
        def add_headers(frame, show_digital=False):
            h_map = ctk.CTkLabel(
                frame, text="Mapping", font=ctk.CTkFont(
                    size=11, weight="bold"))
            h_map.grid(row=1, column=1, padx=5, pady=2, sticky="w")
            h_block = ctk.CTkLabel(
                frame, text="Block", font=ctk.CTkFont(
                    size=11, weight="bold"))
            h_block.grid(row=1, column=3, padx=5, pady=2)
            if show_digital:
                h_dig = ctk.CTkLabel(
                    frame, text="Digital", font=ctk.CTkFont(
                        size=11, weight="bold"))
                h_dig.grid(row=1, column=4, padx=5, pady=2)

        add_headers(self.frame_face)
        add_headers(self.frame_dpad)
        add_headers(self.frame_sticks, show_digital=True)
        add_headers(self.frame_system)

        def add_button_row(frame, btn, row_idx):
            lbl = ctk.CTkLabel(frame, text=self.get_btn_display_name(btn))
            lbl.grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
            self.label_widgets[btn] = lbl

            current_val = ""
            if self.config.has_option('extra_buttons', btn):
                current_val = self.config.get('extra_buttons', btn)

            entry = ctk.CTkEntry(frame, width=120)
            entry.insert(0, current_val)
            entry.grid(row=row_idx, column=1, padx=5, pady=2, sticky="w")

            # Bind events for auto-save
            entry.bind(
                "<FocusOut>",
                lambda e,
                b=btn: self.on_mapping_changed(b))
            entry.bind("<Return>", lambda e, b=btn: self.on_mapping_changed(b))

            self.entries[btn] = entry

            rec_btn = ctk.CTkButton(frame, text="⏺", width=30,
                                    command=lambda b=btn: self.start_recording(b))
            rec_btn.grid(row=row_idx, column=2, padx=5, pady=2)

            # Checkbox for Block XInput
            is_blocked = True
            if self.config.has_option('block_xinput', btn):
                is_blocked = self.config.get(
                    'block_xinput', btn).lower() != 'false'

            cb_var = ctk.BooleanVar(value=is_blocked)
            cb = ctk.CTkCheckBox(frame, text="", variable=cb_var, width=20,
                                 command=lambda b=btn, v=cb_var: self.on_block_toggled(b, v))
            cb.grid(row=row_idx, column=3, padx=5, pady=2)
            self.block_checkboxes[btn] = cb
            self.block_vars[btn] = cb_var

            if current_val == "":
                cb.configure(state="disabled")

            # Checkbox for Digital Trigger (only for lt/rt)
            if btn in ['lt', 'rt']:
                is_digital = False
                if self.config.has_option('settings', f'digital_{btn}'):
                    is_digital = self.config.get(
                        'settings', f'digital_{btn}').lower() == 'true'

                dig_var = ctk.BooleanVar(value=is_digital)
                dig_cb = ctk.CTkCheckBox(frame, text="", variable=dig_var, width=20,
                                         command=lambda b=btn, v=dig_var: self.on_digital_trigger_toggled(b, v))
                dig_cb.grid(row=row_idx, column=4, padx=5, pady=2)
                self.digital_checkboxes[btn] = dig_cb
                self.digital_vars[btn] = dig_var

        # Button groups
        face_buttons = ['a', 'b', 'x', 'y']
        dpad_buttons = ['dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']
        stick_buttons = ['lb', 'rb', 'lt', 'rt', 'l3', 'r3']
        system_buttons = ['select', 'start', 'home']

        # Extra dynamic buttons
        existing_extras = []
        standard_buttons = face_buttons + dpad_buttons + stick_buttons + system_buttons
        if self.config.has_section('extra_buttons'):
            for k in self.config.options('extra_buttons'):
                if k not in standard_buttons:
                    existing_extras.append(k)

        # Populate quadrants
        for i, btn in enumerate(face_buttons):
            add_button_row(self.frame_face, btn, i + 2)

        for i, btn in enumerate(dpad_buttons):
            add_button_row(self.frame_dpad, btn, i + 2)

        for i, btn in enumerate(stick_buttons):
            add_button_row(self.frame_sticks, btn, i + 2)

        all_system_and_extras = system_buttons + existing_extras
        for i, btn in enumerate(all_system_and_extras):
            add_button_row(self.frame_system, btn, i + 2)

    def start_recording(self, btn):
        record_win = ctk.CTkToplevel(self)
        record_win.title(f"Record Mapping for {btn.upper()}")
        record_win.geometry("400x200")
        record_win.attributes("-topmost", True)
        record_win.focus()

        lbl = ctk.CTkLabel(
            record_win,
            text="Press your key combination or mouse button...\n\nClick 'Save' when done.",
            font=ctk.CTkFont(
                size=14))
        lbl.pack(pady=20)

        result_var = ctk.StringVar(value="")
        result_lbl = ctk.CTkLabel(
            record_win,
            textvariable=result_var,
            font=ctk.CTkFont(
                size=16,
                weight="bold"))
        result_lbl.pack(pady=10)

        recorded_keys = []
        is_showing_settings = False
        detected_scroll_direction = None
        accumulated_notches = 1

        mode_var = ctk.StringVar(value="continuous")
        interval_var = ctk.StringVar(value="0.05")
        notches_var = ctk.StringVar(value="Notches: 1")

        scroll_settings_frame = ctk.CTkFrame(record_win)

        def on_mode_change(mode):
            if mode == "oneshot":
                interval_entry.configure(state="disabled")
            else:
                interval_entry.configure(state="normal")

        def update_notches_lbl():
            notches_var.set(f"Notches: {accumulated_notches}")

        def on_test_scroll(event):
            nonlocal accumulated_notches
            ticks = abs(event.delta) // 120
            if ticks == 0:
                ticks = 1
            if event.delta > 0:
                accumulated_notches += ticks
            else:
                accumulated_notches = max(1, accumulated_notches - ticks)
            update_notches_lbl()

        def reset_notches():
            nonlocal accumulated_notches
            accumulated_notches = 1
            update_notches_lbl()

        # Mode selector
        mode_lbl = ctk.CTkLabel(scroll_settings_frame, text="Mode:")
        mode_lbl.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        mode_seg = ctk.CTkSegmentedButton(
            scroll_settings_frame,
            values=[
                "oneshot",
                "continuous"],
            variable=mode_var,
            command=on_mode_change)
        mode_seg.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Interval
        interval_lbl = ctk.CTkLabel(
            scroll_settings_frame,
            text="Interval (sec):")
        interval_lbl.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        interval_entry = ctk.CTkEntry(
            scroll_settings_frame,
            textvariable=interval_var,
            width=80)
        interval_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Tester box
        tester_box = ctk.CTkLabel(
            scroll_settings_frame,
            text="<< SCROLL HERE TO SET NOTCHES >>",
            fg_color="#2b2b2b",
            width=250,
            height=60,
            corner_radius=6)
        tester_box.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=10,
            pady=10,
            sticky="ew")
        tester_box.bind("<MouseWheel>", on_test_scroll)

        # Notches display and reset
        notches_display_lbl = ctk.CTkLabel(
            scroll_settings_frame,
            textvariable=notches_var,
            font=ctk.CTkFont(
                weight="bold"))
        notches_display_lbl.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        reset_btn = ctk.CTkButton(
            scroll_settings_frame,
            text="Reset",
            width=60,
            command=reset_notches)
        reset_btn.grid(row=3, column=1, padx=10, pady=5, sticky="e")

        def show_scroll_settings(direction):
            nonlocal is_showing_settings, detected_scroll_direction
            detected_scroll_direction = direction
            if not is_showing_settings:
                record_win.geometry("450x450")
                scroll_settings_frame.pack(pady=10)
                is_showing_settings = True

        def hide_scroll_settings():
            nonlocal is_showing_settings, detected_scroll_direction
            detected_scroll_direction = None
            if is_showing_settings:
                record_win.geometry("400x200")
                scroll_settings_frame.pack_forget()
                is_showing_settings = False

        def on_press(key):
            try:
                key_name = key.char
            except AttributeError:
                key_name = key.name

            if key_name not in recorded_keys:
                recorded_keys.append(key_name)
                result_var.set("keyboard:" + "+".join(recorded_keys))
                hide_scroll_settings()

        def on_click(x, y, button, pressed):
            if pressed:
                if button.name == 'x1':
                    b_name = 'mouse4'
                elif button.name == 'x2':
                    b_name = 'mouse5'
                else:
                    b_name = f"mouse:{button.name}"

                if button.name == 'left':
                    return

                result_var.set(b_name)
                hide_scroll_settings()

        def on_scroll(x, y, dx, dy):
            if is_showing_settings:
                return

            if dy > 0:
                direction = 'scroll_up'
            elif dy < 0:
                direction = 'scroll_down'
            elif dx > 0:
                direction = 'scroll_right'
            elif dx < 0:
                direction = 'scroll_left'
            else:
                return

            result_var.set(f"mouse:{direction}")
            try:
                k_listener.stop()
            except Exception:
                pass
            try:
                m_listener.stop()
            except Exception:
                pass

            show_scroll_settings(direction)

        k_listener = pynput.keyboard.Listener(on_press=on_press)
        m_listener = pynput.mouse.Listener(
            on_click=on_click, on_scroll=on_scroll)
        k_listener.start()
        m_listener.start()

        def save_and_close():
            try:
                k_listener.stop()
            except Exception:
                pass
            try:
                m_listener.stop()
            except Exception:
                pass

            if is_showing_settings:
                mode = mode_var.get()
                notches_val = accumulated_notches
                if mode == "oneshot":
                    val = f"mouse:{detected_scroll_direction}:oneshot:{notches_val}"
                else:
                    try:
                        int_val = float(interval_var.get())
                    except ValueError:
                        int_val = 0.05
                    val = f"mouse:{detected_scroll_direction}:continuous:{notches_val}:{int_val}"
            else:
                val = result_var.get()

            if val:
                self.entries[btn].delete(0, 'end')
                self.entries[btn].insert(0, val)
                self.on_mapping_changed(btn)
            record_win.destroy()

        def cancel_and_close():
            try:
                k_listener.stop()
            except Exception:
                pass
            try:
                m_listener.stop()
            except Exception:
                pass
            record_win.destroy()

        # Wrap in a frame for side-by-side buttons
        btn_frame = ctk.CTkFrame(record_win, fg_color="transparent")
        btn_frame.pack(pady=10)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save",
            command=save_and_close)
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=cancel_and_close,
            fg_color="gray")
        cancel_btn.pack(side="right", padx=10)

        record_win.protocol("WM_DELETE_WINDOW", cancel_and_close)

    def on_mapping_changed(self, btn):
        val = self.entries[btn].get().strip()
        if val == "":
            if self.config.has_option('extra_buttons', btn):
                self.config.remove_option('extra_buttons', btn)
            if self.config.has_option('block_xinput', btn):
                self.config.remove_option('block_xinput', btn)
            self.block_vars[btn].set(True)
            self.block_checkboxes[btn].configure(state="disabled")
        else:
            self.config.set('extra_buttons', btn, val)
            self.block_checkboxes[btn].configure(state="normal")
        self.save_config()

    def on_block_toggled(self, btn, var):
        is_blocked = var.get()
        if not self.config.has_section('block_xinput'):
            self.config.add_section('block_xinput')
        if is_blocked:
            if self.config.has_option('block_xinput', btn):
                self.config.remove_option('block_xinput', btn)
        else:
            self.config.set('block_xinput', btn, 'false')
        self.save_config()

    def on_digital_trigger_toggled(self, btn, var):
        is_digital = var.get()
        if not self.config.has_section('settings'):
            self.config.add_section('settings')
        self.config.set(
            'settings',
            f'digital_{btn}',
            'true' if is_digital else 'false')
        self.save_config()

    def update_status_loop(self):
        status_text = "Status: Disconnected"
        device_text = "Device: -"

        try:
            if os.path.exists('status.json'):
                with open('status.json', 'r') as f:
                    data = json.load(f)
                    state = data.get("status", "Unknown")
                    dev = data.get("device", "-")

                    if state == "Connected":
                        status_text = f"Status: {state}"
                        self.status_label.configure(text_color="#00FF00")
                    else:
                        status_text = f"Status: {state}"
                        self.status_label.configure(text_color="gray")

                    device_text = f"Device: {dev}"
        except Exception:
            pass

        self.status_label.configure(text=status_text)
        self.device_label.configure(text=device_text)

        # Schedule next update in 1000ms
        self.after(1000, self.update_status_loop)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log',
        action='store_true',
        help='Enable verbose debugging logs')
    parser.add_argument(
        '--append-log',
        action='store_true',
        help='Append to log file instead of overwriting')
    args = parser.parse_args()

    logger = setup_logger('gui', 'wrapper.log', args.log, args.append_log)
    if args.log:
        logger.info("GUI started in debug mode")

    app = App()
    app.mainloop()
