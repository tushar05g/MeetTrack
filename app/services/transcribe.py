import gc
import torch
from faster_whisper import WhisperModel

def transcribe_audio(audio_path, model_size="small", compute_type="int8"):
    """
    Transcribe audio using faster-whisper.
    """
    print(f"Loading faster-whisper model '{model_size}'...")
    # Load model. We use int8 for GTX 1050 Ti to avoid float16 compatibility issues
    model = WhisperModel(model_size, device="cuda", compute_type=compute_type)
    
    print(f"Transcribing {audio_path}...")
    segments_generator, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)
    
    print(f"Detected language '{info.language}' with probability {info.language_probability}")
    
    segments = []
    for segment in segments_generator:
        # Convert to dictionary format for easier pipeline handling
        seg_dict = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "words": [{"word": w.word.strip(), "start": w.start, "end": w.end, "score": w.probability} for w in segment.words]
        }
        segments.append(seg_dict)
        
    # Crucial step for 4GB VRAM: explicitly free GPU memory
    del model
    gc.collect()
    torch.cuda.empty_cache()
    print("Freed GPU memory after transcription.")
    
    return segments

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    results = transcribe_audio(audio_file)
    for res in results:
        print(f"[{res['start']:.2f}s - {res['end']:.2f}s] {res['text']}")
