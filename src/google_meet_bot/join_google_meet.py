# import required modules
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import tempfile
from dotenv import load_dotenv

from .record_audio import AudioRecorder
from .speech_to_text import SpeechToText


load_dotenv()


class JoinGoogleMeet:
    def __init__(self):
        self.mail_address = os.getenv('EMAIL_ID')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.bot_name = os.getenv('BOT_NAME', 'Meeting NoteBot')

        # Configure persistent Chrome profile
        profile_dir = os.getenv("CHROME_PROFILE_PATH")
        if not profile_dir:
            profile_dir = os.path.abspath(os.path.join(os.getcwd(), "chrome_profile"))
        os.makedirs(profile_dir, exist_ok=True)
        print(f"Using persistent Chrome profile: {profile_dir}")

        # create chrome instance
        opt = Options()
        opt.add_argument(f'--user-data-dir={profile_dir}')
        opt.add_argument('--no-first-run')
        opt.add_argument('--no-default-browser-check')
        opt.add_argument('--disable-blink-features=AutomationControlled')
        opt.add_argument('--start-maximized')
        opt.add_argument('--use-fake-ui-for-media-stream')
        opt.add_argument('--use-fake-device-for-media-stream')
        opt.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.geolocation": 0,
            "profile.default_content_setting_values.notifications": 1
        })
        self.driver = webdriver.Chrome(options=opt)

    def Glogin(self):
        try:
            # Check if user is already signed in on this persistent profile
            self.driver.get('https://accounts.google.com/')
            time.sleep(2)
            current_url = self.driver.current_url.lower()

            if "myaccount.google.com" in current_url:
                print("Active Google session detected in Chrome profile! Proceeding to meeting...")
                return

            if not self.mail_address or not self.password:
                print("No credentials provided, proceeding as guest or please log in manually in the browser.")
                return

            print("Entering Google credentials...")
            # input Gmail
            id_inputs = self.driver.find_elements(By.ID, "identifierId")
            if id_inputs:
                id_inputs[0].send_keys(self.mail_address)
                self.driver.find_element(By.ID, "identifierNext").click()
                time.sleep(3)

            # input Password
            pwd_inputs = self.driver.find_elements(By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input')
            if pwd_inputs:
                pwd_inputs[0].send_keys(self.password)
                self.driver.find_element(By.ID, "passwordNext").click()
                time.sleep(4)

            # Check if 2FA or security prompt appeared
            if "myaccount.google.com" in self.driver.current_url.lower():
                print("Gmail login activity: Done")
            else:
                print("Note: If Google shows a 2-Step Verification or security prompt, please approve it once in the Chrome browser.")
                print("Your session will remain saved permanently in the chrome_profile folder.")
        except Exception as e:
            print(f"Gmail login notice: {e}")

    def enterNameIfRequired(self):
        # Look for "What's your name?" / "Your name" input field
        time.sleep(2)
        try:
            name_fields = self.driver.find_elements(
                By.XPATH,
                "//input[@placeholder='Your name'] | //input[contains(@aria-label, 'name') or contains(@aria-label, 'Name')] | //input[@type='text' and not(@disabled)]"
            )
            for inp in name_fields:
                if inp.is_displayed():
                    inp.clear()
                    inp.send_keys(self.bot_name)
                    print(f"Automatically entered name: '{self.bot_name}'")
                    time.sleep(1)
                    return True
        except Exception as e:
            print(f"Note on entering name: {e}")
        return False

    def turnOffMicCam(self, meet_link):
        # Navigate to Google Meet URL
        print(f"Navigating to Meet: {meet_link}")
        self.driver.get(meet_link)
        time.sleep(5)  # Allow page and media devices to initialize

        # Dismiss any unexpected dialogs/popups if present
        for dismiss_btn in self.driver.find_elements(By.XPATH, "//button[contains(., 'Dismiss') or contains(., 'Got it')]"):
            try:
                dismiss_btn.click()
                time.sleep(1)
            except Exception:
                pass

        # Strategy 1: Keyboard shortcuts (Ctrl+d for mic, Ctrl+e for camera)
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.CONTROL + 'd')
            time.sleep(1)
            body.send_keys(Keys.CONTROL + 'e')
            time.sleep(1)
            print("Turned off mic and camera via keyboard shortcuts (Ctrl+D, Ctrl+E)")
        except Exception as e:
            print(f"Note: Keyboard shortcut attempt: {e}")

        # Strategy 2: Button clicks with fallback selectors
        try:
            mic_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'microphone') or contains(@aria-label, 'mic') or contains(@aria-label, 'Microphone')] | //div[@role='button' and (contains(@aria-label, 'microphone') or contains(@aria-label, 'mic'))]"
            )
            for btn in mic_buttons:
                aria = btn.get_attribute("aria-label") or ""
                if "turn off" in aria.lower() or "mute" in aria.lower():
                    btn.click()
                    print("Turn off mic activity: Done")
                    break
        except Exception:
            pass

        try:
            cam_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'camera') or contains(@aria-label, 'Camera') or contains(@aria-label, 'video')] | //div[@role='button' and (contains(@aria-label, 'camera') or contains(@aria-label, 'video'))]"
            )
            for btn in cam_buttons:
                aria = btn.get_attribute("aria-label") or ""
                if "turn off" in aria.lower():
                    btn.click()
                    print("Turn off camera activity: Done")
                    break
        except Exception:
            pass

    def checkIfJoined(self):
        try:
            # Wait for in-call elements
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'Leave call') or contains(@aria-label, 'leave call')]"))
            )
            print("Meeting has been joined successfully!")
            return True
        except (TimeoutException, NoSuchElementException):
            print("Waiting to be admitted to the meeting...")
            return False

    def AskToJoin(self, audio_path, duration):
        # 1. Fill name field if prompted (guest joining)
        self.enterNameIfRequired()
        time.sleep(2)

        # 2. Click "Ask to join" or "Join now"
        join_clicked = False
        candidates = [
            (By.XPATH, "//span[@jsname='V67aGc' and contains(text(), 'Ask to join')]/ancestor::button"),
            (By.XPATH, "//span[contains(text(), 'Ask to join') or contains(text(), 'Join now')]/ancestor::button"),
            (By.XPATH, "//span[@jsname='V67aGc' and contains(text(), 'Ask to join')]"),
            (By.XPATH, "//span[contains(text(), 'Ask to join') or contains(text(), 'Join now')]"),
            (By.XPATH, "//button[contains(., 'Ask to join') or contains(., 'Join now')]"),
            (By.XPATH, "//button[contains(@aria-label, 'Ask to join') or contains(@aria-label, 'Join now')]"),
            (By.CSS_SELECTOR, 'button[jsname="Qx7uuf"]'),
        ]

        for attempt in range(3):
            for by, val in candidates:
                try:
                    elem = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((by, val)))
                    try:
                        elem.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", elem)
                    join_clicked = True
                    print("Ask to join / Join now button clicked successfully!")
                    break
                except Exception:
                    continue
            if join_clicked:
                break
            time.sleep(2)

        if not join_clicked:
            print("Note: If the 'Ask to join' or 'Join now' button is visible, you can also click it in the browser.")

        # Brief delay while waiting for host admission
        time.sleep(5)

        # Start live caption capture and audio recording simultaneously
        from .caption_reader import CaptionReader
        import threading

        caption_reader = CaptionReader(self.driver)

        # Audio recording in background
        audio_thread = threading.Thread(
            target=AudioRecorder().get_audio,
            args=(audio_path, duration),
            daemon=True
        )
        audio_thread.start()

        # Stream and capture speaker-attributed captions on main loop
        captions = caption_reader.capture_during_meeting(duration)
        caption_reader.save_transcript()

        audio_thread.join(timeout=5)
        return captions


def _main():
    DO_ANALYSIS = True
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "output.wav")
    # Get configuration from environment variables
    meet_link = os.getenv('MEET_LINK')
    duration = int(os.getenv('RECORDING_DURATION', 60))

    obj = JoinGoogleMeet()
    obj.Glogin()
    obj.turnOffMicCam(meet_link)
    obj.AskToJoin(audio_path, duration)
    if DO_ANALYSIS:
        SpeechToText().transcribe(audio_path)


