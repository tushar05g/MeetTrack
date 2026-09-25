import os
import torch
from pyannote.audio import Pipeline
from pyannote.core import Segment

def diarize_audio(audio_path, transcript_segments, language="en"):
    """
    Diarize the audio using pyannote.audio and align it with the transcript segments.
    """
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("WARNING: HUGGINGFACE_TOKEN is missing. Cannot run Pyannote diarization.")
        return transcript_segments

    print("Loading Pyannote diarization pipeline...")
    try:
        os.environ["HF_TOKEN"] = hf_token
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        # Move to GPU if available
        if torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
        
        print(f"Diarizing {audio_path}...")
        diarization = pipeline(audio_path)
    except Exception as e:
        print(f"Pyannote diarization failed: {e}")
        return transcript_segments

    # Create an easy lookup from the diarization output
    print("Aligning Whisper transcription with Pyannote speakers...")
    aligned_segments = []
    
    for t_seg in transcript_segments:
        t_start = t_seg["start"]
        t_end = t_seg["end"]
        t_segment = Segment(t_start, t_end)
        
        # Find the speaker who spoke the most during this transcript segment
        speaker_overlap = {}
        for d_turn, d_track, d_speaker in diarization.itertracks(yield_label=True):
            intersection = t_segment & d_turn
            if intersection:
                overlap_duration = intersection.duration
                speaker_overlap[d_speaker] = speaker_overlap.get(d_speaker, 0) + overlap_duration
                
        if speaker_overlap:
            best_speaker = max(speaker_overlap, key=speaker_overlap.get)
            t_seg["speaker"] = best_speaker
        else:
            t_seg["speaker"] = "SPEAKER_00" # fallback
            
        aligned_segments.append(t_seg)

    print("Freed GPU memory after diarization.")
    return aligned_segments
