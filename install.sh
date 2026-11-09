#!/usr/bin/env bash
# Universal Installer for WhatsApp AI Agent (Standard Linux / Android Termux)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing WhatsApp AI Agent from: $SCRIPT_DIR"

# Target directories
LOCAL_BIN="$HOME/.local/bin"
TERMUX_BIN="/data/data/com.termux/files/usr/bin"
if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ]; then
    TERMUX_BIN="$PREFIX/bin"
fi

mkdir -p "$LOCAL_BIN"
if [ -d "$(dirname "$TERMUX_BIN")" ]; then
    mkdir -p "$TERMUX_BIN" 2>/dev/null || true
fi

COMMANDS=(
    "start-ai-whatsapp"
    "pause-ai-whatsapp"
    "resume-ai-whatsapp"
    "stop-ai-whatsapp"
    "minimize-ai-whatsapp"
    "logout-ai-whatsapp"
    "check-ai-whatsapp"
    "pair-ai-whatsapp"
    "connect-ai-whatsapp"
)

for cmd in "${COMMANDS[@]}"; do
    SRC="$LOCAL_BIN/$cmd"
    ACTION="$(echo "$cmd" | sed 's/-ai-whatsapp//')"
    cat << EOF > "$SRC"
#!/usr/bin/env bash
export PYTHONPATH="$SCRIPT_DIR:\${PYTHONPATH}"
exec python3 -m whatsapp_agent.cli.commands "$ACTION" "\$@"
EOF
    chmod +x "$SRC"
    echo "[✓] Configured in $LOCAL_BIN/$cmd"

    # Install into Termux bin if directory exists and is writable
    if [ -d "$TERMUX_BIN" ] && [ -w "$TERMUX_BIN" ]; then
        cp -f "$SRC" "$TERMUX_BIN/$cmd"
        chmod +x "$TERMUX_BIN/$cmd"
        echo "[✓] Configured in $TERMUX_BIN/$cmd"
    fi
done

# Ensure PATH in ~/.bashrc and ~/.profile
for rc in "$HOME/.bashrc" "$HOME/.profile"; do
    if [ -f "$rc" ]; then
        if ! grep -q "\.local/bin" "$rc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
        if [ -d "$TERMUX_BIN" ] && ! grep -q "$TERMUX_BIN" "$rc"; then
            echo "export PATH=\"$TERMUX_BIN:\$PATH\"" >> "$rc"
        fi
    fi
done

# Automatically install & enable ADBKeyboard if script is present
if [ -f "$SCRIPT_DIR/install_adb_keyboard.sh" ]; then
    echo ""
    echo "[*] Checking & Installing ADBKeyboard..."
    bash "$SCRIPT_DIR/install_adb_keyboard.sh" || true
fi

echo ""
echo "Installation completed! Running initial hardware & UI onboarding..."
python3 -m whatsapp_agent.cli.setup_wizard
