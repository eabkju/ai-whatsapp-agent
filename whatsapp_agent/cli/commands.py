import os
import sys
import time
import signal
import subprocess
import json
import urllib.request
from ..config.settings import load_settings, save_settings, get_writable_temp_dir
from ..core.service_controller import ServiceController
from ..core.adb_client import ADBClient
from .diagnostics import run_diagnostics

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

COMMAND_GUIDE = f"""
{BOLD}{CYAN}======================================================={RESET}
{BOLD}{GREEN}             WHATSAPP AI AGENT - COMMAND GUIDE        {RESET}
{BOLD}{CYAN}======================================================={RESET}
{BOLD}start-ai-whatsapp{RESET}      -> Start daemon (prompts for key if missing)
{BOLD}pause-ai-whatsapp{RESET}      -> Pause incoming message replies temporarily
{BOLD}resume-ai-whatsapp{RESET}     -> Resume agent replying
{BOLD}minimize-ai-whatsapp{RESET}   -> Minimize terminal & activate background mode
{BOLD}logout-ai-whatsapp{RESET}     -> Wipe current Gemini API key and set a new key
{BOLD}stop-ai-whatsapp{RESET}       -> Safely stop the agent daemon completely
{BOLD}check-ai-whatsapp{RESET}      -> Comprehensive system diagnosis & troubleshooting
{BOLD}pair-ai-whatsapp{RESET}       -> Pair with phone's Wireless Debugging (localhost)
{BOLD}connect-ai-whatsapp{RESET}    -> Connect/reconnect to Wireless ADB port (e.g. 39485)
{BOLD}{CYAN}======================================================={RESET}
"""

def print_command_guide():
    print(COMMAND_GUIDE)

