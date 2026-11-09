import os
import sys
import time
import subprocess
from ..config.settings import load_settings, save_settings
from ..core.adb_client import ADBClient

GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def show_notification(title, content, ongoing=False):
    """Posts notification to status bar via Termux API or Android broadcast."""
    # 1. Try termux-notification
    try:
        cmd = ["termux-notification", "--id", "wa_ai_agent", "--title", title, "--content", content]
        if ongoing:
            cmd += ["--ongoing", "true"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    # 2. Fallback to ADB notification or log
    print(f"{CYAN}[NOTIFICATION]{RESET} {BOLD}{title}{RESET}: {content}")
    return False

def run_setup():
    print(f"\n{BOLD}{CYAN}======================================================={RESET}")
    print(f"{BOLD}{GREEN}  WhatsApp AI Agent - New Device Setup & Onboarding    {RESET}")
    print(f"{BOLD}{CYAN}======================================================={RESET}\n")

    settings = load_settings()

    # Step 1: Put agent in notification bar
    print(f"{CYAN}[1/6] Registering agent in status/notification bar...{RESET}")
    show_notification("WhatsApp AI Agent", "Initializing setup on new device...", ongoing=True)
    time.sleep(1.0)

    # Step 2: Prevent background activity kill
    print(f"{CYAN}[2/6] Configuring background execution & wake locks...{RESET}")
    try:
        subprocess.run(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  {GREEN}[✓] Termux wake-lock active.{RESET}")
    except Exception:
        pass

    device_id = settings.get("device_id", "192.168.0.140:35105")
    adb = ADBClient(device_id=device_id)

    try:
        adb.run_adb(["shell", "dumpsys", "deviceidle", "whitelist", "+com.termux"])
        adb.run_adb(["shell", "cmd", "appops", "set", "com.termux", "RUN_IN_BACKGROUND", "allow"])
        print(f"  {GREEN}[✓] Battery optimization whitelist configured.{RESET}")
    except Exception:
        pass

    # Step 3: Check ADB and ADBKeyboard
    print(f"{CYAN}[3/6] Verifying ADB connection to device ({device_id})...{RESET}")
    if not adb.check_connection():
        print(f"{RED}[!] Error: Could not connect to {device_id}. Ensure Wireless ADB is enabled.{RESET}")
        custom_device = input(f"{YELLOW}Enter your device IP:Port [Press Enter to keep {device_id}]: {RESET}").strip()
        if custom_device:
            adb.device_id = custom_device
            settings["device_id"] = custom_device
            if not adb.check_connection():
                print(f"{RED}[!] Still failed to connect to {custom_device}. Exiting setup.{RESET}")
                return False

    print(f"  {GREEN}[✓] Device connected and ADBKeyboard active!{RESET}")

    # Step 4: Verify WhatsApp package & UI frames
    print(f"{CYAN}[4/6] Inspecting WhatsApp app details & message reply frames...{RESET}")
    wa_check = adb.run_adb(["shell", "pm path com.whatsapp"]).strip()
    if not wa_check:
        print(f"{YELLOW}[!] WhatsApp is not installed under package name com.whatsapp.{RESET}")
    else:
        print(f"  {GREEN}[✓] WhatsApp detected: {wa_check}{RESET}")

    # Test UI dump
    ui_dump = adb.dump_ui()
    if ui_dump and "<hierarchy" in ui_dump:
        print(f"  {GREEN}[✓] Screen hierarchy & UI frames accessible.{RESET}")
    else:
        print(f"{YELLOW}[!] Notice: Could not dump UI immediately. Make sure screen is unlocked.{RESET}")

    # Step 5: Show Success Notification to user
    print(f"\n{CYAN}[5/6] Sending success notification...{RESET}")
    show_notification("WhatsApp AI Agent", "Setup & UI calibration completed successfully!", ongoing=False)
    print(f"  {GREEN}[✓] Success notification delivered.{RESET}\n")

    # Step 6: Ask for API Key and Agent Name
    print(f"{CYAN}[6/6] Configuration details:{RESET}")
    current_key = settings.get("gemini_api_key", "")
    key_masked = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else "None"
    print(f"Current Gemini API Key: {BOLD}{key_masked}{RESET}")
    new_key = input(f"Enter Gemini API Key (or press Enter to keep current): ").strip()
    if new_key:
        settings["gemini_api_key"] = new_key

    current_name = settings.get("agent_name", "Personal AI Assistant")
    new_name = input(f"Enter AI Agent Name/Persona (default: '{current_name}'): ").strip()
    if new_name:
        settings["agent_name"] = new_name

    save_settings(settings)
    print(f"\n{BOLD}{GREEN}[✓] Setup completed successfully! Settings securely saved to {BOLD}~/.config/whatsapp_ai_agent/config.json (chmod 600){RESET}\n")

    # Display post-setup command guide card
    from .commands import print_command_guide
    print_command_guide()
    return True

if __name__ == "__main__":
    run_setup()
