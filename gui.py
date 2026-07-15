import customtkinter as ctk
import configparser
import json
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Controller Wrapper Configuration")
        self.geometry("600x500")

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

    def save_config(self):
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def setup_dashboard(self):
        self.status_label = ctk.CTkLabel(self.tab_dashboard, text="Status: Unknown", font=ctk.CTkFont(size=20, weight="bold"))
        self.status_label.pack(pady=40)

        self.device_label = ctk.CTkLabel(self.tab_dashboard, text="Device: -", font=ctk.CTkFont(size=16))
        self.device_label.pack(pady=10)
        
        info = ctk.CTkLabel(self.tab_dashboard, text="The background wrapper reloads configuration automatically.", text_color="gray")
        info.pack(pady=40)

    def setup_remapping(self):
        self.scroll = ctk.CTkScrollableFrame(self.tab_remapping)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        header_btn = ctk.CTkLabel(self.scroll, text="Controller Button", font=ctk.CTkFont(weight="bold"))
        header_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        header_map = ctk.CTkLabel(self.scroll, text="Mapped To (e.g., keyboard:space, mouse4)", font=ctk.CTkFont(weight="bold"))
        header_map.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        standard_buttons = [
            'a', 'b', 'x', 'y', 'lb', 'rb', 'lt', 'rt', 
            'select', 'start', 'home', 'l3', 'r3',
            'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right'
        ]

        # Gather any extra buttons already in config
        existing_extras = []
        if self.config.has_section('extra_buttons'):
            for k in self.config.options('extra_buttons'):
                if k not in standard_buttons:
                    existing_extras.append(k)

        all_buttons = standard_buttons + existing_extras
        self.entries = {}

        for i, btn in enumerate(all_buttons):
            row = i + 1
            lbl = ctk.CTkLabel(self.scroll, text=btn.upper())
            lbl.grid(row=row, column=0, padx=10, pady=5, sticky="w")

            current_val = ""
            if self.config.has_option('extra_buttons', btn):
                current_val = self.config.get('extra_buttons', btn)

            entry = ctk.CTkEntry(self.scroll, width=200)
            entry.insert(0, current_val)
            entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            
            # Bind the focus out event to auto-save
            entry.bind("<FocusOut>", lambda e, b=btn: self.on_mapping_changed(b))
            entry.bind("<Return>", lambda e, b=btn: self.on_mapping_changed(b))
            
            self.entries[btn] = entry

    def on_mapping_changed(self, btn):
        val = self.entries[btn].get().strip()
        if val == "":
            if self.config.has_option('extra_buttons', btn):
                self.config.remove_option('extra_buttons', btn)
        else:
            self.config.set('extra_buttons', btn, val)
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
    app = App()
    app.mainloop()
