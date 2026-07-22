import json
import threading
import time
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger('macro_executor')


class MacroExecutor:
    """
    Executes sequence macros (key press, release, wait) in a background thread.
    Supports toggle on/off execution and graceful sequence interruption.
    """

    def __init__(self, mapper: Any):
        self.mapper = mapper
        self.macros: Dict[str, List[Dict[str, Any]]] = {}
        self.active_macro: Optional[str] = None
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        self.load_macros()
        
    def load_macros(self) -> None:
        try:
            if os.path.exists('macros.json'):
                with open('macros.json', 'r', encoding='utf-8') as f:
                    self.macros = json.load(f)
            else:
                self.macros = {}
        except Exception as e:
            print(f"Error loading macros.json: {e}")
            logger.error(f"Error loading macros.json: {e}", exc_info=True)
            self.macros = {}
            
    def execute_or_toggle(self, macro_name: str) -> None:
        with self.lock:
            if self.active_macro == macro_name:
                # Toggle off if pressed again
                self.stop_event.set()
                self.active_macro = None
                return
            elif self.active_macro is not None:
                # Stop existing, start new
                self.stop_event.set()
                if self.worker_thread:
                    self.worker_thread.join(timeout=0.1)
            
            sequence = self.macros.get(macro_name)
            if not sequence:
                return
                
            self.stop_event.clear()
            self.active_macro = macro_name
            self.worker_thread = threading.Thread(target=self._run_macro, args=(macro_name, sequence,), daemon=True)
            self.worker_thread.start()
            
    def _run_macro(self, macro_name: str, sequence: List[Dict[str, Any]]) -> None:
        for step in sequence:
            if self.stop_event.is_set():
                break
                
            action = step.get('action')
            if action == 'press':
                key = step.get('key')
                if key:
                    self.mapper._press(key)
            elif action == 'release':
                key = step.get('key')
                if key:
                    self.mapper._release(key)
            elif action == 'wait':
                # Convert ms to seconds
                ms = step.get('ms', 0)
                end_time = time.time() + (ms / 1000.0)
                # Sleep in small chunks to allow quick interrupt
                while time.time() < end_time:
                    if self.stop_event.is_set():
                        break
                    time.sleep(0.005)
                    
        with self.lock:
            if self.active_macro == macro_name:
                self.active_macro = None

