"""
Single Instance Process Guard
Prevents duplicate instances of application scripts (main.py, gui.py, calibration.py)
from running concurrently by locking a local socket port.
"""
import socket
import sys

_instance_sockets = {}


def ensure_single_instance(app_name: str, port: int) -> socket.socket:
    """
    Ensures that only one instance of app_name is running simultaneously.
    If another instance is already running on the specified port, prints a message
    and exits immediately with status 0, preserving the oldest instance.

    Args:
        app_name (str): Human readable name of the application/script.
        port (int): Port number on localhost to bind for locking.

    Returns:
        socket.socket: Bound socket object (must remain open for process lifetime).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
        # Keep reference in global dict so garbage collector does not close the socket
        _instance_sockets[app_name] = s
        return s
    except (socket.error, OSError):
        print(f"[{app_name}] Another instance of {app_name} is already running. Exiting.")
        sys.exit(0)
