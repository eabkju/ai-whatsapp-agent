#!/usr/bin/env python3
"""
WhatsApp AI Auto-Reply Agent for Android via ADB (v2.1)
- 8-Second Fast Rate-Limiting Cooldown per contact with FIFO Fairness
- Smart Keyboard Switching: ADBKeyboard for typing, user default keyboard restored immediately
- User Interference Detection with 10-20s Idle Reset
- Non-Intrusive Background Execution (No forced pop-ups) & 50-Second Notification Ticker
- Deterministic Medical Disclaimer & Islamic Etiquette
- Multimodal Vision & Audio (Voice Notes playback & ingestion) via Gemini
- Phone Call Auto-Pause & Screen Lock Suspend / Auto-Resume
- CLI Suite: start, pause, resume, stop, minimize, logout, check-ai-whatsapp
"""

import sys
import os
import time
import re
import xml.etree.ElementTree as ET

from whatsapp_agent.config.settings import load_settings, save_settings
from whatsapp_agent.core.adb_client import ADBClient
from whatsapp_agent.core.device_guard import DeviceGuard
from whatsapp_agent.core.keyboard_manager import KeyboardManager
from whatsapp_agent.core.background_worker import BackgroundWorker
from whatsapp_agent.core.queue_manager import QueueManager
from whatsapp_agent.core.safety_guard import SafetyGuard
from whatsapp_agent.core.vision_agent import VisionAgent
from whatsapp_agent.core.audio_agent import AudioAgent
from whatsapp_agent.core.ai_service import AIService
from whatsapp_agent.core.service_controller import ServiceController

GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

