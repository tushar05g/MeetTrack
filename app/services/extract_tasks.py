import json
import requests

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

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

def extract_tasks_from_transcript(segments):
    """
    Pass the formatted transcript to Ollama and ask it to extract action items.
    """
    transcript_text = format_transcript(segments)
    
    prompt = f"""
    You are an AI assistant that extracts action items, commitments, or assigned tasks from meeting transcripts.
    
    Here is a diarized meeting transcript:
    ---
    {transcript_text}
    ---
    
    Identify all action items mentioned. For each task, provide:
    - "task": A clear description of the action item.
    - "owner": The name or speaker label (e.g. "SPEAKER_00") of the person assigned to the task.
    - "deadline": Any mentioned deadline or timeframe (e.g. "Next Friday", "2024-10-31"). Use null if none mentioned.
    
    CRITICAL INSTRUCTION: If there are absolutely no action items, commitments, or tasks mentioned in the transcript, you MUST return an empty JSON array `[]`. Do NOT make up or hallucinate tasks.

    Return ONLY a valid JSON array of objects. Do not include markdown formatting, backticks, or any other text before or after the JSON.
    Example output format:
    [
      {{"task": "Draft the quarterly report", "owner": "SPEAKER_01", "deadline": "Friday"}},
      {{"task": "Send the design files", "owner": "SPEAKER_00", "deadline": null}}
    ]
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"  # Forces JSON output
    }
    
    print("Sending transcript to Ollama for task extraction...")
    response = requests.post(OLLAMA_API_URL, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        raw_text = result.get("response", "[]")
        try:
            tasks = json.loads(raw_text)
            return tasks
        except json.JSONDecodeError:
            print("Failed to parse Ollama output as JSON. Raw output:")
            print(raw_text)
            return []
    else:
        print(f"Error calling Ollama API: {response.status_code}")
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
