import time
import json
import os
from selenium.webdriver.common.by import By


class CaptionReader:
    def __init__(self, driver):
        self.driver = driver
        self.transcript_data = []
        self.has_joined = False

    def enable_captions(self):
        """Enables Google Meet live closed captions using exact tooltip and button mapping."""
        print("[Captions] Enabling Closed Captions...")
        time.sleep(2)

        for attempt in range(1, 4):
            # Strategy 1: Find tooltip and click its associated button
            status = self.driver.execute_script("""
                const tooltips = Array.from(document.querySelectorAll('div[role="tooltip"], .ne2Ple-oshW8e-V67aGc'));
                const ccTooltip = tooltips.find(t => (t.textContent || '').toLowerCase().includes('caption'));

                if (ccTooltip) {
                    const text = ccTooltip.textContent || '';
                    if (text.includes('Turn off captions')) {
                        return 'already_on';
                    }

                    // Find button associated with this tooltip via aria-describedby or proximity
                    const tooltipId = ccTooltip.id;
                    let btn = null;
                    if (tooltipId) {
                        btn = document.querySelector(`button[aria-describedby="${tooltipId}"]`) ||
                              document.querySelector(`[data-tooltip-id="${tooltipId}"]`);
                    }
                    if (!btn) {
                        btn = ccTooltip.closest('button') ||
                              ccTooltip.parentElement?.querySelector('button') ||
                              document.querySelector('button[jsname="r8qRAd"]');
                    }

                    if (btn) {
                        btn.click();
                        return 'clicked_button';
                    }
                }

                // Fallback: search buttons directly by aria-label or jsname
                const allButtons = Array.from(document.querySelectorAll('button'));
                const fallbackBtn = allButtons.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    return aria.includes('caption') || aria.includes('subtitle');
                });
                if (fallbackBtn) {
                    const aria = (fallbackBtn.getAttribute('aria-label') || '').toLowerCase();
                    if (aria.includes('turn off')) return 'already_on';
                    fallbackBtn.click();
                    return 'clicked_fallback';
                }

                return 'not_found';
            """)

            if status == 'already_on':
                print("[Captions] Closed captions are already ON.")
                return True
            elif 'clicked' in status:
                print(f"[Captions] Toggled caption button ({status}).")
                time.sleep(1.5)

            # Strategy 2: Focus page and send Shift+C / C
            try:
                from selenium.webdriver.common.keys import Keys
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.click()
                time.sleep(0.3)
                body.send_keys('c')
                time.sleep(0.5)
                body.send_keys(Keys.SHIFT + 'c')
                print("[Captions] Sent 'c' and 'Shift+C' shortcuts.")
            except Exception as e:
                print(f"[Captions] Note on shortcut: {e}")

            time.sleep(2)

            # Verify using the exact tooltip text provided by Google Meet
            is_active = self.driver.execute_script("""
                const tooltips = Array.from(document.querySelectorAll('div[role="tooltip"], .ne2Ple-oshW8e-V67aGc'));
                const ccTooltip = tooltips.find(t => (t.textContent || '').toLowerCase().includes('caption'));
                if (ccTooltip && ccTooltip.textContent.includes('Turn off captions')) {
                    return true;
                }
                const btns = Array.from(document.querySelectorAll('button'));
                return btns.some(b => (b.getAttribute('aria-label') || '').toLowerCase().includes('turn off caption'));
            """)

            if is_active:
                print("[Captions] Confirmed: Live Captions are active and ON!")
                return True

        print("[Captions] Notice: If captions did not turn on automatically, please click the CC button in the browser.")
        return False

    def set_caption_language_to_india(self):
        """
        Switches Google Meet caption language to 'English (India)'.
        Google Meet has a dedicated English (India) acoustic model that recognizes
        'Am I audible', 'mic testing', and Indian pronunciation with high accuracy.
        Because chrome_profile is persistent, Google Meet will remember this permanently.
        """
        print("[Captions] Checking/Setting caption language to 'English (India)'...")
        time.sleep(1.0)

        try:
            # 1. Click 3 dots button (More options)
            opened_more = self.driver.execute_script("""
                const btns = Array.from(document.querySelectorAll('button'));
                const moreBtn = btns.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    const text = (b.textContent || '').toLowerCase();
                    return (aria.includes('more option') || aria.includes('more call options') || text.includes('more_vert')) && b.offsetParent !== null;
                });
                if (moreBtn) {
                    moreBtn.click();
                    return true;
                }
                return false;
            """)

            if not opened_more:
                print("[Captions] Could not find 3 dots 'More options' button.")
                return False

            time.sleep(1.0)

            # 2. Look for 'Captions' item in the options menu
            caption_menu_clicked = self.driver.execute_script("""
                const items = Array.from(document.querySelectorAll('[role="menuitem"], li, div[jsaction]'));
                const ccItem = items.find(el => {
                    const text = (el.textContent || '').trim().toLowerCase();
                    return (text === 'captions' || text.includes('caption') || text.includes('subtitle')) && el.offsetParent !== null;
                });
                if (ccItem) {
                    ccItem.click();
                    return true;
                }
                return false;
            """)

            if caption_menu_clicked:
                time.sleep(1.0)
                if self._select_english_india_option():
                    print("[Captions] Caption language switched to 'English (India)'.")
                    return True

            # If 'Captions' wasn't directly in menu or didn't open language picker, check 'Settings'
            settings_clicked = self.driver.execute_script("""
                const items = Array.from(document.querySelectorAll('[role="menuitem"], li, div[jsaction]'));
                const settingsItem = items.find(el => {
                    const text = (el.textContent || '').trim().toLowerCase();
                    return text.includes('settings') && el.offsetParent !== null;
                });
                if (settingsItem) {
                    settingsItem.click();
                    return true;
                }
                return false;
            """)

            if settings_clicked:
                time.sleep(1.2)
                # Click 'Captions' tab inside Settings modal
                self.driver.execute_script("""
                    const tabs = Array.from(document.querySelectorAll('[role="tab"], div[jsname], span'));
                    const ccTab = tabs.find(el => (el.textContent || '').trim().toLowerCase() === 'captions' && el.offsetParent !== null);
                    if (ccTab) ccTab.click();
                """)
                time.sleep(1.0)

                if self._select_english_india_option():
                    print("[Captions] Caption language set to 'English (India)' via Settings.")
                    self._close_modals()
                    return True

            self._close_modals()
        except Exception as e:
            print(f"[Captions] Note during caption language setup: {e}")
            self._close_modals()

        print("[Captions] Note: Because chrome_profile is persistent, you can also change language once in Google Meet: 3 dots -> Captions -> English (India). Google Meet will remember it permanently.")
        return False

    def _select_english_india_option(self):
        """Finds and selects 'English (India)' from language picker/combobox and applies it."""
        try:
            # Check if combobox / dropdown is present and click to expand
            self.driver.execute_script("""
                const boxes = Array.from(document.querySelectorAll('[role="combobox"], [role="listbox"], div[aria-haspopup="listbox"]'));
                for (const b of boxes) {
                    if (b.offsetParent !== null) {
                        b.click();
                        break;
                    }
                }
            """)
            time.sleep(0.8)

            # Search for English (India) element
            selected = self.driver.execute_script("""
                const all = Array.from(document.querySelectorAll('[role="option"], [role="radio"], [role="menuitemradio"], li, span, div'));
                const indiaOption = all.find(el => {
                    const text = (el.textContent || '').trim().toLowerCase();
                    return (text === 'english (india)' || text.includes('english (india)')) && el.offsetParent !== null;
                });
                if (indiaOption) {
                    indiaOption.click();
                    return true;
                }
                return false;
            """)

            if selected:
                time.sleep(0.8)
                # Look for Apply or Save button
                self.driver.execute_script("""
                    const btns = Array.from(document.querySelectorAll('button'));
                    const applyBtn = btns.find(b => {
                        const text = (b.textContent || '').trim().toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        return (text === 'apply' || text.includes('apply') || aria.includes('apply')) && b.offsetParent !== null;
                    });
                    if (applyBtn) {
                        applyBtn.click();
                        return true;
                    }
                    return false;
                """)
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"[Captions] Note in selecting English (India): {e}")
        return False

    def _close_modals(self):
        """Closes any open menus or dialogs via Escape key."""
        try:
            from selenium.webdriver.common.keys import Keys
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.3)
            body.send_keys(Keys.ESCAPE)
        except Exception:
            pass


    def wait_until_in_call(self, timeout=45):
        """Waits until the bot is admitted and the meeting room UI is active."""
        print("[Bot] Waiting to be admitted to the meeting room...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                in_call_elements = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Leave call') or contains(@aria-label, 'leave call') or contains(@aria-label, 'Chat') or contains(@aria-label, 'show everyone')]"
                )
                if in_call_elements:
                    print("[Bot] Confirmed inside the meeting room!")
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False

    def is_meeting_ended(self):
        """Detects if the bot was removed, alone, or the meeting ended after joining."""
        if not self.has_joined:
            return False

        try:
            # 1. Check if in-call leave/control buttons disappeared
            in_call = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'Leave call') or contains(@aria-label, 'leave call') or contains(@jsname, 'CQylAd')]"
            )
            if not in_call:
                time.sleep(2)
                in_call = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Leave call') or contains(@aria-label, 'leave call')]"
                )
                if not in_call:
                    print("\n[Bot] In-call controls no longer present. Meeting has ended.")
                    return True

            # 2. Check for text indicators
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            exit_phrases = [
                "You've been removed",
                "You left the meeting",
                "The meeting has ended",
                "Return to home screen",
                "Everyone else has left",
                "You're the only one here"
            ]
            for phrase in exit_phrases:
                if phrase in body_text:
                    print(f"\n[Bot] Detected meeting exit condition: '{phrase}'.")
                    return True
        except Exception:
            pass
        return False

    def capture_during_meeting(self, duration_seconds=0, poll_interval=1.0):
        """
        Listens to Google Meet captions and extracts speaker-attributed dialogue.
        If duration_seconds <= 0, stays in the meeting continuously until it ends or bot is removed.
        """
        # Wait until admitted inside meeting
        self.has_joined = self.wait_until_in_call(timeout=60)

        # Enable captions once inside
        self.enable_captions()

        # Switch captions language to English (India)
        self.set_caption_language_to_india()

        if duration_seconds and duration_seconds > 0:
            print(f"\n[Captions] Listening for meeting dialogue for {duration_seconds}s (or until meeting ends)...")
        else:
            print("\n[Captions] Listening continuously until the meeting ends or bot is removed...")
            print("[Captions] (You can also press Ctrl+C anytime to stop and save the transcript)")
        print("=" * 60)

        start_time = time.time()
        last_printed_idx = 0

        # JavaScript scraper targeting Google Meet caption DOM
        scrape_js = """
            const results = [];
            const nameElements = document.querySelectorAll('.zs7s8d, .YTbUzc, .jxFHg');

            nameElements.forEach(nameEl => {
                const name = nameEl.innerText ? nameEl.innerText.trim() : '';
                const container = nameEl.closest('.a4cQT, div[jsname="dsyhDe"], div[style*="bottom"]') || 
                                  nameEl.parentElement.parentElement;

                if (container) {
                    const textSpans = container.querySelectorAll('.CNusmb, .iTTPOb');
                    let text = '';
                    if (textSpans.length > 0) {
                        text = Array.from(textSpans).map(s => s.innerText).join(' ').trim();
                    } else {
                        text = container.innerText.replace(name, '').trim();
                    }

                    if (name && text) {
                        results.push({ speaker: name, text: text });
                    }
                }
            });
            return results;
        """

        try:
            while True:
                # If a positive duration was set, stop when duration expires
                if duration_seconds and duration_seconds > 0:
                    if time.time() - start_time >= duration_seconds:
                        print(f"\n[Captions] Configured duration ({duration_seconds}s) reached.")
                        break

                # Check if meeting has ended
                if self.is_meeting_ended():
                    break

                try:
                    blocks = self.driver.execute_script(scrape_js)

                    if blocks:
                        for b in blocks:
                            speaker = b.get('speaker', '').strip()
                            text = b.get('text', '').strip()

                            if not speaker or not text:
                                continue

                            current_ts = time.strftime("%I:%M:%S %p")

                            if not self.transcript_data:
                                self.transcript_data.append({
                                    'speaker': speaker,
                                    'text': text,
                                    'timestamp': current_ts
                                })
                            else:
                                last = self.transcript_data[-1]

                                # Same speaker continues speaking
                                if last['speaker'] == speaker:
                                    if text.startswith(last['text']):
                                        last['text'] = text
                                    elif last['text'].startswith(text[:15]):
                                        last['text'] = text
                                    elif text not in last['text']:
                                        last['text'] = last['text'] + " " + text
                                else:
                                    # Different speaker started speaking
                                    self.transcript_data.append({
                                        'speaker': speaker,
                                        'text': text,
                                        'timestamp': current_ts
                                    })

                    # Print newly completed dialogue entries to console in real-time
                    if len(self.transcript_data) > 1 and len(self.transcript_data) - 1 > last_printed_idx:
                        for item in self.transcript_data[last_printed_idx:len(self.transcript_data) - 1]:
                            print(f"[{item['timestamp']}] {item['speaker']}: {item['text']}")
                        last_printed_idx = len(self.transcript_data) - 1

                except Exception:
                    pass

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n[Captions] Stopped by user (Ctrl+C). Finalizing transcript...")

        # Print final dialogue entry
        if self.transcript_data and last_printed_idx < len(self.transcript_data):
            for item in self.transcript_data[last_printed_idx:]:
                print(f"[{item['timestamp']}] {item['speaker']}: {item['text']}")

        print("=" * 60)
        print(f"[Captions] Capture complete. Captured {len(self.transcript_data)} dialogue turn(s).")
        return self.transcript_data

    def save_transcript(self, output_dir=None):
        """Saves formatted speaker transcript to TXT and JSON."""
        if not output_dir:
            output_dir = os.getcwd()
        os.makedirs(output_dir, exist_ok=True)

        txt_file = os.path.join(output_dir, "meeting_transcript.txt")
        json_file = os.path.join(output_dir, "meeting_transcript.json")

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("=== GOOGLE MEET SPEAKER-ATTRIBUTED TRANSCRIPT ===\n\n")
            if not self.transcript_data:
                f.write("(No speech or captions were detected during this meeting)\n")
            for item in self.transcript_data:
                f.write(f"[{item['timestamp']}] {item['speaker']}:\n{item['text']}\n\n")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.transcript_data, f, indent=2, ensure_ascii=False)

        print(f"[Captions] Transcript files saved:")
        print(f"  - TXT:  {txt_file}")
        print(f"  - JSON: {json_file}")
        return txt_file, json_file
