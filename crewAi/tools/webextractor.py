import asyncio
from datetime import datetime
import json
import re
from utils.logger import logger
from crewai.tools import BaseTool


class WebContentExtractor(BaseTool):
    """Tool for extracting all text content from web pages"""
    
    name: str = "web_content_extractor"
    description: str = "Extract all text content from a web page"
    
    def _run(self, url: str) -> str:
        """Extract content from URL"""
        return asyncio.run(self._arun(url))
    
    async def _arun(self, url: str) -> str:
        """Async version of content extraction"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = await context.new_page()
                
                # Set timeout and go to URL
                page.set_default_timeout(30000)
                await page.goto(url, wait_until='networkidle')
                
                # Extract all text content
                content = await page.inner_text('body')
                
                # Clean up the content
                content = re.sub(r'\n+', '\n', content)  # Remove multiple newlines
                content = re.sub(r'\s+', ' ', content)   # Remove multiple spaces
                content = content.strip()
                
                # Get page title
                title = await page.title()
                
                # Get meta description
                meta_desc = ""
                meta_element = await page.query_selector('meta[name="description"]')
                if meta_element:
                    meta_desc = await meta_element.get_attribute('content') or ""
                
                await browser.close()
                
                return json.dumps({
                    'url': url,
                    'title': title,
                    'meta_description': meta_desc,
                    'content': content[:10000],  # Limit content to prevent memory issues
                    'content_length': len(content),
                    'extracted_at': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return json.dumps({
                'url': url,
                'error': str(e),
                'extracted_at': datetime.now().isoformat()
            })

