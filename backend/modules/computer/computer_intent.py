# backend/modules/computer/computer_intent.py
"""
computer_intent.py — ComputerHandler for the existing intent router.

Uses a hybrid detection strategy:
  1. Fast keyword regex pre-filter to detect obvious computer commands
  2. LLM for ambiguous cases and for structured tool+argument extraction
  3. controller.dispatch() to safely execute the action
  4. Streams action status events back to the UI via WebSocket broadcasts

Insert BEFORE ChatHandler in registry.py so it takes priority.
"""
import re
import json
import requests
from backend.modules.computer.controller import (
    dispatch,
    dispatch_sequence,
    format_results_for_llm,
    get_allowed_tools,
)
from backend.modules.computer.files import prepare_delete

_COMPUTER_PATTERNS = re.compile(
    r"\b(open|launch|start|run|close|quit|exit|kill)\b.{0,30}\b(chrome|firefox|edge|notepad|calculator|explorer|vscode|vs code|spotify|discord|slack|zoom|paint|word|excel|powershell|terminal|cmd)\b"
    r"|open (youtube|google|gmail|github|netflix|reddit|whatsapp|instagram|twitter|amazon|linkedin|wikipedia)\b"
    r"|search (google|youtube|bing|web) for\b"
    r"|search for .{2,60} on (google|youtube|bing)\b"
    r"|\b(type|write|enter) .{1,200} (in|into|on) (notepad|word|terminal|the document|it)\b"
    r"|type (this|the following|hello|the message|text)\b"
    r"|\b(take a|capture a?|grab a?) screenshot\b"
    r"|create (a )?folder\b"
    r"|create (a )?file\b"
    r"|open (my )?(downloads|desktop|documents|pictures|videos|music) folder\b"
    r"|\bopen downloads\b|\bopen desktop\b|\bopen documents\b"
    r"|press (enter|escape|ctrl|alt|tab|backspace|delete|the)\b"
    r"|hold (ctrl|alt|shift)\b"
    r"|delete (the |a |this )?(file|folder)\b"
    r"|list (the )?files\b"
    r"|show (me )?(files|what.s in|the contents of)\b"
    r"|rename (the )?(file|folder)\b"
    r"|move (the )?(file|folder)\b",
    re.IGNORECASE,
)

_TOOL_EXTRACTION_PROMPT = """You are a computer-control assistant. The user said:
"{command}"

Your task: Identify which computer tools to call and in what order.

Available tools and their required arguments:
- open_application(application: str) — open Chrome, Notepad, Calculator, etc.
- close_application(application: str)
- open_website(site: str) — site can be "youtube", "google", or a full https:// URL
- web_search(query: str, engine: str="google") — engine options: google, youtube, bing
- type_text(text: str, app: str=null) — app is optional, focus that app before typing
- press_key(key: str) — enter, escape, tab, ctrl, etc.
- hotkey(keys: list) — e.g. ["ctrl","c"]
- create_folder(name: str, location: str="desktop")
- create_file(name: str, location: str="desktop", content: str="")
- open_folder(location: str) — desktop, downloads, documents, or a path
- list_files(location: str="desktop")
- rename_file(path: str, new_name: str)
- move_file(source: str, destination: str)
- take_screenshot()
- delete_file(path: str) — will ask user for confirmation first
- delete_folder(path: str) — will ask user for confirmation first

Respond ONLY with valid JSON. No explanation, no markdown, no extra text.

For a single action:
{{"steps": [{{"tool": "tool_name", "arguments": {{...}}}}]}}

For multi-step (e.g. "Open Notepad and type Hello"):
{{"steps": [{{"tool": "open_application", "arguments": {{"application": "notepad"}}}}, {{"tool": "type_text", "arguments": {{"text": "Hello", "app": "notepad"}}}}]}}

If this is NOT a computer control command, respond with:
{{"steps": []}}
"""


def _is_computer_command(command: str) -> bool:
    """Fast keyword pre-filter. Returns True if definitely a computer command."""
    return bool(_COMPUTER_PATTERNS.search(command))


def _extract_tools_from_llm(command: str) -> list[dict]:
    """Ask Ollama to parse tool steps. Returns list of {tool, arguments} dicts."""
    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.2:3b",
            "prompt": _TOOL_EXTRACTION_PROMPT.format(command=command),
            "stream": False,
        }
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code != 200:
            return []

        raw = res.json().get("response", "").strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            print(f"[ComputerHandler] No JSON found in LLM response: {raw[:100]}")
            return []

        data = json.loads(match.group(0))
        return data.get("steps", [])
    except Exception as e:
        print(f"[ComputerHandler] Error in _extract_tools_from_llm: {e}")
        return []


def _broadcast_action_status(status_type: str, message: str, success: bool = True):
    """Broadcast a computer action status event to the UI via WebSocket."""
    try:
        requests.post(
            "http://localhost:8000/ws/broadcast",
            json={
                "type": "computer_action_status",
                "status": status_type,
                "message": message,
                "success": success,
            },
            timeout=0.5,
        )
    except Exception:
        pass


