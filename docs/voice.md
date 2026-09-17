# Voice Engine

## Purpose

The Voice Engine provides all speech input and output capabilities for Jarvis. It is responsible for converting spoken language into text (Speech-to-Text) and converting AI responses back into natural speech (Text-to-Speech).

The engine supports two execution modes:

- **Beast Mode** – Fully local GPU-accelerated processing using NVIDIA CUDA.
- **Standard Mode** – CPU/cloud fallback for systems without dedicated NVIDIA hardware.

---

## User Experience

Voice interaction follows this sequence:

1. User says the wake word.
2. Jarvis acknowledges the request.
3. Speech is recorded until silence is detected.
4. Speech is transcribed into text.
5. Intent is determined.
6. Jarvis executes the requested action.
7. The response is spoken back to the user.

---

## Features

### Speech-to-Text

- Local speech recognition
- Automatic silence detection
- Voice activity detection (VAD)
- GPU acceleration when available
- CPU fallback mode

### Text-to-Speech

- Local neural voice synthesis
- Cloud voice fallback
- Audio caching
- Markdown cleanup before speaking
- Streaming playback

---

# Architecture

```
Wake Word
      │
      ▼
Listener
      │
      ▼
STT (Whisper)
      │
      ▼
Intent Router
      │
      ▼
Action / LLM
      │
      ▼
TTS
      │
      ▼
Speaker
```

---

# Module Breakdown

## stt_whisper.py

### Purpose

Provides speech-to-text processing.

### Responsibilities

- Capture microphone audio
- Detect speech
- Detect silence
- Transcribe speech
- Return recognized text

### Beast Mode

Uses:

- Faster Whisper
- distil-large-v3
- CUDA
- float16

### Standard Mode

Uses:

- Faster Whisper
- base model
- CPU
- int8

### Speech Detection

Audio recording automatically stops when:

- User stops speaking
- Maximum recording time is reached
- No speech is detected

Voice Activity Detection (VAD) is enabled during transcription.

---

## tts.py

### Purpose

Converts Jarvis responses into speech.

### Responsibilities

- Clean markdown from responses
- Route audio generation
- Play generated audio
- Cache common responses

### Beast Mode

Uses:

- Kokoro-82M
- CUDA
- Local neural synthesis

### Standard Mode

Uses:

- Edge-TTS
- Microsoft Neural Voices

### Audio Caching

Frequently used responses are hashed.

If the same text has already been generated:

- Existing audio is reused.
- No regeneration is required.

This greatly reduces response time.

---

# Hardware Modes

## Beast Mode

Designed for desktop systems with NVIDIA GPUs.

Advantages

- Fully local
- Lowest latency
- Highest voice quality
- No internet required for TTS

Uses

- CUDA
- cuBLAS
- cuDNN
- Kokoro
- Faster Whisper

---

## Standard Mode

Designed for laptops and systems without NVIDIA hardware.

Advantages

- Low resource usage
- Easy installation
- High compatibility

Uses

- CPU
- Edge-TTS
- Faster Whisper Base

---

# Configuration

Voice behavior is controlled through:

```
jarvis_config.py
```

Important settings include:

- BEAST_MODE
- Voice selection
- Audio cache
- Wake response audio
- Speech thresholds

---

# Python Files

Voice Engine

```
backend/modules/voice/
stt_whisper.py

tts.py

```

---

# Python Packages

Speech Recognition

- faster-whisper
- numpy

Audio

- pygame
- soundfile

GPU

- torch
- kokoro

Cloud

- edge-tts

Standard Library

- asyncio
- queue
- pathlib
- hashlib
- tempfile
- os
- re

---

# Dependencies

Required

- Python
- FFmpeg
- Ollama

Optional

- NVIDIA GPU
- CUDA Toolkit
- cuBLAS
- cuDNN

---

# Design Decisions

## Why Faster Whisper?

- Excellent transcription accuracy
- Local execution
- GPU acceleration
- Active open-source community

---

## Why Kokoro?

- High quality local neural voice
- Extremely fast on NVIDIA GPUs
- Natural sounding speech
- No cloud dependency

---

## Why Edge-TTS?

- Excellent quality
- Lightweight
- Works on CPU-only systems
- No GPU required

---

## Why Hybrid Mode?

Jarvis is designed to run on as many computers as possible.

Users with powerful NVIDIA hardware receive the best possible experience while users with standard laptops can still run every feature.

---


# Related Documentation

- architecture.md
- wake_word.md
- local_llm.md
- configuration.md