import os, requests
GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# Get a small sample audio from somewhere or make one
os.system("ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 3 -q:a 9 -acodec libmp3lame silence.mp3 -y > /dev/null 2>&1")

with open("silence.mp3", "rb") as f:
    response = requests.post(
        GROQ_API_URL, 
        headers={"Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}"}, 
        files={"file": ("silence.mp3", f, "audio/mpeg")}, 
        data={"model": "whisper-large-v3", "response_format": "verbose_json", "temperature": "0.0"}
    )
print(response.json())
