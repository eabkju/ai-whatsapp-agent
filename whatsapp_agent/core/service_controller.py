import os
import signal
import sys
import json
import tempfile

def _get_default_temp_dir():
    if os.access("/tmp", os.W_OK):
        return "/tmp"
    return tempfile.gettempdir()

class ServiceController:
    def __init__(self, pid_file=None, state_file=None):
        tmp_dir = _get_default_temp_dir()
        self.pid_file = pid_file or os.path.join(tmp_dir, "whatsapp_ai_agent.pid")
        self.state_file = state_file or os.path.join(tmp_dir, "whatsapp_ai_agent.state")
        self.paused = False

    def write_pid(self):
        """Writes current process PID to file."""
        pid = os.getpid()
        with open(self.pid_file, "w") as f:
            f.write(str(pid))
        self.set_state("RUNNING")

    def remove_pid(self):
        """Cleans up PID and state files."""
        if os.path.exists(self.pid_file):
            try: os.remove(self.pid_file)
            except Exception: pass
        self.set_state("STOPPED")

    @classmethod
    def get_running_pid(cls, pid_file=None):
        """Checks if daemon PID is active."""
        if not pid_file:
            pid_file = os.path.join(_get_default_temp_dir(), "whatsapp_ai_agent.pid")
        if not os.path.exists(pid_file):
            return None
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            # Check if process is running
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            return None

    def set_state(self, state_str):
        try:
            with open(self.state_file, "w") as f:
                json.dump({"state": state_str, "pid": os.getpid()}, f)
        except Exception:
            pass

    def get_state(self):
        if not os.path.exists(self.state_file):
            return "STOPPED"
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return data.get("state", "UNKNOWN")
        except Exception:
            return "UNKNOWN"

    def register_signals(self, on_stop_callback=None):
        """Attaches handlers for SIGUSR1 (pause), SIGUSR2 (resume), and SIGTERM."""
        def handle_pause(signum, frame):
            self.paused = True
            self.set_state("PAUSED")
            print("\n\033[93m[*] Received PAUSE signal (SIGUSR1). Agent is now paused.\033[0m")

        def handle_resume(signum, frame):
            self.paused = False
            self.set_state("RUNNING")
            print("\n\033[92m[*] Received RESUME signal (SIGUSR2). Agent resumed.\033[0m")

        def handle_terminate(signum, frame):
            print("\n\033[91m[*] Received STOP signal. Gracefully exiting...\033[0m")
            if on_stop_callback:
                on_stop_callback()
            self.remove_pid()
            sys.exit(0)

        # Register signals (available on Linux / Android Termux)
        try:
            signal.signal(signal.SIGUSR1, handle_pause)
            signal.signal(signal.SIGUSR2, handle_resume)
            signal.signal(signal.SIGTERM, handle_terminate)
            signal.signal(signal.SIGINT, handle_terminate)
        except Exception as e:
            print(f"[!] Warning registering IPC signals: {e}")

    def is_paused(self):
        return self.paused
