from gtts import gTTS
import os

dialogue = [
    ("com", "Alright team, let's start the meeting. We need to finalize the database migration by next week."),
    ("co.uk", "I can take care of the database migration. I will have it done by Friday afternoon."),
    ("com", "Perfect. Rahul, can you handle the new API endpoints?"),
    ("co.in", "Yes, I will finish coding the new API endpoints by Thursday."),
    ("com", "Great. I will email the clients today to let them know we are on track.")
]

files = []
for i, (tld, text) in enumerate(dialogue):
    filename = f"part_{i}.mp3"
    tts = gTTS(text=text, lang='en', tld=tld, slow=False)
    tts.save(filename)
    files.append(filename)

with open("list.txt", "w") as f:
    for file in files:
        f.write(f"file '{file}'\n")

os.system("ffmpeg -y -f concat -safe 0 -i list.txt -c copy temp.mp3")
os.system("ffmpeg -y -i temp.mp3 -ar 16000 data/team_meeting.wav")

for file in files:
    os.remove(file)
os.remove("list.txt")
os.remove("temp.mp3")
print("Generated data/team_meeting.wav!")
