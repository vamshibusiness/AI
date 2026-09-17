import queue
import threading
import re
import requests
from backend.modules.llm.local_llm import ask_local_llm_stream
from backend.modules.voice.tts import speak

class StreamedResponse(str):
    """A helper string subclass to signal that this response has already been spoken via streaming."""
    def __new__(cls, value, *args, **kwargs):
        obj = super().__new__(cls, value)
        obj.is_streamed = True
        return obj

class ChatHandler:
    def is_related(self, command: str) -> bool:
        """Always returns True. This is the fallback handler."""
        return bool(command)
    
    def handle(self, command: str, history: list = None, speak_response: bool = True) -> str:
        """Streams the LLM response to console. Speaks in sentence chunks ONLY if speak_response is True."""
        print("Jarvis: ", end="", flush=True)

        speech_queue = queue.Queue() if speak_response else None
        ui_notified = False
        worker_thread = None

        if speak_response:
            def speech_worker():
                nonlocal ui_notified
                while True:
                    chunk = speech_queue.get()
                    if chunk is None:
                        speech_queue.task_done()
                        break

                    if not ui_notified:
                        try:
                            requests.get("http://localhost:8000/trigger-speaking", timeout=0.5)
                        except requests.RequestException:
                            pass
                        ui_notified = True

                    speak(chunk)
                    speech_queue.task_done()

            worker_thread = threading.Thread(target=speech_worker, daemon=True)
            worker_thread.start()

        full_response = ""
        buffer = ""
        sentence_end = re.compile(r'(?<=[.!?])\s+|\n+')

        for token in ask_local_llm_stream(history):
            print(token, end="", flush=True)
            full_response += token
            if speak_response:
                buffer += token
                while True:
                    match = sentence_end.search(buffer)
                    if not match:
                        break
                    idx = match.end()
                    sentence = buffer[:idx].strip()
                    buffer = buffer[idx:]
                    if sentence:
                        speech_queue.put(sentence)

        print()

        if speak_response and worker_thread:
            if buffer.strip():
                speech_queue.put(buffer.strip())
            speech_queue.put(None)
            worker_thread.join()

        return StreamedResponse(full_response.strip())