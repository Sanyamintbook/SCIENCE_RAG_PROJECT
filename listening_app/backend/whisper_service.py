import os
import speech_recognition as sr
import subprocess

def get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg" # Fallback to system ffmpeg

def transcribe_audio(audio_path: str) -> str:
    """
    Takes a path to an audio file (.wav) and returns the transcribed text.
    We are using the Google Speech API fallback.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # 1. Convert to a clean, standard PCM WAV format using FFmpeg
    # Streamlit browsers often save WebM disguised as .wav, and speech_recognition doesn't support mp3.
    base_name = os.path.splitext(audio_path)[0]
    clean_audio_path = base_name + "_clean.wav"
    try:
        ffmpeg_exe = get_ffmpeg_exe()
        subprocess.run([
            ffmpeg_exe, "-y", "-i", audio_path,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            clean_audio_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Warning: FFmpeg conversion failed, trying original file. Error: {e}")
        clean_audio_path = audio_path
        
    print(f"Transcribing audio using fallback engine: {clean_audio_path}")
    
    recognizer = sr.Recognizer()
    
    try:
        # Load the audio file
        with sr.AudioFile(clean_audio_path) as source:
            # Read the entire audio file
            audio_data = recognizer.record(source)
            
        # Recognize speech using Google's free API
        text = recognizer.recognize_google(audio_data)
        
        # Cleanup temp file
        if clean_audio_path != audio_path and os.path.exists(clean_audio_path):
            os.remove(clean_audio_path)
            
        return text.strip()
        
    except sr.UnknownValueError:
        return "Error: Could not understand the audio."
    except sr.RequestError as e:
        return f"Error: Could not request results from speech recognition service; {e}"
    except Exception as e:
        return f"Error processing audio: {e}"
