#!/usr/bin/env python3
"""
Creates clean distribution packages (.tar.gz and .zip) for sharing the WhatsApp AI Agent
to another phone or computer without bundling caches or sensitive files.
"""

import os
import tarfile
import zipfile
from pathlib import Path

BASE_DIR = Path("/home/droid")
OUTPUT_TAR = BASE_DIR / "whatsapp_ai_agent.tar.gz"
OUTPUT_ZIP = BASE_DIR / "whatsapp_ai_agent.zip"

INCLUDE_PATHS = [
    "whatsapp_agent",
    "whatsapp_ai_agent.py",
    "install.sh",
    "install_adb_keyboard.sh",
    "setup_termux_env.sh",
    "ADBKeyboard.apk",
    "README.md",
    "tests"
]

EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    ".git",
    "config.json",
    ".state",
    ".pid",
    ".log",
    "tmp"
]

def should_exclude(path_str):
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False

def make_tar():
    print(f"Creating {OUTPUT_TAR.name}...")
    with tarfile.open(OUTPUT_TAR, "w:gz") as tar:
        for item in INCLUDE_PATHS:
            item_path = BASE_DIR / item
            if item_path.exists():
                if item_path.is_file():
                    tar.add(item_path, arcname=f"whatsapp_ai_agent/{item}")
                else:
                    for root, dirs, files in os.walk(item_path):
                        # Filter out excluded directories in place
                        dirs[:] = [d for d in dirs if not should_exclude(d)]
                        for f in files:
                            full_path = Path(root) / f
                            rel_path = full_path.relative_to(BASE_DIR)
                            if not should_exclude(str(rel_path)):
                                tar.add(full_path, arcname=f"whatsapp_ai_agent/{rel_path}")
    print(f"[✓] Created {OUTPUT_TAR} ({OUTPUT_TAR.stat().st_size // 1024} KB)")

def make_zip():
    print(f"Creating {OUTPUT_ZIP.name}...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in INCLUDE_PATHS:
            item_path = BASE_DIR / item
            if item_path.exists():
                if item_path.is_file():
                    zipf.write(item_path, arcname=f"whatsapp_ai_agent/{item}")
                else:
                    for root, dirs, files in os.walk(item_path):
                        dirs[:] = [d for d in dirs if not should_exclude(d)]
                        for f in files:
                            full_path = Path(root) / f
                            rel_path = full_path.relative_to(BASE_DIR)
                            if not should_exclude(str(rel_path)):
                                zipf.write(full_path, arcname=f"whatsapp_ai_agent/{rel_path}")
    print(f"[✓] Created {OUTPUT_ZIP} ({OUTPUT_ZIP.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    make_tar()
    make_zip()
    print("\n[✓] Distribution bundles ready to share!")
