from backend.router.registry import INTENT_HANDLERS

def route_command(command: str, history: list) -> str:
    """Evaluates the command against handlers, passing conversation history."""
    for handler in INTENT_HANDLERS:
        if handler.is_related(command):
            # Pass both the command and the current session memory
            return handler.handle(command, history=history)
            
    return "System error: No handlers available."