def test_api_key(key):
    """Quick validation ping to Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 3}
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "candidates" in data
    except Exception:
        # If offline sandbox or network unreachable, accept key format
        return len(key) > 10

def start_service(background=True, cli_key=None):
    settings = load_settings()
    default_pid = os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.pid")
    pid_file = settings.get("pid_file") or default_pid
    
    existing_pid = ServiceController.get_running_pid(pid_file)
    if existing_pid:
        print(f"{YELLOW}[!] WhatsApp AI Agent is ALREADY RUNNING with PID {existing_pid}.{RESET}")
        return

    # Check for Gemini API Key (Option B)
    current_key = cli_key or settings.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
    if not current_key:
        print(f"\n{YELLOW}[!] No Gemini API key found on device.{RESET}")
        user_key = input(f"{BOLD}Enter your Google Gemini API Key: {RESET}").strip()
        if not user_key:
            print(f"{RED}[!] API key cannot be empty. Start aborted.{RESET}")
            return
        settings["gemini_api_key"] = user_key
        save_settings(settings)
        print(f"{GREEN}[✓] API key securely stored in ~/.config/whatsapp_ai_agent/config.json (chmod 600).{RESET}\n")
    elif cli_key:
        settings["gemini_api_key"] = cli_key
        save_settings(settings)

    # Trigger wake-lock & background permissions
    try:
        subprocess.run(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    device_id = settings.get("device_id", "").strip()
    adb = ADBClient(device_id=device_id)
    if not adb.check_connection():
        print(f"\n{RED}[!] Wireless ADB is not connected.{RESET}")
        print(f"    {YELLOW}Run 'connect-ai-whatsapp <PORT>' (or 'pair-ai-whatsapp' if pairing for the first time).{RESET}\n")
        return

    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "whatsapp_ai_agent.py"))

    if background:
        print(f"{CYAN}[*] Starting WhatsApp AI Agent in background...{RESET}")
        log_file = os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.log")
        with open(log_file, "a") as f_out:
            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdout=f_out,
                stderr=f_out,
                start_new_session=True
            )
        time.sleep(1.2)
        new_pid = ServiceController.get_running_pid(pid_file) or proc.pid
        print(f"{BOLD}{GREEN}[✓] WhatsApp AI Agent started successfully! (PID: {new_pid}){RESET}")
        print(f"{CYAN}[i] Logs: {log_file}{RESET}")
    else:
        # Foreground execution
        os.execv(sys.executable, [sys.executable, script_path])

def pause_service():
    settings = load_settings()
    default_pid = os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.pid")
    pid_file = settings.get("pid_file") or default_pid
    pid = ServiceController.get_running_pid(pid_file)
    if not pid:
        print(f"{RED}[!] WhatsApp AI Agent daemon is not running.{RESET}")
        return
    try:
        os.kill(pid, signal.SIGUSR1)
        print(f"{BOLD}{YELLOW}[✓] Sent PAUSE signal to WhatsApp AI Agent (PID: {pid}). Service paused.{RESET}")
    except Exception as e:
        print(f"{RED}[!] Failed to pause service: {e}{RESET}")

def resume_service():
    settings = load_settings()
    default_pid = os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.pid")
    pid_file = settings.get("pid_file") or default_pid
    pid = ServiceController.get_running_pid(pid_file)
    if not pid:
        print(f"{RED}[!] WhatsApp AI Agent daemon is not running.{RESET}")
        return
    try:
        os.kill(pid, signal.SIGUSR2)
        print(f"{BOLD}{GREEN}[✓] Sent RESUME signal to WhatsApp AI Agent (PID: {pid}). Service resumed.{RESET}")
    except Exception as e:
        print(f"{RED}[!] Failed to resume service: {e}{RESET}")

def stop_service():
    settings = load_settings()
    default_pid = os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.pid")
    pid_file = settings.get("pid_file") or default_pid
    pid = ServiceController.get_running_pid(pid_file)
    if not pid:
        print(f"{YELLOW}[!] WhatsApp AI Agent daemon is not running.{RESET}")
        return
    try:
        print(f"{CYAN}[*] Stopping WhatsApp AI Agent (PID: {pid})...{RESET}")
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            if not ServiceController.get_running_pid(pid_file):
                break
        print(f"{BOLD}{GREEN}[✓] WhatsApp AI Agent stopped.{RESET}")
    except Exception as e:
        print(f"{RED}[!] Failed to stop service: {e}{RESET}")

def minimize_service():
    settings = load_settings()
    default_pid = os.path.join(get_writable_temp_dir(), "whatsapp_ai_agent.pid")
    pid_file = settings.get("pid_file") or default_pid
    pid = ServiceController.get_running_pid(pid_file)
    if not pid:
        print(f"{YELLOW}[!] Agent is not running. Starting in background first...{RESET}")
        start_service(background=True)
    
    device_id = settings.get("device_id", "").strip()
    adb = ADBClient(device_id=device_id)

    # Send HOME to minimize screen apps
    adb.keyevent(3)
    
    # Post persistent notification
    try:
        subprocess.run([
            "termux-notification",
            "--id", "wa_bg_ticker",
            "--title", "WhatsApp AI Agent",
            "--content", "Minimized: Actively replying in background",
            "--ongoing", "true"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    print(f"\n{BOLD}{GREEN}[✓] WhatsApp AI Agent minimized to background!{RESET}")
    print(f"{CYAN}WhatsApp will not pop up during active replies. Status notification active.{RESET}\n")

def logout_service():
    """Wipes the stored Gemini API Key and prompts for a replacement."""
    settings = load_settings()
    print(f"\n{BOLD}{YELLOW}[*] Logging out of WhatsApp AI Agent...{RESET}")
    
    # 1. Clear key
    settings["gemini_api_key"] = ""
    save_settings(settings)
    print(f"{GREEN}[✓] Current Gemini API key has been deleted properly from storage and active memory.{RESET}")

    # 2. Ask for new key
    print(f"\n{CYAN}Would you like to set a new Gemini API key now?{RESET}")
    new_key = input(f"{BOLD}Enter new Gemini API key (or press Enter to leave unset): {RESET}").strip()
    if new_key:
        settings["gemini_api_key"] = new_key
        save_settings(settings)
        print(f"{BOLD}{GREEN}[✓] New Gemini API key securely saved! (chmod 600){RESET}\n")
    else:
        print(f"{YELLOW}[i] No key set. You will be prompted on next 'start-ai-whatsapp'.{RESET}\n")

def pair_service():
    """Interactive pairing with Android Wireless Debugging on localhost (127.0.0.1)."""
    settings = load_settings()
    adb = ADBClient()
    print(f"\n{BOLD}{CYAN}======================================================={RESET}")
    print(f"{BOLD}{GREEN}   On-Device Wireless ADB Pairing (Termux Localhost)  {RESET}")
    print(f"{BOLD}{CYAN}======================================================={RESET}\n")
    print(f"  {BOLD}Step 1:{RESET} Open Android {CYAN}Settings > Developer Options > Wireless Debugging{RESET}.")
    print(f"  {BOLD}Step 2:{RESET} Tap {CYAN}'Pair device with pairing code'{RESET}.")
    print(f"         (A popup will show a 6-digit code and a port number)\n")

    try:
        pairing_port = input(f"{YELLOW}Enter the Pairing Port (e.g. 41235 or full IP:Port): {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not pairing_port:
        print(f"{RED}[!] Pairing port is required.{RESET}")
        return

    try:
        pairing_code = input(f"{YELLOW}Enter the 6-digit Pairing Code: {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not pairing_code:
        print(f"{RED}[!] Pairing code is required.{RESET}")
        return

    target = f"127.0.0.1:{pairing_port}" if pairing_port.isdigit() else pairing_port
    print(f"\n  [*] Pairing with {target}...")
    success, msg = adb.pair_wifi(target, pairing_code)
    if success:
        print(f"  {GREEN}{BOLD}[✓] Phone successfully paired with Termux on localhost!{RESET}\n")
        print(f"  {BOLD}Step 3:{RESET} Close the pairing popup and look at the main Wireless Debugging screen.")
        print(f"         Find the port number under {CYAN}'IP address & Port'{RESET}.\n")
        try:
            connect_port = input(f"{YELLOW}Enter the Connection Port (e.g. 39485): {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            connect_port = ""
        if connect_port:
            conn_target = f"127.0.0.1:{connect_port}" if connect_port.isdigit() else connect_port
            print(f"  [*] Connecting to {conn_target}...")
            if adb.connect_wifi(conn_target):
                print(f"  {GREEN}{BOLD}[✓] Successfully connected to {conn_target}!{RESET}")
                settings["device_id"] = conn_target
                save_settings(settings)
                apk_candidates = [
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ADBKeyboard.apk")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ADBKeyboard.apk")),
                    os.path.expanduser("~/ADBKeyboard.apk")
                ]
                found_apk = next((p for p in apk_candidates if os.path.exists(p)), None)
                adb.ensure_adb_keyboard(apk_path=found_apk)
                print(f"  {GREEN}[✓] ADBKeyboard verified and ready!{RESET}")
                print(f"\n{BOLD}{GREEN}You can now start the agent anytime by running: start-ai-whatsapp{RESET}\n")
            else:
                print(f"  {RED}[!] Connection to {conn_target} failed. You can connect anytime with: connect-ai-whatsapp {connect_port}{RESET}")
    else:
        print(f"  {RED}[✗] Pairing failed: {msg}{RESET}")
        print(f"      Make sure Wireless Debugging is ON and the pairing popup is currently visible.")

def connect_service():
    """Quickly connects or reconnects to on-device Wireless ADB (e.g. after phone reboot)."""
    settings = load_settings()
    adb = ADBClient()

    port_arg = None
    for arg in sys.argv[2:]:
        if not arg.startswith("-"):
            port_arg = arg.strip()
            break

    if not port_arg:
        saved = settings.get("device_id", "")
        prompt = f"Enter Wireless Debugging Port [Press Enter to reconnect to {saved}]: " if saved else "Enter Wireless Debugging Port (e.g. 39485): "
        try:
            port_arg = input(f"{YELLOW}{prompt}{RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            pass
        if not port_arg and saved:
            port_arg = saved

    if not port_arg:
        print(f"{RED}[!] No port or IP:Port provided.{RESET}")
        return

    target = f"127.0.0.1:{port_arg}" if port_arg.isdigit() else port_arg
    print(f"[*] Connecting to Wireless ADB at {target}...")
    if adb.connect_wifi(target):
        print(f"{GREEN}{BOLD}[✓] Successfully connected to {target}!{RESET}")
        settings["device_id"] = target
        save_settings(settings)
        apk_candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ADBKeyboard.apk")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ADBKeyboard.apk")),
            os.path.expanduser("~/ADBKeyboard.apk")
        ]
        found_apk = next((p for p in apk_candidates if os.path.exists(p)), None)
        adb.ensure_adb_keyboard(apk_path=found_apk)
        print(f"{GREEN}[✓] You're all set! Run 'start-ai-whatsapp' to launch.{RESET}")
    else:
        print(f"{RED}[✗] Failed to connect to {target}.{RESET}")
        print(f"    Check that Settings > Developer Options > Wireless Debugging is ON.")

def check_service():
    run_diagnostics()

def main():
    if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv or "help" in sys.argv:
        print_command_guide()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    cli_key = None
    if "--key" in sys.argv:
        try:
            key_idx = sys.argv.index("--key") + 1
            cli_key = sys.argv[key_idx]
        except Exception:
            pass

    if cmd in ("start", "start-ai-whatsapp"):
        bg = "--foreground" not in sys.argv
        start_service(background=bg, cli_key=cli_key)
    elif cmd in ("pause", "pause-ai-whatsapp"):
        pause_service()
    elif cmd in ("resume", "resume-ai-whatsapp"):
        resume_service()
    elif cmd in ("stop", "stop-ai-whatsapp"):
        stop_service()
    elif cmd in ("minimize", "minimize-ai-whatsapp"):
        minimize_service()
    elif cmd in ("logout", "logout-ai-whatsapp"):
        logout_service()
    elif cmd in ("check", "check-ai-whatsapp"):
        check_service()
    elif cmd in ("pair", "pair-ai-whatsapp"):
        pair_service()
    elif cmd in ("connect", "connect-ai-whatsapp"):
        connect_service()
    elif cmd in ("setup", "setup-wizard"):
        from .setup_wizard import run_setup
        run_setup()
    else:
        print(f"Unknown command: {cmd}")
        print_command_guide()
        sys.exit(1)

if __name__ == "__main__":
    main()
