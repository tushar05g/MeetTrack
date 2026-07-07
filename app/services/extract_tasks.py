import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

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

def extract_tasks_from_transcript(segments, meeting_date, users_list, calendar_map_str=""):
    """
    Pass the formatted transcript to Groq and ask it to extract action items.
    """
    transcript_text = format_transcript(segments)
    
    prompt = f"""
    You are an AI assistant that extracts action items and assigned tasks from meeting transcripts.
    
    Context:
    - Meeting date: {meeting_date}
    - Available participants (name → email lookup table): {users_list}
    
    Calendar Reference (use this exact mapping for relative days like "Friday" or "Next Monday"):
    {calendar_map_str}
    
    Here is the diarized meeting transcript:
    ---
    {transcript_text}
    ---
    
    Identify all action items mentioned in the transcript.
    
    CRITICAL INSTRUCTIONS:
    1. DEDUPLICATE: Merge discussions of the same task into ONE task. Do NOT create multiple tasks for the same discussion.
    
    2. ACCURATE DEADLINES: Calculate exact dates from relative phrases ("by Friday", "tomorrow") by STRICTLY looking up the phrase in the "Calendar Reference" above. Do NOT do math yourself.
       Use format: YYYY-MM-DD HH:MM:SS. Default time: 23:59:59. Morning→09:00, Afternoon→14:00, Evening→18:00.
    
    3. OWNER IDENTIFICATION (most important):
       - When a name is mentioned in the transcript (e.g. "Tushar, can you..." or "Alice will handle..."),
         look that name up in the registered team members list above.
       - Set "owner" to their name and "owner_email" to their email from the lookup table.
       - Names in the transcript may be first names only — match them to the full name in the lookup table.
       - If the owner spoke in first person ("I will do X"), use the speaker label + context to identify who that is.
       - If you cannot identify a real name, use the speaker label (e.g. "SPEAKER_00") and set owner_email to null.
    
    4. EMPTY STATE: If there are no action items, return an empty tasks array. Do NOT hallucinate tasks.
    
    Return ONLY a valid JSON object with key "tasks" containing an array. No markdown, no backticks.
    Example:
    {{
      "tasks": [
        {{"task": "Send the quarterly report", "owner": "Tushar", "owner_email": "tushar@example.com", "deadline": "2026-07-10 23:59:59"}},
        {{"task": "Review the design", "owner": "SPEAKER_01", "owner_email": null, "deadline": null}}
      ]
    }}
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    # Note: prompt already instructs the model to return {"tasks": [...]}

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
