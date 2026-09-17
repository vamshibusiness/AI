# Installation Guide

## Purpose

This guide explains how to install and configure Jarvis locally.

Jarvis is a local-first voice assistant with:

- Wake word detection
- Speech-to-text
- Text-to-speech
- Local LLM support through Ollama
- React/Vite user interface
- Weather
- Gmail
- Google Calendar
- Research Agent
- Local memory

Jarvis supports two installation modes:

- **Standard Mode** – CPU-friendly setup for most machines.
- **Beast Mode** – GPU-accelerated setup for NVIDIA/CUDA machines.

Beast Mode should only install GPU-specific packages when the user explicitly wants local GPU acceleration.

---

# Installation Modes

## Standard Mode

Use Standard Mode if the computer does not have a supported NVIDIA GPU or if the user wants the simplest setup.

Standard Mode uses:

- CPU speech-to-text
- Edge-TTS cloud voice fallback
- Standard local Ollama model
- No CUDA-specific Python packages

Recommended for:

- Laptops
- CPU-only desktops
- New users
- Compatibility testing

---

## Beast Mode

Use Beast Mode only if the computer has a supported NVIDIA GPU and the user wants maximum local performance.

Beast Mode uses:

- NVIDIA CUDA
- GPU speech-to-text
- Kokoro local neural TTS
- Larger research model
- CUDA-enabled PyTorch

Recommended for:

- NVIDIA desktop systems
- RTX-class GPUs
- Users who want local neural TTS
- Users who want faster local transcription

Do not install Beast Mode packages unless Beast Mode is enabled.

---

# Prerequisites

## Required for All Installations

Install these before setting up Jarvis:

- Python 3.12
- Git
- FFmpeg
- Node.js
- npm
- Ollama
- Microphone
- Modern web browser

---

## Required for UI

The Jarvis UI requires:

- Node.js
- npm
- React
- Vite

---

## Required for Local LLM

Install Ollama and pull at least one local model.

Example:

```bash
ollama pull gemma4:e4b
```

If using Beast Mode research, also pull the research model:

```bash
ollama pull qwen3.6:27b
```

---

## Required for Google Features

Gmail and Calendar require:

- Google Cloud project
- Gmail API enabled
- Google Calendar API enabled
- Google People API enabled for contacts
- OAuth credentials downloaded as `google_credentials.json`

Place the credential file here:

 
backend/config/google_credentials.json
```

Jarvis will create:

 
backend/config/token.json
```

after OAuth login.

---

## Required for Beast Mode Only

Only install these if using `BEAST_MODE=true`:

- NVIDIA GPU
- Current NVIDIA driver
- CUDA-compatible PyTorch
- CUDA runtime libraries
- cuBLAS
- cuDNN
- Kokoro

---

# Project Setup

## 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Jarvis
```

---

## 2. Create a Python Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

# Python Package Installation

## Standard Mode Python Packages

Install these for the standard CPU/cloud fallback setup:

```bash
pip install fastapi uvicorn[standard] requests httpx python-dotenv
pip install numpy sounddevice pygame soundfile
pip install faster-whisper edge-tts openwakeword onnxruntime
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
pip install ddgs
```

---

## Beast Mode Python Packages

Install the Standard Mode packages first.

Then install Beast Mode packages only if the user wants GPU acceleration:

```bash
pip install torch
pip install kokoro
```

Depending on the GPU and CUDA version, PyTorch may need to be installed using the official CUDA-specific command from PyTorch.

Example pattern:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Use the PyTorch command that matches the user's installed CUDA/NVIDIA setup.

---

## Why Beast Mode Packages Are Separate

Do not include `torch` and `kokoro` in the default install unless the user chooses Beast Mode.

Reasons:

- GPU packages are large.
- CPU-only users do not need them.
- CUDA setup varies by machine.
- Standard Mode should remain lightweight and easier to install.

---

# Suggested requirements Files

## requirements.txt

Use this for Standard Mode:

 
fastapi
uvicorn[standard]
requests
httpx
python-dotenv

numpy
sounddevice
pygame
soundfile

faster-whisper
edge-tts
openwakeword
onnxruntime

google-api-python-client
google-auth
google-auth-oauthlib
google-auth-httplib2

ddgs
```

---

## requirements-beast.txt

Use this only for Beast Mode:

 
kokoro
torch
```

Install with:

```bash
pip install -r requirements.txt
pip install -r requirements-beast.txt
```

For CUDA-specific PyTorch, install `torch` using the official PyTorch command instead of relying on `requirements-beast.txt`.

---

# Frontend Installation

Go to the frontend folder:

```bash
cd frontend
npm install
```

Run the UI:

```bash
npm run dev
```

Default frontend URL:

 
http://localhost:5173
```

---

