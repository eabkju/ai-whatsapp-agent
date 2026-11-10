import subprocess
import time
import base64
import os

class ADBClient:
    def __init__(self, device_id=None, prefer_usb=None):
        self.device_id = device_id
        self.connection_type = "Wi-Fi"
        self.last_action_time = 0

    def run_adb(self, cmd_args, check=False, binary=False):
        """Executes an adb command targeting the configured device."""
        prefix = ["adb"]
        # connect and pair are client commands that don't accept '-s'
        if self.device_id and cmd_args and cmd_args[0] not in ("connect", "pair", "devices"):
            prefix += ["-s", self.device_id]
        full_cmd = prefix + cmd_args
        try:
            if binary:
                res = subprocess.run(full_cmd, capture_output=True)
                return res.stdout
            else:
                res = subprocess.run(full_cmd, capture_output=True, text=True, errors="replace")
                return res.stdout
        except Exception as e:
            return "" if not binary else b""

    def auto_detect_device(self):
        """
        Scans 'adb devices -l' for active Wi-Fi/Wireless ADB connections.
        USB devices are strictly ignored.
        Returns: (device_serial, 'Wi-Fi') or (None, None)
        """
        try:
            res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, errors="replace")
            lines = res.stdout.strip().splitlines()[1:]
        except Exception:
            return None, None

        wifi_devices = []

        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                # Wi-Fi devices have an IP:Port format containing ':'
                if ":" in serial and "usb:" not in line:
                    wifi_devices.append(serial)

        if wifi_devices:
            # If user configured a specific Wi-Fi device that is online, prefer it
            if self.device_id and self.device_id in wifi_devices:
                self.connection_type = "Wi-Fi"
                return self.device_id, "Wi-Fi"
            self.device_id = wifi_devices[0]
            self.connection_type = "Wi-Fi"
            return self.device_id, "Wi-Fi"

        return None, None

    def connect_wifi(self, ip_port):
        """Connects to a Wireless ADB target via IP:Port or local port."""
        if not ip_port:
            return False
        clean_target = str(ip_port).strip()
        if clean_target.isdigit():
            clean_target = f"127.0.0.1:{clean_target}"
        try:
            res = subprocess.run(["adb", "connect", clean_target], capture_output=True, text=True, timeout=10)
            time.sleep(1.0)
            if "connected to" in res.stdout.lower():
                self.device_id = clean_target
                self.connection_type = "Wi-Fi"
                return True
        except Exception:
            pass

        # Re-verify through auto_detect_device
        detected_id, _ = self.auto_detect_device()
        if detected_id and (detected_id == clean_target or not self.device_id):
            self.device_id = detected_id
            self.connection_type = "Wi-Fi"
            return True
        return False

    def pair_wifi(self, pairing_ip_port, pairing_code):
        """Pairs with Android Wireless Debugging using 6-digit code."""
        if not pairing_ip_port or not pairing_code:
            return False, "Missing target or code"
        target = str(pairing_ip_port).strip()
        if target.isdigit():
            target = f"127.0.0.1:{target}"
        try:
            res = subprocess.run(
                ["adb", "pair", target, str(pairing_code).strip()],
                capture_output=True,
                text=True,
                timeout=15
            )
            out = (res.stdout or "") + " " + (res.stderr or "")
            if "successfully paired" in out.lower():
                return True, "Successfully paired!"
            return False, out.strip() or "Pairing failed"
        except Exception as e:
            return False, str(e)

    def ensure_adb_keyboard(self, apk_path=None):
        """Ensures ADBKeyboard is installed and activated on the Wi-Fi connected device."""
        if not self.device_id:
            return False

        # 1. Check if package is installed
        installed = self.run_adb(["shell", "pm list packages com.android.adbkeyboard"])
        if "com.android.adbkeyboard" not in installed:
            if apk_path and os.path.exists(apk_path):
                self.run_adb(["install", "-r", "-g", apk_path])
            else:
                return False

        # 2. Enable & Set ADBKeyboard IME
        self.run_adb(["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"])
        self.run_adb(["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"])

        current_ime = self.run_adb(["shell", "settings get secure default_input_method"]).strip()
        return "com.android.adbkeyboard" in current_ime

    def check_connection(self):
        """Verifies Wireless ADB connection and ensures ADBKeyboard is active."""
        # 1. First check if any Wi-Fi device is already active
        detected_id, conn_type = self.auto_detect_device()
        if detected_id:
            self.device_id = detected_id
            self.connection_type = conn_type
        else:
            # 2. If not active, but target device_id has an IP:Port, attempt to connect
            if self.device_id and ":" in self.device_id:
                if not self.connect_wifi(self.device_id):
                    return False
            else:
                return False

        # 3. Ensure ADBKeyboard is enabled and active
        current_ime = self.run_adb(["shell", "settings get secure default_input_method"]).strip()
        if "com.android.adbkeyboard" not in current_ime:
            self.run_adb(["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"])
            self.run_adb(["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"])

        return True

    def dump_ui(self, tmp_path="/data/local/tmp/window_dump.xml", compressed=True):
        """Captures compressed uiautomator dump to file and returns XML string."""
        self.run_adb(["shell", f"rm -f {tmp_path}"])
        cmd = ["shell", "uiautomator", "dump"]
        if compressed:
            cmd.append("--compressed")
        cmd.append(tmp_path)
        self.run_adb(cmd)
        xml_str = self.run_adb(["shell", f"cat {tmp_path}"])
        return xml_str

    def tap(self, x, y):
        """Simulates touchscreen tap."""
        self.last_action_time = time.time()
        res = self.run_adb(["shell", f"input tap {int(x)} {int(y)}"])
        self.last_action_time = time.time()
        return res

    def keyevent(self, keycode):
        """Sends an Android KEYCODE (e.g., 4 for BACK)."""
        self.last_action_time = time.time()
        res = self.run_adb(["shell", f"input keyevent {keycode}"])
        self.last_action_time = time.time()
        return res

    def send_unicode_text(self, text):
        """Broadcasts base64-encoded Unicode string to ADBKeyboard."""
        self.last_action_time = time.time()
        b64_msg = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        res = self.run_adb(["shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_msg])
        self.last_action_time = time.time()
        return res

    def take_screenshot(self):
        """Captures device screen as raw PNG bytes."""
        return self.run_adb(["exec-out", "screencap", "-p"], binary=True)

    def pull_file(self, remote_path, local_path):
        """Pulls a remote file to a local destination."""
        self.run_adb(["pull", remote_path, local_path])
        return os.path.exists(local_path)
