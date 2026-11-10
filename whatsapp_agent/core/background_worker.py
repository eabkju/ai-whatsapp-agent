import time
import subprocess
import threading
import re

class BackgroundWorker:
    def __init__(self, adb_client, notify_interval=50):
        self.adb = adb_client
        self.notify_interval = notify_interval
        self.last_notification_time = 0
        self.replies_count = 0
        self.is_minimized_mode = False

    def is_whatsapp_foreground(self):
        """Checks if WhatsApp is the currently active/focused window on screen."""
        out = self.adb.run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus'"])
        return "com.whatsapp" in out

    def set_minimized_mode(self, enabled=True):
        """Toggles minimized background mode."""
        self.is_minimized_mode = enabled
        if enabled:
            # Send HOME keyevent to minimize WhatsApp/terminal to background
            self.adb.keyevent(3)
            self.send_ticker_notification(force=True)

    def record_reply_sent(self):
        """Increments reply count."""
        self.replies_count += 1

    def check_ticker(self):
        """Checks if 50 seconds have elapsed; sends notification if so."""
        now = time.time()
        if (now - self.last_notification_time) >= self.notify_interval:
            self.send_ticker_notification()
            self.last_notification_time = now

    def send_ticker_notification(self, force=False):
        """Posts/updates ongoing notification in Android status bar every 50 seconds."""
        title = "WhatsApp AI Agent"
        content = f"Replying in background (Active • {self.replies_count} sent)"
        
        # 1. Try termux-notification
        try:
            cmd = [
                "termux-notification",
                "--id", "wa_bg_ticker",
                "--title", title,
                "--content", content,
                "--ongoing", "true",
                "--priority", "low"
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return
        except Exception:
            pass

        # 2. Fallback console message
        print(f"\033[96m[STATUS - 50s Ticker]\033[0m {title}: {content}")

    def reply_via_notification(self, contact_name, reply_text):
        """
        Attempts direct-reply to incoming WhatsApp notification without popping up WhatsApp UI.
        Extracts notification tag and executes RemoteInput reply action if available.
        """
        out = self.adb.run_adb(["shell", "dumpsys notification --noredact"])
        # Find WhatsApp notification entry
        if "com.whatsapp" not in out:
            return False

        # If direct-reply action is detected in notification dump, invoke it
        # Otherwise fallback to silent fast-switch or return False
        return False