def _step_description(tool: str, args: dict) -> str:
    """Human-readable description of what a step will do."""
    descriptions = {
        "open_application": f"Opening {args.get('application', 'application')}",
        "close_application": f"Closing {args.get('application', 'application')}",
        "open_website": f"Opening {args.get('site', args.get('url', 'website'))}",
        "web_search": f"Searching for '{args.get('query', '')}'",
        "type_text": f"Typing text",
        "press_key": f"Pressing {args.get('key', 'key')}",
        "hotkey": f"Pressing shortcut {'+'.join(args.get('keys', []))}",
        "create_folder": f"Creating folder '{args.get('name', '')}'",
        "create_file": f"Creating file '{args.get('name', '')}'",
        "open_folder": f"Opening {args.get('location', 'folder')}",
        "list_files": f"Listing files in {args.get('location', 'folder')}",
        "rename_file": f"Renaming to '{args.get('new_name', '')}'",
        "move_file": f"Moving '{args.get('source', '')}'",
        "take_screenshot": "Taking screenshot",
        "delete_file": f"Deleting '{args.get('path', '')}'",
        "delete_folder": f"Deleting folder '{args.get('path', '')}'",
        "mouse_click": "Clicking mouse",
        "mouse_double_click": "Double-clicking",
        "mouse_right_click": "Right-clicking",
    }
    return descriptions.get(tool, tool.replace("_", " ").title())


class ComputerHandler:
    def is_related(self, command: str) -> bool:
        """Returns True if this looks like a computer control command."""
        return _is_computer_command(command)

    def handle(
        self,
        command: str,
        history: list = None,
        stream: bool = False,
        speak_output: bool = True,
        on_start: callable = None,
        on_chunk: callable = None,
        on_complete: callable = None,
    ):
        """
        Parse the command, execute tools, verify results, and return a natural-language response.
        Broadcasts live action status events to the UI.
        """
        print(f"[ComputerHandler] Handling: {command}")
        _broadcast_action_status("running", "⚙ Analysing command...", True)

        steps = _extract_tools_from_llm(command)
        if not steps:
            # Fallback to chat handler if no steps extracted
            from backend.modules.llm.chat_intent import ChatHandler
            return ChatHandler().handle(
                command,
                history=history,
                stream=stream,
                speak_output=speak_output,
                on_start=on_start,
                on_chunk=on_chunk,
                on_complete=on_complete,
            )

        # Intercept delete actions to request confirmation
        for step in steps:
            tool = step.get("tool", "")
            args = step.get("arguments", {})
            if tool in ("delete_file", "delete_folder"):
                _broadcast_action_status("running", "⚙ Checking file...", True)
                prep = prepare_delete(args.get("path", ""))
                if prep.get("success"):
                    try:
                        requests.post(
                            "http://localhost:8000/ws/broadcast",
                            json={
                                "type": "confirm_delete",
                                "name": prep.get("name"),
                                "size": prep.get("size"),
                                "path": prep.get("target"),
                                "is_dir": prep.get("is_dir"),
                            },
                            timeout=0.5,
                        )
                    except Exception:
                        pass
                    msg = f"I found **{prep.get('name')}** ({prep.get('size')}). Do you want me to permanently delete it?"
                else:
                    msg = f"I couldn't find that file to delete: {prep.get('error', 'unknown error')}."

                if on_start:
                    on_start()
                if on_chunk:
                    on_chunk(msg)
                if on_complete:
                    on_complete(msg)
                return msg

        # Execute steps
        responses = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            tool = step.get("tool", "")
            args = step.get("arguments", {})
            if isinstance(args, str):
                if tool in ("open_application", "close_application"):
                    args = {"application": args}
                elif tool == "type_text":
                    args = {"text": args}
                elif tool in ("open_website", "web_search"):
                    args = {"site": args, "query": args}
                else:
                    args = {"target": args}
            elif not isinstance(args, dict):
                args = {}

            desc = _step_description(tool, args)
            _broadcast_action_status("running", f"⚙ {desc}...", True)

            if on_chunk:
                on_chunk(f"⚙ {desc}...\n")

            res = dispatch(tool, args)
            if res.get("success"):
                msg = res.get("message") or f"{desc} completed."
                _broadcast_action_status("done", f"✓ {msg}", True)
                responses.append(msg)

                # Format file listings nicely if applicable
                if tool == "list_files" and "entries" in res:
                    entries = res["entries"]
                    names = [e["name"] for e in entries[:10]]
                    extra = f" (and {len(entries) - 10} more)" if len(entries) > 10 else ""
                    responses.append(f"Contents: {', '.join(names)}{extra}")
            else:
                err = res.get("error") or "Unknown error."
                _broadcast_action_status("failed", f"✗ {err}", False)
                responses.append(f"I couldn't complete that: {err}")
                break

        final_msg = "\n".join(responses) if responses else "Done."

        if on_start:
            on_start()
        if on_chunk:
            on_chunk(final_msg)
        if on_complete:
            on_complete(final_msg)

        from backend.modules.llm.chat_intent import StreamedResponse
        return StreamedResponse(final_msg) if hasattr(StreamedResponse, "__call__") else final_msg
