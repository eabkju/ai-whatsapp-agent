import subprocess
import time
import base64
import os

class ADBClient:
    def __init__(self, device_id=None, prefer_usb=True):
        self.device_id = device_id
        self.prefer_usb = prefer_usb
        self.connection_type = "Unknown"

    def run_adb(self, cmd_args, check=False, binary=False):
        """Executes an adb command targeting the configured device."""
        prefix = ["adb"]
        if self.device_id:
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
        Scans 'adb devices -l' and prioritizes USB Debugging over Wi-Fi/Wireless ADB.
        Returns: (device_serial, connection_type) or (None, None)
        """
        try:
            res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, errors="replace")
            lines = res.stdout.strip().splitlines()[1:]
        except Exception:
            return None, None

        usb_devices = []
        wifi_devices = []

        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                # Identify USB devices (hardware serial or contains usb: transport)
                if "usb:" in line or ":" not in serial:
                    usb_devices.append(serial)
                else:
                    wifi_devices.append(serial)

        # Prioritize USB if available and requested
        if self.prefer_usb and usb_devices:
            self.device_id = usb_devices[0]
            self.connection_type = "USB"
            return self.device_id, "USB"

        # Otherwise fallback to Wi-Fi devices
        if wifi_devices:
            # If user configured a specific Wi-Fi device that is online, prefer it
            if self.device_id and self.device_id in wifi_devices:
                self.connection_type = "Wi-Fi"
                return self.device_id, "Wi-Fi"
            self.device_id = wifi_devices[0]
            self.connection_type = "Wi-Fi"
            return self.device_id, "Wi-Fi"

        # If USB exists but prefer_usb was False, use USB as fallback
        if usb_devices:
            self.device_id = usb_devices[0]
            self.connection_type = "USB"
            return self.device_id, "USB"

        return None, None

    def check_connection(self):
        """Verifies ADB connection (prioritizing USB) and ensures ADBKeyboard is active."""
        # 1. First attempt to auto-detect any connected USB device
        detected_id, conn_type = self.auto_detect_device()
        if detected_id:
            self.device_id = detected_id
            self.connection_type = conn_type
        else:
            # 2. If no USB device is connected and we have a Wi-Fi target IP:Port, try adb connect
            if self.device_id and ":" in self.device_id:
                self.run_adb(["connect", self.device_id])
                time.sleep(1.5)
                detected_id, conn_type = self.auto_detect_device()
                if not detected_id:
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
        self.run_adb(["shell", f"input tap {int(x)} {int(y)}"])

    def keyevent(self, keycode):
        """Sends an Android KEYCODE (e.g., 4 for BACK)."""
        self.run_adb(["shell", f"input keyevent {keycode}"])

    def send_unicode_text(self, text):
        """Broadcasts base64-encoded Unicode string to ADBKeyboard."""
        b64_msg = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        self.run_adb(["shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_msg])

    def take_screenshot(self):
        """Captures device screen as raw PNG bytes."""
        return self.run_adb(["exec-out", "screencap", "-p"], binary=True)

    def pull_file(self, remote_path, local_path):
        """Pulls a remote file to a local destination."""
        self.run_adb(["pull", remote_path, local_path])
        return os.path.exists(local_path)
