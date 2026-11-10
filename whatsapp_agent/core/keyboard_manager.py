import time
import re
from contextlib import contextmanager

GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

class KeyboardManager:
    def __init__(self, adb_client, idle_timeout=25):
        self.adb = adb_client
        self.idle_timeout = idle_timeout
        self.user_ime = None
        self.last_user_interaction = 0
        self.last_agent_action = 0
        self.adb_ime = "com.android.adbkeyboard/.AdbIME"
        self.is_paused_for_user = False
        self.current_ime = None
        self.detect_user_ime()

    def detect_user_ime(self):
        """Discovers and caches the user's preferred personal keyboard."""
        current_ime = self.adb.run_adb(["shell", "settings get secure default_input_method"]).strip()
        if current_ime and "com.android.adbkeyboard" not in current_ime:
            self.user_ime = current_ime
        elif not self.user_ime:
            # Check installed IMEs
            out = self.adb.run_adb(["shell", "ime list -s"])
            if out:
                for line in out.strip().splitlines():
                    ime = line.strip()
                    if ime and "com.android.adbkeyboard" not in ime:
                        self.user_ime = ime
                        break
        if not self.user_ime:
            self.user_ime = "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"
        return self.user_ime

    def switch_to_adb_keyboard(self):
        """Enables and switches to ADBKeyboard for typing."""
        if self.current_ime != self.adb_ime:
            self.adb.run_adb(["shell", "ime", "enable", self.adb_ime])
            self.adb.run_adb(["shell", "ime", "set", self.adb_ime])
            self.current_ime = self.adb_ime

    def restore_user_keyboard(self):
        """Restores the user's default personal keyboard."""
        if not self.user_ime:
            self.detect_user_ime()
        if self.user_ime and self.current_ime != self.user_ime:
            self.adb.run_adb(["shell", "ime", "set", self.user_ime])
            self.current_ime = self.user_ime

    def record_agent_action(self):
        """Records timestamp when agent executes an automated tap, swipe, or typing."""
        self.last_agent_action = time.time()

    def record_user_interaction(self):
        """Notifies manager that user touched the screen or focused an input."""
        self.last_user_interaction = time.time()
        self.is_paused_for_user = True
        self.restore_user_keyboard()

    def is_user_active(self):
        """Returns True if user interacted within the idle timeout window (25s)."""
        if self.last_user_interaction == 0:
            return False
        return (time.time() - self.last_user_interaction) < self.idle_timeout

    def check_user_interference(self):
        """
        Polls power user activity and soft keyboard visibility.
        Detects if the human user is physically touching the screen or typing.
        """
        cmd = "dumpsys power | grep -E 'lastUserActivityTime=.*ms ago'; dumpsys input_method | grep -E 'mInputShown'"
        out = self.adb.run_adb(["shell", cmd])
        if not out:
            return False

        time_since_agent = time.time() - self.last_agent_action

        # 1. Physical touch screen activity (user finger touched screen)
        activity_match = re.search(r'lastUserActivityTime=\d+\s+\((\d+)\s*ms ago\)', out)
        if activity_match:
            ms_ago = int(activity_match.group(1))
            # Activity happened within last 2.5 seconds and was not agent's own automated action
            if ms_ago < 2500 and time_since_agent > 2.5:
                return True

        # 2. Soft keyboard is actively shown for user typing
        if "mInputShown=true" in out and time_since_agent > 2.5:
            if self.current_ime != self.adb_ime:
                return True

        return False

    def handle_user_state(self):
        """
        Manages keyboard switching and pause/resume based on user interference:
        - When user interferes with screen:
            1. Switch current keyboard from ADBKeyboard to phone's default keyboard.
            2. Pause agent and update interference timestamp.
        - When no user interference is detected for 25 seconds:
            1. Switch keyboard to ADBKeyboard.
            2. Resume agent doing its job from pause.
        Returns: bool (True if agent should remain paused, False if agent can proceed)
        """
        now = time.time()
        interfering = self.check_user_interference()

        if interfering:
            self.last_user_interaction = now
            if not self.is_paused_for_user:
                self.is_paused_for_user = True
                self.restore_user_keyboard()
                print(f"\n{YELLOW}[!] User screen interference detected!{RESET}", flush=True)
                print(f"    {CYAN}Switched keyboard to default ({self.user_ime}). Agent PAUSED.{RESET}", flush=True)
            return True

        # If currently paused waiting for 25s idle
        if self.is_paused_for_user:
            elapsed = now - self.last_user_interaction
            if elapsed < self.idle_timeout:
                return True
            else:
                # 25 seconds of silence have elapsed!
                self.is_paused_for_user = False
                self.last_user_interaction = 0
                self.switch_to_adb_keyboard()
                print(f"\n{GREEN}[✓] No user interference for {int(self.idle_timeout)}s!{RESET}", flush=True)
                print(f"    {CYAN}Switched keyboard to ADBKeyboard. Agent RESUMED.{RESET}\n", flush=True)
                return False

        # If active and no interference, ensure ADBKeyboard is current
        if self.current_ime != self.adb_ime:
            self.switch_to_adb_keyboard()

        return False

    def check_screen_interaction(self):
        """Backwards compatibility helper."""
        return self.handle_user_state()

    @contextmanager
    def typing_session(self):
        """
        Ensures ADBKeyboard is active during typing, and records agent action.
        """
        self.record_agent_action()
        self.switch_to_adb_keyboard()
        time.sleep(0.05)
        try:
            yield
        finally:
            self.record_agent_action()
