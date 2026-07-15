import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ControllerState:
    a: bool = False
    b: bool = False
    x: bool = False
    y: bool = False
    lb: bool = False
    rb: bool = False
    
    select: bool = False
    start: bool = False
    home: bool = False
    l3: bool = False
    r3: bool = False
    
    # D-pad directions
    dpad_up: bool = False
    dpad_down: bool = False
    dpad_left: bool = False
    dpad_right: bool = False
    
    # Sticks (0-255)
    lx: int = 128
    ly: int = 128
    rx: int = 128
    ry: int = 128
    
    # Triggers (0-255)
    lt: int = 0
    rt: int = 0
    
    # Dynamic extra buttons
    extra_buttons: Dict[str, bool] = field(default_factory=dict)

class Decoder:
    def __init__(self, profile_path: str):
        self.profile = {}
        self.extra_buttons_config = {}
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as f:
                    self.profile = json.load(f)
                    self.extra_buttons_config = self.profile.get('extra_buttons', {})
            except json.JSONDecodeError as e:
                print(f"Error: Profile {profile_path} is not valid JSON: {e}")
            except Exception as e:
                print(f"Error loading profile {profile_path}: {e}")
        else:
            print(f"Warning: Profile {profile_path} not found. Inputs will be ignored.")

    def decode(self, data) -> ControllerState:
        state = ControllerState()
        
        # Ensure we have enough data (min 10 bytes for standard)
        if len(data) < 10:
            return state
            
        buttons = self.profile.get('buttons', {})
        
        # Standard buttons
        for btn_name in ['a', 'b', 'x', 'y', 'lb', 'rb', 'select', 'start', 'home', 'l3', 'r3']:
            cfg = buttons.get(btn_name)
            if cfg and cfg['byte'] < len(data):
                setattr(state, btn_name, bool(data[cfg['byte']] & cfg['mask']))
                
        # D-pad (assuming hat switch for now)
        dpad_cfg = buttons.get('dpad')
        if dpad_cfg and dpad_cfg.get('type') == 'hat' and dpad_cfg['byte'] < len(data):
            hat = data[dpad_cfg['byte']] & 0x0F
            state.dpad_up = hat in (7, 0, 1)
            state.dpad_right = hat in (1, 2, 3)
            state.dpad_down = hat in (3, 4, 5)
            state.dpad_left = hat in (5, 6, 7)
            
        # Extra buttons dynamically decoded
        for extra_name, cfg in self.extra_buttons_config.items():
            if cfg['byte'] < len(data):
                state.extra_buttons[extra_name] = bool(data[cfg['byte']] & cfg['mask'])
                
        # Axes
        axes = self.profile.get('axes', {})
        for axis_name in ['lx', 'ly', 'rx', 'ry', 'lt', 'rt']:
            cfg = axes.get(axis_name)
            if cfg and cfg['byte'] < len(data):
                setattr(state, axis_name, data[cfg['byte']])
                
        return state
