import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
# Upgraded to llama-3.3-70b-versatile for better structured output and reasoning
MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

# Process transcript in chunks to avoid token limit issues on long meetings
CHUNK_SIZE = 30       # Segments per chunk
CHUNK_OVERLAP = 5     # Overlap segments for context continuity between chunks


def format_transcript_for_verification(segments):
    transcript_text = ""
    for segment in segments:
        speaker = segment.get("speaker", "Unknown Speaker")
        text = segment.get("text", "").strip()
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        transcript_text += f"[{start:.1f}s - {end:.1f}s] {speaker}: {text}\n"
    return transcript_text


def _call_llm_for_chunk(chunk_segments, dom_speakers):
    """
    Send a single chunk of segments to the LLM for speaker verification.
    Returns the corrected segment list, or None on failure.
    """
    transcript_text = format_transcript_for_verification(chunk_segments)

    # Build a clean, structured DOM speakers block
    if dom_speakers and len(dom_speakers) > 0:
        dom_list = "\n".join(f"  - {name}" for name in dom_speakers)
        dom_speakers_context = f"""
KNOWN MEETING PARTICIPANTS (scraped from the meeting UI):
{dom_list}

Use these names for speaker labels wherever possible. If a segment is labeled "Unknown Speaker (X)", 
use the conversational context to figure out which participant it is and replace it with their real name.
"""
    else:
        dom_speakers_context = ""

    prompt = f"""You are an AI assistant that corrects speaker diarization in meeting transcripts.
The transcription model assigns generic labels (like A, B, C or "Unknown Speaker") and sometimes 
merges multiple speakers into one segment.
{dom_speakers_context}
Here is the diarized meeting transcript to correct:
---
{transcript_text}
---

CRITICAL INSTRUCTIONS:
1. The transcript may be in English, Hindi, or a mix of both (Hinglish). If you detect any Hindi or non-English text, you MUST TRANSLATE it into clear, natural English. The final output text in the JSON MUST be 100% English.
2. SPLIT SEGMENTS IF NECESSARY: If a segment contains dialogue from multiple speakers (e.g., a question followed by an answer from someone else), you MUST split it into separate segments with correct speaker labels.
3. When splitting, use proportional time estimates based on text length within the original segment's start/end bounds.
4. When splitting, default to retaining the original speaker for continuous speech. Only change the speaker when the text clearly represents a RESPONSE or TURN from someone else (e.g., "Yes", "Okay", answering a direct question).
5. Replace any "Unknown Speaker (X)" labels with the real participant name from the KNOWN PARTICIPANTS list, using conversational context clues.
6. Correct generic A/B/C labels with real names from the KNOWN PARTICIPANTS list where you can confidently infer them.
7. Return a JSON object with two keys:
   - "reasoning": a brief string explaining any splits, label changes, or translations you made
   - "segments": the corrected array of segments

Each segment MUST have: "start" (float), "end" (float), "speaker" (string), "text" (string).

Return ONLY a valid JSON object. No markdown, no backticks, no commentary outside the JSON.

Example (English):
Input:  [0.0s - 10.0s] Unknown Speaker (A): Am I audible? Yes you are. Okay.
Output: {{"reasoning": "A asks a question, B answers, A acknowledges. Split into 3 segments.", "segments": [{{"start": 0.0, "end": 5.0, "speaker": "Tushar", "text": "Am I audible?"}}, {{"start": 5.0, "end": 8.0, "speaker": "Kashish", "text": "Yes you are."}}, {{"start": 8.0, "end": 10.0, "speaker": "Tushar", "text": "Okay."}}]}}

Example (Hinglish translated to English):
Input:  [10.0s - 20.0s] Kashish: हेलो माय नेम इस कशिश ओके थैंक यू कशिश हेलो
Output: {{"reasoning": "Kashish introduces herself, Tushar thanks her, Kashish responds. Split into 3 and translated to English.", "segments": [{{"start": 10.0, "end": 14.0, "speaker": "Kashish", "text": "Hello, my name is Kashish."}}, {{"start": 14.0, "end": 17.0, "speaker": "Tushar", "text": "Okay, thank you Kashish."}}, {{"start": 17.0, "end": 20.0, "speaker": "Kashish", "text": "Hello."}}]}}
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=60)

    if response.status_code == 200:
        result = response.json()
        raw_text = result["choices"][0]["message"]["content"]
        parsed = json.loads(raw_text)

        reasoning = parsed.get("reasoning", "")
        if reasoning:
            print(f"  LLM reasoning: {reasoning}")

        verified_segments = parsed.get("segments", [])

        # Ensure words field exists
        for v_seg in verified_segments:
            if "words" not in v_seg:
                v_seg["words"] = []

        return verified_segments
    else:
        print(f"Error calling Groq API: {response.status_code} — {response.text}")
        return None


def verify_transcript_speakers_with_llm(segments, dom_speakers=None):
    """
    Verify and correct speaker labels in transcript segments using an LLM.

    Processes the transcript in overlapping chunks (CHUNK_SIZE segments with
    CHUNK_OVERLAP context segments) to handle long meetings without hitting
    token limits. Results are merged de-duplicating the overlap.
    """
    if not segments:
        return segments

    dom_speakers = dom_speakers or []

    # Short transcript: process in one shot
    if len(segments) <= CHUNK_SIZE:
        print(f"Sending {len(segments)} segments to Groq for speaker verification...")
        result = _call_llm_for_chunk(segments, dom_speakers)
        return result if result is not None else segments

    # Long transcript: process in overlapping chunks
    print(f"Long transcript ({len(segments)} segments). Processing in chunks of {CHUNK_SIZE} with {CHUNK_OVERLAP} overlap...")
    all_verified = []
    i = 0

    while i < len(segments):
        chunk = segments[i: i + CHUNK_SIZE]
        chunk_num = i // (CHUNK_SIZE - CHUNK_OVERLAP) + 1
        print(f"  Processing chunk {chunk_num} (segments {i}–{i + len(chunk) - 1})...")

        verified_chunk = _call_llm_for_chunk(chunk, dom_speakers)

        if verified_chunk is None:
            # On failure, fall back to the original segments for this chunk
            verified_chunk = chunk

        if i == 0:
            # First chunk: take everything
            all_verified.extend(verified_chunk)
        else:
            # Subsequent chunks: skip the first CHUNK_OVERLAP segments
            # (they were already included from the previous chunk's tail)
            overlap_end_time = segments[i]["start"]
            # Drop verified segments that fall before the overlap boundary
            new_segments = [s for s in verified_chunk if s.get("start", 0) >= overlap_end_time]
            all_verified.extend(new_segments)

        # Advance by CHUNK_SIZE - CHUNK_OVERLAP for overlap
        i += CHUNK_SIZE - CHUNK_OVERLAP

    print(f"Chunked LLM verification complete. Total output segments: {len(all_verified)}")
    return all_verified
