# WhatsApp AI Auto-Reply Agent (v2.1)

Intelligent, multilingual auto-reply agent for WhatsApp powered by **Google Gemini AI** (`gemini-3.5-flash`) and **ADB / ADBKeyboard**. 

Designed to run **standalone directly on Android** (via Termux, no PC or root required) or on any **Linux / macOS / Windows PC** connected to an Android phone over Wireless Debugging.

---

## 🚀 Key Features

* **Sub-2/3s Response & Zero-Delay Sweep**: Instant detection of unread messages with immediate follow-up scans.
* **8-Second Dynamic Cooldown & FIFO Fairness**: Prevents duplicate spamming while answering contacts strictly in order of arrival.
* **Dynamic Keyboard & Screen Interference Management**:
  * The agent operates with `ADBKeyboard` active.
  * When human screen interference (touch, typing, opening other apps) is detected, it **instantly switches the keyboard to your phone's default keyboard** (Gboard, Samsung Keyboard, etc.) and pauses the agent.
  * When screen interference is absent for **25 seconds**, the agent automatically switches back to `ADBKeyboard` and **resumes its work from pause**.
* **Non-Intrusive Background Operation**: Never forces WhatsApp to pop up over active apps (e.g., YouTube, Browser) while replying; provides an ongoing 50-second status notification.
* **Multimodal Intelligence**: Analyzes incoming photos (`gemini-3.5-flash` Vision) and listens to voice notes (`gemini-3.5-flash` Audio) to generate contextual text replies.
* **Privacy & Safety Guardrails**: Zero cross-contact data leakage, natural Islamic etiquette (*Assalamu Alaikum*, *Alhamdulillah*, *InshaALLAH*, *Allah Hafez*), and strict deterministic medical advice disclaimer.
* **Hardware Resilience**: Automatically pauses during incoming or active phone calls; suspends while screen is locked and resumes cleanly when unlocked.
* **Wireless ADB (Wi-Fi / Localhost Only)**: Operates seamlessly over Android Wireless Debugging without requiring USB cables.

---

## 📋 Prerequisites

Before installing, ensure you have:

