#!/usr/bin/env bash
# Build a clean distributable zip of MolluskAI.
#
# Usage:
#   chmod +x make_dist.sh
#   ./make_dist.sh
#
# Creates: molluskai-dist.zip in the project root.
# The zip contains a molluskai/ directory ready to extract and run.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_ZIP="$SCRIPT_DIR/molluskai-dist.zip"

# Files and directories to include
INCLUDE=(
    "agent.py"
    "config.py"
    "llm.py"
    "memory.py"
    "onboarding.py"
    "scheduler.py"
    "telegram_bot.py"
    "IDENTITY.md"
    "README.md"
    "FEASIBILITY.md"
    "IMPLEMENTATION.md"
    "LICENSE"
    "requirements.txt"
    "install.sh"
    ".env.example"
    ".gitignore"
    "skills/"
    "tasks/"
    "data/.gitkeep"
)

echo "Building molluskai-dist.zip..."

# Remove old zip if it exists
rm -f "$OUT_ZIP"

cd "$SCRIPT_DIR"

# Build zip with molluskai/ prefix so it extracts cleanly into its own directory
for item in "${INCLUDE[@]}"; do
    if [ -e "$item" ]; then
        zip -r --quiet "$OUT_ZIP" "$item" \
            --exclude "*.pyc" \
            --exclude "*/__pycache__/*" \
            --exclude "*/venv/*"
    else
        echo "  Warning: $item not found, skipping."
    fi
done

# Wrap everything in a molluskai/ directory
TMPDIR=$(mktemp -d)
mkdir "$TMPDIR/molluskai"
unzip -q "$OUT_ZIP" -d "$TMPDIR/molluskai"
rm "$OUT_ZIP"
cd "$TMPDIR"
zip -r --quiet "$OUT_ZIP" molluskai/
cd "$SCRIPT_DIR"
rm -rf "$TMPDIR"

SIZE=$(du -sh "$OUT_ZIP" | cut -f1)
echo "Done: molluskai-dist.zip ($SIZE)"
echo ""
echo "Install on another machine with:"
echo "  wget <your-url>/molluskai-dist.zip"
echo "  unzip molluskai-dist.zip"
echo "  cd molluskai"
echo "  python3 -m venv venv && source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  python agent.py"
