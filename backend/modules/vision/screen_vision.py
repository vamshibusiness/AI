# backend/modules/vision/screen_vision.py
"""
screen_vision.py — Modular screen vision and OCR for JARVIS.

Respects RTX 3050 4 GB VRAM limits:
- Uses `keep_alive: 0` when calling Ollama vision models so they unload immediately.
- Temporary screenshots are written to secure isolated temp directory and deleted after processing.
"""
import base64
import io
import os
import tempfile
import time
from pathlib import Path
import requests

VISION_MODEL = os.getenv("VISION_MODEL", "llama3.2-vision")
OLLAMA_URL = os.getenv("OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate")


def capture_screen_base64() -> tuple[str | None, str | None]:
    """
    Capture the current screen into a base64 encoded string.
    Returns: (base64_str, temp_file_path)
    """
    try:
        import pyautogui
        tmp_dir = Path(tempfile.gettempdir()) / "jarvis_vision"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        img_path = tmp_dir / f"screen_{int(time.time())}.png"
        
        screenshot = pyautogui.screenshot()
        screenshot.save(str(img_path))

        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            
        return encoded, str(img_path)
    except Exception as e:
        print(f"[ScreenVision] Capture failed: {e}")
        return None, None


def extract_screen_text(img_path: str = None) -> dict:
    """
    Extract text using OCR (tesseract / pytesseract) without using GPU VRAM.
    """
    temp_created = False
    if not img_path:
        _, img_path = capture_screen_base64()
        temp_created = True

    if not img_path or not os.path.exists(img_path):
        return {"ok": False, "error": "Could not capture or find image."}

    try:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img).strip()
            return {"ok": True, "text": text, "count": len(text)}
        except ImportError:
            return {"ok": False, "error": "pytesseract not installed. Please install tesseract to use lightweight OCR."}
    finally:
        if temp_created and img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass


def analyze_screen(prompt: str = "Describe what is on the screen succinctly.") -> dict:
    """
    Analyze the screen using a local multimodal model via Ollama.
    Enforces `keep_alive: 0` to preserve the 4 GB VRAM ceiling.
    """
    b64_img, img_path = capture_screen_base64()
    if not b64_img:
        return {"ok": False, "error": "Failed to capture screen."}

    try:
        payload = {
            "model": VISION_MODEL,
            "prompt": prompt,
            "images": [b64_img],
            "stream": False,
            "keep_alive": 0,  # CRITICAL for 4 GB VRAM: unload immediately after inference
        }

        res = requests.post(OLLAMA_URL, json=payload, timeout=40)
        if res.status_code == 200:
            data = res.json()
            analysis = data.get("response", "").strip()
            return {"ok": True, "analysis": analysis, "model": VISION_MODEL}
        else:
            return {
                "ok": False,
                "error": f"Vision model '{VISION_MODEL}' returned {res.status_code}: {res.text[:100]}",
            }
    except Exception as e:
        return {"ok": False, "error": f"Vision analysis error: {e}"}
    finally:
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass
