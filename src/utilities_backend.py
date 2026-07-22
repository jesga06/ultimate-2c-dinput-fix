import time
import collections
import socket
import json
import threading
import os
import dataclasses
from typing import Dict, Any

class LatencyMonitor:
    """
    Monitors polling rates and processing latencies for backend transport loops.
    Optionally broadcasts state metrics over UDP to live visualizers.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.poll_intervals = collections.deque(maxlen=window_size)
        self.process_latencies = collections.deque(maxlen=window_size)
        self.last_poll_time: float = 0.0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._logging_started = False
        
    def record_poll(self) -> float:
        now = time.perf_counter()
        if self.last_poll_time > 0.0:
            self.poll_intervals.append(now - self.last_poll_time)
        self.last_poll_time = now
        return now
        
    def record_process(self, start_time: float) -> None:
        now = time.perf_counter()
        self.process_latencies.append(now - start_time)
        
    def broadcast_state(self, state: Any) -> None:
        try:
            if dataclasses.is_dataclass(state):
                d = dataclasses.asdict(state)
            elif hasattr(state, '__dict__'):
                d = state.__dict__.copy()
            else:
                return
            msg = json.dumps(d).encode('utf-8')
            self.sock.sendto(msg, ("127.0.0.1", 9999))
        except Exception:
            pass
        
    def get_stats(self) -> Dict[str, float]:
        if not self.poll_intervals or not self.process_latencies:
            return {
                "polling_rate_hz": 0.0,
                "avg_process_ms": 0.0,
                "max_process_ms": 0.0
            }
            
        avg_poll = sum(self.poll_intervals) / len(self.poll_intervals)
        hz = 1.0 / avg_poll if avg_poll > 0.0 else 0.0
        
        avg_lat = sum(self.process_latencies) / len(self.process_latencies)
        max_lat = max(self.process_latencies)
        
        return {
            "polling_rate_hz": round(hz, 1),
            "avg_process_ms": round(avg_lat * 1000.0, 3),
            "max_process_ms": round(max_lat * 1000.0, 3)
        }
        
    def start_logging(self) -> None:
        if self._logging_started:
            return
        self._logging_started = True
        
        def _loop():
            while self._logging_started:
                time.sleep(0.5)
                stats = self.get_stats()
                try:
                    with open('diagnostics.json', 'w', encoding='utf-8') as f:
                        json.dump(stats, f, indent=2)
                except Exception:
                    pass
                    
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def stop_logging(self) -> None:
        self._logging_started = False

monitor = LatencyMonitor()

