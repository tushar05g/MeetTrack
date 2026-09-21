import os

def get_classifier():
    return None

def extract_voice_embedding(audio_path: str):
    """
    Extracts a dummy voice embedding since we are bypassing PyTorch models in Path B.
    """
    import numpy as np
    return np.zeros((192,))

def find_speaker(embedding, db_session, threshold=0.7):
    """
    Finds no speaker since biometrics are disabled.
    """
    return None
