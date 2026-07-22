import json
import os
import re

def get_sanitized_filename(name, mode=None):
    # keep alphanumeric and underscores/dashes, replace spaces with underscores, lowercase
    cleaned = re.sub(r'[^a-zA-Z0-9_\- ]', '', name)
    cleaned = cleaned.replace(' ', '_').lower()
    if mode:
        return f"{cleaned}_{mode}.json"
    return f"{cleaned}.json"

class ControllerConfig:
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.data = {}
        if filepath and os.path.exists(filepath):
            self.load()
        else:
            self._init_defaults()

    def _init_defaults(self):
        self.data = {
            "settings": {
                "layout": "xbox",
                "digital_lt": "false",
                "digital_rt": "false"
            },
            "extra_buttons": {},
            "block_xinput": {},
            "shift_layer": {
                "mode": "hold",
                "trigger_button": ""
            },
            "shift_mappings": {},
            "shift_block_xinput": {},
            "chords": {},
            "hardware_chords": {},
            "backend": {
                "mode": "auto"
            },
            "analog": {
                "deadzone": "0.08",
                "anti_deadzone": "0.0",
                "curve": "linear",
                "exp_factor": "2.0"
            },
            "analog_left": {
                "deadzone": "0.05",
                "anti_deadzone": "0.0",
                "curve": "linear",
                "exp_factor": "2.0"
            },
            "analog_right": {
                "deadzone": "0.05",
                "anti_deadzone": "0.0",
                "curve": "linear",
                "exp_factor": "2.0"
            },
            "trigger_left": {
                "deadzone": "0.05",
                "anti_deadzone": "0.0",
                "curve": "linear",
                "exp_factor": "2.0"
            },
            "trigger_right": {
                "deadzone": "0.05",
                "anti_deadzone": "0.0",
                "curve": "linear",
                "exp_factor": "2.0"
            }
        }

    def load(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")
            self._init_defaults()

    def save(self):
        if not self.filepath:
            return
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving {self.filepath}: {e}")

    def has_section(self, section):
        return section in self.data

    def add_section(self, section):
        if section not in self.data:
            self.data[section] = {}

    def remove_section(self, section):
        if section in self.data:
            del self.data[section]

    def has_option(self, section, option):
        return section in self.data and option in self.data[section]

    def remove_option(self, section, option):
        if section in self.data and option in self.data[section]:
            del self.data[section][option]

    def get(self, section, option, fallback=None):
        if section in self.data and option in self.data[section]:
            return str(self.data[section][option])
        return fallback

    def getboolean(self, section, option, fallback=None):
        val = self.get(section, option)
        if val is None:
            return fallback
        return val.lower() in ('true', 'yes', 'on', '1')

    def getfloat(self, section, option, fallback=None):
        val = self.get(section, option)
        if val is None:
            return fallback
        try:
            return float(val)
        except ValueError:
            return fallback

    def set(self, section, option, value):
        if section not in self.data:
            self.data[section] = {}
        self.data[section][option] = str(value)

    def items(self, section):
        if section in self.data:
            return list(self.data[section].items())
        return []

    def options(self, section):
        if section in self.data:
            return list(self.data[section].keys())
        return []

