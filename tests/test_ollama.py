import json
import requests

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

def test_ollama():
    prompt = """
    You are an AI assistant that extracts action items, commitments, or assigned tasks from meeting transcripts.
    
    Here is a diarized meeting transcript:
    ---
    [0.0s - 4.0s] SPEAKER_00: Alright everyone, thanks for joining the Design Review sync.
    [4.5s - 7.0s] SPEAKER_01: No problem. Are we still on track for the launch?
    [7.5s - 14.0s] SPEAKER_00: Yes, but we have a few things to finalize. First, I will draft the new API architecture document by this Friday.
    [14.5s - 17.0s] SPEAKER_01: Great. What about the frontend UI components?
    [17.5s - 23.0s] SPEAKER_00: I'm going to take care of that too. I'll schedule a meeting with the frontend team to review the new dashboard UI by next Tuesday.
    [23.5s - 28.0s] SPEAKER_01: Perfect. And I'll run a full security audit on the payment gateway.
    ---
    
    Identify all action items mentioned. For each task, provide:
    - "task": A clear description of the action item.
    - "owner": The name or speaker label (e.g. "SPEAKER_00") of the person assigned to the task.
    - "deadline": Any mentioned deadline or timeframe (e.g. "Next Friday", "2024-10-31"). Use null if none mentioned.
    
    Return ONLY a valid JSON array of objects. Do not include markdown formatting, backticks, or any other text before or after the JSON.
    Example output format:
    [
      {"task": "Draft the quarterly report", "owner": "SPEAKER_01", "deadline": "Friday"},
      {"task": "Send the design files", "owner": "SPEAKER_00", "deadline": null}
    ]
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    response = requests.post(OLLAMA_API_URL, json=payload)
    print("RAW OLLAMA OUTPUT:")
    print(response.json().get("response"))

if __name__ == "__main__":
    test_ollama()
