#!/usr/bin/env bash
# Push WhatsApp AI Agent files directly to Android Device Internal Storage (/storage/emulated/0/ai whatsapp)
set -e

SOURCE_DIR="/home/droid/storage/emulated/0/ai whatsapp"
TARGET_DIR="/storage/emulated/0/ai whatsapp"

echo "======================================================="
echo "   Copying WhatsApp AI Agent to Phone Internal Storage "
echo "======================================================="

# Scenario 1: Running directly on phone inside Termux
if [ -d "/storage/emulated/0" ] && [ -w "/storage/emulated/0" ]; then
    echo "[*] Detected Android environment with storage permissions."
    echo "[*] Copying directly to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    cp -r "$SOURCE_DIR/"* "$TARGET_DIR/"
    echo "[✓] Successfully copied all files to $TARGET_DIR!"
    exit 0
elif [ -d "/storage/emulated/0" ]; then
    echo "[!] /storage/emulated/0 is not writable. Running 'termux-setup-storage'..."
    termux-setup-storage 2>/dev/null || true
    echo "Please grant Storage Permission on your phone screen, then re-run this script."
fi

# Scenario 2: Connected via Wireless ADB (Wi-Fi Debugging)
if command -v adb >/dev/null 2>&1; then
    echo "[*] Checking for connected Wireless ADB device..."
    DEVICE=$(adb devices | grep -E ":[0-9]+" | grep -w "device" | head -n 1 | awk '{print $1}')
    if [ -n "$DEVICE" ]; then
        echo "[✓] Connected Wi-Fi device found: $DEVICE"
        echo "[*] Pushing files to phone internal storage: $TARGET_DIR..."
        adb -s "$DEVICE" shell "mkdir -p '$TARGET_DIR'"
        adb -s "$DEVICE" push "$SOURCE_DIR/." "$TARGET_DIR/"
        echo ""
        echo "[✓] Successfully pushed all files to phone internal storage:"
        echo "    $TARGET_DIR"
        exit 0
    fi
fi

echo "[!] Notice: No connected Wi-Fi ADB device found."
echo "    Files are staged and ready in: $SOURCE_DIR"
echo "    Enable Wireless Debugging on your phone, run 'adb connect <PHONE_IP:PORT>', and re-run:"
echo "    bash ./push_to_phone_storage.sh"
