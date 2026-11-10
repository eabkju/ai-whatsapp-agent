import time
import re
import threading
import subprocess
from contextlib import contextmanager

GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

class KeyboardManager:
    def __init__(self, adb_client, idle_timeout=25, user_ime=None):
        self.adb = adb_client
        self.idle_timeout = idle_timeout
        self.user_ime = user_ime
        self.last_user_interaction = 0
        self.last_agent_action = 0
        self.adb_ime = "com.android.adbkeyboard/.AdbIME"
        self.is_paused_for_user = False
        self.current_ime = None
        self._stopped = False
        self._touch_thread = None
        self._touch_proc = None
        self.detect_user_ime()
        self._start_touch_listener()

    def detect_user_ime(self):
        """Discovers and caches the user's preferred personal keyboard."""
        if self.user_ime:
            return self.user_ime

        current_ime = self.adb.run_adb(["shell", "settings get secure default_input_method"]).strip()
        if current_ime and "com.android.adbkeyboard" not in current_ime:
            self.user_ime = current_ime
            return self.user_ime

        # Check installed IMEs, prioritizing standard keyboards (e.g. Gboard, SwiftKey, Samsung)
        out = self.adb.run_adb(["shell", "ime list -s"])
        candidates = []
        if out:
            for line in out.strip().splitlines():
                ime = line.strip()
                if ime and "com.android.adbkeyboard" not in ime:
                    candidates.append(ime)

        # Prioritize Gboard (LatinIME)
        for ime in candidates:
            if "com.google.android.inputmethod.latin" in ime:
                self.user_ime = ime
                return self.user_ime

        # Prioritize SwiftKey or Samsung HoneyBoard
        for ime in candidates:
            if any(k in ime for k in ["swiftkey", "honeyboard", "samsung"]):
                self.user_ime = ime
                return self.user_ime

        # Avoid known OEM bloatware IMEs if other candidates exist
        filtered = [ime for ime in candidates if not any(b in ime for b in ["facemoji", "baidu", "simeji"])]
        if filtered:
            self.user_ime = filtered[0]
            return self.user_ime

        if candidates:
            self.user_ime = candidates[0]
            return self.user_ime

        self.user_ime = "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"
        return self.user_ime

    def _find_touch_device(self):
        """Finds the input event device path for physical touchscreen (e.g. /dev/input/event4)."""
        try:
            out = self.adb.run_adb(["shell", "getevent", "-S"])
            device_path = None
            current_dev = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("add device"):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        current_dev = parts[1].strip()
                elif line.startswith("name:") and current_dev:
                    name = line.lower()
                    if any(k in name for k in ["touch", "tpd", "ts", "synaptics", "goodix", "focaltech"]):
                        device_path = current_dev
                        break
            return device_path or "/dev/input/event4"
        except Exception:
            return "/dev/input/event4"

    def _start_touch_listener(self):
        """Starts real-time hardware touch/event listener thread."""
        if not getattr(self.adb, "device_id", None):
            return
        self._touch_thread = threading.Thread(target=self._touch_listener_loop, daemon=True)
        self._touch_thread.start()

    def _touch_listener_loop(self):
        """Monitors physical hardware touchscreen events via adb shell getevent."""
        touch_dev = self._find_touch_device()
        while not self._stopped:
            try:
                cmd = ["adb"]
                if getattr(self.adb, "device_id", None):
                    cmd += ["-s", self.adb.device_id]
                cmd += ["shell", "getevent", touch_dev]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                self._touch_proc = proc
                while not self._stopped:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    # Verify line is a valid hex input event (not header/banner)
                    line_clean = line.strip()
                    if not re.match(r'^[0-9a-fA-F]{4}\s+[0-9a-fA-F]{4}', line_clean):
                        continue

                    # Physical finger touch detected from user on touchscreen!
                    now = time.time()
                    self.last_user_interaction = now
                    if not self.is_paused_for_user:
                        self.is_paused_for_user = True
                        self.restore_user_keyboard()
                        print(f"\n{YELLOW}[!] User screen interference detected!{RESET}", flush=True)
                        print(f"    {CYAN}Switched keyboard to default ({self.user_ime}). Agent PAUSED.{RESET}", flush=True)
                proc.poll()
            except Exception:
                pass
            time.sleep(1.0)

    def stop(self):
        """Stops background listeners."""
        self._stopped = True
        if self._touch_proc:
            try:
                self._touch_proc.kill()
            except Exception:
                pass

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
        Polls soft keyboard visibility and power user activity as fallback.
        """
        cmd = "dumpsys input_method | grep -E 'mInputShown'"
        out = self.adb.run_adb(["shell", cmd])
        if out and "mInputShown=true" in out:
            # Soft keyboard is visibly open on screen
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