class WhatsAppAIAgent:
    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        self.device_id = self.settings.get("device_id", "")
        self.gemini_key = self.settings.get("gemini_api_key", os.environ.get("GEMINI_API_KEY", ""))
        self.agent_name = self.settings.get("agent_name", "Personal AI Assistant")
        self.cooldown_seconds = self.settings.get("cooldown_seconds", 8)
        self.user_idle_timeout = self.settings.get("user_idle_timeout", 25)
        self.bg_notify_interval = self.settings.get("bg_notify_interval", 50)
        self.poll_interval = self.settings.get("poll_interval", 0.8)
        self.idle_poll_interval = self.settings.get("idle_poll_interval", 1.5)
        self.ignore_groups = self.settings.get("ignore_groups", True)
        self.auto_send = self.settings.get("auto_send", True)
        self.ui_coords = self.settings.get("ui_coords", {})

        # Subsystems
        self.adb = ADBClient(device_id=self.device_id)
        self.guard = DeviceGuard(self.adb)
        self.keyboard_mgr = KeyboardManager(
            self.adb,
            idle_timeout=self.user_idle_timeout,
            user_ime=self.settings.get("user_ime")
        )
        self.bg_worker = BackgroundWorker(self.adb, notify_interval=self.bg_notify_interval)
        self.queue_mgr = QueueManager(cooldown_seconds=self.cooldown_seconds)
        self.vision = VisionAgent(self.adb)
        self.audio = AudioAgent(self.adb, search_paths=self.settings.get("voice_notes_paths"))
        self.ai = AIService(
            api_key=self.gemini_key,
            agent_name=self.agent_name,
            model_config=self.settings.get("models")
        )
        self.controller = ServiceController(
            pid_file=self.settings.get("pid_file"),
            state_file=self.settings.get("state_file")
        )

    def check_connection(self):
        return self.adb.check_connection()

    def ensure_whatsapp_foreground(self):
        """Brings WhatsApp to foreground if not currently active."""
        if not self.bg_worker.is_whatsapp_foreground():
            # Send KEYCODE_HOME first so Android switches window focus cleanly
            self.adb.keyevent(3)
            time.sleep(0.4)
            self.adb.run_adb(["shell", "am start -n com.whatsapp/.home.ui.HomeActivity"])
            time.sleep(0.8)
            if not self.bg_worker.is_whatsapp_foreground():
                self.adb.run_adb(["shell", "monkey -p com.whatsapp -c android.intent.category.LAUNCHER 1"])
                time.sleep(0.8)

    def return_to_home(self):
        """Guarantees returning to WhatsApp HomeActivity cleanly without popping up over other apps."""
        self.keyboard_mgr.record_agent_action()
        # If WhatsApp is minimized and user is elsewhere, do NOT force bring to front
        if not self.bg_worker.is_whatsapp_foreground() and self.bg_worker.is_minimized_mode:
            return True

        if not self.bg_worker.is_whatsapp_foreground():
            self.ensure_whatsapp_foreground()

        back_btn = self.ui_coords.get("back_button", [66, 176])
        for _ in range(3):
            focus = self.adb.run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus'"])
            if "com.whatsapp.home.ui.HomeActivity" in focus:
                return True
            
            # 1. Tap top-left back button
            self.adb.tap(back_btn[0], back_btn[1])
            time.sleep(0.3)

            focus = self.adb.run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus'"])
            if "com.whatsapp.home.ui.HomeActivity" in focus:
                return True

            # 2. Keycode back
            self.adb.keyevent(4)
            time.sleep(0.3)

        # Force bring HomeActivity to front if needed
        self.adb.run_adb(["shell", "am start -n com.whatsapp/.home.ui.HomeActivity"])
        time.sleep(0.6)
        return True

    def is_group_chat(self, root_node):
        """Checks if current open chat or notification is a group chat."""
        for node in root_node.iter("node"):
            rid = node.attrib.get("resource-id", "")
            text = node.attrib.get("text", "")
            if "conversation_contact_status" in rid or "subtitle" in rid:
                if "," in text or "tap here for group info" in text.lower():
                    return True
            if "group" in rid.lower():
                return True
        return False

    def scan_home_unread_chats(self):
        """
        Fast XML scan of WhatsApp home screen for unread badges.
        Returns list of unread chat info dictionaries.
        """
        if not self.bg_worker.is_whatsapp_foreground():
            if not self.bg_worker.is_minimized_mode:
                self.ensure_whatsapp_foreground()
            else:
                return []

        xml_str = self.adb.dump_ui(compressed=True)
        if not xml_str or "<hierarchy" not in xml_str:
            return []

        unread_chats = []
        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                rid = node.attrib.get("resource-id", "")
                if rid.endswith("contact_row_container"):
                    has_unread = False
                    is_group = False
                    contact_name = None
                    last_msg = ""
                    bounds = node.attrib.get("bounds", "")

                    for child in node.iter("node"):
                        c_rid = child.attrib.get("resource-id", "")
                        c_text = child.attrib.get("text", "")
                        c_desc = child.attrib.get("content-desc", "")

                        if "conversations_row_message_count" in c_rid or "unread" in c_desc.lower() or "unread" in c_text.lower():
                            has_unread = True
                        if "conversations_row_contact_name" in c_rid and c_text:
                            contact_name = c_text
                        if "single_msg_tv" in c_rid and c_text:
                            last_msg = c_text
                        if "msg_from_tv" in c_rid:
                            is_group = True

                    if has_unread and contact_name:
                        unread_chats.append({
                            "name": contact_name,
                            "is_group": is_group,
                            "last_msg": last_msg,
                            "bounds": bounds
                        })
        except Exception as e:
            pass

        return unread_chats

    def read_chat_history(self, expected_contact=None):
        """
        Fast inspection of opened chat screen.
        Extracts recent messages, checks for audio voice notes and image attachments.
        """
        xml_str = self.adb.dump_ui(compressed=True)
        messages = []
        is_group = False
        contact_name = expected_contact or "Contact"
        image_bounds = None
        voice_play_coords = None

        if not xml_str:
            return False, contact_name, messages, None, None

        try:
            root = ET.fromstring(xml_str)
            if self.is_group_chat(root):
                return True, contact_name, [], None, None

            for node in root.iter("node"):
                rid = node.attrib.get("resource-id", "")
                text = node.attrib.get("text", "")
                if "conversation_contact_name" in rid and text:
                    contact_name = text
                    break

            # Check for multimodal content
            image_bounds = self.vision.detect_image_bubble(root)
            voice_play_coords = self.audio.detect_voice_note(root)

            for node in root.iter("node"):
                rid = node.attrib.get("resource-id", "")
                text = node.attrib.get("text", "")
                bounds = node.attrib.get("bounds", "")

                if "name_in_group" in rid:
                    return True, contact_name, [], None, None

                if "message_text" in rid and text:
                    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                    is_outgoing = False
                    if m:
                        x1 = int(m.group(1))
                        if x1 > 350:
                            is_outgoing = True
                    sender_tag = "Me" if is_outgoing else contact_name
                    messages.append(f"{sender_tag}: {text}")

        except Exception as e:
            pass

        return is_group, contact_name, messages, image_bounds, voice_play_coords

    def send_reply_text(self, text):
        """
        Smart Keyboard Typing:
        Switches to ADBKeyboard for typing, and IMMEDIATELY restores user's keyboard.
        """
        input_entry = self.ui_coords.get("input_entry", [395, 2314])
        fallback_send = self.ui_coords.get("send_fallback", [988, 2311])

        with self.keyboard_mgr.typing_session():
            # 1. Tap input box
            self.adb.tap(input_entry[0], input_entry[1])
            time.sleep(0.4)

            # 2. Broadcast Base64 Unicode text
            self.adb.send_unicode_text(text)
            time.sleep(0.8)

            # 3. Verify Send button is displayed
            xml_str = self.adb.dump_ui(compressed=True)
            send_coords = None
            has_voice_button = False

            if xml_str:
                try:
                    root = ET.fromstring(xml_str)
                    for node in root.iter("node"):
                        rid = node.attrib.get("resource-id", "")
                        cdesc = node.attrib.get("content-desc", "").lower()

                        if "id/send" in rid or cdesc == "send":
                            bounds = node.attrib.get("bounds", "")
                            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                            if m:
                                x1, y1, x2, y2 = map(int, m.groups())
                                send_coords = ((x1 + x2) // 2, (y1 + y2) // 2)
                                break

                        if "voice_note_btn" in rid or "voice message" in cdesc:
                            has_voice_button = True
                except Exception:
                    pass

            # Fast retry if voice button still pending update
            if not send_coords and has_voice_button:
                time.sleep(0.5)
                xml_str = self.adb.dump_ui(compressed=True)
                if xml_str:
                    try:
                        root = ET.fromstring(xml_str)
                        for node in root.iter("node"):
                            rid = node.attrib.get("resource-id", "")
                            cdesc = node.attrib.get("content-desc", "").lower()
                            if "id/send" in rid or cdesc == "send":
                                bounds = node.attrib.get("bounds", "")
                                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                                if m:
                                    x1, y1, x2, y2 = map(int, m.groups())
                                    send_coords = ((x1 + x2) // 2, (y1 + y2) // 2)
                                    has_voice_button = False
                                    break
                    except Exception:
                        pass

            if send_coords:
                self.adb.tap(send_coords[0], send_coords[1])
                time.sleep(0.8)
                return True
            elif has_voice_button:
                print(f"{RED}[!] SAFETY GUARD: Only Voice Note button is visible. Skipping tap.{RESET}")
                return False
            else:
                self.adb.tap(fallback_send[0], fallback_send[1])
                time.sleep(0.8)
                return True

    def process_contact_job(self, job):
        """Processes an individual contact job in the FIFO queue."""
        self.keyboard_mgr.record_agent_action()
        name = job.name
        print(f"\n{CYAN}[*] Processing chat from queue: {BOLD}{name}{RESET}")

        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", job.bounds)
        if not m:
            return False
        x1, y1, x2, y2 = map(int, m.groups())
        tap_x, tap_y = (x1 + x2) // 2, (y1 + y2) // 2

        # Open chat
        self.adb.tap(tap_x, tap_y)
        time.sleep(0.8)

        is_group, detected_name, recent_msgs, img_bounds, voice_coords = self.read_chat_history(name)

        if self.ignore_groups and is_group:
            print(f"{YELLOW}[-] Group chat detected. Skipping.{RESET}")
            self.return_to_home()
            return False

        # Multimodal handling: Voice Note
        audio_b64 = None
        if voice_coords:
            print(f"{CYAN}[*] Incoming voice note detected! Playing audio on device...{RESET}")
            self.audio.play_voice_note(voice_coords)
            time.sleep(1.0)
            audio_b64 = self.audio.fetch_latest_voice_note()

        # Multimodal handling: Image
        image_b64 = None
        if img_bounds and not audio_b64:
            print(f"{CYAN}[*] Incoming image message detected! Capturing frame...{RESET}")
            image_b64 = self.vision.extract_image_base64(bounds=img_bounds)

        if not recent_msgs and not audio_b64 and not image_b64:
            if job.last_msg:
                recent_msgs = [f"{name}: {job.last_msg}"]
            else:
                print(f"{YELLOW}[!] No recent messages to reply to.{RESET}")
                self.return_to_home()
                return False

        if recent_msgs:
            print(f"{BLUE}[Recent Messages from {name}]:{RESET}")
            for line in recent_msgs[-3:]:
                print(f"   {line}")

        # Generate Reply via AI Service
        print(f"{CYAN}[*] Generating context-aware reply...{RESET}")
        ai_reply = self.ai.generate_reply(
            contact_name=name,
            recent_messages=recent_msgs,
            image_b64=image_b64,
            audio_b64=audio_b64
        )

        if not ai_reply:
            print(f"{RED}[!] Failed to generate AI reply.{RESET}")
            self.return_to_home()
            return False

        print(f"{GREEN}[AI Generated Reply]:{RESET} {BOLD}{ai_reply}{RESET}")

        # Send Reply
        if self.auto_send:
            print(f"{CYAN}[*] Auto-sending reply to {name} via ADBKeyboard...{RESET}")
            sent = self.send_reply_text(ai_reply)
            if sent:
                self.queue_mgr.record_reply_sent(name)
                self.bg_worker.record_reply_sent()
                print(f"{GREEN}[✓] Reply sent to {name}! (Cooldown: {self.cooldown_seconds}s active){RESET}")

        # Return to home
        self.return_to_home()
        return True

    def start(self):
        self.controller.write_pid()
        self.controller.register_signals(on_stop_callback=self.return_to_home)

        print(f"\n{BOLD}{CYAN}======================================================={RESET}")
        print(f"{BOLD}{GREEN}  WhatsApp AI Agent Active (v2.1 - Smart IME & Background){RESET}")
        print(f"{BOLD}{CYAN}======================================================={RESET}")
        print(f"Connection:       {self.adb.connection_type} Debugging (Device: {self.adb.device_id})")
        print(f"Agent Name:       {self.agent_name}")
        print(f"Cooldown Rate:    {self.cooldown_seconds}s per contact")
        print(f"Keyboard:         Smart Switch (ADBKeyboard for typing -> User IME restored)")
        print(f"User Idle Reset:  {self.user_idle_timeout}s timeout")
        print(f"Background Alert: Every {self.bg_notify_interval}s status notification")
        print(f"Safeguards:       Medical Disclaimer + Islamic Etiquette + Call/Lock Pause")
        print(f"{CYAN}Monitoring WhatsApp for incoming messages... (PID: {os.getpid()}){RESET}\n")

        # Keep screen awake and set initial keyboard to ADBKeyboard
        self.guard.prevent_screen_sleep()
        self.keyboard_mgr.switch_to_adb_keyboard()
        self.ensure_whatsapp_foreground()
        self.return_to_home()

        while True:
            try:
                # 1. 50-Second Notification Ticker check
                self.bg_worker.check_ticker()

                # 2. Check if paused via CLI signal
                if self.controller.is_paused():
                    time.sleep(1.0)
                    continue

                # 3. Check user interference:
                # If human user interferes with screen, switches keyboard to default
                # and pauses agent until no interference for 25s, then switches to ADBKeyboard and resumes.
                if self.keyboard_mgr.handle_user_state():
                    time.sleep(1.0)
                    continue

                # 4. Check if phone is locked (wait until user unlocks)
                self.guard.wait_for_screen_unlock()

                # 5. Check for active/incoming phone call (wait until call ends)
                self.guard.wait_for_call_end()

                # 6. Fast scan home screen for unread chats
                unread_chats = self.scan_home_unread_chats()
                if unread_chats:
                    # Enqueue new arrivals into fair FIFO queue
                    self.queue_mgr.sync_incoming_contacts(unread_chats)

                # 7. Fetch next job from queue
                next_job = self.queue_mgr.get_next_job()
                if next_job:
                    # Process the job
                    self.process_contact_job(next_job)

                    # ZERO-DELAY RETURN-TO-HOME SWEEP:
                    # The moment return_to_home finishes, loop immediately to check
                    # if another message arrived while replying!
                    continue

                # 8. If no jobs ready, perform sub-second sleep
                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                print(f"\n{YELLOW}[!] Agent stopped by user.{RESET}")
                break
            except Exception as e:
                print(f"{RED}[!] Error in main loop: {e}{RESET}")
                time.sleep(self.poll_interval)

        # Always restore user personal keyboard upon exiting!
        self.keyboard_mgr.restore_user_keyboard()
        self.controller.remove_pid()

def main():
    agent = WhatsAppAIAgent()
    if not agent.check_connection():
        print(f"{RED}[!] Failed to connect to device. Run 'check-ai-whatsapp' for diagnosis.{RESET}")
        sys.exit(1)
    agent.start()

if __name__ == "__main__":
    main()
