#!/usr/bin/env bash
# MolluskAI installer
#
# Usage (once the repo is public on GitHub):
#   curl -fsSL https://raw.githubusercontent.com/skyl4rk/molluskai/main/install.sh | bash
#
# Or download and run manually:
#   wget https://raw.githubusercontent.com/skyl4rk/molluskai/main/install.sh
#   chmod +x install.sh
#   ./install.sh

set -e  # exit on any error

REPO_URL="https://github.com/skyl4rk/molluskai"
INSTALL_DIR="$HOME/molluskai"
PYTHON="${PYTHON:-python3}"

echo ""
echo "  MolluskAI Installer"
echo "  ───────────────────"
echo ""

# --- Check Python version ---
if ! command -v "$PYTHON" &>/dev/null; then
    echo "Error: python3 not found. Install it with: sudo apt install python3"
    exit 1
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python $PY_VER found."

# --- Check for git or wget/curl ---
if command -v git &>/dev/null; then
    DOWNLOAD_METHOD="git"
elif command -v wget &>/dev/null; then
    DOWNLOAD_METHOD="wget"
elif command -v curl &>/dev/null; then
    DOWNLOAD_METHOD="curl"
else
    echo "Error: git, wget, or curl is required."
    exit 1
fi

# --- Clone or download ---
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists."
    read -r -p "Update existing install? (yes/no): " answer
    if [ "$answer" = "yes" ] || [ "$answer" = "y" ]; then
        if [ -d "$INSTALL_DIR/.git" ]; then
            echo "Pulling latest changes..."
            git -C "$INSTALL_DIR" pull
        else
            echo "Not a git repo — skipping update. Delete $INSTALL_DIR and re-run to reinstall."
            exit 0
        fi
    else
        echo "Skipping download. Using existing files."
    fi
else
    echo "Installing to $INSTALL_DIR ..."
    if [ "$DOWNLOAD_METHOD" = "git" ]; then
        git clone "$REPO_URL" "$INSTALL_DIR"
    elif [ "$DOWNLOAD_METHOD" = "wget" ]; then
        wget -q -O /tmp/molluskai.zip "${REPO_URL}/archive/refs/heads/main.zip"
        unzip -q /tmp/molluskai.zip -d /tmp/
        mv /tmp/molluskai-main "$INSTALL_DIR"
        rm /tmp/molluskai.zip
    else
        curl -fsSL -o /tmp/molluskai.zip "${REPO_URL}/archive/refs/heads/main.zip"
        unzip -q /tmp/molluskai.zip -d /tmp/
        mv /tmp/molluskai-main "$INSTALL_DIR"
        rm /tmp/molluskai.zip
    fi
fi

cd "$INSTALL_DIR"

# --- Create virtual environment ---
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv venv
fi

# Activate venv for this script
# shellcheck source=/dev/null
source venv/bin/activate

# --- Install dependencies ---
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ""
echo "  Installation complete."
echo ""
echo "  To start MolluskAI:"
echo "    cd $INSTALL_DIR"
echo "    source venv/bin/activate"
echo "    python agent.py"
echo ""
echo "  To start automatically on boot, follow the systemd instructions in README.md."
echo ""

# --- Offer to run now ---
read -r -p "Run MolluskAI now? (yes/no): " run_now
if [ "$run_now" = "yes" ] || [ "$run_now" = "y" ]; then
    python agent.py
fi
