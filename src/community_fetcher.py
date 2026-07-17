import os
import json
import urllib.request

# Base raw URL for the community HID maps repository
_RAW_BASE = "https://raw.githubusercontent.com/jesga06/UR-XD-community-HID-maps/main"
_DB_URL   = f"{_RAW_BASE}/database.json"

# Local storage path
_COMMUNITY_DIR = os.path.join("profiles", "community")
_DB_LOCAL_PATH = os.path.join(_COMMUNITY_DIR, "database.json")


def _log(logger, level, msg):
    if logger:
        getattr(logger, level)(msg)
    else:
        print(f"[community_fetcher] {msg}")


def _ensure_dir():
    if not os.path.exists(_COMMUNITY_DIR):
        os.makedirs(_COMMUNITY_DIR)


def _download_raw(url: str, dest_path: str, timeout: int = 10) -> bool:
    """Download a single raw file from a URL to a local path. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UR-XD/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to download {url}: {e}")


def fetch_database(logger=None) -> dict:
    """
    Step 1 of the selective fetch workflow.

    Downloads ONLY database.json from the community repository and caches it locally.
    Returns the parsed database as a dict, or raises on failure.

    REPOSITORY database.json FORMAT:
    {
        "<Device Name>": {
            "aliases": ["XXXX:YYYY", ...],   -- uppercase hex VID:PID strings
            "hid_map_file": "maps/{VID}_{PID}.json"  -- path relative to repo root
        },
        ...
    }
    """
    _ensure_dir()
    _log(logger, "info", f"Fetching community database from {_DB_URL}...")

    _download_raw(_DB_URL, _DB_LOCAL_PATH)

    with open(_DB_LOCAL_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    _log(logger, "info", f"Community database fetched: {len(db)} entries.")
    return db


def fetch_maps_for_devices(connected_vids_pids: list, logger=None) -> dict:
    """
    Step 2 of the selective fetch workflow.

    Given a list of connected (VID, PID) integer tuples, this function:
      1. Loads the locally-cached database.json (downloads it first if missing).
      2. Finds all database entries whose aliases match ANY connected device.
      3. Downloads ONLY those specific HID map files into profiles/community/.

    Returns a dict mapping device_name -> local_path for every map successfully
    downloaded. Devices that already have a local HID map are not fetched.

    Args:
        connected_vids_pids: list of (int, int) tuples, e.g. [(0x2345, 0xE02D), ...]
        logger: optional logger object with .info / .warning / .error methods

    Example:
        fetch_maps_for_devices([(0x2345, 0xE02D), (0x2DC8, 0x301C)])
    """
    _ensure_dir()

    # Load or refresh the local database
    if not os.path.exists(_DB_LOCAL_PATH):
        _log(logger, "info", "No local database found; fetching now...")
        fetch_database(logger=logger)

    with open(_DB_LOCAL_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    # Build set of "VID:PID" strings for all connected devices (uppercase hex)
    connected_set = {f"{vid:04X}:{pid:04X}" for vid, pid in connected_vids_pids}
    _log(logger, "info", f"Looking up community maps for: {connected_set}")

    fetched = {}

    for device_name, entry in db.items():
        aliases = entry.get("aliases", [])
        hid_map_file = entry.get("hid_map_file", "")

        # Check if any alias of this entry matches a connected device
        if not any(alias in connected_set for alias in aliases):
            continue

        if not hid_map_file:
            _log(logger, "warning", f"Entry '{device_name}' has no hid_map_file, skipping.")
            continue

        # Local destination: flatten hid_map_file path into community dir
        # e.g. "maps/2345_e02d.json" -> "profiles/community/2345_e02d.json"
        local_filename = os.path.basename(hid_map_file)
        local_path = os.path.join(_COMMUNITY_DIR, local_filename)

        if os.path.exists(local_path):
            _log(logger, "info", f"[{device_name}] Already cached at '{local_path}', skipping download.")
            fetched[device_name] = local_path
            continue

        # Construct the raw download URL from the relative path in the repo
        download_url = f"{_RAW_BASE}/{hid_map_file}"
        _log(logger, "info", f"[{device_name}] Downloading HID map from {download_url}...")

        try:
            _download_raw(download_url, local_path)
            fetched[device_name] = local_path
            _log(logger, "info", f"[{device_name}] Saved to '{local_path}'.")
        except RuntimeError as e:
            _log(logger, "error", str(e))

    if not fetched:
        _log(logger, "info", "No matching community HID maps found for connected devices.")
    else:
        _log(logger, "info", f"Done. {len(fetched)} map(s) fetched: {list(fetched.keys())}")

    return fetched


def fetch_community_hid_maps(logger=None) -> str:
    """
    Legacy all-in-one fetch used by the GUI 'Update Community HID Maps' button.

    Detects currently connected HID devices, then runs the selective fetch:
      1. Downloads database.json
      2. Downloads only HID maps for connected devices

    Returns a human-readable status string (starts with "Success" on success).
    """
    try:
        import hid_reader
        devices = hid_reader.HIDReader.get_all_devices()
        vids_pids = [(d.get("vendor_id", 0), d.get("product_id", 0)) for d in devices]
    except Exception as e:
        _log(logger, "warning", f"Could not enumerate HID devices: {e}. Fetching database only.")
        vids_pids = []

    try:
        db = fetch_database(logger=logger)
    except RuntimeError as e:
        return f"Error fetching database: {e}"

    if not vids_pids:
        return "Success: Database updated. No connected devices to fetch maps for."

    try:
        fetched = fetch_maps_for_devices(vids_pids, logger=logger)
    except Exception as e:
        return f"Error fetching maps: {e}"

    if fetched:
        names = ", ".join(fetched.keys())
        return f"Success: Downloaded maps for: {names}"
    else:
        return "Success: Database updated. No community maps matched your connected devices."
