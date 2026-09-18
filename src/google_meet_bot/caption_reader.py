import time
import json
import os
from selenium.webdriver.common.by import By


class CaptionReader:
    def __init__(self, driver):
        self.driver = driver
        self.transcript_data = []

    def enable_captions(self):
        """Enables Google Meet live closed captions."""
        print("[Captions] Enabling Closed Captions...")
        time.sleep(2)

        # Strategy 1: Look for CC button
        try:
            cc_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'Turn on captions') or contains(@aria-label, 'turn on captions') or contains(@aria-label, 'caption')]"
            )
            clicked = False
            for btn in cc_buttons:
                aria = btn.get_attribute("aria-label") or ""
                if "turn on" in aria.lower():
                    btn.click()
                    clicked = True
                    print("[Captions] Clicked 'Turn on captions' button.")
                    time.sleep(1)
                    break
            if not clicked:
                # Fallback: Press 'c' keyboard shortcut on body
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.send_keys('c')
                print("[Captions] Pressed 'c' key to enable captions.")
        except Exception as e:
            print(f"[Captions] Note on enabling captions: {e}")

    def is_meeting_ended(self):
        """Detects if the bot was removed or the meeting ended."""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            exit_phrases = [
                "You've been removed",
                "You left the meeting",
                "Return to home screen",
                "The meeting has ended"
            ]
            for phrase in exit_phrases:
                if phrase in body_text:
                    return True
        except Exception:
            pass
        return False

    def capture_during_meeting(self, duration_seconds, poll_interval=1.0):
        """
        Listens to Google Meet captions and extracts speaker-attributed dialogue.
        Deduplicates streaming text in real-time.
        """
        self.enable_captions()
        print(f"\n[Captions] Listening for meeting dialogue for {duration_seconds}s...")
        print("=" * 60)

        start_time = time.time()
        last_printed_idx = 0

        # JavaScript scraper targeting Google Meet caption DOM
        scrape_js = """
            const results = [];
            // Target speaker name elements: .zs7s8d, .YTbUzc, .jxFHg
            const nameElements = document.querySelectorAll('.zs7s8d, .YTbUzc, .jxFHg');

            nameElements.forEach(nameEl => {
                const name = nameEl.innerText ? nameEl.innerText.trim() : '';
                // Target parent subtitle container: .a4cQT, div[jsname="dsyhDe"]
                const container = nameEl.closest('.a4cQT, div[jsname="dsyhDe"], div[style*="bottom"]') || 
                                  nameEl.parentElement.parentElement;

                if (container) {
                    // Subtitle text spans: .CNusmb, .iTTPOb
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

        while time.time() - start_time < duration_seconds:
            # Check for meeting termination
            if self.is_meeting_ended():
                print("\n[Captions] Meeting ended or bot was removed. Finishing capture.")
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
                                # Replace incremental/extending text
                                if text.startswith(last['text']):
                                    last['text'] = text
                                elif last['text'].startswith(text[:15]):
                                    # Streaming update with slight word change
                                    last['text'] = text
                                elif text not in last['text']:
                                    # New sentence from the same speaker
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
