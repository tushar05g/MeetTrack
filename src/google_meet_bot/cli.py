import argparse
import os
import tempfile
from dotenv import load_dotenv

# Load .env from current directory or parent directory
parent_env = os.path.abspath(os.path.join(os.getcwd(), "..", ".env"))
if os.path.exists(parent_env):
    load_dotenv(parent_env, override=True)
load_dotenv(override=True)

from .join_google_meet import JoinGoogleMeet
from .speech_to_text import SpeechToText


def main():
    parser = argparse.ArgumentParser(description="Join a Google Meet, record audio, and summarize it.")
    parser.add_argument("--meet-link", dest="meet_link", default=os.getenv("MEET_LINK"), help="Google Meet link")
    parser.add_argument("--duration", dest="duration", type=int, default=int(os.getenv("RECORDING_DURATION", 60)), help="Recording duration in seconds")
    parser.add_argument("--no-analysis", dest="no_analysis", action="store_true", help="Skip analysis phase")
    args = parser.parse_args()

    if not args.meet_link:
        raise SystemExit("--meet-link (or MEET_LINK env) is required")

    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "output.wav")

    bot = JoinGoogleMeet()
    bot.Glogin()
    bot.turnOffMicCam(args.meet_link)
    captions = bot.AskToJoin(audio_path, args.duration)

    if not args.no_analysis:
        try:
            SpeechToText().transcribe(audio_path)
        except Exception as e:
            print(f"\n[Notice] Audio analysis notice: {e}")
            print("Your speaker-attributed transcript is safely saved in 'meeting_transcript.txt' and 'meeting_transcript.json'!")


