import re
import os
import subprocess
import base64

class VisionAgent:
    def __init__(self, adb_client):
        self.adb = adb_client

    def detect_image_bubble(self, root_node):
        """
        Inspects UI XML tree to locate any incoming image/media bubbles.
        Returns: bounds tuple (x1, y1, x2, y2) or None
        """
        image_bounds = None
        for node in root_node.iter("node"):
            rid = node.attrib.get("resource-id", "")
            cdesc = node.attrib.get("content-desc", "").lower()
            cls = node.attrib.get("class", "")

            # Identify image view widgets in WhatsApp messages
            is_image = False
            if "image_view" in rid or "thumb" in rid or "media_message" in rid:
                is_image = True
            elif "photo" in cdesc or "image" in cdesc:
                is_image = True
            elif cls == "android.widget.ImageView" and ("media" in rid or "content" in rid):
                is_image = True

            if is_image:
                bounds_str = node.attrib.get("bounds", "")
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    # Check if incoming (left-aligned bubble, x1 < 350) and reasonable size
                    if (x2 - x1) > 100 and (y2 - y1) > 100 and x1 < 350:
                        image_bounds = (x1, y1, x2, y2)
                        break

        return image_bounds

    def extract_image_base64(self, bounds=None):
        """
        Captures device screenshot and crops the image bubble using ffmpeg.
        Returns base64 encoded string of PNG or None.
        """
        raw_png = self.adb.take_screenshot()
        if not raw_png:
            return None

        tmp_raw = "/tmp/wa_raw_screen.png"
        tmp_crop = "/tmp/wa_crop_image.png"

        with open(tmp_raw, "wb") as f:
            f.write(raw_png)

        if bounds:
            x1, y1, x2, y2 = bounds
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            # Use ffmpeg to crop exact bounding box
            try:
                cmd = [
                    "ffmpeg", "-y", "-i", tmp_raw,
                    "-vf", f"crop={w}:{h}:{x1}:{y1}",
                    tmp_crop
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                target_file = tmp_crop
            except Exception:
                target_file = tmp_raw
        else:
            target_file = tmp_raw

        try:
            with open(target_file, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
            return b64_data
        except Exception:
            return None
        finally:
            if os.path.exists(tmp_raw):
                try: os.remove(tmp_raw)
                except Exception: pass
            if os.path.exists(tmp_crop):
                try: os.remove(tmp_crop)
                except Exception: pass
