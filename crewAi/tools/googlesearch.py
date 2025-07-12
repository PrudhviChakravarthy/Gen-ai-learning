import os
from server import mcp  # Import MCP server utilities
from urllib.parse import urlparse
import json
import asyncio
from playwright.async_api import async_playwright
from utils.logger import logger


@mcp.tool()
async def google_search(query: str) -> str:
    """
    Search Google and return the top 20 results as JSON.
    
    Args:
        query (str): The search query (e.g., "latest AI news").
    
    Returns:
        str: JSON string containing URLs, titles, and domains of search results.
    
    Example:
        google_search("Python tutorials") -> '[{"url": "https://python.org", "title": "Python Official Site", "domain": "python.org"}]'
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            
            # Search Google
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            await page.goto(search_url)
            await page.wait_for_load_state('networkidle')
            
            # Extract search results
            links = []
            search_results = await page.query_selector_all('div.MjjYud')
            
            for result in search_results:
                link_element = await result.query_selector('a[href]')
                if link_element:
                    href = await link_element.get_attribute('href')
                    title_element = await result.query_selector('h3')
                    title = await title_element.inner_text() if title_element else ""
                    
                    # Filter out Google's internal links
                    if href and not href.startswith('/search') and 'google.com' not in href:
                        links.append({
                            'url': href,
                            'title': title,
                            'domain': urlparse(href).netloc
                        })
            
            await browser.close()
            
            # Return top 20 results as JSON
            return json.dumps(links[:20])
    
    except Exception as e:
        logger.error(f"Google search failed: {e}")
        return json.dumps([])  # Return empty list on error