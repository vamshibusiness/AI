from backend.router.registry import INTENT_HANDLERS
import inspect

def route_command(command: str, history: list, speak_response: bool = True) -> str:
    """Evaluates the command against handlers, passing conversation history."""
    for handler in INTENT_HANDLERS:
        if handler.is_related(command):
            # Inspect signature to pass speak_response if supported
            sig = inspect.signature(handler.handle)
            if "speak_response" in sig.parameters:
                return handler.handle(command, history=history, speak_response=speak_response)
            return handler.handle(command, history=history)

    return "System error: No handlers available."