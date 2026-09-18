# Hybrid Meeting Bot Architecture Plan

This document outlines the R&D strategy for upgrading the `screenappai/meeting-bot` to support exact speaker name identification by hybridizing raw audio capture with visual DOM scraping.

## The Problem
Currently, the pipeline uses **Pyannote** and **Whisper** to process the raw audio file recorded by the bot. While this provides highly accurate transcription and perfect speaker separation (e.g., Speaker 0, Speaker 1), it cannot inherently know the real-world names of the speakers.

## The Hybrid Solution
Since `screenappai/meeting-bot` operates a real Google Chrome browser via Playwright, we have full access to the live webpage DOM. We can inject a JavaScript content script that visually reads the Google Meet captions/UI to capture the real names of the active speakers, and then merge that data with the high-quality Whisper transcript.

---

## Implementation Steps

### Step 1: Automate Captions Activation
Modify the bot's Playwright initialization script (`meeting-bot/src/bots/GoogleMeetBot.ts`). Once the bot is admitted to the meeting, the script must locate and click the "Turn on Captions" button (`[aria-label="Turn on captions"]`).

### Step 2: Inject the DOM Scraper
Inject a continuous `MutationObserver` script into the page context:
1. Target the Google Meet captions container.
2. Every time a new caption node is rendered, scrape the **Speaker Name** and the **Timestamp**.
3. Target the active speaker highlight (the blue ring around a participant's video feed) as a fallback mechanism to capture names when captions are lagging.

### Step 3: Stream Data to Backend
Instead of waiting for the meeting to end, the Playwright script will stream this scraped JSON data (Name + Timestamp) directly to a new FastAPI WebSocket or REST endpoint (`/api/meetings/bot/live-captions`) on the MeetTrack server.
```json
{
  "timestamp": "2026-09-18T10:15:03Z",
  "speaker_name": "Tushar",
  "meeting_id": "123"
}
```

### Step 4: The Diarization Merge (Celery Worker)
Update `app/worker.py`. 
1. When the meeting ends, the worker runs Pyannote to generate the standard biometric clusters (`Speaker 0: 00:15 - 00:30`).
2. The worker pulls the JSON array of scraped names from the database.
3. **Cross-Referencing Algorithm**: The worker overlaps the timestamps. If Pyannote identifies `Speaker 0` talking from `00:15 - 00:30`, and the scraped JSON shows the name "Tushar" appeared on screen at `00:16`, the system permanently maps `Speaker 0` -> `Tushar`.

---

## Benefits of this Architecture
1. **No Quality Loss**: We still use Whisper for the actual transcription, which is much more accurate than Google Meet's native captions.
2. **Perfect Name Mapping**: We solve the Pyannote "Speaker 0" problem without requiring users to manually enroll their voice biometrics beforehand.
3. **Resilience**: Even if Google Meet's captions drop a few words, it doesn't matter. We only need them to flash the speaker's name once to map the voice biometric profile!
