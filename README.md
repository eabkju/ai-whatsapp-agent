# WhatsApp AI Auto-Reply Agent (v2.1)

Intelligent, multilingual auto-reply agent for WhatsApp powered by **Google Gemini AI** and **ADB / ADBKeyboard**. Designed to run standalone on Android (via Termux) or on any Linux / macOS / Windows PC connected to an Android phone.

---

## 🚀 Key Features

* **Sub-2/3s Response & Zero-Delay Sweep**: Instant detection of unread messages with immediate follow-up scans.
* **8-Second Dynamic Cooldown & FIFO Fairness**: Prevents duplicate spamming while answering contacts strictly in order of arrival.
* **Dynamic Keyboard & Screen Interference Management**: The agent operates with `ADBKeyboard` active. When human screen interference is detected, it instantly switches the keyboard to your phone's default keyboard (Gboard, Samsung Keyboard, etc.) and pauses the agent.
* **25-Second Inactivity Auto-Resume**: When screen interference is absent for 25 seconds, the agent automatically switches back to `ADBKeyboard` and resumes its work from pause.
* **Non-Intrusive Background Operation**: Never forces WhatsApp to pop up over active apps (e.g. YouTube, Browser) while replying; provides an ongoing 50-second status notification.
* **Multimodal Intelligence**: Analyzes incoming photos (`gemini-3.5-flash` Vision) and listens to voice notes (`gemini-3.5-flash` Audio) to send contextual text replies.
* **Privacy & Safety Guardrails**: Zero cross-contact data leakage, natural Islamic etiquette (*Assalamu Alaikum*, *Alhamdulillah*, *InshaALLAH*, *Allah Hafez*), and strict deterministic medical advice disclaimer.
* **Hardware Resilience**: Automatically pauses during incoming or active phone calls; suspends while screen is locked and resumes cleanly when unlocked.
* **Wireless ADB (Wi-Fi Only)**: Operates seamlessly over Android Wireless Debugging (Wi-Fi) without requiring USB cables.

---

## 📱 Prerequisites on the Target Device

### 1. Enable Android Developer Options & Wireless Debugging
1. Go to **Settings > About Phone** and tap **Build Number** 7 times to enable Developer Options.
2. Go to **Settings > Developer Options**:
   * Enable **Wireless Debugging** (connect your phone and host to the same Wi-Fi).
   * Note your **IP address & Port** (e.g. `192.168.1.50:41235`).
   * Enable **Disable Permission Monitoring** (if available on your device).

### 2. Install ADBKeyboard (Required for Unicode & Bengali/Hindi text)
1. Download & install the included `ADBKeyboard.apk` (or from GitHub):
   👉 [ADBKeyboard Release on GitHub](https://github.com/senzhk/ADBKeyBoard/releases)
2. Go to **Settings > System > Languages & Input > On-screen Keyboard** and enable **ADB Keyboard**.

### 3. Install Termux & Termux:API (If running directly on phone)
1. Install **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/).
2. Install **Termux:API** from [F-Droid](https://f-droid.org/en/packages/com.termux.api/).
3. Inside Termux, install required tools:
   ```bash
   pkg update && pkg install python android-tools termux-api ffmpeg -y
   ```

*(If running from a PC/Laptop, you only need Python 3, `adb`, and `ffmpeg` installed).*

---

## ⚡ 1-Step Installation & Setup

1. Copy or extract this project folder to the target device.
2. In the terminal (Termux or Linux), navigate to the folder and run:
   ```bash
   bash install.sh
   ```
3. The installer will:
   * Install all 9 CLI commands in `$PREFIX/bin` (Termux) and `~/.local/bin`.
   * Configure background wake-locks and battery optimization exemptions.
   * Verify your Wireless ADB connection (`<PHONE_IP:PORT>`).
   * Prompt you for your **Google Gemini API Key** and **Agent Name** (securely saved with `chmod 600`).

---

## 📲 Standalone On-Device Termux Setup (No PC, No USB Cable)

You can run the entire agent standalone on your Android phone using **Android 11+ Wireless Debugging over Localhost (`127.0.0.1`)**:

1. **Enable Wireless Debugging**:
   * Open Android **Settings > Developer Options > Wireless Debugging** and toggle it **ON**.
2. **Pair with Termux (Once)**:
   * Split-screen or open Termux in a floating/multi-window.
   * Tap **"Pair device with pairing code"** in Developer Options.
   * In Termux, run:
     ```bash
     pair-ai-whatsapp
     ```
   * Enter the 5-digit pairing port and 6-digit code shown on your screen.
3. **Connect to Localhost**:
   * Look at the main Wireless Debugging screen under **"IP address & Port"**.
   * Run:
     ```bash
     connect-ai-whatsapp <PORT>
     ```
     *(Example: `connect-ai-whatsapp 39485`)*
4. **Launch the Agent**:
   ```bash
   start-ai-whatsapp
   ```

*(Whenever your phone reboots or you toggle Wireless Debugging, simply run `connect-ai-whatsapp <NEW_PORT>` to reconnect instantly without re-pairing!)*

---

## 🎮 Command Guide

Once installed, you can run these commands from anywhere in your terminal:

| Command | Description |
| :--- | :--- |
| **`pair-ai-whatsapp`** | Interactively pairs Termux with phone's Wireless Debugging on localhost (`127.0.0.1`). |
| **`connect-ai-whatsapp`** | Connects or reconnects to on-device Wireless ADB (accepts port argument, e.g. `connect-ai-whatsapp 39485`). |
| **`check-ai-whatsapp`** | Runs full diagnostic check (ADB, screen state, calls, keyboard, Gemini quota, WhatsApp UI frames). |
| **`start-ai-whatsapp`** | Starts the agent daemon in the background (prompts for API key if missing). |
| **`minimize-ai-whatsapp`**| Minimizes WhatsApp/terminal and activates silent background mode. |
| **`pause-ai-whatsapp`** | Temporarily pauses auto-replying without stopping the process. |
| **`resume-ai-whatsapp`**| Resumes auto-replying from paused state. |
| **`logout-ai-whatsapp`** | Permanently deletes your stored Gemini API key and prompts to enter a new one. |
| **`stop-ai-whatsapp`**  | Safely shuts down the agent daemon and restores WhatsApp to home. |

---

## 🔒 Security & Privacy

* **Zero Hardcoded Secrets**: No API keys are bundled or shipped inside package code.
* **Local Storage Only**: Your API key is stored locally in `~/.config/whatsapp_ai_agent/config.json` with user-only permissions (`chmod 600`).
* **Complete Independence**: Operates 100% locally on the device with zero cloud telemetry or third-party servers.
