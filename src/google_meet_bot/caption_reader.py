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

    def get_caption_language_text(self):
        """Reads the currently displayed caption language text from the Google Meet UI."""
        return self.driver.execute_script("""
            // 1. Check in .rHGeGc-aPP78e (the language pill dropdown container)
            const pillWrapper = document.querySelector('.rHGeGc-aPP78e');
            if (pillWrapper) {
                const btn = pillWrapper.querySelector('button, [role="button"], [role="combobox"]') || pillWrapper;
                const text = (btn.textContent || '').trim();
                if (text) return text;
            }

            // 2. Search for button containing globe icon or language dropdown text
            const buttons = Array.from(document.querySelectorAll('button, div[role="button"], div[role="combobox"]'));
            const langBtn = buttons.find(b => {
                const text = (b.textContent || '').trim();
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                const hasGlobe = b.innerHTML.includes('language') || b.querySelector('svg, i, span');
                return (text.toLowerCase().includes('english') || aria.includes('language') || aria.includes('caption')) &&
                       b.offsetParent !== null;
            });
            if (langBtn) {
                return (langBtn.textContent || '').trim();
            }
            return null;
        """)

    def set_caption_language_to_india(self):
        """
        Switches Google Meet caption language to 'English (India)' and strictly verifies the action.
        Targets the .rHGeGc-aPP78e language pill directly, selects English (India), and verifies the UI text.
        """
        print("[Captions] Checking caption language indicator...")
        time.sleep(2.0)

        # 1. Check current language from the caption toolbar indicator
        current_lang = self.get_caption_language_text()
        if current_lang:
            print(f"[Captions] Current caption language indicator: '{current_lang}'")
            if 'india' in current_lang.lower():
                print("[Captions] Verified: Caption language is already set to 'English (India)'.")
                return True
        else:
            print("[Captions] Language pill not immediately detected; checking overlay...")

        # 2. Strategy A: Click directly on the .rHGeGc-aPP78e caption pill dropdown
        for attempt in range(1, 4):
            print(f"[Captions] Attempt {attempt} to open language dropdown from caption pill...")
            opened_pill = self.driver.execute_script("""
                const pillWrapper = document.querySelector('.rHGeGc-aPP78e');
                if (pillWrapper) {
                    const trigger = pillWrapper.querySelector('button, [role="button"], [role="combobox"]') || pillWrapper;
                    trigger.click();
                    return 'clicked_pill_wrapper';
                }

                // Fallback: Find button with 'English' and dropdown arrow or globe
                const btns = Array.from(document.querySelectorAll('button, div[role="button"], div[role="combobox"]'));
                const langBtn = btns.find(b => {
                    const text = (b.textContent || '').trim();
                    return text.toLowerCase().includes('english') && b.offsetParent !== null;
                });
                if (langBtn) {
                    langBtn.click();
                    return 'clicked_lang_btn';
                }
                return null;
            """)

            if opened_pill:
                print(f"[Captions] Opened dropdown via {opened_pill}. Selecting 'English (India)'...")
                time.sleep(1.2)
                selected = self._select_english_india_option()
                time.sleep(1.5)

                # Strict verification: read the language indicator text
                new_lang = self.get_caption_language_text()
                if new_lang and 'india' in new_lang.lower():
                    print(f"[Captions] Verified: Caption language successfully changed to '{new_lang}'!")
                    return True
                else:
                    print(f"[Captions] Indicator still displays '{new_lang or 'Unknown'}'. Retrying...")

            time.sleep(1.5)

        # 3. Strategy B: Fallback via 3 dots (More options) -> Captions
        print("[Captions] Trying fallback via 3 dots (More options)...")
        try:
            more_btn = self.driver.execute_script("""
                const btns = Array.from(document.querySelectorAll('button'));
                return btns.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    const text = (b.textContent || '').toLowerCase();
                    return (aria.includes('more option') || aria.includes('more call options') || text.includes('more_vert')) && b.offsetParent !== null;
                });
            """)

            if more_btn:
                self.driver.execute_script("arguments[0].click();", more_btn)
                time.sleep(1.0)

                caption_item = self.driver.execute_script("""
                    const items = Array.from(document.querySelectorAll('[role="menuitem"], li, div[jsaction]'));
                    return items.find(el => {
                        const text = (el.textContent || '').trim().toLowerCase();
                        return (text === 'captions' || text.includes('caption') || text.includes('subtitle')) && el.offsetParent !== null;
                    });
                """)

                if caption_item:
                    self.driver.execute_script("arguments[0].click();", caption_item)
                    time.sleep(1.2)
                    self._select_english_india_option()
                    time.sleep(1.2)

            self._close_modals()
        except Exception as e:
            print(f"[Captions] Note during fallback menu navigation: {e}")
            self._close_modals()

        # Final Verification
        final_lang = self.get_caption_language_text()
        if final_lang and 'india' in final_lang.lower():
            print(f"[Captions] Verified: Caption language confirmed as '{final_lang}'.")
            return True
        else:
            print(f"[Captions] Verification result: Language currently shows '{final_lang or 'English'}'.")
            print("[Captions] Because persistent chrome_profile is active, please click on the '🌐 English ▼' dropdown once and select 'English (India)'. Google Meet will remember it permanently.")
            return False

    def _select_english_india_option(self):
        """Finds and selects 'English (India)' from language picker/combobox and applies it."""
        try:
            # 1. Search for elements containing 'English (India)' or 'English (IN)'
            clicked = self.driver.execute_script("""
                const all = Array.from(document.querySelectorAll('[role="option"], [role="menuitem"], [role="menuitemradio"], [role="radio"], li, div[jsaction], span'));
                const indiaOption = all.find(el => {
                    const text = (el.textContent || '').trim().toLowerCase();
                    const isTarget = text === 'english (india)' || text.includes('english (india)') || text === 'english (in)';
                    return isTarget && el.offsetParent !== null && el.children.length <= 2;
                });

                if (indiaOption) {
                    indiaOption.scrollIntoView({ block: 'center' });
                    indiaOption.click();
                    return 'clicked_direct_option';
                }

                // If not found directly, check if a scrollable menu container exists
                const containers = Array.from(document.querySelectorAll('[role="menu"], [role="listbox"], .JPdR6b, .VfPpkd-xl07Ob-XxIAqe'));
                for (const c of containers) {
                    const items = Array.from(c.querySelectorAll('*'));
                    const item = items.find(el => (el.textContent || '').trim().toLowerCase().includes('english (india)'));
                    if (item) {
                        item.scrollIntoView({ block: 'center' });
                        item.click();
                        return 'clicked_container_item';
                    }
                }

                return null;
            """)

            if clicked:
                print(f"[Captions] Clicked English (India) item ({clicked}).")
                time.sleep(0.8)

                # Check if Apply or Save button needs to be clicked
                self.driver.execute_script("""
                    const btns = Array.from(document.querySelectorAll('button'));
                    const applyBtn = btns.find(b => {
                        const text = (b.textContent || '').trim().toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        return (text === 'apply' || text.includes('apply') || aria.includes('apply')) && b.offsetParent !== null;
                    });
                    if (applyBtn) applyBtn.click();
                """)
                return True
        except Exception as e:
            print(f"[Captions] Note during selecting English (India): {e}")
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
