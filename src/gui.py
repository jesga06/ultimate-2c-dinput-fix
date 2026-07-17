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
import threading
import time
import random
import tkinter as tk
from logger_setup import setup_logger
from hid_reader import HIDReader, RawHIDReport
from decoder import Decoder
from circularity_modal import CircularityCalibrationModal

logger = None

# Read global config to set UI theme early
_global_config = configparser.ConfigParser()
_global_config.read('config.ini')
_appearance = _global_config.get('UI', 'appearance', fallback="Dark")
_theme = _global_config.get('UI', 'theme', fallback="purple")

ctk.set_appearance_mode(_appearance)
script_dir = os.path.dirname(os.path.abspath(__file__))
# Check if theme is in themes directory (new) or root (legacy purple)
theme_path = os.path.join(script_dir, "themes", f"{_theme}_theme.json")
if not os.path.exists(theme_path):
    theme_path = os.path.join(script_dir, f"{_theme}_theme.json")
if os.path.exists(theme_path):
    ctk.set_default_color_theme(theme_path)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(300, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        
        # Simple label for tooltip
        label = ctk.CTkLabel(tw, text=self.text, justify="left", fg_color="#333333", text_color="white", corner_radius=4, padx=10, pady=5)
        label.pack(ipadx=1, ipady=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class LoadingSpinner(tk.Canvas):
    def __init__(self, master, size=30, width=3, color="#7500ab", **kwargs):
        # Resolve the actual background color by walking up the master chain to find a non-transparent fg_color
        bg = "gray10"
        curr = master
        while curr:
            try:
                val = curr.cget("fg_color")
                if val and val != "transparent":
                    if isinstance(val, (list, tuple)):
                        mode = ctk.get_appearance_mode().lower()
                        bg = val[0] if mode == "light" else val[1]
                    else:
                        bg = val
                    break
            except Exception:
                pass
            curr = getattr(curr, "master", None)
            
        super().__init__(master, width=size, height=size, bg=bg, highlightthickness=0, **kwargs)
        self.size = size
        self.arc_width = width
        self.color = color
        self.angle = 0
        self.running = False
        self.arc = None
        self.draw_arc()
        
    def draw_arc(self):
        if self.arc:
            self.delete(self.arc)
        padding = self.arc_width + 2
        self.arc = self.create_arc(
            padding, padding, self.size - padding, self.size - padding,
            outline=self.color, width=self.arc_width, style="arc", start=self.angle, extent=280
        )
        
    def set_color(self, color):
        self.color = color
        self.itemconfig(self.arc, outline=color)
        
    def set_bg(self, bg_color):
        self.configure(bg=bg_color)
        
    def start(self):
        if not self.running:
            self.running = True
            self.rotate()
            
    def stop(self):
        self.running = False
        
    def rotate(self):
        if not self.running:
            return
        self.angle = (self.angle + 8) % 360
        self.itemconfig(self.arc, start=self.angle)
        self.after(20, self.rotate)

# Color configuration for overlay transitions
LOADING_COLORS = {
    "light": {
        "bg_start": "gray95",       # Main window bg in light mode
        "bg_end": "#d4d4d4",        # Slightly greyed out light mode bg
        "text_quote": "gray14",
        "text_quoted": "gray30",
        "spinner": "#9200d6"
    },
    "dark": {
        "bg_start": "gray10",       # Main window bg in dark mode
        "bg_end": "#262626",        # Slightly greyed out dark mode bg (e.g. darker/dimmed)
        "text_quote": "gray84",
        "text_quoted": "gray60",
        "spinner": "#7500ab"
    }
}

class LoadingOverlay(ctk.CTkFrame):
    def __init__(self, parent, quotes, **kwargs):
        super().__init__(parent, corner_radius=0, **kwargs)
        self.parent = parent
        self.quotes = quotes
        
        # Container to hold quote, author and spinner, centered on screen
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Quote label: bold, centered
        self.quote_label = ctk.CTkLabel(
            self.container,
            text="",
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=600,
            justify="center"
        )
        self.quote_label.pack(pady=(10, 5))
        
        # Quoted author label: italic, right offset (using padx=(80, 0) to shift right from center)
        self.quoted_label = ctk.CTkLabel(
            self.container,
            text="",
            font=ctk.CTkFont(size=14, weight="normal", slant="italic"),
            justify="right"
        )
        self.quoted_label.pack(pady=(0, 20), anchor="center", padx=(80, 0))
        
        # Small rotating loading circle (spinner) below the text
        self.spinner = LoadingSpinner(self.container, size=32, width=3)
        self.spinner.pack(pady=(10, 10))
        
        self.fade_after_id = None
        
    def start_loading(self, tab_value, on_complete, on_finish=None):
        self.on_finish_cb = on_finish
        # Cancel any pending transitions
        if self.fade_after_id:
            self.after_cancel(self.fade_after_id)
            self.fade_after_id = None
            
        # Select random quote
        if self.quotes:
            q = random.choice(self.quotes)
            self.quote_label.configure(text=f'"{q["quote"]}"')
            self.quoted_label.configure(text=f"- {q['author']} ")
        else:
            self.quote_label.configure(text="")
            self.quoted_label.configure(text="")
            
        # Place/show overlay
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        
        # Start spinner rotation
        self.spinner.start()
        
        # Animate fade-in (0.0 to 1.0)
        self.animate_fade(0.0, 1.0, 250, on_complete=lambda: self.hold_loading(tab_value, on_complete))
        
    def hold_loading(self, tab_value, on_complete):
        # Perform actual tab switch
        on_complete(tab_value)
        # Hold loading screen for 900ms, then fade out
        self.fade_after_id = self.after(900, lambda: self.animate_fade(1.0, 0.0, 250, on_complete=self.finish_loading))
        
    def finish_loading(self):
        self.spinner.stop()
        self.place_forget()
        if hasattr(self, 'on_finish_cb') and self.on_finish_cb:
            self.on_finish_cb()
            self.on_finish_cb = None
        
    def get_rgb(self, color_spec):
        color = color_spec
        if isinstance(color_spec, (list, tuple)):
            mode = ctk.get_appearance_mode().lower()
            color = color_spec[0] if mode == "light" else color_spec[1]
        
        try:
            r, g, b = self.winfo_rgb(color)
            return r // 256, g // 256, b // 256
        except Exception:
            if color.startswith("#"):
                h = color.lstrip("#")
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            return (0, 0, 0)
            
    def interpolate_color(self, rgb_start, rgb_end, factor):
        r = int(rgb_start[0] + (rgb_end[0] - rgb_start[0]) * factor)
        g = int(rgb_start[1] + (rgb_end[1] - rgb_start[1]) * factor)
        b = int(rgb_start[2] + (rgb_end[2] - rgb_start[2]) * factor)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def animate_fade(self, start_f, end_f, duration_ms, on_complete=None):
        steps = 15
        step_delay = duration_ms // steps
        
        mode = ctk.get_appearance_mode().lower()
        if mode not in ["light", "dark"]:
            mode = "dark"
            
        color_info = LOADING_COLORS[mode]
        rgb_bg_start = self.get_rgb(color_info["bg_start"])
        rgb_bg_end = self.get_rgb(color_info["bg_end"])
        rgb_text_quote = self.get_rgb(color_info["text_quote"])
        rgb_text_quoted = self.get_rgb(color_info["text_quoted"])
        rgb_spinner = self.get_rgb(color_info["spinner"])
        
        self._fade_step(
            0, steps, step_delay, start_f, end_f,
            rgb_bg_start, rgb_bg_end, rgb_text_quote, rgb_text_quoted, rgb_spinner,
            on_complete
        )
        
    def _fade_step(self, current_step, total_steps, step_delay, start_f, end_f,
                   rgb_bg_start, rgb_bg_end, rgb_text_quote, rgb_text_quoted, rgb_spinner,
                   on_complete):
        progress = current_step / total_steps
        f = start_f + (end_f - start_f) * progress
        
        bg_color = self.interpolate_color(rgb_bg_start, rgb_bg_end, f)
        quote_color = self.interpolate_color(rgb_bg_start, rgb_text_quote, f)
        quoted_color = self.interpolate_color(rgb_bg_start, rgb_text_quoted, f)
        spinner_color = self.interpolate_color(rgb_bg_start, rgb_spinner, f)
        
        self.configure(fg_color=bg_color)
        self.quote_label.configure(text_color=quote_color)
        self.quoted_label.configure(text_color=quoted_color)
        self.spinner.set_bg(bg_color)
        self.spinner.set_color(spinner_color)
        
        if current_step < total_steps:
            self.fade_after_id = self.after(
                step_delay,
                lambda: self._fade_step(
                    current_step + 1, total_steps, step_delay, start_f, end_f,
                    rgb_bg_start, rgb_bg_end, rgb_text_quote, rgb_text_quoted, rgb_spinner,
                    on_complete
                )
            )
        else:
            self.fade_after_id = None
            if on_complete:
                on_complete()

class App(ctk.CTk):
    """
    Main Tkinter application class for the Configuration GUI.
    Manages layout tabs (Dashboard and Remapping), listens to status.json,
    and saves user remappings directly to config.ini.
    """

    def __init__(self):
        super().__init__()

        self.title("Controller Wrapper Configuration")
        self.geometry("980x700")

        self.resize_timer = None
        self.bind("<Configure>", self.on_window_resize)

        self.daemon_config_file = 'config.ini'
        self.daemon_config = configparser.ConfigParser()
        if os.path.exists(self.daemon_config_file):
            self.daemon_config.read(self.daemon_config_file)
            
        device_name = "Default Controller"
        hardware_profile_path = None
        if self.daemon_config.has_section('controller'):
            device_name = self.daemon_config.get('controller', 'last_device', fallback=device_name)
            hardware_profile_path = self.daemon_config.get('controller', 'last_profile', fallback=None)

        # Check if a device is connected right now
        from hid_reader import HIDReader
        devices = HIDReader.get_all_devices()
        for d in devices:
            vid = d.get('vendor_id', 0)
            pid = d.get('product_id', 0)
            potential = f"profiles/{vid:04X}_{pid:04X}.json".lower()
            if os.path.exists(potential):
                hardware_profile_path = potential
                try:
                    with open(potential, 'r') as f:
                        prof_data = json.load(f)
                        device_name = prof_data.get('name', device_name)
                except:
                    pass
                break
        
        self.hardware_profile_path = hardware_profile_path
        self.hardware_layout = 'xbox'
        if hardware_profile_path and os.path.exists(hardware_profile_path):
            try:
                with open(hardware_profile_path, 'r') as f:
                    prof_data = json.load(f)
                    self.hardware_layout = prof_data.get('layout', 'xbox')
            except:
                pass

        from config_manager import ControllerConfig, get_sanitized_filename
        sanitized_name = get_sanitized_filename(device_name)
        self.config_file = os.path.join('profiles', sanitized_name)
        self.config = ControllerConfig(self.config_file)
        self.load_config()

        self.current_state = None
        self.hid_reader = None
        self.decoder = None

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_profile = self.tabview.add("Profile")
        self.tab_remapping = self.tabview.add("Remapping")
        self.tab_analog = self.tabview.add("Tuning")
        self.tab_advanced = self.tabview.add("Advanced")
        self.tab_utilities = self.tabview.add("Utilities")
        self.tab_customization = self.tabview.add("Customization")

        self.setup_dashboard()
        self.setup_profile()
        self.setup_remapping()
        self.setup_analog_tuning()
        self.setup_advanced()
        self.setup_utilities()
        self.setup_customization()

        # Load loading quotes from hidden json
        quotes_path = os.path.join(script_dir, ".loading_quotes.json")
        self.loading_quotes = []
        if os.path.exists(quotes_path):
            try:
                with open(quotes_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.loading_quotes = data.get("quotes", [])
            except Exception as e:
                if logger:
                    logger.error(f"Error loading quotes: {e}")
                else:
                    print(f"Error loading quotes: {e}")

        # Initialize Loading Overlay
        self.loading_overlay = LoadingOverlay(self, self.loading_quotes)
        
        # Intercept segmented button callback for tab switching
        original_callback = self.tabview._segmented_button_callback
        
        def custom_tab_callback(value):
            if getattr(self, "_switching_tab", False):
                return
            self._switching_tab = True
            
            def reset_switch():
                self._switching_tab = False
                
            # Start loading overlay
            self.loading_overlay.start_loading(value, original_callback, reset_switch)
            
        self.tabview._segmented_button_callback = custom_tab_callback
        self.tabview._segmented_button.configure(command=custom_tab_callback)

        self.update_status_loop()
        self.start_hid_polling()

    def on_window_resize(self, event):
        if event.widget == self:
            if self.resize_timer:
                self.after_cancel(self.resize_timer)
            else:
                if hasattr(self, 'tabview'):
                    self.tabview.pack_forget()
            self.resize_timer = self.after(150, self.execute_delayed_resize)

    def execute_delayed_resize(self):
        if hasattr(self, 'tabview'):
            self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        self.resize_timer = None

    def start_hid_polling(self):
        def poll_thread():
            # Scan for devices using the same logic as main.py
            devices = HIDReader.get_all_devices()
            selected_vid = None
            selected_pid = None
            profile_path = None

            for d in devices:
                vid = d.get('vendor_id', 0)
                pid = d.get('product_id', 0)
                potential = f"profiles/{vid:04X}_{pid:04X}.json".lower()
                if os.path.exists(potential):
                    selected_vid = vid
                    selected_pid = pid
                    profile_path = potential
                    break

            if not profile_path:
                return

            self.decoder = Decoder(profile_path)
            self.hardware_profile_path = profile_path
            self.after(0, self.refresh_shift_trigger_menu)
            if "layout" in self.decoder.profile:
                self.hardware_layout = self.decoder.profile["layout"]
                if hasattr(self, 'layout_label'):
                    self.layout_label.configure(text=f"Visual Layout: {self.hardware_layout.upper()}")
                self.refresh_labels()

            # Determine which interfaces the profile needs
            req_ifaces = []
            if "interfaces" in self.decoder.profile:
                req_ifaces = self.decoder.profile["interfaces"]
            else:
                req_iface = self.decoder.profile.get('interface_number', -1)
                if req_iface != -1:
                    req_ifaces.append(req_iface)

            def handler(report: RawHIDReport):
                self.current_state = self.decoder.decode(report)

            # Open all matching interfaces, just like main.py
            self.hid_readers = []
            for d in devices:
                if d.get('vendor_id', 0) == selected_vid and d.get('product_id', 0) == selected_pid:
                    iface_num = d.get('interface_number', -1)
                    if req_ifaces and iface_num not in req_ifaces:
                        continue
                    reader = HIDReader(device_path=d['path'], interface_number=iface_num)
                    if reader.connect():
                        reader.set_callback(handler)
                        self.hid_readers.append(reader)

            # Start all readers in their own threads (each .start() blocks)
            for reader in self.hid_readers:
                threading.Thread(target=reader.start, daemon=True).start()

        t = threading.Thread(target=poll_thread, daemon=True)
        t.start()

    def load_config(self):
        # Configuration is already loaded by ControllerConfig, but we ensure sections exist
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
        if not self.config.has_section('shift_mappings'):
            self.config.add_section('shift_mappings')
        if not self.config.has_section('shift_block_xinput'):
            self.config.add_section('shift_block_xinput')

    def save_config(self):
        self.config.save()
        with open(self.daemon_config_file, 'w') as f:
            self.daemon_config.write(f)

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

        layout_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        layout_frame.pack(pady=20)

        self.layout_label = ctk.CTkLabel(
            layout_frame,
            text=f"Visual Layout: {self.hardware_layout.upper()}",
            font=ctk.CTkFont(
                size=14,
                weight="bold"))
        self.layout_label.pack(side="left", padx=10)

        info = ctk.CTkLabel(
            self.tab_dashboard,
            text="The background wrapper reloads configuration automatically.",
            text_color="gray")
        info.pack(pady=40)

    def get_layout_labels(self):
        layout = self.hardware_layout
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

    def get_profile_mapped_keys(self):
        defaults = ["a", "b", "x", "y", "lb", "rb", "lt", "rt", "l3", "r3", "select", "start", "dpad_up", "dpad_down", "dpad_left", "dpad_right", "home", "paddle_l", "paddle_r"]
        path = getattr(self, 'hardware_profile_path', None)
        if not path or not os.path.exists(path):
            if self.daemon_config.has_section('controller'):
                path = self.daemon_config.get('controller', 'last_profile', fallback=None)

        if path and os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    prof_data = json.load(f)
                    mapped = set()
                    for rep_id, rep_cfg in prof_data.get('reports', {}).items():
                        for input_name, cfg in rep_cfg.get('inputs', {}).items():
                            itype = cfg.get('type')
                            if itype == 'button':
                                mapped.add(input_name)
                            elif itype == 'hat':
                                mapped.update(['dpad_up', 'dpad_down', 'dpad_left', 'dpad_right'])
                            elif itype == 'trigger':
                                mapped.add(input_name)
                    if mapped:
                        ordered = [""]
                        for k in defaults:
                            if k in mapped:
                                ordered.append(k)
                        for k in sorted(mapped):
                            if k not in ordered:
                                ordered.append(k)
                        return ordered
            except Exception:
                pass
        return [""] + defaults

    def refresh_shift_trigger_menu(self):
        if hasattr(self, 'trig_menu'):
            keys = self.get_profile_mapped_keys()
            self.trig_menu.configure(values=keys)

    def setup_remapping(self):
        # Configure columns and rows in tab_remapping for expansion
        self.tab_remapping.grid_columnconfigure(0, weight=1)
        self.tab_remapping.grid_columnconfigure(1, weight=1)
        self.tab_remapping.grid_rowconfigure(0, weight=1)
        self.tab_remapping.grid_rowconfigure(1, weight=1)

        # Create 4 quadrants using normal Frames to avoid resize lag
        self.frame_face = ctk.CTkFrame(self.tab_remapping, corner_radius=0)
        self.frame_dpad = ctk.CTkFrame(self.tab_remapping, corner_radius=0)
        self.frame_sticks = ctk.CTkFrame(self.tab_remapping, corner_radius=0)
        self.frame_system = ctk.CTkFrame(self.tab_remapping, corner_radius=0)

        # Labels for the frames since CTkFrame doesn't have label_text
        for f, title in [(self.frame_face, "Face Buttons"), (self.frame_dpad, "D-Pad"),
                         (self.frame_sticks, "Shoulders & Sticks"), (self.frame_system, "System & Extras")]:
            lbl = ctk.CTkLabel(
                f, text=title, font=ctk.CTkFont(
                    size=14, weight="bold"))
            lbl.grid(row=0, column=0, columnspan=6, pady=(5, 5))

        self.frame_face.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        self.frame_dpad.grid(row=1, column=0, padx=10, pady=10, sticky="n")
        self.frame_sticks.grid(row=0, column=1, padx=10, pady=10, sticky="n")
        self.frame_system.grid(row=1, column=1, padx=10, pady=10, sticky="n")

        # Info Guide
        info_frame = ctk.CTkFrame(self.tab_remapping, fg_color="transparent")
        info_frame.grid(row=2, column=0, columnspan=2, pady=(10, 20))
        
        info_btn = ctk.CTkButton(info_frame, text="?  Remapping Guide", width=140, height=24, corner_radius=12, fg_color="#555555", hover_color="#666666", font=ctk.CTkFont(size=12))
        info_btn.pack(side="top")
        ToolTip(info_btn, "Mapping: Use the text box to enter a keyboard key or mouse click.\n⏺: Click to record a key combination interactively.\nBlock: Prevent the original controller button from being sent to the game.\nShift Map/S. Blk: Secondary mapping when the shift trigger is held.")

        self.entries = {}
        self.label_widgets = {}
        self.block_checkboxes = {}
        self.block_vars = {}
        self.digital_checkboxes = {}
        self.digital_vars = {}
        
        self.shift_entries = {}
        self.shift_block_checkboxes = {}
        self.shift_block_vars = {}

        # Add headers helper
        def add_headers(frame):
            h_map = ctk.CTkLabel(frame, text="Mapping", font=ctk.CTkFont(size=11, weight="bold"))
            h_map.grid(row=1, column=1, padx=7, pady=2)
            h_block = ctk.CTkLabel(frame, text="Block", font=ctk.CTkFont(size=11, weight="bold"))
            h_block.grid(row=1, column=3, padx=7, pady=2)
            
            h_smap = ctk.CTkLabel(frame, text="Shift Map", font=ctk.CTkFont(size=11, weight="bold"))
            h_smap.grid(row=1, column=4, padx=7, pady=2)
            h_sblock = ctk.CTkLabel(frame, text="S. Blk", font=ctk.CTkFont(size=11, weight="bold"))
            h_sblock.grid(row=1, column=5, padx=7, pady=2)

        add_headers(self.frame_face)
        add_headers(self.frame_dpad)
        add_headers(self.frame_sticks)
        add_headers(self.frame_system)

        def add_button_row(frame, btn, row_idx):
            lbl = ctk.CTkLabel(frame, text=self.get_btn_display_name(btn))
            lbl.grid(row=row_idx, column=0, padx=7, pady=2, sticky="e")
            self.label_widgets[btn] = lbl

            current_val = ""
            if self.config.has_option('extra_buttons', btn):
                current_val = self.config.get('extra_buttons', btn)

            entry = ctk.CTkEntry(frame, width=90, corner_radius=0)
            entry.insert(0, current_val)
            entry.grid(row=row_idx, column=1, padx=7, pady=2)

            # Bind events for auto-save
            entry.bind("<FocusOut>", lambda e, b=btn: self.on_mapping_changed(b))
            entry.bind("<Return>", lambda e, b=btn: self.on_mapping_changed(b))

            self.entries[btn] = entry

            rec_btn = ctk.CTkButton(frame, text="⏺", width=25, corner_radius=0, command=lambda b=btn: self.start_recording(b))
            rec_btn.grid(row=row_idx, column=2, padx=7, pady=2)

            # Checkbox for Block XInput
            is_blocked = True
            if self.config.has_option('block_xinput', btn):
                is_blocked = self.config.get('block_xinput', btn).lower() != 'false'

            cb_var = ctk.BooleanVar(value=is_blocked)
            cb = ctk.CTkCheckBox(frame, text="", variable=cb_var, width=20, corner_radius=0,
                                 command=lambda b=btn, v=cb_var: self.on_block_toggled(b, v))
            cb.grid(row=row_idx, column=3, padx=7, pady=2)
            self.block_checkboxes[btn] = cb
            self.block_vars[btn] = cb_var

            if current_val == "":
                cb.configure(state="disabled")
                
            # Shift Map
            shift_val = ""
            if self.config.has_option('shift_mappings', btn):
                shift_val = self.config.get('shift_mappings', btn)

            s_entry = ctk.CTkEntry(frame, width=90, corner_radius=0)
            s_entry.insert(0, shift_val)
            s_entry.grid(row=row_idx, column=4, padx=7, pady=2)
            
            s_entry.bind("<FocusOut>", lambda e, b=btn: self.on_shift_mapping_changed(b))
            s_entry.bind("<Return>", lambda e, b=btn: self.on_shift_mapping_changed(b))
            self.shift_entries[btn] = s_entry
            
            # Shift Block
            is_s_blocked = True
            if self.config.has_option('shift_block_xinput', btn):
                is_s_blocked = self.config.get('shift_block_xinput', btn).lower() != 'false'

            scb_var = ctk.BooleanVar(value=is_s_blocked)
            scb = ctk.CTkCheckBox(frame, text="", variable=scb_var, width=20, corner_radius=0,
                                 command=lambda b=btn, v=scb_var: self.on_shift_block_toggled(b, v))
            scb.grid(row=row_idx, column=5, padx=7, pady=2)
            self.shift_block_checkboxes[btn] = scb
            self.shift_block_vars[btn] = scb_var

            if shift_val == "":
                scb.configure(state="disabled")

            # Checkbox for Digital Trigger (only for lt/rt)
            # Moved to Tuning tab

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

    def on_shift_mapping_changed(self, btn):
        val = self.shift_entries[btn].get().strip()
        if val == "":
            if self.config.has_option('shift_mappings', btn):
                self.config.remove_option('shift_mappings', btn)
            if self.config.has_option('shift_block_xinput', btn):
                self.config.remove_option('shift_block_xinput', btn)
            self.shift_block_vars[btn].set(True)
            self.shift_block_checkboxes[btn].configure(state="disabled")
        else:
            self.config.set('shift_mappings', btn, val)
            self.shift_block_checkboxes[btn].configure(state="normal")
        self.save_config()

    def on_shift_block_toggled(self, btn, var):
        is_blocked = var.get()
        if not self.config.has_section('shift_block_xinput'):
            self.config.add_section('shift_block_xinput')
        if is_blocked:
            if self.config.has_option('shift_block_xinput', btn):
                self.config.remove_option('shift_block_xinput', btn)
        else:
            self.config.set('shift_block_xinput', btn, 'false')
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

    def setup_analog_tuning(self):
        self.tuning_scroll = ctk.CTkScrollableFrame(self.tab_analog, fg_color="transparent", corner_radius=0)
        self.tuning_scroll.pack(fill="both", expand=True)
        
        self.tuning_scroll.grid_columnconfigure(0, weight=1)
        self.tuning_scroll.grid_columnconfigure(1, weight=1)
        self.tuning_scroll.grid_rowconfigure(0, weight=1)
        self.tuning_scroll.grid_rowconfigure(1, weight=1)

        if not self.config.has_section('analog_left'):
            self.config.add_section('analog_left')
        if not self.config.has_section('analog_right'):
            self.config.add_section('analog_right')

        # Color legend info button
        legend_frame = ctk.CTkFrame(self.tuning_scroll, fg_color="transparent")
        legend_frame.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 0))
        legend_btn = ctk.CTkButton(legend_frame, text="?  Color Guide", width=110, height=24, corner_radius=12, fg_color="#555555", hover_color="#666666", font=ctk.CTkFont(size=12))
        legend_btn.pack(side="left")
        ToolTip(legend_btn, "Cyan = Raw controller input (what your hardware sends)\nPurple = Processed output (what the game receives\nafter deadzone, curve, and anti-deadzone settings)\n\nThe response curve graph shows the relationship between\nraw input (X axis) and processed output (Y axis).\nThe moving dot/bar tracks your live input on the curve.")

        self.tuning_scroll.grid_rowconfigure(0, weight=0)
        self.tuning_scroll.grid_rowconfigure(1, weight=1)
        self.tuning_scroll.grid_rowconfigure(2, weight=1)

        def create_stick_frame(parent, title, section):
            frame = ctk.CTkFrame(parent)
            
            # Header
            lbl_header = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold"))
            lbl_header.pack(pady=10)
            
            # Canvases Frame
            canv_frame = ctk.CTkFrame(frame, fg_color="transparent")
            canv_frame.pack(fill="x", padx=10, pady=5)
            
            import tkinter as tk
            
            # Curve Canvas
            lbl_curve = ctk.CTkLabel(canv_frame, text="Response Curve")
            lbl_curve.grid(row=0, column=0, padx=10)
            c_curve = tk.Canvas(canv_frame, width=180, height=180, bg="#2b2b2b", highlightthickness=0)
            c_curve.grid(row=1, column=0, padx=10)
            
            # Position Canvas
            lbl_pos = ctk.CTkLabel(canv_frame, text="Current Position")
            lbl_pos.grid(row=0, column=1, padx=10)
            c_pos = tk.Canvas(canv_frame, width=180, height=180, bg="#2b2b2b", highlightthickness=0)
            c_pos.grid(row=1, column=1, padx=10)
            
            # Controls
            controls_frame = ctk.CTkFrame(frame, fg_color="transparent")
            controls_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            dz_var = ctk.DoubleVar(value=float(self.config.get(section, 'deadzone', fallback='0.08')))
            adz_var = ctk.DoubleVar(value=float(self.config.get(section, 'anti_deadzone', fallback='0.0')))
            rest_dz_var = ctk.DoubleVar(value=float(self.config.get(section, 'rest_deadzone', fallback='0.0')))
            curve_var = ctk.StringVar(value=self.config.get(section, 'curve', fallback='linear'))
            exp_var = ctk.DoubleVar(value=float(self.config.get(section, 'exp_factor', fallback='2.0')))
            sens_var = ctk.DoubleVar(value=float(self.config.get(section, 'sensitivity', fallback='1.0')))
            
            update_lbl_callbacks = []
            
            def make_slider(label, var, from_, to, res, tooltip=""):
                row_f = ctk.CTkFrame(controls_frame, fg_color="transparent")
                row_f.pack(fill="x", pady=2)
                
                info_btn = ctk.CTkButton(row_f, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
                info_btn.pack(side="left", padx=(0,5))
                ToolTip(info_btn, tooltip)
                
                lbl = ctk.CTkLabel(row_f, text=label, width=90, anchor="w")
                lbl.pack(side="left")
                
                val_lbl = ctk.CTkLabel(row_f, text=f"{var.get():.2f}", width=35)
                val_lbl.pack(side="right")
                
                def update_lbl():
                    val_lbl.configure(text=f"{var.get():.2f}")
                update_lbl_callbacks.append(update_lbl)
                
                def wrap_cmd(val):
                    update_lbl()
                    self.update_analog_config(section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var)
                    
                slider = ctk.CTkSlider(row_f, from_=from_, to=to, number_of_steps=int((to-from_)/res), variable=var, command=wrap_cmd)
                slider.pack(side="left", fill="x", expand=True, padx=5)

            make_slider("Deadzone", dz_var, 0.0, 0.5, 0.01, "Ignores small movements near the center to prevent stick drift.")
            make_slider("Anti-Deadzone", adz_var, 0.0, 0.5, 0.01, "Instantly jumps the output to this value when the deadzone is crossed.\nUseful for games with their own unchangeable built-in deadzones.")
            make_slider("Rest Deadzone", rest_dz_var, 0.0, 0.3, 0.01, "Secondary buffer after the deadzone.\nPrevents anti-deadzone from activating on controllers\nwhose sticks don't rest exactly at center.")
            make_slider("Curve Factor", exp_var, 0.5, 4.0, 0.1, "Intensity of the curve. >1.0 makes it steeper for exponential,\nor steeper at the start for aggressive.")
            make_slider("Sensitivity", sens_var, 0.1, 5.0, 0.05, "Multiplies the final output. Great for tweaking mouse movement.")

            row_f = ctk.CTkFrame(controls_frame, fg_color="transparent")
            row_f.pack(fill="x", pady=5)
            info_btn = ctk.CTkButton(row_f, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
            info_btn.pack(side="left", padx=(0,5))
            ToolTip(info_btn, "Mathematical shape of the response curve.\nLinear = straight 1:1 line.\nExponential = precise at center, fast at edges.\nAggressive = fast at center, precise at edges.")
            ctk.CTkLabel(row_f, text="Curve Type:", width=90, anchor="w").pack(side="left")
            curve_menu = ctk.CTkOptionMenu(row_f, values=["linear", "exponential", "aggressive", "cubic", "sigmoid", "bezier"], variable=curve_var, command=lambda _: self.update_analog_config(section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var))
            curve_menu.pack(side="left", fill="x", expand=True, padx=5)
            
            def export_math():
                import curves
                import tkinter as tk
                from tkinter import messagebox
                latex_str = curves.export_to_latex(curve_var.get(), exp_var.get(), dz_var.get(), adz_var.get(), rest_dz_var.get())
                # Copy to clipboard
                self.clipboard_clear()
                self.clipboard_append(latex_str)
                messagebox.showinfo("Exported", "LaTeX formula copied to clipboard!\n\n" + latex_str)
                
            export_btn = ctk.CTkButton(row_f, text="Export Math", width=80, command=export_math)
            export_btn.pack(side="right", padx=5)

            btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            
            def reset():
                dz_var.set(0.0)
                adz_var.set(0.0)
                rest_dz_var.set(0.0)
                curve_var.set("linear")
                exp_var.set(1.0)
                sens_var.set(1.0)
                for cb in update_lbl_callbacks:
                    cb()
                self.update_analog_config(section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var)

            ctk.CTkButton(btn_frame, text="Reset", command=reset).pack(side="left", padx=5, expand=True)
            
            circ_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
            circ_frame.pack(fill="x", pady=5)
            
            circ_mode_var = ctk.StringVar(value=self.config.get(section, 'circularity_mode', fallback='disabled'))
            
            def update_circ_mode(val):
                if not self.config.has_section(section):
                    self.config.add_section(section)
                self.config.set(section, 'circularity_mode', val)
                self.save_config()
                
            circ_menu = ctk.CTkOptionMenu(circ_frame, values=["disabled", "before", "after"], variable=circ_mode_var, command=update_circ_mode)
            circ_menu.pack(side="left", fill="x", expand=True, padx=5)
            
            def open_circ_calib():
                CircularityCalibrationModal(self, title, section)
                
            circ_btn = ctk.CTkButton(circ_frame, text="Calibrate Circularity", command=open_circ_calib, fg_color="#1f538d")
            circ_btn.pack(side="right", padx=5)

            return frame, c_curve, c_pos, dz_var, adz_var, rest_dz_var, curve_var, exp_var

        self.f_ls, self.c_ls_curve, self.c_ls_pos, self.ls_dz, self.ls_adz, self.ls_rest_dz, self.ls_curve, self.ls_exp = create_stick_frame(self.tuning_scroll, "Left Stick", "analog_left")
        self.f_ls.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.f_rs, self.c_rs_curve, self.c_rs_pos, self.rs_dz, self.rs_adz, self.rs_rest_dz, self.rs_curve, self.rs_exp = create_stick_frame(self.tuning_scroll, "Right Stick", "analog_right")
        self.f_rs.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        def create_trigger_frame(parent, title, btn, section):
            frame = ctk.CTkFrame(parent)
            lbl_header = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold"))
            lbl_header.pack(pady=10)

            canv_frame = ctk.CTkFrame(frame, fg_color="transparent")
            canv_frame.pack(fill="x", padx=10, pady=5)
            
            import tkinter as tk
            
            lbl_curve = ctk.CTkLabel(canv_frame, text="Response Curve")
            lbl_curve.grid(row=0, column=0, padx=10)
            c_curve = tk.Canvas(canv_frame, width=180, height=180, bg="#2b2b2b", highlightthickness=0)
            c_curve.grid(row=1, column=0, padx=10)
            
            lbl_pos = ctk.CTkLabel(canv_frame, text="Trigger Pull")
            lbl_pos.grid(row=0, column=1, padx=10)
            c_pos = tk.Canvas(canv_frame, width=60, height=180, bg="#2b2b2b", highlightthickness=0)
            c_pos.grid(row=1, column=1, padx=10)

            controls_frame = ctk.CTkFrame(frame, fg_color="transparent")
            controls_frame.pack(fill="both", expand=True, padx=10, pady=10)

            dz_var = ctk.DoubleVar(value=float(self.config.get(section, 'deadzone', fallback='0.05')))
            adz_var = ctk.DoubleVar(value=float(self.config.get(section, 'anti_deadzone', fallback='0.0')))
            rest_dz_var = ctk.DoubleVar(value=float(self.config.get(section, 'rest_deadzone', fallback='0.0')))
            curve_var = ctk.StringVar(value=self.config.get(section, 'curve', fallback='linear'))
            exp_var = ctk.DoubleVar(value=float(self.config.get(section, 'exp_factor', fallback='2.0')))
            sens_var = ctk.DoubleVar(value=float(self.config.get(section, 'sensitivity', fallback='1.0')))
            
            update_lbl_callbacks = []
            
            def make_slider(label, var, from_, to, res, tooltip=""):
                row_f = ctk.CTkFrame(controls_frame, fg_color="transparent")
                row_f.pack(fill="x", pady=2)
                
                info_btn = ctk.CTkButton(row_f, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
                info_btn.pack(side="left", padx=(0,5))
                ToolTip(info_btn, tooltip)
                
                lbl = ctk.CTkLabel(row_f, text=label, width=90, anchor="w")
                lbl.pack(side="left")
                
                val_lbl = ctk.CTkLabel(row_f, text=f"{var.get():.2f}", width=35)
                val_lbl.pack(side="right")
                
                def update_lbl():
                    val_lbl.configure(text=f"{var.get():.2f}")
                update_lbl_callbacks.append(update_lbl)
                
                def wrap_cmd(val):
                    update_lbl()
                    self.update_analog_config(section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var)
                    
                slider = ctk.CTkSlider(row_f, from_=from_, to=to, number_of_steps=int((to-from_)/res), variable=var, command=wrap_cmd)
                slider.pack(side="left", fill="x", expand=True, padx=5)

            make_slider("Deadzone", dz_var, 0.0, 0.5, 0.01, "Ignores small initial trigger pulls.")
            make_slider("Anti-Deadzone", adz_var, 0.0, 0.5, 0.01, "Instantly jumps the output to this value when the deadzone is crossed.")
            make_slider("Rest Deadzone", rest_dz_var, 0.0, 0.3, 0.01, "Secondary buffer after the deadzone.\nPrevents anti-deadzone from activating on\ncontrollers with trigger resting drift.")
            make_slider("Curve Factor", exp_var, 0.5, 4.0, 0.1, "Intensity of the curve.")

            row_f = ctk.CTkFrame(controls_frame, fg_color="transparent")
            row_f.pack(fill="x", pady=5)
            info_btn = ctk.CTkButton(row_f, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
            info_btn.pack(side="left", padx=(0,5))
            ToolTip(info_btn, "Mathematical shape of the response curve.")
            ctk.CTkLabel(row_f, text="Curve Type:", width=90, anchor="w").pack(side="left")
            curve_menu = ctk.CTkOptionMenu(row_f, values=["linear", "exponential", "aggressive", "cubic", "sigmoid", "bezier"], variable=curve_var, command=lambda _: self.update_analog_config(section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var))
            curve_menu.pack(side="left", fill="x", expand=True, padx=5)
            
            def export_math():
                import curves
                import tkinter as tk
                from tkinter import messagebox
                latex_str = curves.export_to_latex(curve_var.get(), exp_var.get(), dz_var.get(), adz_var.get(), rest_dz_var.get())
                # Copy to clipboard
                self.clipboard_clear()
                self.clipboard_append(latex_str)
                messagebox.showinfo("Exported", "LaTeX formula copied to clipboard!\n\n" + latex_str)
                
            export_btn = ctk.CTkButton(row_f, text="Export Math", width=80, command=export_math)
            export_btn.pack(side="right", padx=5)

            btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            
            def reset():
                dz_var.set(0.0)
                adz_var.set(0.0)
                rest_dz_var.set(0.0)
                curve_var.set("linear")
                exp_var.set(1.0)
                sens_var.set(1.0)
                for cb in update_lbl_callbacks:
                    cb()
                self.update_analog_config(section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var)

            ctk.CTkButton(btn_frame, text="Reset", command=reset).pack(side="left", padx=5, expand=True)

            # Digital Trigger Checkbox
            dig_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
            dig_row.pack(fill="x", pady=10)
            
            is_digital = False
            if self.config.has_option('settings', f'digital_{btn}'):
                is_digital = self.config.get('settings', f'digital_{btn}').lower() == 'true'

            dig_var = ctk.BooleanVar(value=is_digital)
            dig_cb = ctk.CTkCheckBox(dig_row, text="Digital Trigger Mode", variable=dig_var,
                                     command=lambda b=btn, v=dig_var: self.on_digital_trigger_toggled(b, v))
            dig_cb.pack(side="left", padx=5)
            
            return frame, c_curve, c_pos, dz_var, adz_var, rest_dz_var, curve_var, exp_var

        self.f_lt, self.c_lt_curve, self.c_lt_pos, self.lt_dz, self.lt_adz, self.lt_rest_dz, self.lt_curve, self.lt_exp = create_trigger_frame(self.tuning_scroll, "Left Trigger", "lt", "trigger_left")
        self.f_lt.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.f_rt, self.c_rt_curve, self.c_rt_pos, self.rt_dz, self.rt_adz, self.rt_rest_dz, self.rt_curve, self.rt_exp = create_trigger_frame(self.tuning_scroll, "Right Trigger", "rt", "trigger_right")
        self.f_rt.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

        # Initial draw
        self.draw_curve(self.c_ls_curve, self.ls_dz.get(), self.ls_adz.get(), self.ls_rest_dz.get(), self.ls_curve.get(), self.ls_exp.get())
        self.draw_curve(self.c_rs_curve, self.rs_dz.get(), self.rs_adz.get(), self.rs_rest_dz.get(), self.rs_curve.get(), self.rs_exp.get())
        self.draw_curve_trigger(self.c_lt_curve, self.lt_dz.get(), self.lt_adz.get(), self.lt_rest_dz.get(), self.lt_curve.get(), self.lt_exp.get())
        self.draw_curve_trigger(self.c_rt_curve, self.rt_dz.get(), self.rt_adz.get(), self.rt_rest_dz.get(), self.rt_curve.get(), self.rt_exp.get())
        
        self.update_position_loop()

    def update_analog_config(self, section, dz_var, adz_var, rest_dz_var, curve_var, exp_var, sens_var=None):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, 'deadzone', str(round(dz_var.get(), 3)))
        self.config.set(section, 'anti_deadzone', str(round(adz_var.get(), 3)))
        self.config.set(section, 'rest_deadzone', str(round(rest_dz_var.get(), 3)))
        self.config.set(section, 'curve', curve_var.get())
        self.config.set(section, 'exp_factor', str(round(exp_var.get(), 3)))
        if sens_var is not None:
            self.config.set(section, 'sensitivity', str(round(sens_var.get(), 3)))
        self.save_config()
        
        if section == "analog_left":
            self.draw_curve(self.c_ls_curve, dz_var.get(), adz_var.get(), rest_dz_var.get(), curve_var.get(), exp_var.get())
        elif section == "analog_right":
            self.draw_curve(self.c_rs_curve, dz_var.get(), adz_var.get(), rest_dz_var.get(), curve_var.get(), exp_var.get())
        elif section == "trigger_left":
            self.draw_curve_trigger(self.c_lt_curve, dz_var.get(), adz_var.get(), rest_dz_var.get(), curve_var.get(), exp_var.get())
        elif section == "trigger_right":
            self.draw_curve_trigger(self.c_rt_curve, dz_var.get(), adz_var.get(), rest_dz_var.get(), curve_var.get(), exp_var.get())

    def draw_curve(self, canvas, dz, adz, rest_dz, curve_type, exp_factor):
        canvas.delete("all")
        width = 180
        height = 180
        
        canvas.create_line(0, height, width, 0, fill="#444444", dash=(4, 4))
        canvas.create_line(width/2, 0, width/2, height, fill="#444444", dash=(2, 2))
        canvas.create_line(0, height/2, width, height/2, fill="#444444", dash=(2, 2))
        
        import math_utils
        points = []
        for x_px in range(width + 1):
            input_val = x_px / width
            # Pass 0 for Y so magnitude = input_val
            out_x, _ = math_utils.process_analog_stick(input_val, 0.0, dz, adz, curve_type, exp_factor, rest_dz, 1.0)
            y_px = height - (out_x * height)
            points.append(x_px)
            points.append(y_px)
            
        if points:
            canvas.create_line(points, fill="#AF00FA", width=2)

    def draw_curve_trigger(self, canvas, dz, adz, rest_dz, curve_type, exp_factor):
        canvas.delete("all")
        width = 180
        height = 180
        
        canvas.create_line(0, height, width, 0, fill="#444444", dash=(4, 4))
        
        import math_utils
        points = []
        for x_px in range(width + 1):
            input_val = x_px / width
            out_val = math_utils.process_trigger(input_val, dz, adz, curve_type, exp_factor, rest_dz)
            y_px = height - (out_val * height)
            points.append(x_px)
            points.append(y_px)
            
        if points:
            canvas.create_line(points, fill="#AF00FA", width=2)

    def draw_crosshair(self, canvas, raw_x, raw_y, out_x, out_y):
        canvas.delete("all")
        width = 180
        height = 180
        cx = width / 2
        cy = height / 2
        
        canvas.create_line(cx, 0, cx, height, fill="#444444", dash=(2, 2))
        canvas.create_line(0, cy, width, cy, fill="#444444", dash=(2, 2))
        
        # Raw position (cyan dot)
        rx_px = cx + (raw_x * cx)
        ry_px = cy - (raw_y * cy)
        canvas.create_oval(rx_px-4, ry_px-4, rx_px+4, ry_px+4, fill="#00D4FF", outline="")
        
        # Processed position (purple crosshair)
        px_px = cx + (out_x * cx)
        py_px = cy - (out_y * cy)
        canvas.create_oval(px_px-5, py_px-5, px_px+5, py_px+5, fill="", outline="#AF00FA", width=2)
        canvas.create_line(cx, cy, px_px, py_px, fill="#AF00FA", dash=(2,2))

    def draw_trigger_bar(self, canvas, raw_val, out_val):
        canvas.delete("all")
        width = 60
        height = 180
        
        # Side-by-side bars to prevent overlap
        # Left bar: Raw input (cyan)
        canvas.create_rectangle(5, 0, 27, height, fill="#222222", outline="#444444")
        raw_h = int(raw_val * height)
        if raw_h > 0:
            canvas.create_rectangle(5, height - raw_h, 27, height, fill="#00D4FF", outline="")
        
        # Right bar: Processed output (purple)
        canvas.create_rectangle(33, 0, 55, height, fill="#222222", outline="#444444")
        out_h = int(out_val * height)
        if out_h > 0:
            canvas.create_rectangle(33, height - out_h, 55, height, fill="#AF00FA", outline="")

    def update_curve_cursor(self, canvas, raw_magnitude, out_magnitude):
        """Overlays a cyan dot on the response curve canvas at the current input/output."""
        canvas.delete("cursor")
        width = 180
        height = 180
        x_px = raw_magnitude * width
        y_px = height - (out_magnitude * height)
        canvas.create_oval(x_px-4, y_px-4, x_px+4, y_px+4, fill="#00D4FF", outline="white", width=1, tags="cursor")

    def update_trigger_curve_cursor(self, canvas, raw_val, out_val):
        """Overlays a white vertical line + dot on the trigger response curve at current input."""
        canvas.delete("cursor")
        width = 180
        height = 180
        x_px = raw_val * width
        y_px = height - (out_val * height)
        # Vertical guide line from bottom to the curve point
        canvas.create_line(x_px, height, x_px, y_px, fill="#FFFFFF", dash=(2, 2), tags="cursor")
        # Dot at the curve point
        canvas.create_oval(x_px-4, y_px-4, x_px+4, y_px+4, fill="#FFFFFF", outline="#00D4FF", width=1, tags="cursor")

    def update_position_loop(self):
        # 60fps refresh
        if hasattr(self, 'current_state') and self.current_state:
            state = self.current_state
            import math_utils
            import math
            
            # Left Stick
            raw_lx, raw_ly = state.lx, state.ly
            disp_raw_ly = -raw_ly
            
            ls_circ_mode = self.config.get('analog_left', 'circularity_mode', fallback='disabled').lower()
            ls_circ_cx = self.config.getfloat('analog_left', 'circularity_center_x', fallback=0.0)
            ls_circ_cy = self.config.getfloat('analog_left', 'circularity_center_y', fallback=0.0)
            ls_bounds_str = self.config.get('analog_left', 'circularity_bounds', fallback='')
            ls_circ_bounds = [float(x) for x in ls_bounds_str.split(',')] if ls_bounds_str else None
            
            out_lx, out_ly = raw_lx, disp_raw_ly
            
            if ls_circ_mode == 'before':
                out_lx, out_ly = math_utils.apply_circularity_correction(out_lx, out_ly, ls_circ_cx, ls_circ_cy, ls_circ_bounds)
                out_lx, out_ly = math_utils.process_analog_stick(out_lx, out_ly, self.ls_dz.get(), self.ls_adz.get(), self.ls_curve.get(), self.ls_exp.get(), self.ls_rest_dz.get(), self.ls_sens.get())
            elif ls_circ_mode == 'after':
                out_lx, out_ly = math_utils.process_analog_stick(out_lx, out_ly, self.ls_dz.get(), self.ls_adz.get(), self.ls_curve.get(), self.ls_exp.get(), self.ls_rest_dz.get(), self.ls_sens.get())
                out_lx, out_ly = math_utils.apply_circularity_correction(out_lx, out_ly, ls_circ_cx, ls_circ_cy, ls_circ_bounds)
            else:
                out_lx, out_ly = math_utils.process_analog_stick(out_lx, out_ly, self.ls_dz.get(), self.ls_adz.get(), self.ls_curve.get(), self.ls_exp.get(), self.ls_rest_dz.get(), self.ls_sens.get())
                
            self.draw_crosshair(self.c_ls_pos, raw_lx, disp_raw_ly, out_lx, out_ly)
            raw_mag = math.sqrt(raw_lx**2 + disp_raw_ly**2)
            out_mag = math.sqrt(out_lx**2 + out_ly**2)
            self.update_curve_cursor(self.c_ls_curve, min(raw_mag, 1.0), min(out_mag, 1.0))
            
            # Right Stick
            disp_raw_ry = -state.ry
            
            rs_circ_mode = self.config.get('analog_right', 'circularity_mode', fallback='disabled').lower()
            rs_circ_cx = self.config.getfloat('analog_right', 'circularity_center_x', fallback=0.0)
            rs_circ_cy = self.config.getfloat('analog_right', 'circularity_center_y', fallback=0.0)
            rs_bounds_str = self.config.get('analog_right', 'circularity_bounds', fallback='')
            rs_circ_bounds = [float(x) for x in rs_bounds_str.split(',')] if rs_bounds_str else None
            
            out_rx, out_ry = state.rx, disp_raw_ry
            
            if rs_circ_mode == 'before':
                out_rx, out_ry = math_utils.apply_circularity_correction(out_rx, out_ry, rs_circ_cx, rs_circ_cy, rs_circ_bounds)
                out_rx, out_ry = math_utils.process_analog_stick(out_rx, out_ry, self.rs_dz.get(), self.rs_adz.get(), self.rs_curve.get(), self.rs_exp.get(), self.rs_rest_dz.get(), self.rs_sens.get())
            elif rs_circ_mode == 'after':
                out_rx, out_ry = math_utils.process_analog_stick(out_rx, out_ry, self.rs_dz.get(), self.rs_adz.get(), self.rs_curve.get(), self.rs_exp.get(), self.rs_rest_dz.get(), self.rs_sens.get())
                out_rx, out_ry = math_utils.apply_circularity_correction(out_rx, out_ry, rs_circ_cx, rs_circ_cy, rs_circ_bounds)
            else:
                out_rx, out_ry = math_utils.process_analog_stick(out_rx, out_ry, self.rs_dz.get(), self.rs_adz.get(), self.rs_curve.get(), self.rs_exp.get(), self.rs_rest_dz.get(), self.rs_sens.get())
                
            self.draw_crosshair(self.c_rs_pos, state.rx, disp_raw_ry, out_rx, out_ry)
            raw_mag_r = math.sqrt(state.rx**2 + disp_raw_ry**2)
            out_mag_r = math.sqrt(out_rx**2 + out_ry**2)
            self.update_curve_cursor(self.c_rs_curve, min(raw_mag_r, 1.0), min(out_mag_r, 1.0))
            
            # Left Trigger
            out_lt = math_utils.process_trigger(state.lt, self.lt_dz.get(), self.lt_adz.get(), self.lt_curve.get(), self.lt_exp.get(), self.lt_rest_dz.get())
            self.draw_trigger_bar(self.c_lt_pos, state.lt, out_lt)
            self.update_trigger_curve_cursor(self.c_lt_curve, state.lt, out_lt)

            # Right Trigger
            out_rt = math_utils.process_trigger(state.rt, self.rt_dz.get(), self.rt_adz.get(), self.rt_curve.get(), self.rt_exp.get(), self.rt_rest_dz.get())
            self.draw_trigger_bar(self.c_rt_pos, state.rt, out_rt)
            self.update_trigger_curve_cursor(self.c_rt_curve, state.rt, out_rt)
            
        self.after(16, self.update_position_loop)
            
    def setup_advanced(self):
        if not self.config.has_section('shift_layer'):
            self.config.add_section('shift_layer')
        if not self.config.has_section('chords'):
            self.config.add_section('chords')
            
        # Shift Layer Settings
        shift_frame = ctk.CTkFrame(self.tab_advanced)
        shift_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(shift_frame, text="Shift Layer Settings", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Trigger Button
        trig_frame = ctk.CTkFrame(shift_frame, fg_color="transparent")
        trig_frame.pack(fill="x", padx=10, pady=5)
        
        info_btn_trig = ctk.CTkButton(trig_frame, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
        info_btn_trig.pack(side="left", padx=(0,5))
        ToolTip(info_btn_trig, "Select the button that activates the secondary Shift Layer.\nWhen held or toggled, all other buttons will map to their Shift Layer configurations.")
        
        ctk.CTkLabel(trig_frame, text="Trigger Button:", width=120, anchor="w").pack(side="left")
        
        self.shift_trig_var = ctk.StringVar(value=self.config.get('shift_layer', 'trigger_button', fallback=''))
        base_buttons = self.get_profile_mapped_keys()
        
        def on_shift_trig_changed(val):
            val = val.strip()
            if val and self.config.has_option('extra_buttons', val):
                import tkinter.messagebox
                tkinter.messagebox.showwarning(
                    "Shift Trigger Conflict",
                    f"The button '{val}' is currently mapped to an action.\n\n"
                    "It will be cleared and blocked from XInput so it can act as the Shift Trigger."
                )
                self.config.remove_option('extra_buttons', val)
                if not self.config.has_section('block_xinput'):
                    self.config.add_section('block_xinput')
                if self.config.has_option('block_xinput', val):
                    self.config.remove_option('block_xinput', val)
                
                # Update UI elements in remapping tab if they exist
                if hasattr(self, 'entries') and val in self.entries:
                    self.entries[val].delete(0, 'end')
                    self.block_vars[val].set(True)
                    self.block_checkboxes[val].configure(state="disabled")
            self.save_advanced()
            
        self.trig_menu = ctk.CTkOptionMenu(trig_frame, values=base_buttons, variable=self.shift_trig_var, command=on_shift_trig_changed)
        self.trig_menu.pack(side="left", fill="x", expand=True)
        
        # Mode
        mode_frame = ctk.CTkFrame(shift_frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        info_btn_mode = ctk.CTkButton(mode_frame, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
        info_btn_mode.pack(side="left", padx=(0,5))
        ToolTip(info_btn_mode, "Hold: Shift layer is active only while the trigger button is held down.\nToggle: Pressing the trigger button toggles the Shift layer permanently on or off.")
        
        ctk.CTkLabel(mode_frame, text="Mode:", width=120, anchor="w").pack(side="left")
        
        self.shift_mode_var = ctk.StringVar(value=self.config.get('shift_layer', 'mode', fallback='hold'))
        mode_menu = ctk.CTkOptionMenu(mode_frame, values=["hold", "toggle"], variable=self.shift_mode_var, command=lambda _: self.save_advanced())
        mode_menu.pack(side="left")

        # Chords Setting
        self.chords_frame = ctk.CTkFrame(self.tab_advanced)
        self.chords_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        header_f = ctk.CTkFrame(self.chords_frame, fg_color="transparent")
        header_f.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(header_f, text="Chords & Macros", font=ctk.CTkFont(weight="bold")).pack(side="left")
        info_btn_chords = ctk.CTkButton(header_f, text="?", width=20, height=20, corner_radius=10, fg_color="#555555")
        info_btn_chords.pack(side="left", padx=(5,0))
        ToolTip(info_btn_chords, "Map multiple simultaneous button presses (a chord) to a macro sequence.\nExample Outputs: 'keyboard:h, wait:50, mouse:left'")
        
        self.chord_rows = []
        self.chord_list_frame = ctk.CTkScrollableFrame(self.chords_frame, height=250, corner_radius=0)
        self.chord_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Load chords & macros
        import os, json
        macros_data = {}
        if os.path.exists('macros.json'):
            try:
                with open('macros.json', 'r') as f:
                    macros_data = json.load(f)
            except Exception:
                pass
                
        for k, v in self.config.items('chords'):
            if v.startswith('macro:'):
                m_name = v.split('macro:')[1]
                m_steps = macros_data.get(m_name, [])
                # Reconstruct string from steps
                out_str_parts = []
                for step in m_steps:
                    action = step.get('action')
                    if action == 'wait':
                        out_str_parts.append(f"wait:{step.get('ms')}")
                    elif action == 'press':
                        out_str_parts.append(f"press:{step.get('key')}")
                    elif action == 'release':
                        out_str_parts.append(f"release:{step.get('key')}")
                
                # Simplify full clicks back to basic binds? Or just keep raw for now
                out_str = ", ".join(out_str_parts)
                self.add_chord_row(m_name, k, out_str)
            
        btn_add = ctk.CTkButton(self.chords_frame, text="+ Add Macro", command=lambda: self.add_chord_row("", "", ""))
        btn_add.pack(pady=5)
        
        save_btn = ctk.CTkButton(self.chords_frame, text="Save Settings", command=self.save_advanced)
        save_btn.pack(pady=5)

    def start_macro_recording(self, entry_widget, mode):
        # mode: 'inputs' (Gamepad only) or 'outputs' (KBM + Gamepad)
        record_win = ctk.CTkToplevel(self)
        record_win.title("Record Macro")
        record_win.geometry("400x200")
        record_win.attributes("-topmost", True)
        record_win.focus()
        
        lbl = ctk.CTkLabel(record_win, text=f"Recording {mode}...\nPress buttons to append.\nClick Save when done.")
        lbl.pack(pady=10)
        
        result_var = ctk.StringVar(value=entry_widget.get())
        result_lbl = ctk.CTkLabel(record_win, textvariable=result_var, font=ctk.CTkFont(size=12), wraplength=380)
        result_lbl.pack(pady=10)
        
        # Simple implementation: append to string
        import pynput
        
        def append_result(text):
            current = result_var.get().strip()
            if current:
                result_var.set(f"{current}, {text}")
            else:
                result_var.set(text)
                
        def on_press(key):
            try:
                k_name = key.char
            except AttributeError:
                k_name = key.name
            append_result(f"keyboard:{k_name}")
            
        def on_click(x, y, button, pressed):
            if pressed:
                if button.name == 'left': return
                append_result(f"mouse:{button.name}")
                
        k_listener = None
        m_listener = None
        if mode == 'outputs':
            k_listener = pynput.keyboard.Listener(on_press=on_press)
            m_listener = pynput.mouse.Listener(on_click=on_click)
            k_listener.start()
            m_listener.start()
            
        # Add a wait button
        wait_btn = ctk.CTkButton(record_win, text="Add Wait: 50ms", width=120, command=lambda: append_result("wait:50"))
        wait_btn.pack(pady=5)
            
        def save_and_close():
            if k_listener: k_listener.stop()
            if m_listener: m_listener.stop()
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, result_var.get())
            record_win.destroy()
            
        ctk.CTkButton(record_win, text="Save", command=save_and_close).pack(pady=10)

    def add_chord_row(self, name_val, inputs_val, outputs_val):
        row_f = ctk.CTkFrame(self.chord_list_frame)
        row_f.pack(fill="x", pady=2)
        
        row1 = ctk.CTkFrame(row_f, fg_color="transparent")
        row1.pack(fill="x", padx=2, pady=2)
        
        ctk.CTkLabel(row1, text="Name:").pack(side="left", padx=2)
        ent_name = ctk.CTkEntry(row1, width=80)
        ent_name.insert(0, name_val)
        ent_name.pack(side="left", padx=2)
        
        ctk.CTkLabel(row1, text="Inputs:").pack(side="left", padx=2)
        ent_in = ctk.CTkEntry(row1, width=100)
        ent_in.insert(0, inputs_val)
        ent_in.pack(side="left", padx=2)
        
        btn_rec_in = ctk.CTkButton(row1, text="⏺ GP", width=40, command=lambda: self.start_macro_recording(ent_in, 'inputs'))
        btn_rec_in.pack(side="left", padx=2)
        
        def delete_row():
            row_f.destroy()
            self.chord_rows.remove(row_data)
        btn_del = ctk.CTkButton(row1, text="X", width=25, fg_color="#990000", hover_color="#660000", command=delete_row)
        btn_del.pack(side="right", padx=2)
        
        row2 = ctk.CTkFrame(row_f, fg_color="transparent")
        row2.pack(fill="x", padx=2, pady=2)
        
        ctk.CTkLabel(row2, text="Outputs:").pack(side="left", padx=2)
        ent_out = ctk.CTkEntry(row2)
        ent_out.insert(0, outputs_val)
        ent_out.pack(side="left", fill="x", expand=True, padx=2)
        
        btn_rec_out = ctk.CTkButton(row2, text="⏺ KBM", width=40, command=lambda: self.start_macro_recording(ent_out, 'outputs'))
        btn_rec_out.pack(side="right", padx=2)
        
        row_data = {"name": ent_name, "in": ent_in, "out": ent_out, "frame": row_f}
        self.chord_rows.append(row_data)

    def save_advanced(self):
        # Save Shift Layer
        trig = self.shift_trig_var.get().strip()
        if trig:
            self.config.set('shift_layer', 'trigger_button', trig)
        else:
            if self.config.has_option('shift_layer', 'trigger_button'):
                self.config.remove_option('shift_layer', 'trigger_button')
                
        self.config.set('shift_layer', 'mode', self.shift_mode_var.get())
        
        # Save Chords & Macros
        self.config.remove_section('chords')
        self.config.add_section('chords')
        
        macros_dict = {}
        for row in self.chord_rows:
            name = row["name"].get().strip()
            inputs = row["in"].get().strip()
            outputs = row["out"].get().strip()
            if name and inputs and outputs:
                self.config.set('chords', inputs, f"macro:{name}")
                
                steps = []
                # parse outputs like: "press:keyboard:h, wait:50, release:keyboard:h, keyboard:j"
                for part in outputs.split(','):
                    part = part.strip()
                    if not part: continue
                    if part.startswith('wait:'):
                        try:
                            steps.append({"action": "wait", "ms": int(part.split(':')[1])})
                        except: pass
                    elif part.startswith('press:'):
                        steps.append({"action": "press", "key": part.split('press:')[1]})
                    elif part.startswith('release:'):
                        steps.append({"action": "release", "key": part.split('release:')[1]})
                    else:
                        # Full press and release with 50ms wait implicitly
                        steps.append({"action": "press", "key": part})
                        steps.append({"action": "wait", "ms": 50})
                        steps.append({"action": "release", "key": part})
                
                macros_dict[name] = steps
                
        import json
        with open('macros.json', 'w') as f:
            json.dump(macros_dict, f, indent=2)
            
        self.save_config()
        
        if logger:
            logger.info("Advanced configuration saved.")

    def setup_customization(self):
        lbl = ctk.CTkLabel(self.tab_customization, text="UI Customization", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=(20, 10))

        frame = ctk.CTkFrame(self.tab_customization)
        frame.pack(padx=20, pady=10, fill="x")

        # Appearance Mode
        lbl_mode = ctk.CTkLabel(frame, text="Appearance Mode (Light/Dark):")
        lbl_mode.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        current_mode = "Dark"
        if self.daemon_config.has_option('UI', 'appearance'):
            current_mode = self.daemon_config.get('UI', 'appearance')
            
        self.mode_var = ctk.StringVar(value=current_mode)
        opt_mode = ctk.CTkOptionMenu(frame, variable=self.mode_var, values=["Dark", "Light", "System"], command=self.change_appearance_mode)
        opt_mode.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        # Theme Color
        lbl_theme = ctk.CTkLabel(frame, text="Accent Theme (Requires Restart):")
        lbl_theme.grid(row=1, column=0, padx=15, pady=10, sticky="w")
        
        current_theme = "purple"
        if self.daemon_config.has_option('UI', 'theme'):
            current_theme = self.daemon_config.get('UI', 'theme')
            
        self.theme_var = ctk.StringVar(value=current_theme)
        opt_theme = ctk.CTkOptionMenu(frame, variable=self.theme_var, values=["purple", "red", "blue", "green", "yellow", "orange", "white"], command=self.change_theme)
        opt_theme.grid(row=1, column=1, padx=15, pady=10, sticky="ew")

        # Font Selection
        lbl_font = ctk.CTkLabel(frame, text="Application Font (Requires Restart):")
        lbl_font.grid(row=2, column=0, padx=15, pady=10, sticky="w")
        
        current_font = "Arial"
        if self.daemon_config.has_option('UI', 'font'):
            current_font = self.daemon_config.get('UI', 'font')
            
        self.font_var = ctk.StringVar(value=current_font)
        opt_font = ctk.CTkOptionMenu(frame, variable=self.font_var, values=["Arial", "Consolas", "Courier New", "Segoe UI", "Tahoma"], command=self.change_font)
        opt_font.grid(row=2, column=1, padx=15, pady=10, sticky="ew")
        
        frame.columnconfigure(1, weight=1)

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        if not self.daemon_config.has_section('UI'):
            self.daemon_config.add_section('UI')
        self.daemon_config.set('UI', 'appearance', new_mode)
        with open(self.daemon_config_file, 'w') as f:
            self.daemon_config.write(f)

    def change_theme(self, new_theme):
        if not self.daemon_config.has_section('UI'):
            self.daemon_config.add_section('UI')
        self.daemon_config.set('UI', 'theme', new_theme)
        with open(self.daemon_config_file, 'w') as f:
            self.daemon_config.write(f)

    def change_font(self, new_font):
        if not self.daemon_config.has_section('UI'):
            self.daemon_config.add_section('UI')
        self.daemon_config.set('UI', 'font', new_font)
        with open(self.daemon_config_file, 'w') as f:
            self.daemon_config.write(f)

    def setup_profile(self):
        lbl = ctk.CTkLabel(self.tab_profile, text="Profile Validation & Diff", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=(20, 10))
        
        main_frame = ctk.CTkFrame(self.tab_profile, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        import os
        import glob
        profiles = [os.path.basename(p) for p in glob.glob("profiles/*.json")]
        if not profiles:
            profiles = ["No profiles found"]
            
        p1_var = ctk.StringVar(value=profiles[0])
        p2_var = ctk.StringVar(value=profiles[0])
        
        # Profile 1 Selection
        p1_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        p1_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(p1_frame, text="Profile 1 (Base):", width=120, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(p1_frame, values=profiles, variable=p1_var).pack(side="left", fill="x", expand=True)
        
        # Profile 2 Selection
        p2_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        p2_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(p2_frame, text="Profile 2 (Compare):", width=120, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(p2_frame, values=profiles, variable=p2_var).pack(side="left", fill="x", expand=True)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        output_txt = ctk.CTkTextbox(main_frame, height=300)
        output_txt.pack(fill="both", expand=True, pady=10)
        
        def run_validate():
            import profile_tools
            p_path = os.path.join("profiles", p1_var.get())
            res = profile_tools.validate_profile(p_path)
            output_txt.delete("0.0", "end")
            output_txt.insert("0.0", res)
            
        def run_diff():
            import profile_tools
            p1_path = os.path.join("profiles", p1_var.get())
            p2_path = os.path.join("profiles", p2_var.get())
            res = profile_tools.diff_profiles(p1_path, p2_path)
            output_txt.delete("0.0", "end")
            output_txt.insert("0.0", res)
            
        def export_output():
            from tkinter import filedialog, messagebox
            fpath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
            if fpath:
                with open(fpath, 'w') as f:
                    f.write(output_txt.get("0.0", "end"))
                messagebox.showinfo("Exported", f"Output exported to {fpath}")
        
        ctk.CTkButton(btn_frame, text="Validate Profile 1", command=run_validate).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Diff Profiles (1 vs 2)", command=run_diff).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Export Output", command=export_output).pack(side="left", padx=5, expand=True)

    def setup_utilities(self):
        lbl = ctk.CTkLabel(self.tab_utilities, text="Utilities & Diagnostics", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=(20, 10))
        
        main_frame = ctk.CTkFrame(self.tab_utilities, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Latency Monitor Frame
        lat_frame = ctk.CTkFrame(main_frame)
        lat_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(lat_frame, text="Live Latency Monitor", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        self.lbl_poll = ctk.CTkLabel(lat_frame, text="Polling Rate: -- Hz")
        self.lbl_poll.pack()
        self.lbl_avg = ctk.CTkLabel(lat_frame, text="Avg Processing Latency: -- ms")
        self.lbl_avg.pack()
        self.lbl_max = ctk.CTkLabel(lat_frame, text="Max Processing Latency: -- ms")
        self.lbl_max.pack(pady=(0, 10))
        
        # Benchmark Frame
        bench_frame = ctk.CTkFrame(main_frame)
        bench_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(bench_frame, text="Synthetic Benchmark", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        ctk.CTkLabel(bench_frame, text="Runs 10,000 simulated packets through the decoding and math engines.").pack()
        
        self.bench_result = ctk.CTkLabel(bench_frame, text="")
        self.bench_result.pack(pady=5)
        
        def run_benchmark():
            self.bench_result.configure(text="Running benchmark...")
            self.update_idletasks()
            
            import time
            import math_utils
            from decoder import Decoder
            from hid_reader import RawHIDReport
            
            d = Decoder("")
            d.reports_config = {"0": {"inputs": {"lx": {"type": "axis", "byte": 1}}}}
            
            start = time.perf_counter()
            for _ in range(10000):
                rep = RawHIDReport(0, bytes([0, 128]))
                state = d.decode(rep)
                lx, ly = math_utils.process_analog_stick(state.lx, state.ly, 0.1, 0.1, "bezier", 2.0, 0.0)
            end = time.perf_counter()
            
            total_ms = (end - start) * 1000.0
            per_packet_us = (total_ms / 10000.0) * 1000.0
            self.bench_result.configure(text=f"Score: 10,000 packets in {total_ms:.1f}ms\nAverage per packet: {per_packet_us:.2f}us")
            
        ctk.CTkButton(bench_frame, text="Run Benchmark", command=run_benchmark).pack(pady=(5, 10))
        
        def open_graph():
            import subprocess
            import sys
            import os
            script_path = os.path.join(os.path.dirname(__file__), "input_graph.py")
            subprocess.Popen([sys.executable, script_path])
            
        ctk.CTkButton(bench_frame, text="Open Live Input Inspector", command=open_graph, fg_color="#2c7a2c", hover_color="#1f591f").pack(pady=(5, 10))
        
        self.update_utilities_loop()
        
    def update_utilities_loop(self):
        try:
            import os, json
            if os.path.exists('diagnostics.json'):
                with open('diagnostics.json', 'r') as f:
                    stats = json.load(f)
                self.lbl_poll.configure(text=f"Polling Rate: {stats.get('polling_rate_hz', 0)} Hz")
                self.lbl_avg.configure(text=f"Avg Processing Latency: {stats.get('avg_process_ms', 0)} ms")
                self.lbl_max.configure(text=f"Max Processing Latency: {stats.get('max_process_ms', 0)} ms")
        except Exception:
            pass
            
        self.after(500, self.update_utilities_loop)


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
