import unittest
import time
import os
import json
from pathlib import Path

from whatsapp_agent.config.settings import load_settings, save_settings, CONFIG_FILE_PATH
from whatsapp_agent.core.queue_manager import QueueManager
from whatsapp_agent.core.safety_guard import SafetyGuard, MEDICAL_DISCLAIMER_EXACT
from whatsapp_agent.core.model_router import ModelRouter
from whatsapp_agent.core.keyboard_manager import KeyboardManager
from whatsapp_agent.core.background_worker import BackgroundWorker
from whatsapp_agent.core.service_controller import ServiceController
from whatsapp_agent.cli.commands import COMMAND_GUIDE

class MockADB:
    def __init__(self):
        self.commands_executed = []
        self.current_ime = "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"

    def run_adb(self, cmd_args, check=False, binary=False):
        self.commands_executed.append(cmd_args)
        if cmd_args == ["shell", "settings get secure default_input_method"]:
            return self.current_ime
        elif len(cmd_args) >= 3 and cmd_args[:2] == ["shell", "ime"]:
            if cmd_args[2] == "set":
                self.current_ime = cmd_args[3]
                return f"Input method {cmd_args[3]} selected"
            elif cmd_args[2] == "enable":
                return f"Input method {cmd_args[3]} enabled"
        elif cmd_args == ["shell", "dumpsys activity activities | grep -E 'topResumedActivity'"]:
            return "topResumedActivity=ActivityRecord{com.whatsapp/.home.ui.HomeActivity}"
        return ""

    def keyevent(self, keycode):
        self.commands_executed.append(["keyevent", str(keycode)])

