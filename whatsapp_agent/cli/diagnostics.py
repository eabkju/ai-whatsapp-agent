import os
import sys
import json
import urllib.request
from ..config.settings import load_settings
from ..core.adb_client import ADBClient
from ..core.device_guard import DeviceGuard
from ..core.service_controller import ServiceController

GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def run_diagnostics():
    print(f"\n{BOLD}{CYAN}======================================================={RESET}")
    print(f"{BOLD}{GREEN}  WhatsApp AI Agent - Comprehensive System Diagnosis   {RESET}")
    print(f"{BOLD}{CYAN}======================================================={RESET}\n")

    settings = load_settings()
    device_id = settings.get("device_id", "").strip()
    api_key = settings.get("gemini_api_key", "")
    pid_file = settings.get("pid_file", "/tmp/whatsapp_ai_agent.pid")
    
    issues_found = 0

    # 1. Daemon Process State
    print(f"{BOLD}[1] Agent Daemon Status:{RESET}")
    pid = ServiceController.get_running_pid(pid_file)
    if pid:
        controller = ServiceController(pid_file=pid_file)
        state = controller.get_state()
        color = GREEN if state == "RUNNING" else YELLOW
        print(f"  {color}[✓] Daemon is ACTIVE (PID: {pid}, State: {state}){RESET}")
    else:
        print(f"  {YELLOW}[-] Daemon is not currently running.{RESET}")

    # 2. ADB Connection
    adb = ADBClient(device_id=device_id)
    print(f"\n{BOLD}[2] Wireless ADB Connection (Wi-Fi Debugging):{RESET}")
    if adb.check_connection():
        print(f"  {GREEN}[✓] Connected via Wireless ADB (Device: {adb.device_id}).{RESET}")
    else:
        target_display = device_id if device_id else "No IP:Port set"
        print(f"  {RED}[✗] Failed to connect to Wireless ADB device ({target_display})!{RESET}")
        print(f"      {YELLOW}Troubleshooting: Enable Wireless Debugging on your phone and run: adb connect <PHONE_IP:PORT>{RESET}")
        issues_found += 1

    guard = DeviceGuard(adb)

    # 3. Screen & Power State
    print(f"\n{BOLD}[3] Device Screen & Lock Status:{RESET}")
    is_locked = guard.is_screen_locked()
    if is_locked:
        print(f"  {YELLOW}[!] Device screen is currently LOCKED or OFF.{RESET}")
        print(f"      {YELLOW}Note: The agent will automatically wait until the user unlocks the screen.{RESET}")
    else:
        print(f"  {GREEN}[✓] Device screen is ON and UNLOCKED.{RESET}")

    # 4. Telephony / Call State
    print(f"\n{BOLD}[4] Telephony Call State:{RESET}")
    call_state = guard.get_call_state()
    if call_state == 0:
        print(f"  {GREEN}[✓] Telephony idle (no incoming or active phone calls).{RESET}")
    elif call_state == 1:
        print(f"  {YELLOW}[!] Phone is currently RINGING (Incoming call).{RESET}")
    else:
        print(f"  {YELLOW}[!] Phone call is IN PROGRESS (Off-hook).{RESET}")

    # 5. ADBKeyboard IME
    print(f"\n{BOLD}[5] Unicode Keyboard (ADBKeyboard):{RESET}")
    current_ime = adb.run_adb(["shell", "settings get secure default_input_method"]).strip()
    if "com.android.adbkeyboard" in current_ime:
        print(f"  {GREEN}[✓] ADBKeyboard is active default IME.{RESET}")
    else:
        print(f"  {YELLOW}[!] Active IME is: {current_ime}. Attempting to enable ADBKeyboard...{RESET}")
        adb.run_adb(["shell", "ime enable com.android.adbkeyboard/.AdbIME"])
        adb.run_adb(["shell", "ime set com.android.adbkeyboard/.AdbIME"])
        ime_after = adb.run_adb(["shell", "settings get secure default_input_method"]).strip()
        if "com.android.adbkeyboard" in ime_after:
            print(f"  {GREEN}[✓] ADBKeyboard successfully set.{RESET}")
        else:
            print(f"  {RED}[✗] Could not set ADBKeyboard. Ensure ADBKeyboard APK is installed.{RESET}")
            issues_found += 1

    # 6. WhatsApp Status
    print(f"\n{BOLD}[6] WhatsApp App Status:{RESET}")
    pkg_out = adb.run_adb(["shell", "pm path com.whatsapp"]).strip()
    if pkg_out:
        print(f"  {GREEN}[✓] WhatsApp package installed ({pkg_out}){RESET}")
        top_act = adb.run_adb(["shell", "dumpsys activity activities | grep -E 'topResumedActivity'"]).strip()
        if "com.whatsapp" in top_act:
            print(f"  {GREEN}[✓] WhatsApp is currently the foreground active app.{RESET}")
        else:
            print(f"  {YELLOW}[-] WhatsApp is in background. Top app: {top_act}{RESET}")
    else:
        print(f"  {RED}[✗] WhatsApp (com.whatsapp) not found on device.{RESET}")
        issues_found += 1

    # 7. Gemini API Key Verification
    print(f"\n{BOLD}[7] Google Gemini API Connection:{RESET}")
    if not api_key:
        print(f"  {RED}[✗] No Gemini API Key configured in settings.json!{RESET}")
        issues_found += 1
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        test_payload = {
            "contents": [{"parts": [{"text": "Reply with 'OK'"}]}],
            "generationConfig": {"maxOutputTokens": 5}
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(test_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                if "candidates" in resp_json:
                    print(f"  {GREEN}[✓] Gemini API authenticated successfully and quota is active.{RESET}")
                else:
                    print(f"  {YELLOW}[!] Unexpected Gemini API response structure.{RESET}")
        except Exception as e:
            print(f"  {RED}[✗] Gemini API request failed: {e}{RESET}")
            issues_found += 1

    # 8. WhatsApp Voice Notes Directory Check
    print(f"\n{BOLD}[8] WhatsApp Voice Notes Media Storage:{RESET}")
    media_found = False
    for path in settings.get("voice_notes_paths", []):
        check_dir = adb.run_adb(["shell", f"[ -d '{path}' ] && echo 'EXISTS'"]).strip()
        if "EXISTS" in check_dir:
            print(f"  {GREEN}[✓] Found Voice Notes path: {path}{RESET}")
            media_found = True
            break
    if not media_found:
        print(f"  {YELLOW}[-] Default Voice Notes directory not found yet (will auto-discover upon arrival).{RESET}")

    # Summary
    print(f"\n{BOLD}{CYAN}-------------------------------------------------------{RESET}")
    if issues_found == 0:
        print(f"{BOLD}{GREEN}[✓] ALL SYSTEMS OPERATIONAL! WhatsApp AI Agent is ready.{RESET}\n")
    else:
        print(f"{BOLD}{YELLOW}[!] Diagnosis completed with {issues_found} issue(s) detected. See above for details.{RESET}\n")

if __name__ == "__main__":
    run_diagnostics()
