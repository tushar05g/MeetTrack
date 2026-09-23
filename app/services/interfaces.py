from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class TranscriberProvider(ABC):
    @abstractmethod
    def transcribe_audio(self, audio_path: str, model_size: str = "default", compute_type: str = "default", speakers_expected: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Transcribe the audio file and return a list of segments.
        Each segment should be a dictionary with at least 'speaker' and 'text'.
        """
        pass

class LLMProvider(ABC):
    @abstractmethod
    def verify_speakers(self, transcript_segments: List[Dict[str, Any]], expected_speakers: Optional[List[str]] = None) -> str:
        """
        Process the transcript segments and return a verified string with speaker mappings.
        """
        pass

    @abstractmethod
    def extract_tasks(self, transcript_segments: List[Dict[str, Any]], meeting_date: str, users_list: str, calendar_map_str: str, rag_context: str) -> str:
        """
        Process the transcript segments and extract action items/tasks.
        """
        pass
