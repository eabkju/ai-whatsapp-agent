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
        test_settings = load_settings()
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

    def test_3_smart_keyboard_switching_and_user_interference(self):
        """Feature 3: ADBKeyboard for typing -> immediate user IME restoration with 15s reset."""
        mock_adb = MockADB()
        km = KeyboardManager(mock_adb, idle_timeout=15)
        
        # User default keyboard should be preserved
        self.assertEqual(km.user_ime, "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME")

        # Test typing session context manager
        with km.typing_session():
            # Inside typing session, active keyboard is ADBKeyboard
            self.assertEqual(mock_adb.current_ime, "com.android.adbkeyboard/.AdbIME")

        # Immediately after typing session exits, user keyboard MUST be restored!
        self.assertEqual(mock_adb.current_ime, "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME")

        # Test user interference detection
        self.assertFalse(km.is_user_active())
        km.record_user_interaction()
        self.assertTrue(km.is_user_active())

        # Test idle reset after timeout
        km.last_user_interaction = time.time() - 16  # 16 seconds ago
        self.assertFalse(km.is_user_active())

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
        self.assertEqual(model, "gemini-2.0-flash")

        # Vision / Image
        c_type, model = router.route(has_image=True)
        self.assertEqual(c_type, "vision")
        self.assertEqual(model, "gemini-2.0-flash")

        # Text default
        c_type, model = router.route(has_audio=False, has_image=False)
        self.assertEqual(c_type, "text")
        self.assertEqual(model, "gemini-2.5-flash")

    def test_7_command_guide_completeness(self):
        """Feature 7: Post-setup command guide contains all 7 CLI commands."""
        expected_cmds = [
            "start-ai-whatsapp",
            "pause-ai-whatsapp",
            "resume-ai-whatsapp",
            "minimize-ai-whatsapp",
            "logout-ai-whatsapp",
            "stop-ai-whatsapp",
            "check-ai-whatsapp"
        ]
        for cmd in expected_cmds:
            self.assertIn(cmd, COMMAND_GUIDE)

    def test_8_usb_debugging_priority(self):
        """Feature 8: Auto-detects USB debugging and prioritizes it over Wi-Fi."""
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

            # 1. When prefer_usb is True, MUST pick USB device R58M10ABCDE
            client = ADBClient(device_id="192.168.0.140:35105", prefer_usb=True)
            serial, conn_type = client.auto_detect_device()
            self.assertEqual(conn_type, "USB")
            self.assertEqual(serial, "R58M10ABCDE")

            # 2. When only Wi-Fi device exists, falls back to Wi-Fi
            mock_run.return_value.stdout = (
                "List of devices attached\n"
                "192.168.0.140:35105    device product:a52sxq\n"
            )
            client_wifi_only = ADBClient(device_id="192.168.0.140:35105", prefer_usb=True)
            serial, conn_type = client_wifi_only.auto_detect_device()
            self.assertEqual(conn_type, "Wi-Fi")
            self.assertEqual(serial, "192.168.0.140:35105")

if __name__ == "__main__":
    unittest.main()
