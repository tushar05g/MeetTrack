import os
import requests
import tempfile
from pydub import AudioSegment

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

def transcribe_audio(audio_path, model_size="whisper-large-v3", compute_type="int8"):
    """
    Transcribe audio using Groq API by chunking audio to bypass 25MB limit.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing")

    print(f"Loading audio {audio_path} for chunking...")
    # Load audio (pydub supports webm, mp3, wav, etc.)
    audio = AudioSegment.from_file(audio_path)
    
    # Chunk duration in milliseconds. 
    # 10 minutes of 64kbps mp3 is ~5MB, well below Groq's 25MB limit.
    chunk_length_ms = 10 * 60 * 1000 
    chunks = [audio[i:i+chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    
    all_segments = []
    
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
    }
    
    print(f"Divided audio into {len(chunks)} chunks for Groq API processing.")
    
    for i, chunk in enumerate(chunks):
        chunk_offset_seconds = (i * chunk_length_ms) / 1000.0
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            print(f"Exporting chunk {i+1}/{len(chunks)}...")
            chunk.export(tmp_file.name, format="mp3", parameters=["-b:a", "64k"])
            
            print(f"Sending chunk {i+1} to Groq API...")
            with open(tmp_file.name, "rb") as f:
                files = {
                    "file": (tmp_file.name, f, "audio/mpeg"),
                }
                data = {
                    "model": model_size,
                    "response_format": "verbose_json",
                    "temperature": "0.0",
                    "prompt": "Please do not transcribe silence, background noise, or include phantom words like 'you' or 'thank you' or 'subtitles'."
                }
                response = requests.post(GROQ_API_URL, headers=headers, files=files, data=data)
            
            # Clean up temp file
            os.remove(tmp_file.name)
            
            if response.status_code != 200:
                print(f"Groq API Error on chunk {i+1}: {response.text}")
                continue
                
            result = response.json()
            # Groq verbose_json returns "segments"
            chunk_segments = result.get("segments", [])

            # Adjust timestamps by adding chunk_offset_seconds
            for seg in chunk_segments:
                text = seg.get("text", "").strip().lower()
                if text == "":
                    continue

                seg["start"] += chunk_offset_seconds
                seg["end"] += chunk_offset_seconds
                if "words" in seg:
                    for word in seg["words"]:
                        word["start"] += chunk_offset_seconds
                        word["end"] += chunk_offset_seconds
                all_segments.append(seg)
                
    return all_segments

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)
    
    # Requires GROQ_API_KEY exported in env
    results = transcribe_audio(sys.argv[1])
    for res in results:
        print(f"[{res['start']:.2f}s - {res['end']:.2f}s] {res.get('text', '')}")

