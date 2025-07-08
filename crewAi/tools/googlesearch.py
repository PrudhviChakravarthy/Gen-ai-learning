import asyncio
import json
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from crewai.tools import BaseTool
from utils.logger import logger


class GoogleSearchTool(BaseTool):
    """Tool for searching Google and extracting links"""
    
    name: str = "google_search_tool"
    description: str = "Search Google with a query and extract result links"
    
    def _run(self, query: str) -> str:
        """Search Google and return links"""
        return asyncio.run(self._arun(query))   
    
    async def _arun(self, query: str) -> str:
        """Async version of Google search"""
        try:
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = await context.new_page()
                
                # Search on Google
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                await page.goto(search_url)
                await page.wait_for_load_state('networkidle')
                
                # Extract search result links
                links = []
                search_results = await page.query_selector_all('div.MjjYud')
                
                for result in search_results:
                    link_element = await result.query_selector('a[href]')
                    if link_element:
                        href = await link_element.get_attribute('href')
                        title_element = await result.query_selector('h3')
                        title = await title_element.inner_text() if title_element else ""
                        
                        if href and not href.startswith('/search') and not 'google.com' in href:
                            links.append({
                                'url': href,
                                'title': title,
                                'domain': urlparse(href).netloc
                            })
                
                await browser.close()
                
                # Return top 20 links
                return json.dumps(links[:20])
                
        except Exception as e:
            logger.error(f"Error in Google search: {str(e)}")
            return json.dumps([])
