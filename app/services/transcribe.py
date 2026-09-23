import os
import requests
import time
from app.services.verify_speakers import verify_transcript_speakers_with_llm

ASSEMBLYAI_API_URL = "https://api.assemblyai.com/v2"

def transcribe_audio(audio_path, model_size="default", compute_type="default"):
    """
    Transcribe audio and perform speaker diarization using AssemblyAI.
    """
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY environment variable is missing")

    headers = {
        "authorization": api_key
    }

    print(f"Uploading audio {audio_path} to AssemblyAI...")
    
    # 1. Upload the file
    def read_file(path, chunk_size=5242880):
        with open(path, 'rb') as _file:
            while True:
                data = _file.read(chunk_size)
                if not data:
                    break
                yield data

    upload_response = requests.post(
        f"{ASSEMBLYAI_API_URL}/upload",
        headers=headers,
        data=read_file(audio_path)
    )
    
    if upload_response.status_code != 200:
        print(f"AssemblyAI Upload Error: {upload_response.text}")
        return []
        
    upload_url = upload_response.json().get("upload_url")
    print("Upload complete. Submitting transcription job...")

    # 2. Submit transcription job with speaker diarization enabled
    transcript_request = {
        "audio_url": upload_url,
        "speaker_labels": True,
        "language_detection": True
    }
    
    headers["content-type"] = "application/json"
    
    transcript_response = requests.post(
        f"{ASSEMBLYAI_API_URL}/transcript",
        json=transcript_request,
        headers=headers
    )
    
    if transcript_response.status_code != 200:
        print(f"AssemblyAI Transcription Request Error: {transcript_response.text}")
        return []
        
    transcript_id = transcript_response.json().get("id")
    print(f"Transcription job {transcript_id} started. Waiting for completion...")

    # 3. Poll for completion
    polling_endpoint = f"{ASSEMBLYAI_API_URL}/transcript/{transcript_id}"
    
    while True:
        polling_response = requests.get(polling_endpoint, headers=headers)
        polling_result = polling_response.json()
        
        if polling_result.get("status") == "completed":
            print("Transcription completed successfully!")
            break
        elif polling_result.get("status") == "error":
            print(f"AssemblyAI Transcription Error: {polling_result.get('error')}")
            return []
            
        print("Still processing... waiting 10 seconds.")
        time.sleep(10)

    # 4. Parse the results into the expected format
    all_segments = []
    utterances = polling_result.get("utterances")
    if not utterances:
        print(f"AssemblyAI returned no utterances! Full response keys: {polling_result.keys()}")
        print(f"Full text: {polling_result.get('text', '')[:100]}...")
    utterances = utterances or []
    
    for utterance in utterances:
        segment = {
            "start": utterance.get("start") / 1000.0, # Convert ms to seconds
            "end": utterance.get("end") / 1000.0,
            "text": utterance.get("text", "").strip(),
            "speaker": utterance.get("speaker", "Unknown Speaker"),
            "words": []
        }
        
        # Parse individual words if needed
        for word in utterance.get("words", []):
            segment["words"].append({
                "start": word.get("start") / 1000.0,
                "end": word.get("end") / 1000.0,
                "word": word.get("text")
            })
            
        all_segments.append(segment)
        
    # Optional: Merge DOM-scraped speakers if available
    speakers_json_path = audio_path.replace(".webm", "_speakers.json")
    if os.path.exists(speakers_json_path):
        try:
            import json
            with open(speakers_json_path, 'r') as f:
                dom_events = json.load(f)
                
            if dom_events:
                print(f"Loaded {len(dom_events)} DOM speaker events. Mapping to AssemblyAI speakers...")
                # Map generic AssemblyAI speaker labels (e.g. A, B) to DOM real names
                mapping_votes = {}
                for seg in all_segments:
                    seg_start = seg["start"]
                    seg_end = seg["end"]
                    assembly_spk = seg["speaker"]
                    
                    # Find any DOM event that overlaps this segment
                    for ev in dom_events:
                        ev_time = ev["timestamp"]
                        ev_name = ev["name"]
                        if seg_start <= ev_time <= seg_end + 2.0:
                            if assembly_spk not in mapping_votes:
                                mapping_votes[assembly_spk] = {}
                            mapping_votes[assembly_spk][ev_name] = mapping_votes[assembly_spk].get(ev_name, 0) + 1
                
                # Resolve mapping
                final_mapping = {}
                for assembly_spk, votes in mapping_votes.items():
                    if votes:
                        best_name = max(votes, key=votes.get)
                        final_mapping[assembly_spk] = best_name
                        print(f"Mapped AssemblyAI {assembly_spk} -> {best_name}")
                        
                # Apply mapping
                for seg in all_segments:
                    assembly_spk = seg["speaker"]
                    if assembly_spk in final_mapping:
                        seg["speaker"] = final_mapping[assembly_spk]
        except Exception as e:
            print(f"Failed to merge DOM speaker events: {e}")
            
    # LLM Verification Step
    dom_speaker_names = []
    if 'dom_events' in locals() and dom_events:
        dom_speaker_names = list(set(ev["name"] for ev in dom_events))
    
    print("Verifying speaker assignments with LLM...")
    all_segments = verify_transcript_speakers_with_llm(all_segments, dom_speakers=dom_speaker_names)
            
    return all_segments

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)
    
    # Requires ASSEMBLYAI_API_KEY exported in env
    results = transcribe_audio(sys.argv[1])
    for res in results:
        print(f"[{res['start']:.2f}s - {res['end']:.2f}s] Speaker {res.get('speaker')}: {res.get('text', '')}")
