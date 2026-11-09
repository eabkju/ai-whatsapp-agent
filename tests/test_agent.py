import unittest
import time
import os
import tempfile
from whatsapp_agent.core.queue_manager import QueueManager
from whatsapp_agent.core.safety_guard import SafetyGuard, MEDICAL_DISCLAIMER_EXACT
from whatsapp_agent.core.model_router import ModelRouter
from whatsapp_agent.core.service_controller import ServiceController

class TestWhatsAppAIAgent(unittest.TestCase):
    def test_queue_fairness_and_cooldown(self):
        """Tests Req 1 & Req 3: 25s cooldown and dynamic FIFO fairness re-queueing."""
        qm = QueueManager(cooldown_seconds=25)
        
        # Incoming contacts: A, B, C, D
        chats = [
            {"name": "Contact A", "bounds": "[0,100][1000,200]"},
            {"name": "Contact B", "bounds": "[0,200][1000,300]"},
            {"name": "Contact C", "bounds": "[0,300][1000,400]"},
            {"name": "Contact D", "bounds": "[0,400][1000,500]"},
        ]
        qm.sync_incoming_contacts(chats)
        self.assertEqual(qm.queue_length(), 4)

        # 1. First job popped should be Contact A
        job1 = qm.get_next_job()
        self.assertIsNotNone(job1)
        self.assertEqual(job1.name, "Contact A")

        # Record reply sent to Contact A (starts 25s cooldown)
        qm.record_reply_sent("Contact A")
        self.assertTrue(qm.is_on_cooldown("Contact A"))
        self.assertGreater(qm.remaining_cooldown("Contact A"), 20)

        # 2. While B, C, D are waiting, Contact A sends another message!
        # Re-queue Contact A
        qm.requeue_contact("Contact A", bounds="[0,100][1000,200]", last_msg="Hey again")

        # 3. Next job must be Contact B, then Contact C, then Contact D
        job2 = qm.get_next_job()
        self.assertEqual(job2.name, "Contact B")
        qm.record_reply_sent("Contact B")

        job3 = qm.get_next_job()
        self.assertEqual(job3.name, "Contact C")
        qm.record_reply_sent("Contact C")

        job4 = qm.get_next_job()
        self.assertEqual(job4.name, "Contact D")
        qm.record_reply_sent("Contact D")

        # 4. Now the 5th job in queue must be Contact A!
        # (Once cooldown expires or if checked in queue)
        self.assertEqual(qm.queue_length(), 1)
        self.assertEqual(qm.queue[0].name, "Contact A")

    def test_medical_disclaimer_interceptor(self):
        """Tests Req 9: Exact medical disclaimer returned deterministically."""
        guard = SafetyGuard(agent_name="Personal Assistant")

        test_queries = [
            "Can you suggest some medicine for my headache?",
            "What drug should I take for fever?",
            "Which antibiotic tablet is good?",
            "Please prescribe a cough syrup for me",
            "মাথাব্যথার জন্য কোন ওষুধ খাব?",
            "প্যারাসিটামল ঔষধ কী খাব?"
        ]

        for q in test_queries:
            resp = guard.check_medical_query(q)
            self.assertEqual(
                resp,
                MEDICAL_DISCLAIMER_EXACT,
                f"Failed to trigger medical disclaimer for query: {q}"
            )

        # Regular conversational queries should NOT trigger medical disclaimer
        non_medical = [
            "Assalamu Alaikum! How are you doing today?",
            "Will we meet tomorrow at the office?",
            "Alhamdulillah, finished the project."
        ]
        for q in non_medical:
            resp = guard.check_medical_query(q)
            self.assertIsNone(resp, f"False positive for medical query: {q}")

    def test_system_prompt_privacy_and_islamic_tone(self):
        """Tests Req 7 & Req 8: Cross-contact privacy directive & Islamic greetings."""
        guard = SafetyGuard(agent_name="Zayan AI")
        prompt = guard.build_system_prompt("Rafiq")

        # Privacy directive test
        self.assertIn("ABSOLUTE PRIVACY DIRECTIVE", prompt)
        self.assertIn("MUST NEVER disclose any information", prompt)
        self.assertIn("I am sorry, I do not have access to any other conversations", prompt)

        # Islamic etiquette test
        self.assertIn("Assalamu Alaikum", prompt)
        self.assertIn("Alhamdulillah", prompt)
        self.assertIn("InshaALLAH", prompt)
        self.assertIn("Allah Hafez", prompt)
        self.assertIn("NEVER use any offensive slangs", prompt)

    def test_model_router(self):
        """Tests Req 10 & Dynamic Model Router."""
        router = ModelRouter()
        
        # Audio priority
        c_type, model = router.route(has_audio=True, has_image=True)
        self.assertEqual(c_type, "audio")
        self.assertEqual(model, "gemini-3.5-flash")

        # Vision priority
        c_type, model = router.route(has_audio=False, has_image=True)
        self.assertEqual(c_type, "vision")
        self.assertEqual(model, "gemini-3.5-flash")

        # Text default
        c_type, model = router.route(has_audio=False, has_image=False)
        self.assertEqual(c_type, "text")
        self.assertEqual(model, "gemini-3.5-flash")

    def test_service_controller_states(self):
        """Tests Req 11b: Service states and pause/resume logic."""
        tmp_dir = "/tmp" if os.access("/tmp", os.W_OK) else tempfile.gettempdir()
        pid_file = os.path.join(tmp_dir, "test_agent.pid")
        state_file = os.path.join(tmp_dir, "test_agent.state")
        ctrl = ServiceController(pid_file=pid_file, state_file=state_file)
        ctrl.set_state("RUNNING")
        self.assertEqual(ctrl.get_state(), "RUNNING")
        
        ctrl.set_state("PAUSED")
        self.assertEqual(ctrl.get_state(), "PAUSED")
        
        ctrl.set_state("STOPPED")
        self.assertEqual(ctrl.get_state(), "STOPPED")

if __name__ == "__main__":
    unittest.main()
