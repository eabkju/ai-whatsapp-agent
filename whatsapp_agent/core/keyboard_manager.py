import time
from contextlib import contextmanager

class KeyboardManager:
    def __init__(self, adb_client, idle_timeout=15):
        self.adb = adb_client
        self.idle_timeout = idle_timeout
        self.user_ime = None
        self.last_user_interaction = 0
        self.adb_ime = "com.android.adbkeyboard/.AdbIME"
        self.detect_user_ime()

    def detect_user_ime(self):
        """Discovers and caches the user's preferred keyboard."""
        current_ime = self.adb.run_adb(["shell", "settings get secure default_input_method"]).strip()
        if current_ime and "com.android.adbkeyboard" not in current_ime:
            self.user_ime = current_ime
        elif not self.user_ime:
            # Fallback to standard Gboard or Android Latin IME if not detected yet
            self.user_ime = "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"
        return self.user_ime

    def switch_to_adb_keyboard(self):
        """Enables and switches to ADBKeyboard for typing."""
        self.adb.run_adb(["shell", "ime", "enable", self.adb_ime])
        self.adb.run_adb(["shell", "ime", "set", self.adb_ime])

    def restore_user_keyboard(self):
        """Restores the user's default personal keyboard."""
        if self.user_ime:
            self.adb.run_adb(["shell", "ime", "set", self.user_ime])

    def record_user_interaction(self):
        """Notifies manager that user touched the screen or focused an input."""
        self.last_user_interaction = time.time()
        self.restore_user_keyboard()

    def is_user_active(self):
        """Returns True if user interacted within the idle timeout window (10-20s)."""
        if self.last_user_interaction == 0:
            return False
        return (time.time() - self.last_user_interaction) < self.idle_timeout

    def check_screen_interaction(self):
        """
        Polls input touch events or window focus.
        If user interaction is detected, yields keyboard back to user.
        """
        out = self.adb.run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"])
        if out and "com.whatsapp" not in out:
            self.restore_user_keyboard()

    @contextmanager
    def typing_session(self):
        """
        Context manager that activates ADBKeyboard ONLY for the brief
        duration of text injection, then immediately restores the user's keyboard.
        """
        try:
            self.switch_to_adb_keyboard()
            time.sleep(0.1)
            yield
        finally:
            self.restore_user_keyboard()
