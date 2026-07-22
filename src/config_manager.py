import json
import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger('config_manager')


def get_sanitized_filename(name: str, mode: Optional[str] = None) -> str:
    """
    Sanitizes a string to be a safe JSON filename.
    Replaces non-alphanumeric chars, converts spaces to underscores, and lowercases.
    """
    cleaned = re.sub(r'[^a-zA-Z0-9_\- ]', '', name)
    cleaned = cleaned.replace(' ', '_').lower()
    if mode:
        return f"{cleaned}_{mode}.json"
    return f"{cleaned}.json"


class ControllerConfig:
    """
    Manages JSON configuration profiles for controller mappings,
    deadzones, response curves, and macro settings.
    """

    def __init__(self, filepath: Optional[str] = None):
        self.filepath: Optional[str] = filepath
        self.data: Dict[str, Any] = {}
        if filepath and os.path.exists(filepath):
            self.load()
        else:
            self._init_defaults()

    def _init_defaults(self) -> None:
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

    def load(self) -> None:
        if not self.filepath:
            self._init_defaults()
            return
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")
            logger.error(f"Error loading {self.filepath}: {e}", exc_info=True)
            self._init_defaults()

    def save(self) -> None:
        if not self.filepath:
            return
        try:
            dirname = os.path.dirname(self.filepath)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving {self.filepath}: {e}")
            logger.error(f"Error saving {self.filepath}: {e}", exc_info=True)

    def has_section(self, section: str) -> bool:
        return section in self.data

    def add_section(self, section: str) -> None:
        if section not in self.data:
            self.data[section] = {}

    def remove_section(self, section: str) -> None:
        if section in self.data:
            del self.data[section]

    def has_option(self, section: str, option: str) -> bool:
        return section in self.data and isinstance(self.data[section], dict) and option in self.data[section]

    def remove_option(self, section: str, option: str) -> None:
        if section in self.data and isinstance(self.data[section], dict) and option in self.data[section]:
            del self.data[section][option]

    def get(self, section: str, option: str, fallback: Optional[str] = None) -> Optional[str]:
        if section in self.data and isinstance(self.data[section], dict) and option in self.data[section]:
            return str(self.data[section][option])
        return fallback

    def getboolean(self, section: str, option: str, fallback: Optional[bool] = None) -> Optional[bool]:
        val = self.get(section, option)
        if val is None:
            return fallback
        return val.lower() in ('true', 'yes', 'on', '1')

    def getfloat(self, section: str, option: str, fallback: Optional[float] = None) -> Optional[float]:
        val = self.get(section, option)
        if val is None:
            return fallback
        try:
            return float(val)
        except ValueError:
            return fallback

    def set(self, section: str, option: str, value: Any) -> None:
        if section not in self.data or not isinstance(self.data[section], dict):
            self.data[section] = {}
        self.data[section][option] = str(value)

    def items(self, section: str) -> List[Tuple[str, Any]]:
        if section in self.data and isinstance(self.data[section], dict):
            return list(self.data[section].items())
        return []

    def options(self, section: str) -> List[str]:
        if section in self.data and isinstance(self.data[section], dict):
            return list(self.data[section].keys())
        return []


