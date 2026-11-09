import os
import json
import tempfile
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "whatsapp_ai_agent"
CONFIG_FILE_PATH = DEFAULT_CONFIG_DIR / "config.json"

def get_writable_temp_dir():
    """Returns /tmp if writable, otherwise falls back to system/Termux temp directory."""
    if os.access("/tmp", os.W_OK):
        return "/tmp"
    return tempfile.gettempdir()

DEFAULT_SETTINGS = {
    "device_id": "",
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "agent_name": "Personal AI Assistant",
    "cooldown_seconds": 8,
    "user_idle_timeout": 25,
    "bg_notify_interval": 50,
    "poll_interval": 0.8,
    "idle_poll_interval": 1.5,
    "ignore_groups": True,
    "auto_send": True,
    "models": {
        "text": "gemini-3.5-flash",
        "vision": "gemini-3.5-flash",
        "audio": "gemini-3.5-flash"
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
    "pid_file": os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.pid"),
    "state_file": os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.state")
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
            
            # Ensure pid_file and state_file are in a writable temp directory
            tmp_dir = get_writable_temp_dir()
            for key, filename in [("pid_file", "whatsapp_ai_agent.pid"), ("state_file", "whatsapp_ai_agent.state")]:
                cur = merged.get(key, "")
                if not cur or (cur.startswith("/tmp") and not os.access("/tmp", os.W_OK)):
                    merged[key] = os.path.join(tmp_dir, filename)

            if merged.get("user_idle_timeout") in (15, None):
                merged["user_idle_timeout"] = 25

            # Auto-migrate deprecated models
            models = merged.get("models", {})
            if isinstance(models, dict):
                deprecated = ("gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash")
                for m_type in ("text", "vision", "audio"):
                    if models.get(m_type) in deprecated:
                        models[m_type] = "gemini-3.5-flash"
                merged["models"] = models

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
