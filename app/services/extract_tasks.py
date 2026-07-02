import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"

def format_transcript(segments):
    """
    Format the diarized segments into a readable script for the LLM.
    """
    transcript_text = ""
    for segment in segments:
        speaker = segment.get("speaker", "Unknown Speaker")
        text = segment.get("text", "").strip()
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        transcript_text += f"[{start:.1f}s - {end:.1f}s] {speaker}: {text}\n"
    return transcript_text

def extract_tasks_from_transcript(segments, meeting_date, users_list):
    """
    Pass the formatted transcript to Groq and ask it to extract action items.
    """
    transcript_text = format_transcript(segments)
    
    prompt = f"""
    You are an AI assistant that extracts action items, commitments, or assigned tasks from meeting transcripts.
    
    Context:
    - The meeting took place on: {meeting_date}
    - The available team members are: {users_list}
    
    Here is the diarized meeting transcript:
    ---
    {transcript_text}
    ---
    
    Identify all action items mentioned. 
    
    CRITICAL INSTRUCTIONS:
    1. DEDUPLICATE: If multiple people discuss the same task (e.g. someone proposes a task, someone else accepts it, and they set a deadline), merge this into a SINGLE task. Do NOT create multiple tasks for the same discussion.
    2. ACCURATE DEADLINES: If a timeframe is mentioned (e.g. "by Friday", "tomorrow"), calculate the exact date and time in YYYY-MM-DD HH:MM:SS format based on the Meeting Date ({meeting_date}). If a time of day is mentioned (e.g. "morning" -> 09:00:00, "afternoon" -> 14:00:00, "evening" -> 18:00:00), use that. If no specific time of day is mentioned, default to End of Day (23:59:59).
    3. ASSIGNMENT: Try to identify the real name of the owner from the transcript or the available team members list. If unknown, use the speaker label (e.g. "SPEAKER_00").
    4. EMPTY STATE: If there are absolutely no action items, return an empty JSON array []. Do not hallucinate.

    Return ONLY a valid JSON array of objects. Do not include markdown formatting, backticks, or any other text before or after the JSON.
    Example output format:
    [
      {{"task": "Draft the quarterly report", "owner": "Tushar", "owner_email": "tushar@chicmicstudios.in", "deadline": "2026-07-10 23:59:59"}},
      {{"task": "Send the design files", "owner": "SPEAKER_00", "owner_email": null, "deadline": null}}
    ]
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    # We wrap the array in an object for Groq JSON mode compliance, then extract it.
    payload["messages"][0]["content"] += "\nWrap your array in a JSON object with a single key 'tasks'. Example: {\"tasks\": [...]}"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    print("Sending transcript to Groq for task extraction...")
    response = requests.post(GROQ_API_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        raw_text = result["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(raw_text)
            return parsed.get("tasks", [])
        except json.JSONDecodeError:
            print("Failed to parse Groq output as JSON. Raw output:")
            print(raw_text)
            return []
    else:
        print(f"Error calling Groq API: {response.status_code}")
        print(response.text)
        return []

if __name__ == "__main__":
    # Test script with dummy segments
    dummy_segments = [
        {"speaker": "SPEAKER_00", "text": "Alright, let's wrap this up. Tushar, can you send me the final designs by tomorrow?", "start": 0.0, "end": 5.0},
        {"speaker": "SPEAKER_01", "text": "Sure, I will get those to you by tomorrow evening.", "start": 5.5, "end": 8.0}
    ]
    tasks = extract_tasks_from_transcript(dummy_segments)
    print(json.dumps(tasks, indent=2))
