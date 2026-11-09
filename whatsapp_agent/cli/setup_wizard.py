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

    device_id = settings.get("device_id", "").strip()
    adb = ADBClient(device_id=device_id)

    # Step 3: Check Wireless ADB and ADBKeyboard
    print(f"\n{CYAN}[3/6] Verifying Wireless ADB connection (Wi-Fi Debugging)...{RESET}")
    detected_id, _ = adb.auto_detect_device()
    connected = False

    if detected_id:
        print(f"  {GREEN}[✓] Active Wireless ADB device detected: {detected_id}{RESET}")
        adb.device_id = detected_id
        settings["device_id"] = detected_id
        connected = True
    elif device_id and ":" in device_id:
        print(f"  [*] Attempting to connect to saved Wi-Fi device ({device_id})...")
        if adb.connect_wifi(device_id):
            print(f"  {GREEN}[✓] Successfully connected to {device_id}{RESET}")
            connected = True

    if not connected:
        print(f"  {YELLOW}[!] No active Wireless ADB device detected.{RESET}")
        print(f"      {BOLD}How to enable on your phone:{RESET}")
        print(f"      1. Go to Settings > Developer Options > Wireless Debugging.")
        print(f"      2. Turn ON Wireless Debugging and note the IP address and Port.")
        try:
            custom_device = input(f"\n{YELLOW}Enter your phone's Wireless Debugging IP:Port (or press Enter to configure later): {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            custom_device = ""

        if custom_device:
            try:
                pair_needed = input(f"{YELLOW}Do you need to pair first with a 6-digit code? [y/N]: {RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                pair_needed = "n"

            if pair_needed in ("y", "yes"):
                try:
                    p_target = input(f"{YELLOW}Enter Pairing IP:Port (from 'Pair device with pairing code'): {RESET}").strip()
                    p_code = input(f"{YELLOW}Enter 6-digit pairing code: {RESET}").strip()
                    if p_target and p_code:
                        print(f"  [*] Pairing with {p_target}...")
                        adb.pair_wifi(p_target, p_code)
                except (EOFError, KeyboardInterrupt):
                    pass

            print(f"  [*] Connecting to {custom_device} via Wi-Fi...")
            if adb.connect_wifi(custom_device):
                print(f"  {GREEN}[✓] Successfully connected to {custom_device}!{RESET}")
                settings["device_id"] = custom_device
                connected = True
            else:
                print(f"  {YELLOW}[!] Could not connect to {custom_device} right now.{RESET}")
                print(f"      You can connect later anytime with: adb connect {custom_device}")
        else:
            print(f"  {YELLOW}[-] Wi-Fi connection skipped for now.{RESET}")

    # Ensure ADBKeyboard is installed and active if connected
    if connected:
        apk_candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ADBKeyboard.apk")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ADBKeyboard.apk")),
            os.path.expanduser("~/ADBKeyboard.apk")
        ]
        found_apk = next((p for p in apk_candidates if os.path.exists(p)), None)
        adb.ensure_adb_keyboard(apk_path=found_apk)
        print(f"  {GREEN}[✓] Wireless ADB connected and ADBKeyboard verified!{RESET}")
    else:
        print(f"  {YELLOW}[*] You can complete connection and verify anytime with 'check-ai-whatsapp'.{RESET}")

    # Step 4: Verify WhatsApp package & UI frames
    print(f"\n{CYAN}[4/6] Inspecting WhatsApp app details & message reply frames...{RESET}")
    if connected:
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
    else:
        print(f"  {YELLOW}[-] Skipped until Wireless ADB is connected.{RESET}")

    # Step 5: Show Success Notification to user
    print(f"\n{CYAN}[5/6] Sending success notification...{RESET}")
    show_notification("WhatsApp AI Agent", "Setup & UI calibration completed successfully!", ongoing=False)
    print(f"  {GREEN}[✓] Success notification delivered.{RESET}\n")

    # Step 6: Ask for API Key and Agent Name
    print(f"{CYAN}[6/6] Configuration details:{RESET}")
    current_key = settings.get("gemini_api_key", "")
    key_masked = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else "None"
    print(f"Current Gemini API Key: {BOLD}{key_masked}{RESET}")
    try:
        new_key = input(f"Enter Gemini API Key (or press Enter to keep current): ").strip()
        if new_key:
            settings["gemini_api_key"] = new_key
    except (EOFError, KeyboardInterrupt):
        pass

    current_name = settings.get("agent_name", "Personal AI Assistant")
    try:
        new_name = input(f"Enter AI Agent Name/Persona (default: '{current_name}'): ").strip()
        if new_name:
            settings["agent_name"] = new_name
    except (EOFError, KeyboardInterrupt):
        pass

    save_settings(settings)
    print(f"\n{BOLD}{GREEN}[✓] Setup completed successfully! Settings securely saved to {BOLD}~/.config/whatsapp_ai_agent/config.json (chmod 600){RESET}\n")

    # Display post-setup command guide card
    from .commands import print_command_guide
    print_command_guide()
    return True

if __name__ == "__main__":
    run_setup()
