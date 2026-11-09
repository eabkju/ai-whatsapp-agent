#!/usr/bin/env bash
# Termux / Terminal Environment Bootstrap for WhatsApp AI Agent
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================="
echo "   WhatsApp AI Agent - Termux / Terminal Bootstrap     "
echo "======================================================="

# 1. Package Installation
if command -v pkg >/dev/null 2>&1; then
    echo "[*] Detected Termux environment. Running package installation..."
    pkg update -y
    pkg install python android-tools termux-api ffmpeg -y
elif command -v apt-get >/dev/null 2>&1; then
    echo "[*] Detected Debian/Linux environment. Running apt package installation..."
    sudo apt-get update -y 2>/dev/null || apt-get update -y
    sudo apt-get install -y python3 python3-pip adb ffmpeg 2>/dev/null || apt-get install -y python3 python3-pip adb ffmpeg
else
    echo "[!] Warning: Neither 'pkg' nor 'apt-get' found. Please ensure Python, ADB, and ffmpeg are installed."
fi

# 2. Automatically install ADBKeyboard
if [ -f "$SCRIPT_DIR/install_adb_keyboard.sh" ]; then
    echo ""
    echo "[*] Running automated ADBKeyboard installer..."
    bash "$SCRIPT_DIR/install_adb_keyboard.sh" || true
fi

# 3. Run Universal Agent Installer
if [ -f "$SCRIPT_DIR/install.sh" ]; then
    echo ""
    echo "[*] Running WhatsApp AI Agent system installer..."
    bash "$SCRIPT_DIR/install.sh"
fi

echo "======================================================="
echo "  [✓] All dependencies and services configured!       "
echo "======================================================="
