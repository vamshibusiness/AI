# backend/modules/google/search_tool.py
from ddgs import DDGS

def search(query: str, max_results: int = 3) -> str:
    """
    Performs a web search without requiring API keys.
    Returns a formatted string of results optimized for LLM reading.
    """
    print(f"[Search Tool] Hunting for: '{query}'...")
    
    try:
        # DDGS() initializes the DuckDuckGo search session
        results = DDGS().text(query, max_results=max_results)
        
        if not results:
            return f"No search results found for '{query}'."
            
        formatted_results = f"Search Results for '{query}':\n\n"
        
        for i, res in enumerate(results):
            title = res.get('title', 'Unknown Title')
            summary = res.get('body', 'No summary available.')
            url = res.get('href', 'No URL')
            
            # Format cleanly so the LLM can easily distinguish separate facts
            formatted_results += f"[{i+1}] {title}\n"
            formatted_results += f"Summary: {summary}\n"
            formatted_results += f"Source: {url}\n"
            formatted_results += "-" * 40 + "\n"
            
        return formatted_results.strip()
        
    except Exception as e:
        print(f"[Search Tool Error] {e}")
        return f"Search failed due to a network or parsing error: {e}"

# Quick local test to ensure it works before hooking it into the Research Agent
if __name__ == "__main__":
    test_query = "What are the latest breakthroughs in local LLMs?"
    output = search(test_query)
    print(output)