import sounddevice as sd
from scipy.io.wavfile import write
import os
from dotenv import load_dotenv

load_dotenv()

class AudioRecorder:
    def __init__(self):
        self.sample_rate = int(os.getenv('SAMPLE_RATE', 44100))
        self.device = self._find_input_device()

    def _find_input_device(self):
        # 1. Custom device from .env
        env_dev = os.getenv('AUDIO_DEVICE')
        if env_dev is not None and env_dev.strip() != "":
            try:
                return int(env_dev)
            except ValueError:
                return env_dev

        # 2. Check if default system input is valid
        try:
            default_in = sd.default.device[0]
            if default_in is not None and default_in >= 0:
                return default_in
        except Exception:
            pass

        # 3. Prefer "Stereo Mix" or any device with input channels > 0
        try:
            devices = sd.query_devices()
            # Try to find Stereo Mix (captures system/meeting sound)
            for idx, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0 and 'stereo mix' in dev.get('name', '').lower():
                    return idx

            # Fallback to any input device
            for idx, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0:
                    return idx
        except Exception as e:
            print(f"Error querying audio devices: {e}")

        return None

    def get_audio(self, filename, duration):
        print("Recording...")
        if self.device is None:
            print("Warning: No audio input device or microphone detected. Creating placeholder audio file.")
            import numpy as np
            empty_recording = np.zeros((int(duration * self.sample_rate), 2), dtype='int16')
            write(filename, self.sample_rate, empty_recording)
            print(f"Placeholder audio saved as {filename}.")
            return

        try:
            device_info = sd.query_devices(self.device)
            print(f"Recording using device #{self.device}: {device_info['name']}")
        except Exception:
            pass

        try:
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=2,
                dtype='int16',
                device=self.device
            )
            sd.wait()  # Wait until the recording is finished
            write(filename, self.sample_rate, recording)
            print(f"Recording finished. Saved as {filename}.")
        except Exception as e:
            print(f"Audio recording error: {e}. Writing placeholder file so workflow continues.")
            import numpy as np
            empty_recording = np.zeros((int(duration * self.sample_rate), 2), dtype='int16')
            write(filename, self.sample_rate, empty_recording)
