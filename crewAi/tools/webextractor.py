from server import mcp
import json
from datetime import datetime
from utils.logger import logger
from playwright.async_api import async_playwright
import re

@mcp.tool()
async def extract_web_content(url: str) -> str:
    """
    Extract structured content from a webpage including text, title, and metadata.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        JSON string containing:
        - url
        - title
        - meta_description
        - cleaned_content
        - content_length
        - extracted_at
        - error (if any)
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            
            # Configure timeout and navigation
            page.set_default_timeout(10000)
            await page.goto(url, wait_until='networkidle')
            
            # Extract content
            content = await page.inner_text('body')
            title = await page.title()
            
            # Get meta description
            meta_desc = ""
            meta_element = await page.query_selector('meta[name="description"]')
            if meta_element:
                meta_desc = await meta_element.get_attribute('content') or ""
            
            # Clean content
            content = re.sub(r'\n+', '\n', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            await browser.close()
            
            return json.dumps({
                'url': url,
                'title': title,
                'meta_description': meta_desc,
                'content': content[:100000],  # Safety limit
                'content_length': len(content),
                'extracted_at': datetime.now().isoformat(),
                'status': 'success'
            })
            
    except Exception as e:
        logger.error(f"Content extraction failed for {url}: {str(e)}")
        return json.dumps({
            'url': url,
            'error': str(e),
            'extracted_at': datetime.now().isoformat(),
            'status': 'failed'
        })
