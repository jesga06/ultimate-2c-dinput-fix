"""
HID Report Decoder (decoder.py)
This module decodes raw byte packets received from a DirectInput gamepad
using a flexible metadata-driven HID map ({VID}_{PID}.json).
"""
import json
import os
import logging

logger = logging.getLogger('decoder')
from dataclasses import dataclass, field
from typing import Dict, Any
from hid_reader import RawHIDReport


@dataclass
class ControllerState:
    """
    Data structure representing the parsed state of a gamepad.
    Standard inputs use common names for convenience, but the decoder
    can handle completely arbitrary inputs by populating extra_inputs.
    Axes are normalized to floats.
    """
    # Standard digital buttons
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

    # Standard Axes (Normalized -1.0 to 1.0)
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0

    # Triggers (Normalized 0.0 to 1.0)
    lt: float = 0.0
    rt: float = 0.0

    # Dynamic inputs for arbitrary controller layouts
    extra_inputs: Dict[str, Any] = field(default_factory=dict)


class Decoder:
    """
    Decodes raw byte buffers into a ControllerState object based on
    a generic, metadata-driven HID map ({VID}_{PID}.json).
    The HID map describes the physical byte layout of the controller's HID reports.
    """

    def __init__(self, hid_map_path: str):
        # 'profile' is kept as the internal attribute name for backwards-compatibility
        # with other code that reads self.profile; the file itself is called the HID map.
        self.profile = {}
        self.reports_config = {}
        self.has_report_ids = True

        self.use_length_as_id = False

        if os.path.exists(hid_map_path):
            try:
                with open(hid_map_path, 'r') as f:
                    self.profile = json.load(f)
                    self.reports_config = self.profile.get('reports', {})
                    self.has_report_ids = self.profile.get('has_report_id', True)
                    self.use_length_as_id = self.profile.get('use_length_as_id', False)
            except json.JSONDecodeError as e:
                print(f"Error: HID map {hid_map_path} is not valid JSON: {e}")
                logger.error(f"Error: HID map {hid_map_path} is not valid JSON: {e}")
            except Exception as e:
                print(f"Error loading HID map {hid_map_path}: {e}")
                logger.error(f"Error loading HID map {hid_map_path}: {e}")
        else:
            print(f"Warning: HID map {hid_map_path} not found. Inputs will be ignored.")
            logger.warning(f"HID map {hid_map_path} not found. Inputs will be ignored.")

        # Persistent state: fields are updated in place, retaining their state between reports
        self.state = ControllerState()

    def decode(self, report: RawHIDReport) -> ControllerState:
        data = report.payload
        if not data:
            return self.state

        if self.use_length_as_id:
            report_id_str = str(len(data))
        else:
            report_id_str = str(report.report_id) if self.has_report_ids else "0"
            
        if report.interface_number != -1:
            full_id = f"{report.interface_number}_{report_id_str}"
            if full_id in self.reports_config:
                report_id_str = full_id
        
        # If this report ID is not in our profile, ignore it.
        if report_id_str not in self.reports_config:
            return self.state

        config = self.reports_config[report_id_str]
        inputs = config.get('inputs', {})

        # If report IDs are used, data[0] is the report ID, payload starts at data[1].
        # However, to be fully generic, the JSON profile author determines the byte index
        # knowing that byte 0 is the report ID. Thus, we don't apply an offset here.
        # The user's calibration tool will generate the correct absolute byte indices into the payload array.

        for input_name, cfg in inputs.items():
            input_type = cfg.get('type')
            byte_idx = cfg.get('byte')

            # Handle 16-bit values if length is 2
            length = cfg.get('length', 1)
            
            # Bounds check to prevent IndexError
            if byte_idx is None or byte_idx + length > len(data):
                continue

            # Read raw integer value
            if length == 1:
                raw_val = data[byte_idx]
            elif length == 2:
                # Assuming little-endian which is standard for USB HID
                raw_val = data[byte_idx] | (data[byte_idx + 1] << 8)
            else:
                continue # Unsupported length

            if input_type == 'button':
                bitmask = cfg.get('bitmask', 1)
                pressed = bool(raw_val & bitmask)
                self._set_state(input_name, pressed)

            elif input_type == 'axis':
                # Axis processing (scaling, deadzones, normalization)
                bitmask = cfg.get('bitmask', (1 << (length * 8)) - 1)
                masked_val = raw_val & bitmask
                bitshift = cfg.get('bitshift', 0)
                shifted_val = masked_val >> bitshift

                # Signedness
                is_signed = cfg.get('signed', False)
                max_val = (1 << ( (length * 8) - bitshift))
                if is_signed:
                    half_val = max_val // 2
                    if shifted_val >= half_val:
                        shifted_val -= max_val
                    # Normalize -1.0 to 1.0
                    norm_val = shifted_val / float(half_val)
                else:
                    # Normalize 0.0 to 1.0, then scale to -1.0 to 1.0 if it's a joystick
                    norm_val = shifted_val / float(max_val - 1)
                    if cfg.get('center', False):  # e.g., lx, ly usually center at 0
                        norm_val = (norm_val * 2.0) - 1.0

                # Inversion
                if cfg.get('invert', False):
                    norm_val = -norm_val

                # Deadzone
                deadzone = cfg.get('deadzone', 0.0)
                if abs(norm_val) < deadzone:
                    norm_val = 0.0
                elif norm_val > 0:
                    norm_val = (norm_val - deadzone) / (1.0 - deadzone)
                else:
                    norm_val = (norm_val + deadzone) / (1.0 - deadzone)

                # Clamp
                norm_val = max(-1.0, min(1.0, norm_val))
                self._set_state(input_name, float(norm_val))

            elif input_type == 'trigger':
                # Similar to axis but strictly 0.0 to 1.0
                bitmask = cfg.get('bitmask', (1 << (length * 8)) - 1)
                masked_val = raw_val & bitmask
                bitshift = cfg.get('bitshift', 0)
                shifted_val = masked_val >> bitshift
                max_val = (1 << ( (length * 8) - bitshift)) - 1
                
                norm_val = shifted_val / float(max_val) if max_val > 0 else 0.0
                
                deadzone = cfg.get('deadzone', 0.0)
                if norm_val < deadzone:
                    norm_val = 0.0
                else:
                    norm_val = (norm_val - deadzone) / (1.0 - deadzone)
                    
                norm_val = max(0.0, min(1.0, norm_val))
                self._set_state(input_name, float(norm_val))

            elif input_type == 'hat':
                # Standard 8-way hat switch
                hat = raw_val & 0x0F
                self._set_state('dpad_up', hat in (7, 0, 1))
                self._set_state('dpad_right', hat in (1, 2, 3))
                self._set_state('dpad_down', hat in (3, 4, 5))
                self._set_state('dpad_left', hat in (5, 6, 7))

        return self.state

    def _set_state(self, key: str, value: Any):
        if hasattr(self.state, key):
            setattr(self.state, key, value)
        else:
            self.state.extra_inputs[key] = value
