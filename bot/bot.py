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

async def start_bot(meet_url, output_json, duration_seconds):
    print(f"[BOT] Starting bot for {meet_url}")

    env = os.environ.copy()

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
            print("[BOT] Timed out waiting to be admitted.")
            await screenshot(page, "04_admission_timeout")
            await browser.close()
            sys.exit(1)

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
                            
                            # Deduplication logic
                            if not transcript_data:
                                transcript_data.append({"speaker": speaker, "text": text, "start": time.time() - start_time, "end": time.time() - start_time})
                            else:
                                last = transcript_data[-1]
                                if last['speaker'] == speaker:
                                    # If the text is an extension of the last text, replace it
                                    if text.startswith(last['text']) or last['text'].startswith(text[:10]):
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
        await scrape_loop()

        print("[BOT] Recording complete...")
        
        try:
            await browser.close()
        except Exception as e:
            print(f"[BOT] Browser close warning: {e}")

        print("[BOT] Done. Transcript saved to:", output_json)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python bot.py <meet_url> <output_json> <duration_sec>")
        sys.exit(1)
        
    meet_url = sys.argv[1]
    output_json = sys.argv[2]
    try:
        duration_seconds = int(sys.argv[3])
    except ValueError:
        duration_seconds = 60
        
    try:
        asyncio.run(start_bot(meet_url, output_json, duration_seconds))
    except Exception as e:
        print(f"[BOT] Fatal Error: {e}")
        traceback.print_exc()
        sys.exit(1)
