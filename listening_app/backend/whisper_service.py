"""
whisper_service.py
==================
Local, offline speech-to-text (audio -> words) using faster-whisper.

Everything happens in RAM:
  - the uploaded audio bytes are decoded into an in-memory waveform via an
    ffmpeg pipe (stdin -> stdout, no temp files),
  - the waveform is transcribed by a locally-downloaded Whisper model.

Nothing is ever written to disk, and no audio leaves the machine.

WHO CALLS THIS: listening_api.py calls transcribe_audio_bytes() when the
teacher uploads an audio clip (see listening_api.py -> create_assignment).
"""

import subprocess          # standard library: lets us run the external ffmpeg program
import numpy as np         # third-party: arrays of numbers; Whisper wants the audio as a numpy array

# Module-level cache for the loaded model. We load it once (it is heavy) and
# reuse it for every transcription. Starts as None = "not loaded yet".
_model = None
_MODEL_SIZE = "base"       # which Whisper model to download/use; "base" ~150 MB, good CPU speed/accuracy


def _get_ffmpeg_exe():
    """Return the path to an ffmpeg executable (prefer the bundled one)."""
    try:
        import imageio_ffmpeg                       # third-party: ships a ready-to-use ffmpeg binary
        return imageio_ffmpeg.get_ffmpeg_exe()      # ask it for the path to that binary
    except Exception:
        return "ffmpeg"                             # fallback: assume ffmpeg is on the system PATH


def _get_model():
    """Load the Whisper model once and keep it in memory for reuse."""
    global _model                                   # we want to modify the module-level _model variable
    if _model is None:                              # only load on the first call
        from faster_whisper import WhisperModel     # third-party: the local Whisper engine (uses ctranslate2, not torch)
        # device="cpu" + compute_type="int8" = run on the CPU using low memory.
        _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model                                   # hand back the (now cached) model


def _decode_to_waveform(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Convert arbitrary audio bytes (wav / mp3 / m4a / webm ...) into a mono
    float32 waveform entirely in memory using an ffmpeg pipe. No temp files.
    """
    ffmpeg = _get_ffmpeg_exe()                       # find the ffmpeg program to run
    proc = subprocess.run(                           # run ffmpeg as a child process
        [
            ffmpeg, "-nostdin", "-threads", "0",     # don't wait for keyboard input; use all CPU threads
            "-i", "pipe:0",                          # INPUT comes from stdin (pipe 0), not a file
            "-f", "f32le", "-acodec", "pcm_f32le",   # OUTPUT format: raw 32-bit float little-endian PCM
            "-ac", "1", "-ar", str(sample_rate),     # 1 audio channel (mono), 16000 samples/second
            "pipe:1",                                # write that raw audio to stdout (pipe 1)
        ],
        input=audio_bytes,                           # feed the uploaded bytes into ffmpeg's stdin
        stdout=subprocess.PIPE,                       # capture ffmpeg's stdout (the decoded audio)
        stderr=subprocess.PIPE,                       # capture errors (so they don't spam the console)
    )
    if proc.returncode != 0:                         # non-zero exit code means ffmpeg failed
        detail = proc.stderr.decode(errors="ignore")[-300:]   # last 300 chars of the error message
        raise RuntimeError(f"ffmpeg failed to decode audio: {detail}")

    # np.frombuffer reads the raw bytes as float32 numbers; .copy() makes the
    # array writable (Whisper needs a writable array).
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Transcribe in-memory audio bytes to text. RAM-only and fully offline.
    Raises on failure so the caller can report a clear error.
    """
    if not audio_bytes:                              # guard: empty upload
        raise ValueError("No audio data received.")

    waveform = _decode_to_waveform(audio_bytes)      # bytes -> numpy waveform (defined above)
    if waveform.size == 0:                           # ffmpeg produced no samples
        raise RuntimeError("Decoded audio is empty.")

    model = _get_model()                             # get the cached Whisper model (defined above)
    # model.transcribe() returns a generator of "segments" (chunks of speech)
    # plus info; beam_size=1 = fastest greedy decoding.
    segments, _info = model.transcribe(waveform, beam_size=1)
    # Join every segment's text into one string, trimming whitespace.
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text                                      # the final transcript, handed back to listening_api.py
