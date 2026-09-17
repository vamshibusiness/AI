# stt_whisper.py
import os
import sys
import numpy as np
import queue
from faster_whisper import WhisperModel
from backend.config.jarvis_config import BEAST_MODE

SAMPLE_RATE = 16000
CHUNK_SIZE = 1600 

# =====================================================================
# CONDITIONAL HARDWARE INITIALIZATION
# =====================================================================
if BEAST_MODE:
    print("🚀 [STT Engine] Activating Beast Mode. Injecting Blackwell CUDA Binaries...")
    # Explicitly point to your VS Code virtual environment site-packages
    venv_site_packages = r"C:\VS Code\Jarvis\.venv\Lib\site-packages"

    # Define the precise directories where your GPU packages store their .dll files
    paths_to_inject = [
        os.path.join(venv_site_packages, "nvidia", "cublas", "bin"),
        os.path.join(venv_site_packages, "nvidia", "cudnn", "bin"),
        os.path.join(venv_site_packages, "torch", "lib")
    ]

    # Force Windows to look inside these directories
    for path in paths_to_inject:
        if os.path.exists(path):
            os.environ["PATH"] = path + os.path.pathsep + os.environ["PATH"]
            print(f"Successfully bound CUDA path: {path}")

    # Load the optimal flagship setup for dedicated hardware
    model = WhisperModel(
        "distil-large-v3",       # Flagship-grade accuracy but lightning fast
        device="cuda",           # Commands the underlying NVIDIA CUDA cores
        compute_type="float16"   # Leverages your RTX Tensor Cores for instant processing
    )
    print("Whisper successfully loaded on NVIDIA GPU (FP16 Mode)")

    if model is None:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )
        print("GPU Model failed to load, reverting back to CPU")
else:
    print("☁️ [STT Engine] Launching Standard Core (Lightweight CPU Fallback)...")
    # Loads a small, highly compressed model optimized for standard processors
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )
    print("Whisper successfully loaded on CPU (INT8 Mode)")


def listen_for_question(audio_queue: queue.Queue, seconds: int = 6) -> str:
    print("Listening for your question. Speak now.")

    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

    chunks_per_second = SAMPLE_RATE / CHUNK_SIZE  
    max_chunks = int(seconds * chunks_per_second)
    
    silence_duration_limit = 1.0
    silence_chunks_limit = int(silence_duration_limit * chunks_per_second)
    
    initial_silence_limit = seconds 
    initial_silence_chunks_limit = int(initial_silence_limit * chunks_per_second)

    silence_threshold = 0.012

    recorded_chunks = []
    silence_counter = 0
    initial_silence_counter = 0  
    has_spoken = False

    for _ in range(max_chunks):
        try:
            chunk = audio_queue.get(timeout=1.0)
        except queue.Empty:
            break

        recorded_chunks.append(chunk)
        volume = np.sqrt(np.mean(chunk ** 2))

        if volume > silence_threshold:
            if not has_spoken:
                print("Speech detected...")
            has_spoken = True
            silence_counter = 0
        else:
            if has_spoken:
                silence_counter += 1
            else:
                initial_silence_counter += 1

        if has_spoken and silence_counter >= silence_chunks_limit:
            print("Silence detected. Stopping recording early...")
            break
            
        if not has_spoken and initial_silence_counter >= initial_silence_chunks_limit:
            print("No speech detected within time limit. Stopping early...")
            break

    if not recorded_chunks or not has_spoken:
        print("No speech captured.")
        return ""

    audio_float32 = np.concatenate(recorded_chunks, axis=0).flatten()

    # Dynamic print statement matching chosen hardware execution path
    engine_label = "GPU" if BEAST_MODE else "CPU"
    print(f"Transcribing on {engine_label}...")
    
    segments, info = model.transcribe(
        audio_float32,
        language="en",
        vad_filter=True,
        beam_size=5,
        best_of=5,
        patience=1.2,
        condition_on_previous_text=False
    )

    text = " ".join(segment.text.strip() for segment in segments).strip()
    print(f"You said: {text}")
    return text