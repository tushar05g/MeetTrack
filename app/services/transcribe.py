import os
from faster_whisper import WhisperModel

def transcribe_audio(audio_path, model_size="small", compute_type="default"):
    """
    Transcribe audio locally using faster-whisper.
    """
    print(f"Loading faster-whisper model '{model_size}'...")
    
    # Try to load on GPU first, fallback to CPU
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
    except Exception:
        print("CUDA not available or failed. Falling back to CPU.")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"Transcribing {audio_path}...")
    segments, info = model.transcribe(
        audio_path, 
        beam_size=5, 
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_speech_duration_ms=250, threshold=0.2)
    )

    print(f"Detected language '{info.language}' with probability {info.language_probability}")

    raw_segments = []
    for segment in segments:
        raw_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "speaker": "SPEAKER_00",  # Placeholder, will be diarized next
            "words": [] # We could extract words if word_timestamps=True
        })

    print("Freed GPU memory after transcription.")
    return raw_segments

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)
    results = transcribe_audio(sys.argv[1])
    for res in results:
        print(f"[{res['start']:.2f}s - {res['end']:.2f}s] {res.get('text', '')}")
