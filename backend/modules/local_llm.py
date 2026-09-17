import requests
import json
from backend.config.jarvis_config import BEAST_MODE, OLLAMA_URL, CHAT_MODEL, RESEARCH_MODE



MODEL_NAME = CHAT_MODEL



def ask_local_llm_stream(messages: list, model_name: str = MODEL_NAME, keep_alive=None,  num_predict: int = None):
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
    } 
    options = {}   

    if num_predict is not None:
        options["num_predict"] = num_predict

    if options:
        payload["options"] = options

    if keep_alive is not None:
        payload["keep_alive"] = keep_alive

    if model_name == MODEL_NAME:
        payload["think"] = False    

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("message", {}).get("content", "")
                yield token

    except Exception as e:
        print(f"Ollama error: {e}")
        yield "Critical Exception: Mainframe link offline. Check local engine deployment."

def ask_local_llm(messages: list) -> str:
    """
    Non-streaming wrapper for background tasks.
    Returns the full string response from the LLM.
    """
    full_response = ""
    for token in ask_local_llm_stream(messages):
        full_response += token
    return full_response        

def ask_local_llm_research(messages: list) -> str:
    """
    Non-streaming wrapper for background research.
    Research should not keep the model loaded in VRAM.
    """
    research_model = RESEARCH_MODE if BEAST_MODE else MODEL_NAME

    full_response = ""

    try:
        for token in ask_local_llm_stream(
            messages,
            model_name=research_model,
            keep_alive=0,
            num_predict=2048,
        ):
            full_response += token

        return full_response

    finally:
        unload_ollama_model(research_model)       


def unload_ollama_model(model_name: str) -> None:
    try:
        requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "messages": [],
                "keep_alive": 0,
            },
            timeout=10,
        )
        print(f"[Ollama] Unloaded research model: {model_name}")
    except Exception as e:
        print(f"[Ollama] Could not unload research model: {e}")