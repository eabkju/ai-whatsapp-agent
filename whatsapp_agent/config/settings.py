import os
import json
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "whatsapp_ai_agent"
CONFIG_FILE_PATH = DEFAULT_CONFIG_DIR / "config.json"

DEFAULT_SETTINGS = {
    "device_id": "",
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "agent_name": "Personal AI Assistant",
    "cooldown_seconds": 8,
    "user_idle_timeout": 15,
    "bg_notify_interval": 50,
    "poll_interval": 0.8,
    "idle_poll_interval": 1.5,
    "ignore_groups": True,
    "auto_send": True,
    "models": {
        "text": "gemini-2.5-flash",
        "vision": "gemini-2.0-flash",
        "audio": "gemini-2.0-flash"
    },
    "ui_coords": {
        "back_button": [66, 176],
        "input_entry": [395, 2314],
        "send_fallback": [988, 2314]
    },
    "voice_notes_paths": [
        "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Voice Notes/",
        "/sdcard/WhatsApp/Media/WhatsApp Voice Notes/"
    ],
    "pid_file": "/tmp/whatsapp_ai_agent.pid",
    "state_file": "/tmp/whatsapp_ai_agent.state"
}

def load_settings():
    """Loads settings from config.json or initializes with defaults."""
    if not DEFAULT_CONFIG_DIR.exists():
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
    if not CONFIG_FILE_PATH.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
        
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            user_settings = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(user_settings)
            return merged
    except Exception as e:
        print(f"[!] Warning: Failed to read {CONFIG_FILE_PATH} ({e}). Using defaults.")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Saves settings dictionary to config.json with secure 600 permissions."""
    if not DEFAULT_CONFIG_DIR.exists():
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
    try:
        os.chmod(CONFIG_FILE_PATH, 0o600)
    except Exception:
        pass
