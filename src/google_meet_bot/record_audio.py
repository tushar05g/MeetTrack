import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import os
import threading
import queue
import time
from dotenv import load_dotenv

load_dotenv()


class AudioRecorder:
    def __init__(self):
        self.sample_rate = int(os.getenv('SAMPLE_RATE', 44100))
        self.device = self._find_input_device()
        self.is_recording = False
        self._stop_event = threading.Event()
        self._audio_queue = queue.Queue()
        self._record_thread = None
        self.output_filename = None
        self.start_time = None

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
            print(f"[Audio] Error querying audio devices: {e}")

        return None

    def start_recording(self, filename, max_duration=0):
        """Starts recording audio continuously in the background until stop_recording() is called."""
        self.output_filename = filename
        self._stop_event.clear()
        self.is_recording = True
        self.start_time = time.time()

        if self.device is None:
            print("[Audio] Warning: No audio input device detected. Will generate silent placeholder on finish.")
            return

        try:
            device_info = sd.query_devices(self.device)
            print(f"[Audio] Started continuous recording using #{self.device}: {device_info['name']}")
        except Exception:
            print(f"[Audio] Started continuous recording using device #{self.device}")

        def _worker():
            chunks = []

            def _callback(indata, frames, time_info, status):
                if status:
                    pass
                self._audio_queue.put(indata.copy())

            try:
                with sd.InputStream(samplerate=self.sample_rate, channels=2, dtype='int16', device=self.device, callback=_callback):
                    while not self._stop_event.is_set():
                        if max_duration and max_duration > 0 and (time.time() - self.start_time >= max_duration):
                            break
                        try:
                            chunk = self._audio_queue.get(timeout=0.2)
                            chunks.append(chunk)
                        except queue.Empty:
                            pass

                # Drain remaining chunks
                while not self._audio_queue.empty():
                    chunks.append(self._audio_queue.get_nowait())

                if chunks:
                    full_audio = np.concatenate(chunks, axis=0)
                    write(self.output_filename, self.sample_rate, full_audio)
                    duration_sec = len(full_audio) / self.sample_rate
                    print(f"[Audio] Recording finished ({duration_sec:.1f}s). Saved as {self.output_filename}")
                else:
                    # Write brief placeholder if no chunks captured
                    write(self.output_filename, self.sample_rate, np.zeros((self.sample_rate, 2), dtype='int16'))
            except Exception as e:
                print(f"[Audio] Error during audio stream capture: {e}")
                # Fallback placeholder
                write(self.output_filename, self.sample_rate, np.zeros((self.sample_rate, 2), dtype='int16'))
            finally:
                self.is_recording = False

        self._record_thread = threading.Thread(target=_worker, daemon=True)
        self._record_thread.start()

    def stop_recording(self):
        """Stops the continuous audio recording and ensures file is finalized."""
        if not self.is_recording and (self._record_thread is None or not self._record_thread.is_alive()):
            return

        print("[Audio] Finalizing audio recording...")
        self._stop_event.set()
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=4)
        self.is_recording = False

    def get_audio(self, filename, duration):
        """Legacy synchronous / fixed duration wrapper."""
        self.start_recording(filename, max_duration=duration)
        if duration and duration > 0:
            time.sleep(duration)
            self.stop_recording()
