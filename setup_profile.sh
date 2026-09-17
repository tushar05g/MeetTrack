#!/bin/bash

# Get the absolute path to the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_DIR="$PROJECT_ROOT/bot_profile"
mkdir -p "$PROFILE_DIR"

# Try to find a Chrome or Chromium binary on the system
CHROME_BIN=$(which google-chrome || which google-chrome-stable || which chromium-browser || which chromium || echo "")

if [ -z "$CHROME_BIN" ]; then
    # Fallback to Playwright's Chromium if system Chrome isn't found
    PLAYWRIGHT_CHROME=$(find ~/.cache/ms-playwright -name "chrome" -type f -executable 2>/dev/null | head -n 1)
    if [ -z "$PLAYWRIGHT_CHROME" ]; then
        echo "Could not find a Chrome or Chromium binary."
        exit 1
    fi
    CHROME_BIN=$PLAYWRIGHT_CHROME
fi

echo "=================================================="
echo "      MeetTrack Bot Profile Setup"
echo "=================================================="
echo "Launching a normal, un-automated Chrome browser..."
echo ""
echo "INSTRUCTIONS:"
echo "1. Log in to the Google Account you want the bot to use."
echo "2. Once you are successfully on your Google Account dashboard, CLOSE the entire browser window."
echo "3. The bot will use these saved cookies to bypass Google's bot detection!"
echo "=================================================="

"$CHROME_BIN" --user-data-dir="$PROFILE_DIR" "https://accounts.google.com"

echo ""
echo "Profile saved! You can now use the bot."
