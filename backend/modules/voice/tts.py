# tts.py
import asyncio
import pygame
import tempfile
import os
import hashlib
from pathlib import Path
import re
from queue import Queue
import threading
from threading import Thread
import time
from backend.config.jarvis_config import BEAST_MODE

_stop_playback = threading.Event()


def stop_speaking():
    """Immediately interrupt and stop any ongoing TTS speech playback."""
    _stop_playback.set()
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass


def is_speaking() -> bool:
    """Return True if TTS audio is currently playing."""
    try:
        return pygame.mixer.get_init() and pygame.mixer.music.get_busy()
    except Exception:
        return False

pygame.mixer.init()

# Global pipeline placeholder for local neural generation
pipeline = None
audio_queue = Queue()

import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# =====================================================================
# CONDITIONAL TEXT-TO-SPEECH ROUTING CONFIGURATION
# =====================================================================
if BEAST_MODE:
    print("[TTS Engine] Activating Beast Mode. Binding Blackwell Compute Layers...")
    # Path Injection Wrapper
    venv_site_packages = os.path.join(sys.prefix, "Lib", "site-packages")
    paths_to_inject = [
        os.path.join(venv_site_packages, "nvidia", "cublas", "bin"),
        os.path.join(venv_site_packages, "nvidia", "cudnn", "bin"),
        os.path.join(venv_site_packages, "torch", "lib")
    ]
    for path in paths_to_inject:
        if os.path.exists(path):
            os.environ["PATH"] = path + os.path.pathsep + os.environ["PATH"]

    try:
        import torch
        import soundfile as sf
        from kokoro import KPipeline
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[TTS Engine] Initializing Kokoro-82M on: {device.upper()}")
        
        # 'b' sets the British English language pack profile
        pipeline = KPipeline(lang_code='b')
    except ImportError as e:
        print(f"[TTS Engine] Failed to load local neural architecture: {e}. Falling back to Cloud Core.")
        BEAST_MODE = False
else:
    print("[TTS Engine] Initializing Standard Core (Lightweight Cloud Processing)...")
    import edge_tts

# Edge-TTS Specific settings preserved for CPU fallback mode
VOICE = "en-GB-ThomasNeural"
PITCH = "-5Hz"
RATE = "+10%"


def get_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def play_mp3(filename: str, on_start=None):
    if _stop_playback.is_set():
        return
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    if on_start:
        on_start()

    while pygame.mixer.music.get_busy() and not _stop_playback.is_set():
        pygame.time.wait(10)

    pygame.mixer.music.stop()
    pygame.mixer.music.unload()


# --- CPU Mode: Cloud Execution Architecture ---
async def generate_audio_file_async(text: str, filename: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, pitch=PITCH, rate=RATE)
    await communicate.save(filename)


async def speak_async(text: str, on_start=None):
    if not text or not text.strip():
        return

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    filename = temp_file.name
    temp_file.close()

    try:
        await generate_audio_file_async(text, filename)
        play_mp3(filename, on_start)
    finally:
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception:
            pass


# --- GPU Mode: Local Neural Execution Architecture ---
def speak_beast_mode(text: str, on_start=None):
    import soundfile as sf
    
    # Process text fragments sequentially through the local pipeline
    generator = pipeline(
        text, 
        voice='bm_lewis', 
        speed=1.1, 
        split_pattern=r'\n+'
    )
    
    # Track state to guarantee the UI on_start callback only fires once on the first chunk
    callback_fired = False

    for i, (gs, ps, audio) in enumerate(generator):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        filename = temp_file.name
        temp_file.close()
        
        try:
            # Kokoro natively outputs high-fidelity 24000Hz PCM floats
            sf.write(filename, audio, 24000)
            
            # Fire the UI state trigger the millisecond the first file is written and ready
            if on_start and not callback_fired:
                play_mp3(filename, on_start=on_start)
                callback_fired = True
            else:
                play_mp3(filename)
        finally:
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception:
                pass


# =====================================================================
# MASTER ENTRYPOINT (Preserves signature integration with framework)
# =====================================================================
def speak_chunk(text: str, on_start=None):
    if BEAST_MODE and pipeline is not None:
        speak_beast_mode(text, on_start)
    else:
        asyncio.run(speak_async(text, on_start))


def speak(text: str, on_start=None):
    _stop_playback.clear()
    text = clean_for_speech(text)
    if not text:
        return

    parts = re.split(r"(\[\[pause:\d+(?:\.\d+)?\]\])", text)

    on_start_used = False

    for part in parts:
        if _stop_playback.is_set():
            break
        part = part.strip()

        if not part:
            continue

        pause_match = re.fullmatch(r"\[\[pause:(\d+(?:\.\d+)?)\]\]", part)

        if pause_match:
            seconds = float(pause_match.group(1))
            time.sleep(seconds)
            continue

        speak_chunk(
            part,
            on_start=on_start if not on_start_used else None
        )
        on_start_used = True

def clean_for_speech(text: str) -> str:
    if not text:
        return ""
    text = text.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
    text = text.replace("`", "")
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate_cached_audio(text: str, audio_path: str, hash_path: str):
    """
    Preserves boot asset preprocessing capability for wake word feedback.
    Dynamically creates a local GPU .wav or cloud .mp3 under the assets folder
    depending on the active execution framework (BEAST_MODE).
    """
    import numpy as np
    
    audio_file = Path(audio_path)
    hash_file = Path(hash_path)
    
    # 1. Dynamic Asset Routing: If local GPU engine is alive, enforce WAV specifications
    if BEAST_MODE and pipeline is not None:
        if audio_file.suffix == '.mp3':
            audio_file = audio_file.with_suffix('.wav')
        if hash_file.suffix == '.txt' or hash_file.suffix == '.hash':
            hash_file = hash_file.with_suffix('.wav.hash')

    # 2. Replicate directory tree structure (Ensures assets/ folder exists)
    audio_file.parent.mkdir(parents=True, exist_ok=True)

    current_hash = get_text_hash(text)
    saved_hash = None
    if hash_file.exists():
        saved_hash = hash_file.read_text().strip()

    # 3. Cache Validation Check
    if audio_file.exists() and saved_hash == current_hash:
        print(f"Wake response audio cache is current: {audio_file.name}")
        return

    print(f"Generating wake response audio asset -> {audio_file.name}...")
    try:
        if BEAST_MODE and pipeline is not None:
            import soundfile as sf
            
            # Run text through local Blackwell-bound Kokoro pipeline
            generator = pipeline(
                text, 
                voice='bm_lewis', # Modern British accent asset
                speed=1.1, 
                split_pattern=r'\n+'
            )
            
            # Collect and stitch raw audio matrix arrays together
            audio_chunks = []
            for _, _, audio in generator:
                audio_chunks.append(audio)
                
            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                # Write uncompressed 24kHz master WAV directly to your assets directory
                sf.write(str(audio_file), full_audio, 24000)
                print(f"⚡ [TTS Cache] Local GPU WAV asset successfully baked to disk.")
        else:
            # Fallback: Run legacy async cloud workflow to output compressed MP3
            import asyncio
            asyncio.run(generate_audio_file_async(text, str(audio_file)))
            print(f"☁️ [TTS Cache] Standard Cloud MP3 asset downloaded successfully.")
            
        # Write matching validation verification hash file
        hash_file.write_text(current_hash)
        
    except Exception as e:
        print(f"❌ Failed to compile wake response cache asset: {e}")