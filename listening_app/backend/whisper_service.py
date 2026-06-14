"""
whisper_service.py
==================
Local, offline speech-to-text using faster-whisper.

Everything happens in RAM:
  - the uploaded audio bytes are decoded into an in-memory waveform via an
    ffmpeg pipe (stdin -> stdout, no temp files),
  - the waveform is transcribed by a locally-downloaded Whisper model.

Nothing is ever written to disk, and no audio leaves the machine.
"""

import subprocess
import numpy as np

# The model is loaded once, lazily, and kept in RAM for reuse.
_model = None
_MODEL_SIZE = "base"   # ~150 MB; good speed/accuracy balance on CPU


def _get_ffmpeg_exe():
    """Prefer the bundled ffmpeg from imageio-ffmpeg, else the system one."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _get_model():
    """Load the Whisper model once and keep it in memory."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # int8 on CPU keeps memory low and runs fast without a GPU.
        _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _decode_to_waveform(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Convert arbitrary audio bytes (wav / mp3 / m4a / webm ...) into a mono
    float32 waveform entirely in memory using an ffmpeg pipe. No temp files.
    """
    ffmpeg = _get_ffmpeg_exe()
    proc = subprocess.run(
        [
            ffmpeg, "-nostdin", "-threads", "0",
            "-i", "pipe:0",                       # read input from stdin
            "-f", "f32le", "-acodec", "pcm_f32le",
            "-ac", "1", "-ar", str(sample_rate),
            "pipe:1",                             # write raw PCM to stdout
        ],
        input=audio_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="ignore")[-300:]
        raise RuntimeError(f"ffmpeg failed to decode audio: {detail}")

    # .copy() makes the buffer writable (np.frombuffer is read-only).
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Transcribe in-memory audio bytes to text. RAM-only and fully offline.
    Raises on failure so the caller can report a clear error.
    """
    if not audio_bytes:
        raise ValueError("No audio data received.")

    waveform = _decode_to_waveform(audio_bytes)
    if waveform.size == 0:
        raise RuntimeError("Decoded audio is empty.")

    model = _get_model()
    segments, _info = model.transcribe(waveform, beam_size=1)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text
