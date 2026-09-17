import os
import torch

# Monkey-patch torch.amp for PyTorch 2.1 compatibility with newer SpeechBrain versions
if not hasattr(torch, "amp") or not hasattr(torch.amp, "custom_fwd"):
    if not hasattr(torch, "amp"):
        class _Amp: pass
        torch.amp = _Amp()
        
    def _custom_fwd_wrapper(*args, **kwargs):
        kwargs.pop("device_type", None)
        return torch.cuda.amp.custom_fwd(*args, **kwargs)
        
    def _custom_bwd_wrapper(*args, **kwargs):
        kwargs.pop("device_type", None)
        return torch.cuda.amp.custom_bwd(*args, **kwargs)

    torch.amp.custom_fwd = _custom_fwd_wrapper
    torch.amp.custom_bwd = _custom_bwd_wrapper

import torchaudio
from sqlalchemy import select

# We cache the classifier so it's not reloaded on every inference
_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        try:
            from speechbrain.inference.speaker import EncoderClassifier
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                run_opts={"device": device}
            )
        except ImportError:
            raise RuntimeError("SpeechBrain is not installed. Please install it for biometrics.")
    return _classifier

def extract_voice_embedding(audio_path: str):
    """
    Extracts a 192-dimensional voice embedding vector from an audio file.
    """
    classifier = get_classifier()
    signal, fs = torchaudio.load(audio_path)
    
    # ECAPA-TDNN expects 16kHz audio
    if fs != 16000:
        resampler = torchaudio.transforms.Resample(fs, 16000)
        signal = resampler(signal)
        
    # Ensure audio is mono
    if signal.shape[0] > 1:
        signal = signal.mean(dim=0, keepdim=True)
        
    embeddings = classifier.encode_batch(signal)
    
    # The output is [batch, 1, channels]. We squeeze to a 1D array.
    emb = embeddings.squeeze().detach().cpu().numpy()
    return emb

def find_speaker(embedding, db_session, threshold=0.7):
    """
    Finds the user that matches the voice embedding using pgvector's cosine distance.
    Threshold of 0.7 means we need at least 0.7 cosine similarity 
    (which is a cosine distance <= 0.3).
    """
    from app.models import User
    
    # pgvector cosine_distance returns (1 - cosine_similarity)
    max_distance = 1.0 - threshold
    
    stmt = (
        select(User, User.voice_embedding.cosine_distance(embedding).label('distance'))
        .filter(User.voice_embedding.isnot(None))
        .order_by('distance')
        .limit(1)
    )
    
    result = db_session.execute(stmt).first()
    
    if result:
        user, distance = result
        if distance <= max_distance:
            return user
            
    return None
