# backend/modules/computer/controller.py
"""
controller.py — Main action dispatcher for computer control.

Validates tool names and arguments, routes to the correct module,
and returns structured ActionResult dicts.

The LLM only supplies tool + arguments. This layer never executes
arbitrary code — it only calls the fixed, pre-defined tool functions.
"""
import time
from backend.modules.computer import (
    applications,
    browser,
    keyboard,
    mouse,
    files,
    screenshots,
)

TOOL_MAP = {
    "open_application": lambda args: applications.open_application(args.get("application", "")),
    "close_application": lambda args: applications.close_application(args.get("application", "")),
    "open_website": lambda args: browser.open_website(args.get("site", args.get("url", ""))),
    "web_search": lambda args: browser.web_search(args.get("query", ""), engine=args.get("engine", "google")),
    "type_text": lambda args: keyboard.type_text(
        args.get("text", ""),
        app=args.get("app", ""),
        interval=args.get("interval", 0.04),
    ),
    "press_key": lambda args: keyboard.press_key(args.get("key", "")),
    "hotkey": lambda args: keyboard.hotkey(args.get("keys", [])),
    "create_folder": lambda args: files.create_folder(args.get("name", ""), location=args.get("location", "desktop")),
    "create_file": lambda args: files.create_file(
        args.get("name", ""),
        location=args.get("location", "desktop"),
        content=args.get("content", ""),
    ),
    "open_folder": lambda args: files.open_folder(location=args.get("location", "desktop")),
    "list_files": lambda args: files.list_files(location=args.get("location", "desktop")),
    "rename_file": lambda args: files.rename_file(args.get("path", ""), args.get("new_name", "")),
    "move_file": lambda args: files.move_file(args.get("source", ""), args.get("destination", "")),
    "take_screenshot": lambda args: screenshots.take_screenshot(),
    "delete_file": lambda args: files.prepare_delete(args.get("path", "")),
    "delete_folder": lambda args: files.prepare_delete(args.get("path", "")),
    "click": lambda args: mouse.click(args.get("x"), args.get("y")),
    "double_click": lambda args: mouse.double_click(args.get("x"), args.get("y")),
    "right_click": lambda args: mouse.right_click(args.get("x"), args.get("y")),
}

MULTI_STEP_ACTIONS = [
    "open_and_type",
]


def dispatch(tool: str, arguments: dict = None) -> dict:
    """
    Execute a single tool call. Returns a structured dict:
    { success, action, target, message } or { success, action, target, error }
    """
    if arguments is None:
        arguments = {}
    elif isinstance(arguments, str):
        if tool in ("open_application", "close_application"):
            arguments = {"application": arguments}
        elif tool in ("open_website", "web_search"):
            arguments = {"site": arguments, "query": arguments}
        elif tool == "type_text":
            arguments = {"text": arguments}
        elif tool == "press_key":
            arguments = {"key": arguments}
        elif tool in ("open_folder", "list_files"):
            arguments = {"location": arguments}
        else:
            arguments = {"target": arguments}
    elif not isinstance(arguments, dict):
        arguments = {}

    if tool not in TOOL_MAP:
        return {
            "success": False,
            "action": tool,
            "target": "",
            "error": f"Unknown tool: '{tool}'. Not in allowed tool list.",
        }

    try:
        handler = TOOL_MAP[tool]
        return handler(arguments)
    except Exception as e:
        return {
            "success": False,
            "action": tool,
            "target": str(arguments),
            "error": f"Unexpected error: {e}",
        }


def dispatch_sequence(steps: list) -> list:
    """
    Execute a sequence of tool calls, stopping on first failure.
    Each step: { "tool": str, "arguments": dict }
    Returns list of results.
    """
    results = []
    for step in steps:
        tool_name = step.get("tool", "")
        args = step.get("arguments", {})
        res = dispatch(tool_name, args)
        results.append(res)
        if not res.get("success", False):
            break
        time.sleep(0.5)
    return results


def format_results_for_llm(results: list) -> str:
    """Convert action results to a concise string for the LLM to use in its response."""
    lines = []
    for r in results:
        if r.get("success", False):
            msg = r.get("message") or f"{r.get('action')} succeeded."
            lines.append(f"[OK] {msg}")
        else:
            err = r.get("error", "Unknown error")
            lines.append(f"[FAILED] {r.get('action')}: {err}")
    return "\n".join(lines)


def get_allowed_tools() -> list:
    """Return the list of all allowed tool names."""
    return list(TOOL_MAP.keys())
