import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
# We use qwen2.5:3b or whatever model is currently pulled. 
# The user mentioned having qwen2.5:3b and qwen2.5:7b. We'll use 3b for speed, 
# or you can change it to 7b for better accuracy.
MODEL_NAME = "qwen2.5:3b"

def evaluate_answer(expected_answer: str, student_answer: str) -> dict:
    """
    Compares the student's answer against the expected answer semantically.
    Returns a dictionary with 'score' (0-100) and 'feedback' (string).
    """
    
    prompt = f"""You are a strict but fair teacher evaluating a student's listening comprehension answer.

Teacher's Expected Answer: "{expected_answer}"
Student's Answer: "{student_answer}"

Task:
1. Compare the MEANING of the student's answer to the expected answer. Do not punish for spelling or grammar mistakes if the meaning is correct.
2. Give a Score from 0 to 100 based on how well the core concepts match.
3. Provide exactly ONE sentence of constructive feedback.

Format your response EXACTLY like this (and nothing else):
Score: [number]
Feedback: [your one sentence feedback]
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.1  # Low temperature for consistent grading
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        result_text = response.json().get("response", "").strip()
        
        # Parse the output
        score = 0
        feedback = "Could not generate feedback."
        
        # Extract score using regex
        score_match = re.search(r"Score:\s*(\d+)", result_text)
        if score_match:
            score = int(score_match.group(1))
            
        # Extract feedback using regex
        feedback_match = re.search(r"Feedback:\s*(.+)", result_text, re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
            
        return {
            "score": min(max(score, 0), 100), # Ensure it's between 0 and 100
            "feedback": feedback
        }
        
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return {
            "score": 0,
            "feedback": f"Error communicating with AI evaluator: {str(e)}"
        }

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load model once (global for performance)
model = SentenceTransformer('all-MiniLM-L6-v2')

def validate_text_accuracy(text1: str, text2: str, threshold: float = 0.75):
    """
    Compare two texts using FAISS embeddings and return similarity score + decision.

    Args:
        text1 (str): Reference text
        text2 (str): Input text to validate
        threshold (float): Similarity threshold (0 to 1)

    Returns:
        dict: {
            "similarity_score": float,
            "is_accurate": bool
        }
    """

    # Step 1: Generate embeddings
    embeddings = model.encode([text1, text2])
    
    # Normalize for cosine similarity
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    # Step 2: Create FAISS index (cosine similarity using Inner Product)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)

    # Step 3: Add reference embedding (text1)
    index.add(np.array([embeddings[0]]).astype('float32'))

    # Step 4: Search similarity for text2
    D, I = index.search(np.array([embeddings[1]]).astype('float32'), k=1)

    similarity_score = float(D[0][0])  # cosine similarity

    # Step 5: Decision
    is_accurate = similarity_score >= threshold

    return {
        "similarity_score": round(similarity_score, 4),
        "is_accurate": is_accurate
    }

def evaluate_dictation(expected_transcript: str, student_dictation: str, threshold: float = 0.75) -> dict:
    """
    Wrapper function to use the user's provided FAISS validation logic.
    Converts the output to the format expected by listening_api.py
    """
    try:
        # Call the user's exact function
        result = validate_text_accuracy(expected_transcript, student_dictation, threshold)
        
        print('validate_text_accuracy................');
        
        similarity = result["similarity_score"]
        is_accurate = result["is_accurate"]
        
        # Convert 0-1 similarity to 0-100 score
        score = int((similarity - 0.5) * (100 / 0.45))
        score = min(max(score, 0), 100)
        
        if is_accurate:
            score = 100
            
        if score == 100:
            feedback = "Excellent dictation! Your understanding is highly accurate."
        elif score >= 75:
            feedback = "Good job! You captured most of the key concepts but missed a few words."
        elif score >= 50:
            feedback = "Fair attempt, but you missed a significant portion of the audio context."
        else:
            feedback = "Poor dictation. It seems you had trouble understanding the audio."
            
        return {
            "score": score,
            "feedback": f"{feedback} (Similarity score: {similarity})"
        }
        
    except Exception as e:
        print(f"Error in vector evaluation: {e}")
        return {
            "score": 0,
            "feedback": f"Error using vector embeddings: {str(e)}"
        }
