# WhatsApp AI Auto-Reply Agent (v2.1)

Intelligent, multilingual auto-reply agent for WhatsApp powered by **Google Gemini AI** and **ADB / ADBKeyboard**. Designed to run standalone on Android (via Termux) or on any Linux / macOS / Windows PC connected to an Android phone.

---

## 🚀 Key Features

* **Sub-2/3s Response & Zero-Delay Sweep**: Instant detection of unread messages with immediate follow-up scans.
* **8-Second Dynamic Cooldown & FIFO Fairness**: Prevents duplicate spamming while answering contacts strictly in order of arrival.
* **Smart Keyboard Switching**: Uses `ADBKeyboard` strictly for 1–2 seconds to send Unicode text, then immediately restores your personal keyboard (Gboard, Samsung Keyboard, etc.).
* **User Interference & 15s Idle Reset**: Yields instantly when you touch the screen or type; automatically resumes after 15 seconds of inactivity.
* **Non-Intrusive Background Operation**: Never forces WhatsApp to pop up over active apps (e.g. YouTube, Browser) while replying; provides an ongoing 50-second status notification.
* **Multimodal Intelligence**: Analyzes incoming photos (`gemini-2.0-flash` Vision) and listens to voice notes (`gemini-2.0-flash` Audio) to send contextual text replies.
* **Privacy & Safety Guardrails**: Zero cross-contact data leakage, natural Islamic etiquette (*Assalamu Alaikum*, *Alhamdulillah*, *InshaALLAH*, *Allah Hafez*), and strict deterministic medical advice disclaimer.
* **Hardware Resilience**: Automatically pauses during incoming or active phone calls; suspends while screen is locked and resumes cleanly when unlocked.
* **USB Debugging Priority**: Automatically detects and prioritizes USB-OTG/USB cable over Wi-Fi for zero latency and rock-solid stability.

---

## 📱 Prerequisites on the Target Device

### 1. Enable Android Developer Options & USB Debugging
1. Go to **Settings > About Phone** and tap **Build Number** 7 times to enable Developer Options.
2. Go to **Settings > Developer Options**:
   * Enable **USB Debugging** (or **Wireless Debugging** if connecting without cable).
   * Enable **Disable Permission Monitoring** (if available on your device).

### 2. Install ADBKeyboard (Required for Unicode & Bengali/Hindi text)
1. Download & install the free open-source APK:
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
   * Install all 7 CLI commands in `$PREFIX/bin` (Termux) and `~/.local/bin`.
   * Configure background wake-locks and battery optimization exemptions.
   * Verify your ADB connection (USB or Wi-Fi).
   * Prompt you for your **Google Gemini API Key** and **Agent Name** (securely saved with `chmod 600`).

---

## 🎮 Command Guide

Once installed, you can run these commands from anywhere in your terminal:

| Command | Description |
| :--- | :--- |
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
