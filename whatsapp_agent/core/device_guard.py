import time
import subprocess
import os

class DeviceGuard:
    def __init__(self, adb_client):
        self.adb = adb_client

    def prevent_screen_sleep(self):
        """Configures Android to stay awake and maxes screen off timeout."""
        try:
            # Keep screen awake on power / USB / wireless
            self.adb.run_adb(["shell", "svc power stayon true"])
            # Set display timeout to max (~24 days)
            self.adb.run_adb(["shell", "settings put system screen_off_timeout 2147483647"])
        except Exception as e:
            print(f"[!] Warning setting screen keepawake: {e}")

        # If running inside Termux, trigger termux-wake-lock
        if os.environ.get("TERMUX_VERSION") or os.path.exists("/data/data/com.termux"):
            try:
                subprocess.run(["termux-wake-lock"], capture_output=True)
            except Exception:
                pass

    def is_screen_locked(self):
        """Checks if screen is currently locked by keyguard / PIN / swipe."""
        out = self.adb.run_adb(["shell", "dumpsys window policy"])
        if not out:
            out = self.adb.run_adb(["shell", "dumpsys window"])

        # Check for keyguard flags
        for line in out.splitlines():
            line_l = line.lower()
            if "iskeyguardlocked=true" in line_l or "mshowinglockscreen=true" in line_l:
                return True
            if "mdreaminglockscreen=true" in line_l or "keyguardshowing=true" in line_l:
                return True

        # Check display power state
        power_out = self.adb.run_adb(["shell", "dumpsys power | grep -E 'Display Power: state='"])
        if "state=off" in power_out.lower():
            return True

        return False

    def wait_for_screen_unlock(self, check_interval=2.0):
        """Blocks execution until the screen is unlocked by the user."""
        if not self.is_screen_locked():
            return

        print("\033[93m[!] Screen is locked. Pausing agent until user unlocks device...\033[0m")
        while self.is_screen_locked():
            time.sleep(check_interval)
        print("\033[92m[✓] Device unlocked! Resuming agent service...\033[0m")
        time.sleep(0.5)

    def get_call_state(self):
        """
        Returns telephony call state:
        0: IDLE (no active call)
        1: RINGING (incoming call)
        2: OFFHOOK (call in progress)
        """
        out = self.adb.run_adb(["shell", "dumpsys telephony.registry | grep -m 1 mCallState"])
        if not out:
            return 0
        try:
            for part in out.strip().split():
                if part.startswith("mCallState="):
                    return int(part.split("=")[1])
                elif part.isdigit():
                    return int(part)
        except Exception:
            pass
        return 0

    def wait_for_call_end(self, check_interval=1.0):
        """Blocks execution while an incoming or active phone call is ongoing."""
        call_state = self.get_call_state()
        if call_state == 0:
            return

        state_name = "Incoming call ringing" if call_state == 1 else "Active call in progress"
        print(f"\033[93m[!] {state_name}. Agent paused until call ends...\033[0m")

        while self.get_call_state() != 0:
            time.sleep(check_interval)

        print("\033[92m[✓] Phone call ended. Resuming WhatsApp agent...\033[0m")
        time.sleep(1.0)
