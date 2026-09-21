import os
from sqlalchemy import select
from app.models import Transcript, Meeting

def extract_text_embedding(text: str):
    """
    Extracts a 384-dimensional text embedding vector from a string
    using HuggingFace Inference API to avoid local models.
    """
    hf_token = os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("Warning: HUGGINGFACE_TOKEN not set, RAG is disabled.")
        return [0.0] * 384 # Return dummy embedding
        
    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    import requests
    response = requests.post(api_url, headers=headers, json={"inputs": text})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching embedding from HF: {response.text}")
        return [0.0] * 384

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
