import sys
import os
import time
import json
import asyncio
import subprocess
import traceback
import re
import websockets
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def screenshot(page, name):
    try:
        screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "uploads", "bot_screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        p = os.path.join(screenshot_dir, f"{name}.png")
        await page.screenshot(path=p, full_page=False)
        print(f"[BOT] Screenshot saved: {p}")
    except Exception as e:
        print(f"[BOT] Screenshot failed ({name}): {e}")

async def start_bot(meet_url, output_audio, output_json, duration_seconds, meeting_id, bot_email="", bot_password=""):
    print(f"[BOT] Starting bot for {meet_url} (meeting_id={meeting_id})")

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
        proxy_server = os.environ.get("MEETTRACK_PROXY_SERVER")
        proxy_username = os.environ.get("MEETTRACK_PROXY_USERNAME")
        proxy_password = os.environ.get("MEETTRACK_PROXY_PASSWORD")
        
        proxy_config = None
        if proxy_server:
            proxy_config = {"server": proxy_server}
            if proxy_username and proxy_password:
                proxy_config["username"] = proxy_username
                proxy_config["password"] = proxy_password

        auth_file = os.path.join(os.path.dirname(__file__), "auth.json")
        profile_dir = os.path.join(os.path.dirname(__file__), "..", "bot_profile")
        


        if os.path.exists(profile_dir):
            print("[BOT] Found persistent profile. Launching persistent context...")
            context_args = {
                "viewport": {"width": 1280, "height": 800}
            }
            context = await p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                channel="chrome",
                ignore_default_args=["--enable-automation"],
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1280,800"
                ],
                proxy=proxy_config,
                env=env,
                **context_args
            )
            browser = None
            page = context.pages[0] if context.pages else await context.new_page()
            
        else:
            print("[BOT] No persistent profile found. Launching standard Playwright Chromium...")
            context_args = {
                "viewport": {"width": 1280, "height": 800}
            }
            if os.path.exists(auth_file):
                print("[BOT] Found existing session in auth.json. Loading it...")
                context_args["storage_state"] = auth_file
                
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
                ignore_default_args=["--enable-automation"],
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1280,800"
                ],
                proxy=proxy_config,
                env=env
            )
            context = await browser.new_context(**context_args)
            page = await context.new_page()

        await context.grant_permissions(['microphone', 'camera'], origin='https://meet.google.com')

        # Hide webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        # In a persistent context, the first page is created BEFORE the init script is added.
        # We must create a new page to guarantee stealth scripts are applied properly, and close the old one.
        new_page = await context.new_page()
        if page:
            await page.close()
        page = new_page



        page.on("console", lambda msg: print(f"[PAGE LOG] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        if bot_email and bot_password and not os.path.exists(profile_dir):
            print(f"[BOT] No persistent profile found. Authenticating with Google Account: {bot_email}...")
            try:
                await page.goto("https://accounts.google.com/signin/v2/identifier", wait_until='domcontentloaded')
                await page.wait_for_selector('input[type="email"]', timeout=10000)
                await page.fill('input[type="email"]', bot_email)
                await page.click('#identifierNext')
                await page.wait_for_timeout(3000)
                
                await page.wait_for_selector('input[type="password"]', timeout=10000)
                await page.fill('input[type="password"]', bot_password)
                await page.click('#passwordNext')
                await page.wait_for_timeout(5000)
                
                if "signin" in page.url:
                    print("[BOT] Waiting for manual 2FA or Captcha... (30 seconds)")
                    await page.wait_for_timeout(30000)
                
                await context.storage_state(path=auth_file)
                print("[BOT] Authentication flow complete. Session saved to auth.json")
            except Exception as e:
                print(f"[BOT] Failed to automate signin: {e}")

        print("[BOT] Navigating to Google Meet...")
        try:
            await page.goto(meet_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(4000)
            print(f"[BOT] Page loaded. URL: {page.url}")
            await screenshot(page, "01_page_loaded")
        except Exception as e:
            print(f"[BOT] Failed to load Google Meet page: {e}")
            await screenshot(page, "01_load_error")
            if browser: await browser.close()
            else: await context.close()
            sys.exit(1)

        title = await page.title()
        current_url = page.url
        print(f'[BOT] Page title: "{title}" | URL: {current_url}')

        if "accounts.google.com" in current_url:
            print("[BOT] Redirected to Google Sign-In (Verify it's you). Attempting to auto-fill or wait for manual verification...")
            await screenshot(page, "02_signin_redirect")
            
            try:
                if bot_password:
                    try:
                        pwd_input = page.locator('input[type="password"]')
                        if await pwd_input.is_visible(timeout=5000):
                            print("[BOT] Found password field, auto-filling...")
                            await pwd_input.fill(bot_password)
                            await page.keyboard.press("Enter")
                    except Exception:
                        pass
                
                print("[BOT] Waiting up to 60 seconds for you to manually verify on the screen...")
                await page.wait_for_url("**/meet.google.com/**", timeout=60000)
                print("[BOT] Verification successful! Proceeding to meeting...")
            except Exception:
                print("[BOT] Verification timed out or failed. Exiting.")
                if browser: await browser.close()
                else: await context.close()
                sys.exit(1)

        print("[BOT] Requesting to join with humanized delays...")
        try:
            print("[BOT] Waiting up to 60 seconds for the 'Join now' or 'Ask to join' button to appear...")
            print("[BOT] If you see a 'Verify it's you' or 'You can't join' error, resolve it manually on the screen now!")
            
            # Wait for either Join button or Ask to join button to be in the DOM
            await page.wait_for_function(
                """() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    return buttons.some(b => b.innerText.includes('Ask to join') || b.innerText.includes('Join now'));
                }""",
                timeout=60000
            )
            
            name_input = page.locator('input[type="text"]')
            if await name_input.is_visible():
                print("[BOT] Not logged in, entering guest name...")
                await name_input.focus()
                await page.wait_for_timeout(500)
                await name_input.press_sequentially("MeetTrack AI Bot", delay=120)
                await page.wait_for_timeout(1500)
            
            print("[BOT] Automation paused. Please click 'Ask to join' or 'Join now' manually in the browser window.")
            # We skip clicking the button so the human can click it.
        except Exception as e:
            print(f"[BOT] Failed to automate name entry: {e}")
            
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
                timeout=300000  # Give human 5 minutes to click and get admitted
            )
            print("[BOT] Joined the meeting successfully!")
            await screenshot(page, "04_inside_meeting")
            
            print("[BOT] Auto-muting microphone and camera...")
            await page.keyboard.press("Control+d")
            await page.wait_for_timeout(500)
            await page.keyboard.press("Control+e")
            await page.wait_for_timeout(500)
            
            try:
                print("[BOT] Turning on Closed Captions...")
                cc_btn = page.locator('button[aria-label*="Turn on captions" i], button[aria-label*="caption" i]').first
                if await cc_btn.is_visible():
                    await cc_btn.click()
                    print("[BOT] Closed Captions enabled.")
                else:
                    print("[BOT] Could not find Closed Captions button. Pressing 'c' key as fallback.")
                    await page.keyboard.press("c")
            except Exception as e:
                print(f"[BOT] Error turning on captions: {e}")
            
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
            print(f"[BOT] Failed waiting to be admitted: {e}")
            await screenshot(page, "04_admission_timeout")
            await page.close()
            if virtual_sink_module:
                try:
                    subprocess.run(f"pactl unload-module {virtual_sink_module}", shell=True)
                except:
                    pass
            sys.exit(1)

        print(f"[BOT] Starting ffmpeg audio recording from source: {record_source}")
        ffmpeg_proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-f", "pulse", "-i", record_source,
            "-ac", "1", "-ar", "16000", output_audio,
            "-f", "s16le", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def stream_ffmpeg():
            try:
                # BUG FIX: Use meeting_id passed directly as an argument, not parsed from filename
                uri = f"ws://localhost:8000/api/bot/stream/{meeting_id}"
                print(f"[BOT] Connecting to streaming WebSocket: {uri}")
                async with websockets.connect(uri) as websocket:
                    chunk_size = 64000
                    while True:
                        data = await ffmpeg_proc.stdout.read(chunk_size)
                        if not data:
                            break
                        await websocket.send(data)
            except Exception as e:
                print(f"[BOT] Audio stream error: {e}")

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

        transcript_data = []
        
        async def scrape_loop():
            start_time = time.time()
            last_text = ""
            
            while time.time() - start_time < duration_seconds:
                try:
                    # Detect if removed or meeting ended
                    body_text = await page.evaluate("document.body.innerText")
                    if "You've been removed" in body_text or "You left the meeting" in body_text or "Return to home screen" in body_text:
                        print("[BOT] Bot was removed or meeting ended. Stopping early.")
                        break
                except Exception as e:
                    pass
                
                try:
                    # Scrape Captions
                    blocks = await page.evaluate("""
                        () => {
                            const results = [];
                            const nameElements = document.querySelectorAll('.zs7s8d, .YTbUzc');
                            nameElements.forEach(nameEl => {
                                const name = nameEl.innerText.trim();
                                const container = nameEl.closest('.a4cQT, div[style*="bottom"]') || nameEl.parentElement.parentElement;
                                if (container) {
                                    const textSpans = container.querySelectorAll('.CNusmb');
                                    let text = Array.from(textSpans).map(span => span.innerText).join(' ').trim();
                                    if (text) {
                                        results.push({speaker: name, text: text});
                                    }
                                }
                            });
                            return results;
                        }
                    """)
                    
                    if blocks:
                        for b in blocks:
                            speaker = b['speaker']
                            text = b['text']
                            
                            # BUG FIX: Skip very short captions to reduce false-positive dedup
                            if len(text) < 3:
                                continue
                            
                            # Deduplication logic
                            if not transcript_data:
                                transcript_data.append({"speaker": speaker, "text": text, "start": time.time() - start_time, "end": time.time() - start_time})
                            else:
                                last = transcript_data[-1]
                                if last['speaker'] == speaker:
                                    if text.startswith(last['text']) or last['text'].startswith(text[:min(10, len(text))]):
                                        last['text'] = text
                                        last['end'] = time.time() - start_time
                                    elif text not in last['text']:
                                        transcript_data.append({"speaker": speaker, "text": text, "start": time.time() - start_time, "end": time.time() - start_time})
                                else:
                                    if text not in last['text'] and text != last_text:
                                        transcript_data.append({"speaker": speaker, "text": text, "start": time.time() - start_time, "end": time.time() - start_time})
                            last_text = text
                    
                    with open(output_json, "w") as f:
                        json.dump(transcript_data, f, indent=2)
                        
                except Exception as e:
                    print(f"[BOT] Caption scrape error: {e}")
                    
                await asyncio.sleep(2)

        print(f"[BOT] Recording for {duration_seconds} seconds...")
        scrape_task = asyncio.create_task(scrape_loop())
        stream_task = asyncio.create_task(stream_ffmpeg())
        
        await scrape_task
        
        print("[BOT] Recording complete. Stopping ffmpeg...")
        try:
            ffmpeg_proc.terminate()
            await ffmpeg_proc.wait()
        except Exception:
            try:
                ffmpeg_proc.kill()
            except:
                pass
                
        await stream_task

        try:
            await page.close()
            if browser:
                await browser.close()
            else:
                await context.close()
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
    if len(sys.argv) < 6:
        print("Usage: python bot.py <meet_url> <output_audio> <output_json> <duration_sec> <meeting_id> [bot_email] [bot_password]")
        sys.exit(1)
        
    meet_url = sys.argv[1]
    output_audio = sys.argv[2]
    output_json = sys.argv[3]
    try:
        duration_seconds = int(sys.argv[4])
    except ValueError:
        duration_seconds = 60

    meeting_id = sys.argv[5]  # BUG FIX: accept meeting_id as direct argument
    bot_email = sys.argv[6] if len(sys.argv) > 6 else ""
    bot_password = sys.argv[7] if len(sys.argv) > 7 else ""
        
    try:
        asyncio.run(start_bot(meet_url, output_audio, output_json, duration_seconds, meeting_id, bot_email, bot_password))
    except Exception as e:
        print(f"[BOT] Fatal Error: {e}")
        traceback.print_exc()
        sys.exit(1)
