import sys
import os
import time
import platform

# 1. Setup logging redirection to capture everything (both stdout/stderr)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(REPO_ROOT, "diagnostics_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "01_environment_audit.log")

class DualLogger:
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.error_terminal = sys.stderr
        self.log = open(filepath, "w", encoding="utf-8")
        self.closed = False

    def write(self, message):
        self.terminal.write(message)
        if not self.closed:
            try:
                self.log.write(message)
                self.log.flush()
            except ValueError:
                pass

    def write_err(self, message):
        self.error_terminal.write(message)
        if not self.closed:
            try:
                self.log.write(message)
                self.log.flush()
            except ValueError:
                pass

    def flush(self):
        self.terminal.flush()
        self.error_terminal.flush()
        if not self.closed:
            try:
                self.log.flush()
            except ValueError:
                pass

    def close(self):
        if not self.closed:
            self.log.close()
            self.closed = True

logger = DualLogger(LOG_FILE)
sys.stdout = logger

class StderrWrapper:
    def __init__(self, dual_logger):
        self.dual_logger = dual_logger
    def write(self, message):
        self.dual_logger.write_err(message)
    def flush(self):
        self.dual_logger.flush()

sys.stderr = StderrWrapper(logger)

def show_progress(message, duration_seconds=1.5):
    print(f"\n[WAIT] {message}")
    print(">>> STATUS: DO NOT TOUCH ANYTHING <<<")
    symbols = ["|", "/", "-", "\\"]
    start = time.time()
    i = 0
    while time.time() - start < duration_seconds:
        sys.stdout.write(f"\r[{symbols[i % len(symbols)]}] Working...")
        sys.stdout.flush()
        time.sleep(0.15)
        i += 1
    sys.stdout.write("\r[+] Completed.                      \n")
    sys.stdout.flush()

def main():
    print("=" * 60)
    print("   DIAGNOSTIC STEP 1: ENVIRONMENT AUDIT")
    print("=" * 60)
    print("This script checks if your computer's environment is correctly set up.")
    print("It will examine your operating system, Python setup, installed libraries,")
    print("and virtual gamepad drivers.")
    print("-" * 60)
    
    # OS & Python details
    show_progress("Retrieving system and Python versions", 1.0)
    print(f"OS Version: {platform.platform()} ({platform.version()})")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    
    # Library imports
    show_progress("Testing Python library imports (hid, vgamepad, pynput)", 1.5)
    
    libraries = ['hid', 'vgamepad', 'pynput']
    import_success = True
    for lib in libraries:
        try:
            print(f"Attempting to import library '{lib}'...")
            if lib == 'hid':
                import hid
                print(f" -> SUCCESS: '{lib}' successfully imported.")
                print(f"    Location: {hid.__file__}")
            elif lib == 'vgamepad':
                import vgamepad
                print(f" -> SUCCESS: '{lib}' successfully imported.")
                print(f"    Location: {vgamepad.__file__}")
            elif lib == 'pynput':
                import pynput
                print(f" -> SUCCESS: '{lib}' successfully imported.")
                print(f"    Location: {pynput.__file__}")
        except ImportError as e:
            print(f" -> ERROR: Failed to import library '{lib}'!")
            print(f"    Details: {e}")
            import_success = False
            
    if not import_success:
        print("\n[CRITICAL ERROR] One or more libraries failed to import.")
        print("Please run 'pip install -r requirements.txt' in your virtual environment to install them.")
        sys.exit(1)
        
    # VX360Gamepad Driver check
    show_progress("Checking Virtual Gamepad (ViGEmBus) driver functionality", 2.0)
    try:
        print("Attempting to instantiate a virtual Xbox 360 controller...")
        import vgamepad
        gamepad = vgamepad.VX360Gamepad()
        print(" -> SUCCESS: Virtual Xbox 360 controller instantiated successfully.")
        print("    This confirms that the ViGEmBus driver is installed and working correctly.")
        # Clean up gamepad
        del gamepad
    except Exception as e:
        print(" -> ERROR: Failed to create virtual gamepad.")
        print("    This usually means the ViGEmBus driver is missing or not functioning.")
        print(f"    Details: {e}")
        print("\n[INSTRUCTIONS]")
        print("Please download and install the ViGEmBus driver from the official website:")
        print("https://github.com/ViGEm/ViGEmBus/releases")
        sys.exit(1)

    print("=" * 60)
    print("   ENVIRONMENT AUDIT COMPLETED")
    print("=" * 60)
    print("All checks passed successfully! Your environment is ready.")
    print(f"A log of this audit has been saved to:\n  {LOG_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    finally:
        logger.close()
