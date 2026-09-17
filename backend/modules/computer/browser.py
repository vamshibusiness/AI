# backend/modules/computer/browser.py
"""
browser.py — Safe browser and web search control.

Constructs URLs programmatically. The LLM cannot supply arbitrary URLs directly;
all URLs go through validation before opening.
"""
import urllib.parse
import webbrowser
from backend.modules.computer.action_log import log_action

SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}",
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={query}",
}

KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://www.github.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "reddit": "https://www.reddit.com",
    "stackoverflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "whatsapp": "https://web.whatsapp.com",
    "amazon": "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
}

_ALLOWED_SCHEMES = ("http", "https")


def _safe_url(url: str) -> bool:
    """Validate that the URL uses a safe scheme."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


def open_website(site: str) -> dict:
    """Open a known website or a validated HTTPS URL in the default browser."""
    site_key = site.lower().strip().rstrip("/")
    target_url = KNOWN_SITES.get(site_key)

    if not target_url:
        if site_key.startswith("http://") or site_key.startswith("https://"):
            if _safe_url(site_key):
                target_url = site_key
        elif "." in site_key and not site_key.startswith("."):
            candidate = f"https://{site_key}"
            if _safe_url(candidate):
                target_url = candidate

    if not target_url:
        log_action("open_website", site, False, "Unknown or unsafe site")
        return {
            "success": False,
            "action": "open_website",
            "target": site,
            "error": f"'{site}' is not a known site and is not a valid https URL.",
        }

    try:
        webbrowser.open(target_url)
        log_action("open_website", target_url, True, extra={"url": target_url})
        return {
            "success": True,
            "action": "open_website",
            "target": site,
            "message": f"Opened {site} in your browser.",
            "url": target_url,
        }
    except Exception as e:
        log_action("open_website", site, False, str(e))
        return {"success": False, "action": "open_website", "target": site, "error": str(e)}


def web_search(query: str, engine: str = "google") -> dict:
    """Build a safe search URL and open it in the default browser."""
    engine_key = engine.lower().strip()
    if engine_key not in SEARCH_ENGINES:
        engine_key = "google"

    encoded_query = urllib.parse.quote_plus(query)
    target_url = SEARCH_ENGINES[engine_key].format(query=encoded_query)

    try:
        webbrowser.open(target_url)
        log_action("web_search", query, True, extra={"engine": engine_key, "url": target_url})
        return {
            "success": True,
            "action": "web_search",
            "target": query,
            "message": f"Searching {engine_key} for: {query}",
            "url": target_url,
        }
    except Exception as e:
        log_action("web_search", query, False, str(e))
        return {"success": False, "action": "web_search", "target": query, "error": str(e)}
