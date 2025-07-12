from datetime import datetime
import json
import re
import asyncio
from crewai.tools import BaseTool
from utils.logger import logger
from playwright.async_api import async_playwright


class PlaywrightTool(BaseTool):
    """Custom tool for web scraping with Playwright"""
    name: str = "playwright_scraper"
    description: str = "Scrapes web pages using Playwright browser automation"
    
    def _run(self, instruction: str) -> str:
        """Synchronous wrapper for async operations"""
        return asyncio.run(self._arun(instruction))
    
    async def _arun(self, instruction: str) -> str:
        """Execute scraping instruction"""
        try:
            # Parse instruction
            if "search_laptops" in instruction:
                return await self.search_laptops_flipkart()
            elif "extract_details" in instruction:
                url = instruction.split("url:")[-1].strip()
                return await self.extract_laptop_details(url)
            else:
                return "Invalid instruction"
        except Exception as e:
            logger.error(f"Error in playwright tool: {str(e)}")
            return f"Error: {str(e)}"
    
    async def search_laptops_flipkart(self) -> str:
        """Search for laptops on Flipkart under ₹60,000"""
        playwright = None
        browser = None
        context = None
        page = None
        
        try:
            logger.info("🔍 Starting laptop search on Flipkart...")
            
            # Setup browser for this session
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=False,  # Set to True for production
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            # Add stealth measures
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # Navigate to Flipkart laptops section
            await page.goto("https://www.flipkart.com/laptops/~buyback-guarantee-on-laptops-/pr?sid=6bo%2Cb5g&uniq")
            await page.wait_for_load_state('networkidle')
            
            # Apply price filter (under ₹60,000)
            try:
                await page.click('div[title="Price -- Low to High"]')
                await asyncio.sleep(2)
                
                # Look for price filter options
                price_filter = await page.query_selector('div:has-text("₹50,000 - ₹60,000")')
                if price_filter:
                    await price_filter.click()
                    await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Price filter not applied: {e}")
            
            # Collect laptop URLs
            laptop_urls = []
            page_num = 1
            
            while len(laptop_urls) < 50 and page_num <= 10:
                logger.info(f"📄 Scraping page {page_num}...")
                
                # Extract laptop links from current page
                links = await page.query_selector_all('a[href*="/laptops/"]')
                
                for link in links:
                    href = await link.get_attribute('href')
                    if href and '/laptops/' in href and 'pid=' in href:
                        full_url = f"https://www.flipkart.com{href}" if href.startswith('/') else href
                        if full_url not in laptop_urls:
                            laptop_urls.append(full_url)
                            logger.info(f"✅ Found laptop {len(laptop_urls)}: {full_url}")
                
                if len(laptop_urls) >= 50:
                    break
                
                # Go to next page
                try:
                    next_button = await page.query_selector('a[aria-label="Next"]')
                    if next_button:
                        await next_button.click()
                        await page.wait_for_load_state('networkidle')
                        page_num += 1
                    else:
                        break
                except Exception as e:
                    logger.warning(f"Could not navigate to next page: {e}")
                    break
            
            logger.info(f"🎯 Total laptops found: {len(laptop_urls)}")
            return json.dumps(laptop_urls[:50])
            
        except Exception as e:
            logger.error(f"Error in search_laptops_flipkart: {str(e)}")
            return json.dumps([])
        finally:
            # Cleanup browser resources
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    
    async def extract_laptop_details(self, url: str) -> str:
        """Extract detailed information from laptop page"""
        playwright = None
        browser = None
        context = None
        page = None
        
        try:
            logger.info(f"📋 Extracting details from: {url}")
            
            # Setup browser for this session
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=False,  # Set to True for production
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            # Add stealth measures
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            # Extract laptop details
            laptop_data = {}
            
            # Title
            try:
                title_element = await page.query_selector('span.B_NuCI, h1.yhB1nd')
                laptop_data['title'] = await title_element.inner_text() if title_element else "N/A"
            except:
                laptop_data['title'] = "N/A"
            
            # Price
            try:
                price_element = await page.query_selector('div._30jeq3._16Jk6d')
                price_text = await price_element.inner_text() if price_element else "N/A"
                # Extract numeric price
                price_match = re.search(r'₹([\d,]+)', price_text)
                laptop_data['price'] = int(price_match.group(1).replace(',', '')) if price_match else 0
            except:
                laptop_data['price'] = 0
            
            # Rating
            try:
                rating_element = await page.query_selector('div._3LWZlK')
                laptop_data['rating'] = await rating_element.inner_text() if rating_element else "N/A"
            except:
                laptop_data['rating'] = "N/A"
            
            # Specifications
            try:
                spec_elements = await page.query_selector_all('tr._1s_Smc')
                specs = {}
                for spec in spec_elements:
                    key_elem = await spec.query_selector('td._1hKmbr')
                    value_elem = await spec.query_selector('td._21lJbe')
                    if key_elem and value_elem:
                        key = await key_elem.inner_text()
                        value = await value_elem.inner_text()
                        specs[key] = value
                
                laptop_data['processor'] = specs.get('Processor', 'N/A')
                laptop_data['ram'] = specs.get('RAM', 'N/A')
                laptop_data['storage'] = specs.get('Storage', 'N/A')
                laptop_data['display'] = specs.get('Display', 'N/A')
                laptop_data['graphics'] = specs.get('Graphics', 'N/A')
                laptop_data['os'] = specs.get('Operating System', 'N/A')
            except:
                laptop_data.update({
                    'processor': 'N/A',
                    'ram': 'N/A',
                    'storage': 'N/A',
                    'display': 'N/A',
                    'graphics': 'N/A',
                    'os': 'N/A'
                })
            
            # Brand
            try:
                brand_match = re.search(r'^([A-Za-z]+)', laptop_data['title'])
                laptop_data['brand'] = brand_match.group(1) if brand_match else "N/A"
            except:
                laptop_data['brand'] = "N/A"
            
            laptop_data['url'] = url
            laptop_data['scraped_at'] = datetime.now().isoformat()
            
            # Filter out sponsored/ad links
            if any(keyword in laptop_data['title'].lower() for keyword in ['sponsored', 'ad', 'advertisement']):
                return json.dumps({})
            
            # Only include laptops under ₹60,000
            if laptop_data['price'] > 60000:
                return json.dumps({})
            
            logger.info(f"✅ Extracted: {laptop_data['title']} - ₹{laptop_data['price']}")
            return json.dumps(laptop_data)
            
        except Exception as e:
            logger.error(f"Error extracting details from {url}: {str(e)}")
            return json.dumps({})
        finally:
            # Cleanup browser resources
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()