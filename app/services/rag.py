import os
from sqlalchemy import select
from app.models import Transcript, Meeting

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            # all-MiniLM-L6-v2 produces a 384-dimensional embedding
            _embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            raise RuntimeError("sentence-transformers is not installed. Please install it for RAG features.")
    return _embedder

def extract_text_embedding(text: str):
    """
    Extracts a 384-dimensional text embedding vector from a string.
    """
    embedder = get_embedder()
    return embedder.encode(text)

def find_relevant_transcripts(embedding, db_session, current_meeting_id: int, top_k=3, threshold=0.3):
    """
    Finds past meeting transcripts that are semantically similar to the current meeting
    using pgvector cosine distance.
    Threshold of 0.3 means we want cosine similarity >= 0.3 (cosine distance <= 0.7).
    """
    max_distance = 1.0 - threshold
    
    stmt = (
        select(Transcript, Transcript.embedding.cosine_distance(embedding).label('distance'))
        .filter(Transcript.embedding.isnot(None))
        .filter(Transcript.meeting_id != current_meeting_id) # exclude current meeting
        .order_by('distance')
        .limit(top_k)
    )
    
    results = db_session.execute(stmt).all()
    
    relevant_transcripts = []
    for transcript, distance in results:
        if distance <= max_distance:
            relevant_transcripts.append(transcript)
            
    return relevant_transcripts
