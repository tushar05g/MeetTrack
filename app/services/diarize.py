import os
import gc
import torch
import whisperx
from whisperx.diarize import DiarizationPipeline, assign_word_speakers

def diarize_audio(audio_path, transcript_segments, language="en"):
    """
    Align transcript and perform speaker diarization using whisperx and pyannote.
    Requires HUGGINGFACE_TOKEN environment variable to be set for pyannote.audio access.
    """
    hf_token = os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        raise ValueError("HUGGINGFACE_TOKEN environment variable is required for speaker diarization.")
        
    device = "cuda"
    print("Loading audio for diarization...")
    audio = whisperx.load_audio(audio_path)
    
    # 1. Align the transcripts
    print(f"Loading alignment model for language: {language}...")
    model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
    
    print("Aligning transcripts with audio...")
    # whisperx.align expects segments to have 'start', 'end', and 'text' keys
    aligned_result = whisperx.align(transcript_segments, model_a, metadata, audio, device, return_char_alignments=False)
    
    # Free alignment model
    del model_a
    gc.collect()
    torch.cuda.empty_cache()
    print("Freed GPU memory after alignment.")

    # 2. Diarize
    print("Loading diarization pipeline...")
    diarize_model = DiarizationPipeline(token=hf_token, device=device)
    
    print("Diarizing speakers...")
    diarize_segments = diarize_model(audio)
    
    # Free diarization model
    del diarize_model
    gc.collect()
    torch.cuda.empty_cache()
    print("Freed GPU memory after diarization.")
    
    # 3. Assign speakers to words/segments
    print("Assigning speakers to segments...")
    final_result = assign_word_speakers(diarize_segments, aligned_result)
    
    return final_result["segments"]

if __name__ == "__main__":
    # Test script - requires valid segments structure
    print("This script is meant to be run via pipeline.py with segments from transcribe.py")
