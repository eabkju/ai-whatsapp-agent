import re
import os
import time
import base64
import tempfile

class AudioAgent:
    def __init__(self, adb_client, search_paths=None):
        self.adb = adb_client
        self.search_paths = search_paths or [
            "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Voice Notes/",
            "/sdcard/WhatsApp/Media/WhatsApp Voice Notes/"
        ]

    def detect_voice_note(self, root_node):
        """
        Inspects UI XML tree to locate any incoming voice notes / audio messages.
        Returns: play_button_coords tuple (x, y) or None
        """
        play_coords = None
        for node in root_node.iter("node"):
            rid = node.attrib.get("resource-id", "")
            cdesc = node.attrib.get("content-desc", "").lower()

            is_audio_bubble = (
                "conversation_row_audio" in rid or
                "voice_note" in rid or
                "play_pause_btn" in rid or
                "play" in cdesc and "audio" in cdesc or
                "voice message" in cdesc
            )

            if is_audio_bubble:
                bounds_str = node.attrib.get("bounds", "")
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    # Incoming messages are generally left-aligned (x1 < 400)
                    if x1 < 400:
                        play_coords = ((x1 + x2) // 2, (y1 + y2) // 2)
                        break

        return play_coords

    def play_voice_note(self, play_coords):
        """Taps the play button on the voice message bubble in the UI."""
        if play_coords:
            self.adb.tap(play_coords[0], play_coords[1])
            time.sleep(0.5)
            return True
        return False

    def fetch_latest_voice_note(self):
        """
        Finds and pulls the most recent incoming WhatsApp .opus voice note file from device.
        Returns Base64 audio string or None.
        """
        latest_file = None
        for p in self.search_paths:
            # Query the newest .opus file recursively
            cmd = ["shell", f"find '{p}' -type f -name '*.opus' -exec ls -td {{}} + 2>/dev/null | head -n 1"]
            res = self.adb.run_adb(cmd).strip()
            if res and res.endswith(".opus"):
                latest_file = res
                break

        if not latest_file:
            # Fallback: check ls on directory
            for p in self.search_paths:
                cmd = ["shell", f"ls -t '{p}'*/*.opus 2>/dev/null | head -n 1"]
                res = self.adb.run_adb(cmd).strip()
                if res and res.endswith(".opus"):
                    latest_file = res
                    break

        if not latest_file:
            return None

        tmp_dir = "/tmp" if os.access("/tmp", os.W_OK) else tempfile.gettempdir()
        local_tmp = os.path.join(tmp_dir, "wa_latest_voice.opus")
        if os.path.exists(local_tmp):
            try: os.remove(local_tmp)
            except Exception: pass

        success = self.adb.pull_file(latest_file, local_tmp)
        if success and os.path.exists(local_tmp) and os.path.getsize(local_tmp) > 0:
            try:
                with open(local_tmp, "rb") as f:
                    b64_audio = base64.b64encode(f.read()).decode("utf-8")
                return b64_audio
            except Exception:
                return None
            finally:
                if os.path.exists(local_tmp):
                    try: os.remove(local_tmp)
                    except Exception: pass

        return None
