#!/bin/bash
# Setup script for appartments-scanner GitHub repo
# Run from anywhere — it handles the move and push
set -e

DEST="$HOME/galexand/appartments-scanner"
SRC="$HOME/galexand/lita-home/appartments-scanner"

# Step 0: Move from lita-home to galexand/ if needed
if [ -d "$SRC" ] && [ ! -d "$DEST" ]; then
  echo "Moving repo to $DEST..."
  mv "$SRC" "$DEST"
elif [ ! -d "$DEST" ]; then
  echo "Error: neither $SRC nor $DEST found"
  exit 1
fi

cd "$DEST"

# Step 1: Check for gh CLI
if ! command -v gh &> /dev/null; then
  echo "gh CLI not found. Install with: brew install gh"
  echo "Then run: gh auth login"
  exit 1
fi

# Step 2: Create GitHub repo + init + push
echo "Creating GitHub repo..."
git init
git add .
git commit -m "Initial commit: skill, database, and dashboards"
git branch -M main
gh repo create galexand/appartments-scanner --public --source=. --remote=origin --push \
  --description "Automated real estate scanner for Bucharest apartments"

echo ""
echo "Done! Repo at: https://github.com/galexand/appartments-scanner"
echo "Local path: $DEST"
