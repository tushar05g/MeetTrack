"""
MeetTrack Bot Account Setup Script
===================================
Run this script ONCE to log into the bot's Google account and save a persistent
browser profile. After running this script, the bot will always be logged in
automatically during meetings.

Usage:
    conda activate meettrack
    python bot/setup_bot_account.py

What it does:
    1. Opens a visible Chrome window
    2. Navigates to Google Sign-In
    3. Waits for you to manually log in as meettrack-bot@gmail.com
    4. Saves the session to bot_profile/ directory
    5. Closes the browser
"""

import os
import sys
import subprocess

def setup():
    profile_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot_profile")
    
    print("=" * 60)
    print("  MeetTrack Bot Account Setup (Native Mode)")
    print("=" * 60)
    print(f"\nThis will open a native Chrome window and save your session to:")
    print(f"  {profile_dir}")
    print("\nPlease log in as: meettrack-bot@gmail.com")
    print("=" * 60)
    input("\nPress Enter to open the browser...")
    
    chrome_bin = "google-chrome"
    for chrome_path in ["google-chrome", "google-chrome-stable", "chromium-browser"]:
        if subprocess.run(["which", chrome_path], capture_output=True).returncode == 0:
            chrome_bin = chrome_path
            break
            
    print("\n[SETUP] Launching Native Chrome...")
    print("[SETUP] Please sign into Google. Once you are done, CLOSE the Chrome window.")
    
    subprocess.run([
        chrome_bin,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://accounts.google.com/signin"
    ])
    
    if os.path.exists(profile_dir) and os.listdir(profile_dir):
        print(f"\n✅ SUCCESS! Bot profile saved to: {profile_dir}")
        print("\nThe MeetTrack bot will now automatically log in as meettrack-bot@gmail.com")
    else:
        print(f"\n❌ WARNING: Profile directory appears empty at: {profile_dir}")

if __name__ == "__main__":
    setup()
