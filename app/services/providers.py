import os
import requests
import json
import time
from typing import List, Dict, Any, Optional
from app.services.interfaces import TranscriberProvider, LLMProvider
from app.core.config import settings

class AssemblyAITranscriber(TranscriberProvider):
    def transcribe_audio(self, audio_path: str, model_size: str = "default", compute_type: str = "default", speakers_expected: Optional[int] = None) -> List[Dict[str, Any]]:
        api_key = settings.ASSEMBLYAI_API_KEY
        if not api_key:
            raise ValueError("ASSEMBLYAI_API_KEY is not configured")

        headers = {"authorization": api_key}
        
        upload_url = ""
        if audio_path.startswith("s3://"):
            from app.core.storage import generate_presigned_url
            # Parse s3://bucket/key
            # e.g. s3://meettrack-bot-bucket/meetings/bot_meeting_1.webm
            key = audio_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
            print(f"[AssemblyAI] Generating presigned URL for S3 key: {key}")
            upload_url = generate_presigned_url(key)
        else:
            # 1. Upload local audio file
            print(f"[AssemblyAI] Uploading {audio_path}...")
            def read_file(path, chunk_size=5242880):
                with open(path, 'rb') as _file:
                    while True:
                        data = _file.read(chunk_size)
                        if not data:
                            break
                        yield data

            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=read_file(audio_path),
                timeout=300
            )
            upload_url = upload_response.json()["upload_url"]

        # 2. Request transcription
        transcript_request = {
            "audio_url": upload_url,
            "speaker_labels": True,
            "speech_model": "universal-2",
            "language_detection": True,
            "punctuate": True,
            "format_text": True,
            "disfluencies": False
        }
        if speakers_expected is not None:
            transcript_request["speakers_expected"] = speakers_expected

        print("[AssemblyAI] Starting transcription...")
        response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=transcript_request,
            headers=headers
        )
        transcript_id = response.json()["id"]

        # 3. Poll for completion
        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        while True:
            transcription_result = requests.get(polling_endpoint, headers=headers).json()
            if transcription_result['status'] == 'completed':
                print("[AssemblyAI] Transcription complete.")
                break
            elif transcription_result['status'] == 'error':
                raise Exception(f"Transcription failed: {transcription_result['error']}")
            else:
                time.sleep(3)

        segments = []
        for utterance in transcription_result.get('utterances', []):
            segments.append({
                "speaker": utterance["speaker"],
                "text": utterance["text"],
                "start": utterance["start"],
                "end": utterance["end"]
            })
        return segments

class GroqLLMProvider(LLMProvider):
    def verify_speakers(self, transcript_segments: List[Dict[str, Any]], expected_speakers: Optional[List[str]] = None) -> str:
        # Import the logic from verify_speakers.py or copy it here.
        from app.services.verify_speakers import verify_transcript_speakers_with_llm
        return verify_transcript_speakers_with_llm(transcript_segments, expected_speakers)

    def extract_tasks(self, transcript_segments: List[Dict[str, Any]], meeting_date: str, users_list: str, calendar_map_str: str, rag_context: str) -> str:
        from app.services.extract_tasks import extract_tasks_from_transcript
        return extract_tasks_from_transcript(transcript_segments, meeting_date, users_list, calendar_map_str, rag_context)
