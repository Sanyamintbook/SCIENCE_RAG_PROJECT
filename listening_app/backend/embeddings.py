import requests
import json
import numpy as np

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "qwen2.5:3b"

def get_embedding(text: str) -> np.ndarray:
    """
    Sends text to Ollama and returns a numpy array representing its vector embedding.
    """
    if not text.strip():
        # Return a zero vector if the text is empty
        # A common dimension for qwen2.5 embeddings might be 4096 or similar.
        # We'll just call the API with a space to get the right dimension.
        text = " "
        
    payload = {
        "model": MODEL_NAME,
        "prompt": text
    }
    
    try:
        response = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        embedding_list = response.json().get("embedding", [])
        if not embedding_list:
            raise ValueError("Empty embedding returned from Ollama")
            
        return np.array(embedding_list, dtype=np.float32)
        
    except Exception as e:
        err_msg = f"Error generating embedding: {str(e)}"
        print(err_msg)
        import os
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(BASE_DIR, "embeddings_error.txt"), "w") as f:
            f.write(err_msg)
        # Return an empty array on error, handle in the caller
        return np.array([], dtype=np.float32)

def calculate_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculates the cosine similarity between two numpy vectors.
    Returns a value between -1.0 and 1.0.
    """
    if vec1.size == 0 or vec2.size == 0:
        return 0.0
        
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return dot_product / (norm1 * norm2)
