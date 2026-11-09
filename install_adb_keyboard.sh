#!/usr/bin/env bash
# Automated ADBKeyboard Installer & Activator for Android
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APK_PATH="$SCRIPT_DIR/ADBKeyboard.apk"
GITHUB_APK_URL="https://github.com/senzhk/ADBKeyBoard/raw/master/bin/ADBKeyboard.apk"

echo "======================================================="
echo "       Automated ADBKeyboard Installer & Activator     "
echo "======================================================="

# 1. Check if ADB is available
if ! command -v adb >/dev/null 2>&1; then
    echo "[!] Error: 'adb' command not found. Please install android-tools first."
    exit 1
fi

# 2. Check for connected device (USB prioritized)
DEVICE_OUT=$(adb devices -l | grep -w "device" || true)
if [ -z "$DEVICE_OUT" ]; then
    echo "[!] No ADB device connected. Trying to connect to 127.0.0.1:5555 or USB..."
    adb connect 127.0.0.1:5555 2>/dev/null || true
    sleep 1
fi

# Re-check device
DEVICE=$(adb devices | grep -w "device" | head -n 1 | awk '{print $1}')
if [ -z "$DEVICE" ]; then
    echo "[✗] No connected Android device found via ADB."
    echo "    Please connect your phone via USB cable (USB Debugging ON) or Wi-Fi."
    exit 1
fi

echo "[✓] Target Device detected: $DEVICE"

# 3. Ensure APK is present (download if missing)
if [ ! -f "$APK_PATH" ] || [ ! -s "$APK_PATH" ]; then
    echo "[*] Downloading ADBKeyboard.apk from GitHub..."
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$APK_PATH" "$GITHUB_APK_URL"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$APK_PATH" "$GITHUB_APK_URL"
    else
        echo "[!] Error: Neither curl nor wget is available to download ADBKeyboard.apk."
        exit 1
    fi
fi

# 4. Install ADBKeyboard on the device
echo "[*] Installing ADBKeyboard.apk onto device..."
adb -s "$DEVICE" install -r -g "$APK_PATH" || adb -s "$DEVICE" install -r "$APK_PATH"

# 5. Enable ADBKeyboard IME
echo "[*] Enabling ADBKeyboard input method..."
adb -s "$DEVICE" shell ime enable com.android.adbkeyboard/.AdbIME 2>/dev/null || true

# 6. Set as default IME
echo "[*] Activating ADBKeyboard as active IME..."
adb -s "$DEVICE" shell ime set com.android.adbkeyboard/.AdbIME 2>/dev/null || true

# 7. Verify
CURRENT_IME=$(adb -s "$DEVICE" shell settings get secure default_input_method 2>/dev/null || true)
if echo "$CURRENT_IME" | grep -q "com.android.adbkeyboard"; then
    echo "[✓] ADBKeyboard successfully installed and activated!"
else
    echo "[!] ADBKeyboard installed. If prompted on your phone screen, approve enabling 'ADB Keyboard' in Settings."
fi

echo "======================================================="
