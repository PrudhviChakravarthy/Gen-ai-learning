import os
from server import mcp
import requests
import json
from urllib.parse import urlparse
from utils.logger import logger
from config import SERPER_KEY


@mcp.tool()
def serper_search(query: str) -> str:
    """
    Search Google using Serper API and return top results as JSON.
    
    Args:
        query (str): Search query (e.g., "latest AI news")
    
    Returns:
        str: JSON string containing titles, URLs, and snippets
    
    Requires:
        SERPER_API_KEY in environment variables
    """
    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_KEY, 
            "Content-Type": "application/json"
        }
        payload = json.dumps({"q": query})

        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        
        results = []
        for item in response.json().get("organic", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "domain": urlparse(item.get("link")).netloc
            })
            
        return json.dumps(results[:10])  

    except Exception as e:
        logger.error(f"Serper search failed: {str(e)}")
        return json.dumps([])