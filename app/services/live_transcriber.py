import os
import asyncio
import wave
import tempfile
import logging
from app.database import SessionLocal
from app.services.biometrics import extract_voice_embedding, find_speaker
from groq import Groq

logger = logging.getLogger(__name__)

# Audio chunk settings: 5 seconds of 16kHz 16-bit mono audio
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHUNK_SECONDS = 15
CHUNK_SIZE = SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_SECONDS  # 160,000 bytes

# Biometrics runs every 3 seconds of audio
BIOMETRICS_CHUNK_SIZE = SAMPLE_RATE * BYTES_PER_SAMPLE * 3  # 96,000 bytes


class ConnectionManager:
    """Pub/sub broadcast mechanism to push transcripts to connected frontend WebSockets."""

    def __init__(self):
        self.active_connections: dict[str, list] = {}

    async def connect(self, websocket, meeting_id: str):
        await websocket.accept()
        if meeting_id not in self.active_connections:
            self.active_connections[meeting_id] = []
        self.active_connections[meeting_id].append(websocket)

    def disconnect(self, websocket, meeting_id: str):
        if meeting_id in self.active_connections:
            if websocket in self.active_connections[meeting_id]:
                self.active_connections[meeting_id].remove(websocket)
            if not self.active_connections[meeting_id]:
                del self.active_connections[meeting_id]

    async def broadcast_transcript(self, meeting_id: str, transcript: dict):
        if meeting_id not in self.active_connections:
            return
        dead = []
        for connection in self.active_connections[meeting_id]:
            try:
                await connection.send_json(transcript)
            except Exception as e:
                logger.error(f"Error sending to frontend websocket: {e}")
                dead.append(connection)
        for conn in dead:
            self.active_connections[meeting_id].remove(conn)


manager = ConnectionManager()


def _transcribe_chunk(audio_bytes: bytes, speaker_name: str) -> str | None:
    """
    Synchronous function: saves audio bytes to a temp WAV, sends to Groq Whisper,
    returns the transcribed text (or None on failure).
    Designed to be run in a thread pool executor.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            with wave.open(f, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(BYTES_PER_SAMPLE)
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(audio_bytes)

        client = Groq(api_key=api_key)
        with open(path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                file=("chunk.wav", audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="en",
            )
        # result is a plain string when response_format="text"
        text = str(result).strip() if result else ""
        return text if text else None

    except Exception as e:
        logger.error(f"[Groq Whisper] Transcription error: {e}")
        return None
    finally:
        if os.path.exists(path):
            os.remove(path)


def _identify_speaker(audio_bytes: bytes) -> str | None:
    """
    Synchronous function: extracts voice embedding and matches against known users.
    Returns the matched user's name, or None.
    Designed to be run in a thread pool executor.
    """
    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            with wave.open(f, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(BYTES_PER_SAMPLE)
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(audio_bytes)

        embedding = extract_voice_embedding(path)
        db = SessionLocal()
        try:
            user = find_speaker(embedding, db, threshold=0.7)
            return user.name if user else None
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[Biometrics] Speaker identification error: {e}")
        return None
    finally:
        if os.path.exists(path):
            os.remove(path)


async def process_audio_stream(bot_websocket, meeting_id: str):
    """
    Receives raw s16le audio chunks from the bot WebSocket.
    Buffers into 5-second windows and sends to Groq Whisper for transcription.
    Broadcasts results to all connected frontend WebSockets.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("[Groq Whisper] GROQ_API_KEY is not set. Live transcription disabled.")
        # Drain the socket gracefully without crashing
        try:
            while True:
                await bot_websocket.receive_bytes()
        except Exception:
            pass
        return

    logger.info(f"[{meeting_id}] Live transcription started with Groq Whisper (whisper-large-v3-turbo)")

    transcription_buffer = bytearray()
    biometrics_buffer = bytearray()
    current_speaker = "Unknown Speaker"

    loop = asyncio.get_running_loop()

    try:
        while True:
            data = await bot_websocket.receive_bytes()

            transcription_buffer.extend(data)
            biometrics_buffer.extend(data)

            # --- Biometrics: identify speaker every 3 seconds ---
            if len(biometrics_buffer) >= BIOMETRICS_CHUNK_SIZE:
                audio_snapshot = bytes(biometrics_buffer)
                biometrics_buffer.clear()

                async def run_biometrics(audio):
                    nonlocal current_speaker
                    name = await loop.run_in_executor(None, _identify_speaker, audio)
                    if name:
                        current_speaker = name
                        logger.info(f"[{meeting_id}] Speaker identified: {name}")

                asyncio.create_task(run_biometrics(audio_snapshot))

            # --- Transcription: send to Groq Whisper every 5 seconds ---
            if len(transcription_buffer) >= CHUNK_SIZE:
                audio_chunk = bytes(transcription_buffer)
                transcription_buffer.clear()
                speaker_at_time = current_speaker  # capture current value

                async def run_transcription(audio, speaker):
                    text = await loop.run_in_executor(None, _transcribe_chunk, audio, speaker)
                    if text:
                        transcript_data = {
                            "text": text,
                            "is_final": True,
                            "speaker": speaker
                        }
                        logger.info(f"[{meeting_id}] {speaker}: {text}")
                        await manager.broadcast_transcript(meeting_id, transcript_data)

                asyncio.create_task(run_transcription(audio_chunk, speaker_at_time))

    except Exception as e:
        logger.info(f"[{meeting_id}] Bot websocket disconnected: {e}")

    # Flush any remaining audio in the buffer
    if len(transcription_buffer) > SAMPLE_RATE * BYTES_PER_SAMPLE:  # at least 0.5s of audio
        logger.info(f"[{meeting_id}] Flushing remaining {len(transcription_buffer)} bytes...")
        audio_chunk = bytes(transcription_buffer)
        speaker_at_time = current_speaker
        text = await loop.run_in_executor(None, _transcribe_chunk, audio_chunk, speaker_at_time)
        if text:
            await manager.broadcast_transcript(meeting_id, {
                "text": text,
                "is_final": True,
                "speaker": speaker_at_time
            })

    logger.info(f"[{meeting_id}] Live transcription session ended.")