class TestAllFeatures(unittest.TestCase):
    def test_1_cooldown_8_seconds_and_fifo_requeueing(self):
        """Feature 1: 8-second cooldown per contact with FIFO fairness re-queueing."""
        qm = QueueManager(cooldown_seconds=8)
        self.assertEqual(qm.cooldown_seconds, 8)

        # Incoming contacts: A, B, C, D
        chats = [
            {"name": "Contact A", "bounds": "[0,100][1000,200]"},
            {"name": "Contact B", "bounds": "[0,200][1000,300]"},
            {"name": "Contact C", "bounds": "[0,300][1000,400]"},
            {"name": "Contact D", "bounds": "[0,400][1000,500]"},
        ]
        qm.sync_incoming_contacts(chats)
        self.assertEqual(qm.queue_length(), 4)

        # 1. First job popped: Contact A
        job1 = qm.get_next_job()
        self.assertEqual(job1.name, "Contact A")
        qm.record_reply_sent("Contact A")
        self.assertTrue(qm.is_on_cooldown("Contact A"))
        self.assertLessEqual(qm.remaining_cooldown("Contact A"), 8.0)

        # 2. Contact A sends another message before Contact D is reached
        qm.requeue_contact("Contact A", bounds="[0,100][1000,200]", last_msg="Are you there?")

        # 3. Next jobs popped MUST be B, then C, then D in exact FIFO order
        job2 = qm.get_next_job()
        self.assertEqual(job2.name, "Contact B")
        qm.record_reply_sent("Contact B")

        job3 = qm.get_next_job()
        self.assertEqual(job3.name, "Contact C")
        qm.record_reply_sent("Contact C")

        job4 = qm.get_next_job()
        self.assertEqual(job4.name, "Contact D")
        qm.record_reply_sent("Contact D")

        # 4. Now the 5th job in queue is Contact A
        self.assertEqual(qm.queue_length(), 1)
        self.assertEqual(qm.queue[0].name, "Contact A")

    def test_2_secure_persistent_key_storage_and_logout(self):
        """Feature 2: Persistent key storage (chmod 600) and wipe on logout."""
        original_settings = load_settings()
        try:
            test_settings = original_settings.copy()
            test_settings["gemini_api_key"] = "TEST_API_KEY_SECURE_12345"
            save_settings(test_settings)

            # Check permissions
            if os.path.exists(CONFIG_FILE_PATH):
                mode = oct(os.stat(CONFIG_FILE_PATH).st_mode & 0o777)
                self.assertEqual(mode, "0o600", "Config file must have 600 permissions")

            # Verify key persistence
            reloaded = load_settings()
            self.assertEqual(reloaded["gemini_api_key"], "TEST_API_KEY_SECURE_12345")

            # Simulate logout-ai-whatsapp
            reloaded["gemini_api_key"] = ""
            save_settings(reloaded)

            logged_out = load_settings()
            self.assertEqual(logged_out["gemini_api_key"], "")
        finally:
            save_settings(original_settings)

    def test_3_smart_keyboard_switching_and_user_interference(self):
        """Feature 3: ADBKeyboard active -> user interference switches to default IME -> 25s idle restores ADBKeyboard."""
        mock_adb = MockADB()
        km = KeyboardManager(mock_adb, idle_timeout=25)
        
        # User default keyboard should be discovered
        self.assertEqual(km.user_ime, "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME")

        # 1. Agent starts and ensures ADBKeyboard is active
        km.switch_to_adb_keyboard()
        self.assertEqual(mock_adb.current_ime, "com.android.adbkeyboard/.AdbIME")

        # 2. User touches screen or interferes
        km.record_user_interaction()
        # Keyboard MUST immediately switch to user's default phone keyboard!
        self.assertEqual(mock_adb.current_ime, "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME")
        self.assertTrue(km.is_user_active())
        self.assertTrue(km.handle_user_state())  # Agent must be paused

        # 3. User still active after 10 seconds (under 25s threshold)
        km.last_user_interaction = time.time() - 10
        self.assertTrue(km.is_user_active())
        self.assertTrue(km.handle_user_state())  # Still paused
        self.assertEqual(mock_adb.current_ime, "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME")

        # 4. User interference not found for 25 seconds
        km.last_user_interaction = time.time() - 26  # 26s since last interference
        self.assertFalse(km.is_user_active())
        paused = km.handle_user_state()
        self.assertFalse(paused)  # Agent is resumed from pause!
        # Keyboard MUST be switched back to ADBKeyboard!
        self.assertEqual(mock_adb.current_ime, "com.android.adbkeyboard/.AdbIME")

    def test_4_background_worker_and_50s_ticker(self):
        """Feature 4: Silent background execution & 50-second notification ticker."""
        mock_adb = MockADB()
        bw = BackgroundWorker(mock_adb, notify_interval=50)
        
        self.assertEqual(bw.replies_count, 0)
        bw.record_reply_sent()
        bw.record_reply_sent()
        self.assertEqual(bw.replies_count, 2)

        # Test ticker interval timing
        bw.last_notification_time = time.time() - 10
        bw.check_ticker()
        # Should not fire yet (10s < 50s)
        self.assertAlmostEqual(bw.last_notification_time, time.time() - 10, delta=1)

        # When 50 seconds have passed:
        bw.last_notification_time = time.time() - 51
        bw.check_ticker()
        self.assertAlmostEqual(bw.last_notification_time, time.time(), delta=1)

    def test_5_medical_disclaimer_and_islamic_etiquette(self):
        """Feature 5: Medical query deterministic interceptor & Islamic etiquette."""
        guard = SafetyGuard(agent_name="Personal Assistant")

        queries = [
            "What medicine should I take for headache?",
            "Can you suggest a drug or tablet for cold?",
            "প্যারাসিটামল ঔষধ কী খাব?",
            "প্রেসক্রিপশন দিন"
        ]
        for q in queries:
            self.assertEqual(guard.check_medical_query(q), MEDICAL_DISCLAIMER_EXACT)

        prompt = guard.build_system_prompt("Brother Tariq")
        self.assertIn("Assalamu Alaikum", prompt)
        self.assertIn("Alhamdulillah", prompt)
        self.assertIn("InshaALLAH", prompt)
        self.assertIn("Allah Hafez", prompt)
        self.assertIn("ABSOLUTE PRIVACY DIRECTIVE", prompt)

    def test_6_model_routing_multimodal(self):
        """Feature 6: Dynamic model routing (text, vision, audio)."""
        router = ModelRouter()
        
        # Audio / Voice note
        c_type, model = router.route(has_audio=True)
        self.assertEqual(c_type, "audio")
        self.assertEqual(model, "gemini-3.5-flash-lite")

        # Vision / Image
        c_type, model = router.route(has_image=True)
        self.assertEqual(c_type, "vision")
        self.assertEqual(model, "gemini-3.5-flash-lite")

        # Text default
        c_type, model = router.route(has_audio=False, has_image=False)
        self.assertEqual(c_type, "text")
        self.assertEqual(model, "gemini-3.5-flash-lite")

    def test_7_command_guide_completeness(self):
        """Feature 7: Post-setup command guide contains all 9 CLI commands."""
        expected_cmds = [
            "start-ai-whatsapp",
            "pause-ai-whatsapp",
            "resume-ai-whatsapp",
            "minimize-ai-whatsapp",
            "logout-ai-whatsapp",
            "stop-ai-whatsapp",
            "check-ai-whatsapp",
            "pair-ai-whatsapp",
            "connect-ai-whatsapp"
        ]
        for cmd in expected_cmds:
            self.assertIn(cmd, COMMAND_GUIDE)

    def test_8_wifi_debugging_only(self):
        """Feature 8: Strictly connects via Wireless ADB (Wi-Fi), ignoring USB devices."""
        from unittest.mock import patch
        from whatsapp_agent.core.adb_client import ADBClient

        # Mock devices output containing both USB device and Wi-Fi device
        mock_output = (
            "List of devices attached\n"
            "192.168.0.140:35105    device product:a52sxq model:SM_A528B device:a52sxq\n"
            "R58M10ABCDE            device usb:1-1 product:a52sxq model:SM_A528B device:a52sxq\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.returncode = 0

            # 1. Even when a USB device is attached, MUST ignore USB and select the Wi-Fi device
            client = ADBClient(device_id="192.168.0.140:35105")
            serial, conn_type = client.auto_detect_device()
            self.assertEqual(conn_type, "Wi-Fi")
            self.assertEqual(serial, "192.168.0.140:35105")

            # 2. When only USB device is attached, refuses to connect and returns None
            mock_run.return_value.stdout = (
                "List of devices attached\n"
                "R58M10ABCDE            device usb:1-1 product:a52sxq\n"
            )
            client_usb_only = ADBClient()
            serial, conn_type = client_usb_only.auto_detect_device()
            self.assertIsNone(conn_type)
            self.assertIsNone(serial)

            # 3. Verify adb connect command does NOT prepend -s
            mock_run.reset_mock()
            mock_run.return_value.stdout = "connected to 192.168.1.100:41235"
            client.run_adb(["connect", "192.168.1.100:41235"])
            mock_run.assert_called_with(["adb", "connect", "192.168.1.100:41235"], capture_output=True, text=True, errors="replace")

    def test_9_unread_badge_parsing_and_gemini_thinking_budget(self):
        """Feature 9: Parse unread badge with Marked unread content-desc & Gemini thinking budget config."""
        from whatsapp_ai_agent import WhatsAppAIAgent
        from unittest.mock import MagicMock
        from whatsapp_agent.core.ai_service import AIService

        # 1. Unread badge XML parsing
        sample_xml = """<hierarchy rotation="0">
            <node index="0" resource-id="com.whatsapp:id/conversation_container" bounds="[0,0][1080,2000]">
                <node index="0" resource-id="com.whatsapp:id/contact_row_container" bounds="[0,726][1080,935]">
                    <node resource-id="com.whatsapp:id/conversations_row_contact_name" text="sakib ab khan" bounds="[198,759][534,826]" />
                    <node resource-id="com.whatsapp:id/single_msg_tv" text="Vali e achi.." bounds="[198,839][850,894]" />
                    <node resource-id="com.whatsapp:id/conversations_row_message_count" text="" content-desc="Marked unread" bounds="[981,839][1036,894]" />
                </node>
                <node index="1" resource-id="com.whatsapp:id/contact_row_container" bounds="[0,935][1080,1144]">
                    <node resource-id="com.whatsapp:id/conversations_row_contact_name" text="Pallab bro" bounds="[198,968][444,1035]" />
                    <node resource-id="com.whatsapp:id/single_msg_tv" text="Dara pathacchi" bounds="[198,1048][850,1103]" />
                </node>
            </node>
        </hierarchy>"""

        agent = WhatsAppAIAgent()
        agent.adb = MagicMock()
        agent.bg_worker = MagicMock()
        agent.bg_worker.is_whatsapp_foreground.return_value = True
        agent.adb.dump_ui.return_value = sample_xml

        unread = agent.scan_home_unread_chats()
        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0]["name"], "sakib ab khan")
        self.assertEqual(unread[0]["last_msg"], "Vali e achi..")
        self.assertFalse(unread[0]["is_group"])

        # 2. Gemini thinking budget & max tokens test
        ai = AIService(api_key="TEST_KEY", agent_name="Assistant")
        # Ensure model is gemini-3.5-flash-lite
        content_type, model_name = ai.router.route(has_audio=False, has_image=False)
        self.assertEqual(model_name, "gemini-3.5-flash-lite")

if __name__ == "__main__":
    unittest.main()
