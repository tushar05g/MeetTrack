import sys
import os
import time
import json
import asyncio
import subprocess
import traceback
from playwright.async_api import async_playwright

async def screenshot(page, name):
    try:
        screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "uploads", "bot_screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        p = os.path.join(screenshot_dir, f"{name}.png")
        await page.screenshot(path=p, full_page=False)
        print(f"[BOT] Screenshot saved: {p}")
    except Exception as e:
        print(f"[BOT] Screenshot failed ({name}): {e}")

async def start_bot(meet_url, output_audio, output_json, duration_seconds):
    print(f"[BOT] Starting bot for {meet_url}")

    SINK_NAME = "meettrack_bot_sink"
    virtual_sink_module = None

    try:
        # Load a null sink into PulseAudio
        result = subprocess.run(
            f"pactl load-module module-null-sink sink_name={SINK_NAME} sink_properties=device.description=MeetTrackBot",
            shell=True, capture_output=True, text=True, check=True
        )
        virtual_sink_module = result.stdout.strip()
        print(f"[BOT] Virtual PulseAudio sink created (module {virtual_sink_module}).")
    except Exception as e:
        print(f"[BOT] Could not create virtual sink (PulseAudio unavailable?): {e}")
        print("[BOT] Falling back to default audio sink for recording.")

    record_source = f"{SINK_NAME}.monitor" if virtual_sink_module else "default.monitor"

    env = os.environ.copy()
    if virtual_sink_module:
        env["PULSE_SINK"] = SINK_NAME

    async with async_playwright() as p:
        # We must run headless=False to avoid bot detection
        browser = await p.chromium.launch(
            headless=False,
            ignore_default_args=["--enable-automation"],
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--lang=en-US",
                "--window-size=1280,800"
            ],
            env=env
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        await context.grant_permissions(['microphone', 'camera'], origin='https://meet.google.com')

        # Hide webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        print("[BOT] Navigating to Google Meet...")
        try:
            await page.goto(meet_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(4000)
            print(f"[BOT] Page loaded. URL: {page.url}")
            await screenshot(page, "01_page_loaded")
        except Exception as e:
            print(f"[BOT] Failed to load Google Meet page: {e}")
            await screenshot(page, "01_load_error")
            await browser.close()
            sys.exit(1)

        title = await page.title()
        current_url = page.url
        print(f'[BOT] Page title: "{title}" | URL: {current_url}')

        if "accounts.google.com" in current_url:
            print("[BOT] BLOCKED: Redirected to Google Sign-In.")
            await screenshot(page, "02_signin_redirect")
            await browser.close()
            sys.exit(1)

        print("[BOT] Skipping automated name entry. Please manually type the name and click 'Ask to join'.")
        await screenshot(page, "02_before_join_click")

        # Dismiss "Sign in with your Google account" popup
        try:
            got_it_btn = page.locator("button", has_text="Got it").first
            if await got_it_btn.is_visible(timeout=1000):
                await got_it_btn.click()
                print('[BOT] Dismissed "Sign in" popup.')
                await page.wait_for_timeout(800)
        except Exception:
            pass

        await page.wait_for_timeout(1000)

        print("[BOT] Skipping auto-click. Waiting for human to manually click 'Ask to join'...")
        await screenshot(page, "03_after_join_click")

        # Wait until inside the meeting
        print("[BOT] Waiting to be admitted (up to 2 minutes)...")
        try:
            # We wait for any of the main meeting control buttons
            await page.wait_for_function(
                """() => {
                    const selectors = [
                        'button[aria-label*="leave call" i]',
                        'button[aria-label*="meeting details" i]',
                        'button[aria-label*="chat with everyone" i]',
                        'button[aria-label*="show everyone" i]'
                    ];
                    return selectors.some(sel => document.querySelectorAll(sel).length > 0);
                }""",
                timeout=120000
            )
            print("[BOT] Joined the meeting successfully!")
            await screenshot(page, "04_inside_meeting")
            
            print("[BOT] Auto-muting microphone and camera...")
            await page.keyboard.press("Control+d")
            await page.wait_for_timeout(500)
            await page.keyboard.press("Control+e")
            
            try:
                print("[BOT] Minimizing Chrome window...")
                session = await context.new_cdp_session(page)
                res = await session.send("Browser.getWindowForTarget")
                await session.send("Browser.setWindowBounds", {
                    "windowId": res["windowId"],
                    "bounds": {"windowState": "minimized"}
                })
                print("[BOT] Window minimized.")
            except Exception as e:
                print(f"[BOT] Could not minimize window: {e}")
                
        except Exception as e:
            print("[BOT] Timed out waiting to be admitted.")
            await screenshot(page, "04_admission_timeout")
            await browser.close()
            if virtual_sink_module:
                try:
                    subprocess.run(f"pactl unload-module {virtual_sink_module}", shell=True)
                except:
                    pass
            sys.exit(1)

        print(f"[BOT] Starting ffmpeg audio recording from source: {record_source}")
        ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg", "-y", "-f", "pulse", "-i", record_source,
                "-c:a", "libopus", "-b:a", "96k", output_audio
            ],
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"[BOT] Recording audio to: {output_audio}")

        # Try to open the participants panel
        try:
            # We can use Playwright's native locator to find the people button
            people_btn = page.locator('button[aria-label*="people" i], button[aria-label*="show everyone" i]').first
            if await people_btn.is_visible():
                await people_btn.click()
                print("[BOT] Opened participants sidebar.")
            else:
                print("[BOT] Could not find participants button.")
            await page.wait_for_timeout(1500)
            await screenshot(page, "05_participants_panel")
        except Exception as e:
            print(f"[BOT] Error opening participants: {e}")

        participants = set()
        
        async def scrape_loop():
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                try:
                    # Detect if removed or meeting ended
                    body_text = await page.evaluate("document.body.innerText")
                    if "You've been removed" in body_text or "You left the meeting" in body_text or "Return to home screen" in body_text:
                        print("[BOT] Bot was removed or meeting ended. Stopping early.")
                        break
                except Exception as e:
                    print(f"[BOT] Error checking removal status: {e}")
                
                try:
                    elements = await page.locator('[role="listitem"] span[dir="auto"], [role="listitem"] div[dir="auto"]').all_inner_texts()
                    names = [n.strip() for n in elements if n.strip() and n.strip() != "You" and "Presentation" not in n]
                    for name in names:
                        participants.add(name)
                    
                    with open(output_json, "w") as f:
                        json.dump(list(participants), f, indent=2)
                    
                    if names:
                        print(f"[BOT] Current participants: {', '.join(participants)}")
                except Exception:
                    pass
                await asyncio.sleep(5)

        print(f"[BOT] Recording for {duration_seconds} seconds...")
        await scrape_loop()

        print("[BOT] Recording complete. Stopping ffmpeg...")
        
        # Stop ffmpeg gracefully
        ffmpeg_proc.terminate()
        try:
            ffmpeg_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg_proc.kill()

        try:
            await browser.close()
        except Exception as e:
            print(f"[BOT] Browser close warning: {e}")

        if virtual_sink_module:
            try:
                subprocess.run(f"pactl unload-module {virtual_sink_module}", shell=True)
                print("[BOT] Removed virtual PulseAudio sink.")
            except:
                pass

        print("[BOT] Done. Audio saved to:", output_audio)
        print("[BOT] Participants saved to:", output_json)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python bot.py <meet_url> <output_audio> <output_json> <duration_sec>")
        sys.exit(1)
        
    meet_url = sys.argv[1]
    output_audio = sys.argv[2]
    output_json = sys.argv[3]
    try:
        duration_seconds = int(sys.argv[4])
    except ValueError:
        duration_seconds = 60
        
    try:
        asyncio.run(start_bot(meet_url, output_audio, output_json, duration_seconds))
    except Exception as e:
        print(f"[BOT] Fatal Error: {e}")
        traceback.print_exc()
        sys.exit(1)
