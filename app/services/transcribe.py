import os
import subprocess
import requests
import time
import json
from app.services.verify_speakers import verify_transcript_speakers_with_llm

from app.core.config import settings

ASSEMBLYAI_API_URL = "https://api.assemblyai.com/v2"

def transcribe_audio(audio_path, model_size="default", compute_type="default"):
    """
    Transcribe audio and perform speaker diarization using AssemblyAI.
    Uses DOM speaker events to map generic labels (A, B, C) to real names,
    then passes the result through an LLM for final verification and segment splitting.
    """
    api_key = settings.ASSEMBLYAI_API_KEY
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY environment variable is missing")

    headers = {
        "authorization": api_key
    }

    # --- Pre-load DOM speaker events early so we can pass speakers_expected to AssemblyAI ---
    dom_events = []
    speakers_json_path = audio_path.replace(".webm", "_speakers.json")
    if os.path.exists(speakers_json_path):
        try:
            with open(speakers_json_path, 'r') as f:
                dom_events = json.load(f)
            print(f"Pre-loaded {len(dom_events)} DOM speaker events.")
        except Exception as e:
            print(f"Could not pre-load DOM speaker events: {e}")

    # Derive expected speaker count from unique DOM names
    unique_dom_names = list(set(ev["name"] for ev in dom_events)) if dom_events else []
    speakers_expected = len(unique_dom_names) if len(unique_dom_names) >= 2 else None

    # 1. Pre-convert to 16kHz mono WAV for best transcription accuracy
    wav_path = audio_path.rsplit(".", 1)[0] + "_converted.wav"
    try:
        print(f"Converting {audio_path} to 16kHz mono WAV for optimal accuracy...")
        result = subprocess.run(
            [
                "ffmpeg", "-y",           # -y = overwrite if exists
                "-i", audio_path,
                "-ac", "1",               # mono channel
                "-ar", "16000",           # 16kHz sample rate
                "-acodec", "pcm_s16le",   # 16-bit PCM (uncompressed)
                wav_path
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            print(f"ffmpeg conversion failed: {result.stderr}")
            print("Falling back to original file.")
            wav_path = audio_path
        else:
            print(f"Conversion successful -> {wav_path}")
    except Exception as conv_err:
        print(f"ffmpeg not available or errored ({conv_err}), using original file.")
        wav_path = audio_path

    upload_path = wav_path
    print(f"Uploading audio {upload_path} to AssemblyAI...")

    # 2. Upload the file
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
        data=read_file(upload_path)
    )

    # Clean up temp WAV file to save disk space
    if wav_path != audio_path and os.path.exists(wav_path):
        os.remove(wav_path)
        print(f"Cleaned up temp file: {wav_path}")

    if upload_response.status_code != 200:
        print(f"AssemblyAI Upload Error: {upload_response.text}")
        return []

    upload_url = upload_response.json().get("upload_url")
    print("Upload complete. Submitting transcription job...")

    # 2. Submit transcription job with optimized parameters
    transcript_request = {
        "audio_url": upload_url,
        "speaker_labels": True,
        "language_detection": True,
        "speech_models": ["universal-2", "universal-3-5-pro"],  # universal-2 is more lenient, fallback to pro
        "punctuate": True,
        "format_text": True,
        "disfluencies": False,
    }

    # Tell AssemblyAI how many speakers to expect — biggest single accuracy boost
    if speakers_expected:
        transcript_request["speakers_expected"] = speakers_expected
        print(f"Telling AssemblyAI to expect {speakers_expected} speakers: {unique_dom_names}")

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
            "start": utterance.get("start") / 1000.0,  # Convert ms to seconds
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

    # 5. Map DOM speaker events to AssemblyAI labels (improved algorithm)
    if dom_events:
        print(f"Mapping {len(dom_events)} DOM speaker events to AssemblyAI labels...")
        all_segments = _map_dom_speakers_to_segments(all_segments, dom_events)

    # 6. LLM Verification Step
    dom_speaker_names = unique_dom_names if unique_dom_names else []

    print("Verifying speaker assignments with LLM...")
    all_segments = verify_transcript_speakers_with_llm(all_segments, dom_speakers=dom_speaker_names)

    return all_segments


def _map_dom_speakers_to_segments(segments, dom_events):
    """
    Maps generic AssemblyAI speaker labels (A, B, C) to real participant names
    using DOM-scraped speaker events.

    Improvements over naive approach:
    - No lookahead buffer: only events strictly within the segment window are counted.
    - Votes are weighted by the duration the speaker was active in the window,
      not just raw event count.
    - Unmatched speakers are labeled "Unknown Speaker (X)" for clear LLM handling.
    """
    if not dom_events:
        return segments

    # Build a sorted list of (timestamp, name) pairs for efficient lookup
    sorted_events = sorted(dom_events, key=lambda e: e["timestamp"])

    # For each AssemblyAI speaker, accumulate weighted time coverage by DOM name
    # Structure: { "A": { "Tushar": 8.5, "Kashish": 1.5 }, "B": { ... } }
    speaker_duration_weights = {}

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_duration = max(seg_end - seg_start, 0.001)
        assembly_spk = seg["speaker"]

        if assembly_spk not in speaker_duration_weights:
            speaker_duration_weights[assembly_spk] = {}

        # Find DOM events that fall strictly within the segment window
        overlapping_events = [
            ev for ev in sorted_events
            if seg_start <= ev["timestamp"] <= seg_end
        ]

        if not overlapping_events:
            continue

        # Weight each event by the time gap until the next event (or segment end)
        # This measures how long each speaker was "active" in this window
        for i, ev in enumerate(overlapping_events):
            ev_name = ev["name"]
            ev_time = ev["timestamp"]

            # Duration this event covers = gap to next event (or segment end)
            if i + 1 < len(overlapping_events):
                next_time = overlapping_events[i + 1]["timestamp"]
            else:
                next_time = seg_end

            duration_covered = max(next_time - ev_time, 0.1)

            if ev_name not in speaker_duration_weights[assembly_spk]:
                speaker_duration_weights[assembly_spk][ev_name] = 0
            speaker_duration_weights[assembly_spk][ev_name] += duration_covered

    # Resolve the best name for each AssemblyAI speaker label
    final_mapping = {}
    for assembly_spk, name_weights in speaker_duration_weights.items():
        if name_weights:
            best_name = max(name_weights, key=name_weights.get)
            final_mapping[assembly_spk] = best_name
            total = sum(name_weights.values())
            confidence = name_weights[best_name] / total * 100
            print(f"Mapped AssemblyAI '{assembly_spk}' -> '{best_name}' (confidence: {confidence:.0f}%)")
        else:
            # No DOM events matched — label clearly for the LLM
            final_mapping[assembly_spk] = f"Unknown Speaker ({assembly_spk})"
            print(f"No DOM events for AssemblyAI '{assembly_spk}' — labeled as Unknown")

    # Apply the mapping to all segments
    for seg in segments:
        assembly_spk = seg["speaker"]
        seg["speaker"] = final_mapping.get(assembly_spk, f"Unknown Speaker ({assembly_spk})")

    return segments


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)

    # Requires ASSEMBLYAI_API_KEY exported in env
    results = transcribe_audio(sys.argv[1])
    for res in results:
        print(f"[{res['start']:.2f}s - {res['end']:.2f}s] Speaker {res.get('speaker')}: {res.get('text', '')}")
