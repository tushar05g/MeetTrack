import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()

from app.services.transcribe import transcribe_audio
from app.services.diarize import diarize_audio
from app.services.extract_tasks import extract_tasks_from_transcript

def run_pipeline(audio_file):
    print(f"--- Starting Pipeline for {audio_file} ---")
    start_time = time.time()
    
    # 1. Transcription
    print("\n[STEP 1] Transcribing audio...")
    t_start = time.time()
    raw_segments = transcribe_audio(audio_file, model_size="small", compute_type="int8")
    print(f"Transcription finished in {time.time() - t_start:.2f}s")
    
    # 2. Diarization
    print("\n[STEP 2] Diarizing audio...")
    t_start = time.time()
    try:
        diarized_segments = diarize_audio(audio_file, raw_segments)
        print(f"Diarization finished in {time.time() - t_start:.2f}s")
    except ValueError as e:
        print(f"\n[ERROR] Diarization failed: {e}")
        print("Falling back to raw transcription segments for task extraction...")
        diarized_segments = raw_segments
        
    # 3. Task Extraction
    print("\n[STEP 3] Extracting tasks...")
    t_start = time.time()
    tasks = extract_tasks_from_transcript(diarized_segments)
    print(f"Task extraction finished in {time.time() - t_start:.2f}s")
    
    # Output final results
    print("\n--- Pipeline Complete ---")
    print(f"Total processing time: {time.time() - start_time:.2f}s")
    
    print("\n--- Extracted Tasks ---")
    print(json.dumps(tasks, indent=2))
    
    # Output full transcript
    print("\n--- Full Transcript ---")
    for segment in diarized_segments:
        speaker = segment.get("speaker", "Unknown Speaker")
        text = segment.get("text", "").strip()
        print(f"[{segment.get('start', 0):.2f}s - {segment.get('end', 0):.2f}s] {speaker}: {text}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <audio_file>")
        sys.exit(1)
        
    run_pipeline(sys.argv[1])