# Environment Configuration

## 1. Create `.env`

Create a `.env` file in the project root:

 
Jarvis/
├── .env
├── backend/
└── frontend/
```

---

## 2. Example `.env`

```env
#######################################
# User
#######################################

USER_TITLE=sir
WAKE_RESPONSE=Hello sir, how can I help you?

USER_CITY=New York
USER_STATE=NY

#######################################
# AI
#######################################

OLLAMA_URL=http://localhost:11434/api/chat
CHAT_MODEL=gemma4:e4b
RESEARCH_MODEL=qwen3.6:27b

#######################################
# Gmail
#######################################

KEEP_GMAIL_DAYS=7

#######################################
# Performance
#######################################

BEAST_MODE=false

#######################################
# Future RAG
#######################################

RAG_TOP_K=3
RAG_SCORE_THRESHOLD=0.72
```

---

## 3. Enable Beast Mode

Only set this to true if the user installed the Beast Mode packages and has supported NVIDIA hardware:

```env
BEAST_MODE=true
```

For Standard Mode:

```env
BEAST_MODE=false
```

---

# Google API Setup

## Gmail

Gmail requires:

- Gmail API
- Google OAuth credentials
- `google_credentials.json`
- `token.json`

The Gmail Agent monitors important unread emails, summarizes them, and stores local summaries.

Local files used by Gmail:

 
backend/assets/inbox.json
backend/assets/google_contacts.json
```

---

## Calendar

Calendar requires:

- Google Calendar API
- Google OAuth credentials
- `google_credentials.json`
- `token.json`

Calendar allows Jarvis to:

- View schedules
- Add events
- Modify events
- Delete events

---

## Contacts

Contacts require:

- Google People API

Jarvis syncs contacts so users can say names instead of email addresses.

---

# Weather Setup

Weather requires:

- Internet connection
- Open-Meteo access

No API key is required.

Default location comes from:

```env
USER_CITY=New York
USER_STATE=NY
```

---

# Research Setup

Research requires:

- Internet connection
- Local LLM
- DuckDuckGo Search package

The Research Agent uses:

 
ddgs
```

Completed research is stored locally:

 
backend/assets/completed_research.json
backend/assets/active_research.json
```

---

# Running Jarvis

Jarvis usually needs three processes:

1. Backend API
2. Frontend UI
3. Wake word listener

---

## 1. Start Ollama

Make sure Ollama is running.

Test:

```bash
ollama list
```

---

## 2. Start Backend

From the project root:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 3. Start Frontend

In another terminal:

```bash
cd frontend
npm run dev
```

---

## 4. Start Wake Word Listener

In another terminal:

```bash
python backend/modules/wakeword/listener.py
```

Then say:

 
Hey Jarvis
```

---

# Verification Checklist

## Standard Mode

Confirm:

- `.env` has `BEAST_MODE=false`
- Ollama is running
- Frontend loads
- Backend responds on port 8000
- Wake word listener starts
- Microphone is detected
- Jarvis can answer a basic question
- Jarvis can speak using Edge-TTS

---

## Beast Mode

Confirm:

- `.env` has `BEAST_MODE=true`
- NVIDIA driver is installed
- PyTorch detects CUDA
- Kokoro imports successfully
- Faster Whisper loads on CUDA
- Wake response audio cache generates
- Jarvis speaks locally

Quick CUDA test:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Expected:

 
True
```

---

# Troubleshooting

## Ollama Is Not Responding

Check:

```bash
ollama list
```

Make sure the model in `.env` exists locally.

Example:

```bash
ollama pull gemma4:e4b
```

---

## Wake Word Does Not Start

Check:

- Microphone permissions
- `sounddevice` installation
- `openwakeword` installation
- `onnxruntime` installation

---

## No Audio Output

Check:

- Speakers/headphones
- `pygame`
- `edge-tts` for Standard Mode
- `kokoro` and `soundfile` for Beast Mode

---

## Gmail or Calendar Fails

Check:

 
backend/config/google_credentials.json
backend/config/token.json
```

Also confirm the required Google APIs are enabled.

---

## Beast Mode Fails

Set:

```env
BEAST_MODE=false
```

Then restart Jarvis.

If Standard Mode works, the issue is likely CUDA, PyTorch, or GPU package configuration.

---

# Git Ignore Recommendations

Do not commit local secrets, tokens, memory, inboxes, or research files.


---

# Installation Summary

Standard Mode:

```bash
pip install -r requirements.txt
cd frontend
npm install
```

Beast Mode:

```bash
pip install -r requirements.txt
pip install -r requirements-beast.txt
```

Then set:

```env
BEAST_MODE=true
```

Standard Mode should be the default install.

Beast Mode should be optional and only installed by users with supported NVIDIA GPU hardware.