1. **An Android Phone (Android 11+)** with WhatsApp installed and active.
2. **Termux & Termux:API** installed on your phone:
   * 👉 Download [Termux from F-Droid](https://f-droid.org/en/packages/com.termux/) (Do NOT use Google Play Store version).
   * 👉 Download [Termux:API from F-Droid](https://f-droid.org/en/packages/com.termux.api/).
3. **A Google Gemini API Key**:
   * Free key available from [Google AI Studio](https://aistudio.google.com/api-keys).

---

## 📥 Installation & Setup Guide

### Option 1: Standalone On-Device Setup in Termux (Recommended)

Follow these steps directly inside the **Termux** app on your phone:

#### Step 1: Update Packages & Clone the Repository
Open Termux and run:
```bash
pkg update -y
pkg install git gh -y
```

Clone the repository using GitHub CLI or standard Git:
```bash
# Using GitHub CLI:
gh repo clone eabkju/ai-whatsapp-agent
cd ai-whatsapp-agent

# OR using standard Git:
git clone https://github.com/eabkju/ai-whatsapp-agent.git
cd ai-whatsapp-agent
```

#### Step 2: Run the Automated Environment Bootstrap
Run the bootstrap script to automatically install all dependencies (`python`, `android-tools`, `termux-api`, `ffmpeg`) and configure the CLI commands:
```bash
bash setup_termux_env.sh
```
*(Alternatively, if dependencies are already installed, run `bash install.sh`)*

#### Step 3: Enable Wireless Debugging on Your Phone
1. Open Android **Settings > About Phone** and tap **Build Number** 7 times to enable **Developer Options**.
2. Go to **Settings > Developer Options**:
   * Connect your phone to **Wi-Fi** (or your own Wi-Fi Hotspot).
   * Toggle **Wireless Debugging** to **ON**.
   * Enable **Disable Permission Monitoring** (if available on your device).

#### Step 4: Pair Termux with Phone Wireless Debugging (One-Time)
1. Split-screen or open Termux in a floating / popup window alongside Developer Options.
2. In Developer Options, tap **"Pair device with pairing code"** (a dialog will show a 6-digit code and a port number).
3. In Termux, run:
   ```bash
   pair-ai-whatsapp
   ```
4. Enter the **5-digit pairing port** and **6-digit pairing code** shown in the dialog.

#### Step 5: Connect to Wireless Debugging
1. Look at the main **Wireless Debugging** screen under **"IP address & Port"** (e.g., `127.0.0.1:39485` or `192.168.0.140:39485`).
2. In Termux, run:
   ```bash
   connect-ai-whatsapp <PORT>
   ```
   *(Example: `connect-ai-whatsapp 39485`)*

#### Step 6: Verify System Health
Run the comprehensive diagnostic check:
```bash
check-ai-whatsapp
```
It tests Wireless ADB connectivity, screen lock state, telephony, ADBKeyboard installation, WhatsApp app state, and Gemini API quota.

#### Step 7: Launch the Agent
```bash
start-ai-whatsapp
```
*If starting for the first time, you will be prompted to paste your Google Gemini API key.*

---

### Option 2: Running from a PC / Laptop (Linux, macOS, Windows)

If you prefer to run the agent from your computer while controlling your phone wirelessly over local Wi-Fi:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/eabkju/ai-whatsapp-agent.git
   cd ai-whatsapp-agent
   ```
2. **Install prerequisites**:
   * Python 3.10+
   * ADB (`adb`) and `ffmpeg` installed and in your system `PATH`.
3. **Connect to your phone's Wireless ADB**:
   ```bash
   adb connect <PHONE_IP>:<PORT>
   ```
4. **Run the installer or launch directly**:
   ```bash
   bash install.sh
   start-ai-whatsapp
   # OR run directly with Python:
   python3 whatsapp_ai_agent.py
   ```

---

## 🎮 Complete Command Reference

Once installed, all helper commands are globally available in your terminal (`$PREFIX/bin` and `~/.local/bin`):

| Command | Usage / Syntax | Description |
| :--- | :--- | :--- |
| **`start-ai-whatsapp`** | `start-ai-whatsapp`<br>`start-ai-whatsapp --key <API_KEY>`<br>`start-ai-whatsapp --foreground` | Starts the agent daemon in the background. Prompts for your Gemini API key if not configured yet. |
| **`stop-ai-whatsapp`** | `stop-ai-whatsapp` | Safely sends `SIGTERM` to gracefully stop the background agent daemon, removes PID locks, and restores WhatsApp to home. |
| **`pause-ai-whatsapp`** | `pause-ai-whatsapp` | Sends `SIGUSR1` to temporarily pause auto-replying without stopping the process or killing background wake-locks. |
| **`resume-ai-whatsapp`** | `resume-ai-whatsapp` | Sends `SIGUSR2` to resume the agent from paused state. |
| **`check-ai-whatsapp`** | `check-ai-whatsapp` | Runs an 8-point diagnostic check: daemon status, Wireless ADB connection, screen wakefulness & lock state, call state, ADBKeyboard status, WhatsApp installation, Gemini API connection, and voice notes media storage. |
| **`pair-ai-whatsapp`** | `pair-ai-whatsapp` | Interactively pairs Termux with Android Wireless Debugging on localhost (`127.0.0.1`) using a 6-digit pairing code. |
| **`connect-ai-whatsapp`** | `connect-ai-whatsapp [PORT]` | Connects or reconnects to on-device Wireless ADB (e.g., `connect-ai-whatsapp 39485`). If no port is specified, reconnects to your last saved port. |
| **`minimize-ai-whatsapp`** | `minimize-ai-whatsapp` | Minimizes WhatsApp and Termux to the background, enabling silent background operation mode. |
| **`logout-ai-whatsapp`** | `logout-ai-whatsapp` | Securely wipes your current stored Google Gemini API key from `config.json` and prompts you to enter a new key. |

---

### Direct Python Execution (Alternative)

You can also run any command directly with Python from inside the project directory:

```bash
# View command help guide:
python3 -m whatsapp_agent.cli.commands --help

# Run diagnostic check:
python3 -m whatsapp_agent.cli.commands check

# Start in foreground (ideal for live logs and debugging):
python3 whatsapp_ai_agent.py

# Pair or connect:
python3 -m whatsapp_agent.cli.commands pair
python3 -m whatsapp_agent.cli.commands connect 39485

# Control daemon state:
python3 -m whatsapp_agent.cli.commands pause
python3 -m whatsapp_agent.cli.commands resume
python3 -m whatsapp_agent.cli.commands stop
```

---

## 🔄 Daily Workflow & Reconnecting After Reboot

Android randomizes the Wireless Debugging port whenever the phone reboots or Wi-Fi reconnects:

1. Look at Android **Settings > Developer Options > Wireless Debugging** for the new port number (e.g., `42135`).
2. Open Termux and connect:
   ```bash
   connect-ai-whatsapp 42135
   ```
3. Launch the agent:
   ```bash
   start-ai-whatsapp
   ```
*(You do **not** need to re-pair. Re-pairing is only needed once).*

---

## ⌨️ How Smart Keyboard Switching Works

1. **Agent Active**: While the agent is running and waiting for unread chats, **`ADBKeyboard`** is active to allow instant, automated typing of Unicode, English, Bengali, and emoji text.
2. **User Touches Screen / Switches Apps**: The moment you touch the screen, type in any app, or open another window, the agent detects user interference:
   * **Instantly switches the active keyboard to your phone's personal default keyboard** (e.g., Gboard, Samsung Keyboard).
   * **Pauses automated agent actions** so you have full, uninterrupted control of your phone.
3. **25-Second Inactivity Auto-Resume**:
   * Every touch or screen interaction resets a 25-second countdown timer.
   * After **25 seconds** of no user interference, the agent automatically switches back to `ADBKeyboard` and resumes its monitoring and auto-replying duties.
4. **Shutdown Restoration**: Whenever `stop-ai-whatsapp` is called or the process exits, your phone's personal default keyboard is restored.

---

## 🔒 Security & Privacy

* **Zero Hardcoded Secrets**: No API keys are bundled or shipped inside package code.
* **Local Storage Only**: Your API key is stored locally in `~/.config/whatsapp_ai_agent/config.json` with user-only permissions (`chmod 600`).
* **Complete Independence**: Operates 100% locally on the device with zero cloud telemetry or third-party servers.
* **Isolated Temporary Storage**: Automatically selects writable temporary directories (`$PREFIX/tmp` on Termux / `/tmp` on standard Linux) to prevent permission conflicts.

---

## 🧪 Running Automated Unit Tests

To run the complete test suite:

```bash
cd ai-whatsapp-agent
python3 -m unittest discover tests
```
All 13 unit tests run with full test isolation to verify:
* FIFO queue fairness and 8-second contact cooldown
* Deterministic medical disclaimer interceptor
* Privacy directives and Islamic greeting guardrails
* Dynamic multimodal routing (`gemini-3.5-flash` text, vision, audio)
* 25-second user screen interference & keyboard switching
* Wireless ADB connection enforcement
* CLI command guide completeness
