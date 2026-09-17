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

import asyncio
import os
import sys

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def setup():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright is not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    profile_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot_profile")
    
    print("=" * 60)
    print("  MeetTrack Bot Account Setup")
    print("=" * 60)
    print(f"\nThis will open a Chrome window and save your session to:")
    print(f"  {profile_dir}")
    print("\nPlease log in as: meettrack-bot@gmail.com")
    print("\nPress Ctrl+C at any time to cancel.")
    print("=" * 60)
    input("\nPress Enter to open the browser...")
    
    async with async_playwright() as p:
        print("\n[SETUP] Launching Chrome with persistent profile...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,  # Must be visible for manual login
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1280,800",
                "--use-fake-ui-for-media-stream",  # Auto-grant mic/camera
                "--use-fake-device-for-media-stream",
            ],
            ignore_default_args=["--enable-automation"],
        )
        
        page = await context.new_page()
        
        print("[SETUP] Navigating to Google Sign-In...")
        await page.goto("https://accounts.google.com/signin", wait_until="domcontentloaded")
        
        print("\n" + "=" * 60)
        print("  ACTION REQUIRED")
        print("=" * 60)
        print("  Please complete the following steps in the Chrome window:")
        print("  1. Sign in with meettrack-bot@gmail.com")
        print("  2. Complete any 2FA if prompted")
        print("  3. Once you see your Google Account page, return here")
        print("=" * 60)
        print("\nWaiting for you to finish logging in...")
        print("(Press Enter in this terminal when you are done)")
        
        # Run a background check while waiting
        done = asyncio.Event()
        
        async def check_logged_in():
            """Poll every 3 seconds to check if the user has successfully logged in."""
            while not done.is_set():
                try:
                    current_url = page.url
                    if "myaccount.google.com" in current_url or "accounts.google.com/o/oauth2" in current_url:
                        print(f"\n[SETUP] ✅ Detected Google account page! You appear to be logged in.")
                except Exception:
                    pass
                await asyncio.sleep(3)
        
        # Run the check concurrently while waiting for user input
        check_task = asyncio.create_task(check_logged_in())
        
        # Wait for user to press Enter
        await asyncio.get_event_loop().run_in_executor(None, input)
        done.set()
        check_task.cancel()
        
        print("\n[SETUP] Saving browser session...")
        await context.close()
        
        # Verify the profile was saved
        if os.path.exists(profile_dir) and os.listdir(profile_dir):
            print(f"\n✅ SUCCESS! Bot profile saved to: {profile_dir}")
            print("\nThe MeetTrack bot will now automatically log in as meettrack-bot@gmail.com")
            print("in all future meetings. No further setup is needed!")
            print("\nNext steps:")
            print("  1. Make sure BOT_EMAIL=meettrack-bot@gmail.com is in your .env file")
            print("  2. Connect your personal Google Calendar in the MeetTrack web app")
            print("  3. Use 'Fetch Upcoming' to auto-invite the bot to your meetings")
        else:
            print(f"\n❌ WARNING: Profile directory appears empty at: {profile_dir}")
            print("Please try running this script again.")

if __name__ == "__main__":
    asyncio.run(setup())
