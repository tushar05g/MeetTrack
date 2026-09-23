import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.1-70b-versatile")

def format_transcript_for_verification(segments):
    transcript_text = ""
    for segment in segments:
        speaker = segment.get("speaker", "Unknown Speaker")
        text = segment.get("text", "").strip()
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        transcript_text += f"[{start:.1f}s - {end:.1f}s] {speaker}: {text}\n"
    return transcript_text

def verify_transcript_speakers_with_llm(segments, dom_speakers=None):
    """
    Pass the formatted transcript to Groq and ask it to verify/correct speaker names.
    """
    if not segments:
        return segments
        
    transcript_text = format_transcript_for_verification(segments)
    
    dom_speakers_context = ""
    if dom_speakers and len(dom_speakers) > 0:
        dom_speakers_context = f"\nHere are the names of the speakers who were detected in the meeting (from DOM elements): {', '.join(dom_speakers)}\n"
    
    prompt = f"""
    You are an AI assistant that corrects speaker diarization in meeting transcripts.
    The transcription model may have grouped multiple people into one speaker, or mislabeled them.
    {dom_speakers_context}
    
    Here is the initially diarized meeting transcript:
    ---
    {transcript_text}
    ---
    
    CRITICAL INSTRUCTIONS:
    1. Read the conversational flow. Look for introductions like "Hello, my name is X" or conversational turns to determine who is actually speaking.
    2. Correct the "speaker" labels for each segment. If you can infer their name from the conversation or the provided detected speaker names, use their real name.
    3. Return a JSON object with a single key "segments" which is an array of the transcript segments.
    4. Each segment in the array MUST contain "start" (float), "end" (float), "speaker" (string), and "text" (string).
    5. Do not alter the start, end, or text. Only modify the "speaker" field if it is incorrect.
    
    Return ONLY a valid JSON object. No markdown, no backticks.
    Example:
    {{
      "segments": [
        {{"start": 0.0, "end": 5.0, "speaker": "Kashish", "text": "Hello, my name is Kashish."}},
        {{"start": 5.5, "end": 8.0, "speaker": "Tushar", "text": "And I'm Tushar. Let's start."}}
      ]
    }}
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    print("Sending transcript to Groq for speaker verification...")
    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            raw_text = result["choices"][0]["message"]["content"]
            parsed = json.loads(raw_text)
            
            verified_segments = parsed.get("segments", [])
            
            # Map the words back if they existed in the original segments
            for i, v_seg in enumerate(verified_segments):
                if i < len(segments):
                    v_seg["words"] = segments[i].get("words", [])
            
            return verified_segments
        else:
            print(f"Error calling Groq API for speaker verification: {response.status_code}")
            print(response.text)
            return segments
    except Exception as e:
        print(f"Failed to verify speakers with LLM: {e}")
        return segments
