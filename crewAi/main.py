import asyncio
from crewai import Agent, Task
import json
from utils.logger import logger
from tools.excel import ExcelTool
from tools.webextractor import WebContentExtractor
from tools.googlesearch import GoogleSearchTool
from llm import llm


class GoogleScrapingCrew:
    """Main crew orchestrating the Google search and web scraping workflow"""
    
    def __init__(self, search_query: str):
        self.search_query = search_query
        self.google_tool = GoogleSearchTool()
        self.content_extractor = WebContentExtractor()
        self.excel_tool = ExcelTool()
        self.setup_agents()
    
    def setup_agents(self):
        """Setup specialized agents for different tasks"""
        
        # Google Search Agent
        self.search_agent = Agent(
            role='Google Search Specialist',
            goal='Search Google with queries and extract relevant links',
            backstory="""You are an expert at searching Google and finding the most 
            relevant links for any given query. You know how to filter out irrelevant 
            results and focus on high-quality sources.""",
            tools=[self.google_tool],
            verbose=True,
            llm=llm
        )
        
        # Web Content Extraction Agent
        self.extractor_agent = Agent(
            role='Web Content Extraction Specialist',
            goal='Extract comprehensive text content from web pages',
            backstory="""You are an expert at extracting and processing web content. 
            You can navigate any website and extract all meaningful text content 
            while handling various page structures and loading patterns.""",
            tools=[self.content_extractor],
            verbose=True,
            llm=llm
        )
        
        # Data Processing Agent
        self.processor_agent = Agent(
            role='Data Processing Specialist',
            goal='Process and analyze extracted web content',
            backstory="""You are a data processing expert who analyzes web content, 
            identifies key information, and structures data for better understanding 
            and reporting.""",
            verbose=True,
            llm=llm
        )
        
        # Report Generation Agent
        self.report_agent = Agent(
            role='Report Generator',
            goal='Create comprehensive reports from processed web data',
            backstory="""You are an expert at creating detailed reports and summaries 
            from web content. You can identify key insights and present them in a 
            well-structured format.""",
            tools=[self.excel_tool],
            verbose=True,
            llm=llm
        )
    
    def create_tasks(self):
        """Create tasks for the crew"""
        
        # Task 1: Search Google for links
        search_task = Task(
            description=f"""Search Google for: "{self.search_query}"
            Extract the top 20 relevant links from search results.
            Focus on authoritative sources and avoid spam or low-quality sites.""",
            agent=self.search_agent,
            expected_output="JSON list of search result links with titles and domains"
        )
        
        # Task 2: Extract content from each link
        extract_task = Task(
            description="""Visit each link from the search results and extract 
            all text content from the web pages. Include page titles, meta descriptions, 
            and the full text content. Handle errors gracefully if pages are inaccessible.""",
            agent=self.extractor_agent,
            expected_output="JSON list of extracted web content"
        )
        
        # Task 3: Process and analyze content
        process_task = Task(
            description="""Process the extracted web content and identify key themes, 
            topics, and important information. Categorize content by domain and 
            create summaries for each page.""",
            agent=self.processor_agent,
            expected_output="Processed and analyzed web content data"
        )
        
        # Task 4: Generate comprehensive report
        report_task = Task(
            description="""Create a comprehensive report from the processed web content. 
            Include an Excel file with all extracted data, summaries, and insights. 
            Organize data by source, content type, and relevance.""",
            agent=self.report_agent,
            expected_output="Excel report with web content analysis"
        )
        
        return [search_task, extract_task, process_task, report_task]
    
    async def run_workflow(self):
        """Run the complete Google search and web scraping workflow"""
        try:
            logger.info(f"🚀 Starting Google Search Workflow for: {self.search_query}")
            
            # Step 1: Search Google for links
            logger.info("📍 Step 1: Searching Google for relevant links...")
            links_json = await self.google_tool._arun(self.search_query)
            links = json.loads(links_json)
            
            if not len(links):
                logger.error("No links found in Google search!")
                return
            
            logger.info(f"Found {len(links)} links from Google search")
            
            # Step 2: Extract content from each link
            logger.info("📍 Step 2: Extracting content from web pages...")
            content_data = []
            
            for i, link in enumerate(links):
                logger.info(f"Processing page {i+1}/{len(links)}: {link['domain']}")
                
                try:
                    content_json = await self.content_extractor._arun(link['url'])
                    content = json.loads(content_json)
                    
                    # Add search result metadata
                    content['search_title'] = link['title']
                    content['domain'] = link['domain']
                    content['search_rank'] = i + 1
                    
                    content_data.append(content)
                    
                except Exception as e:
                    logger.error(f"Error processing {link['url']}: {str(e)}")
                    content_data.append({
                        'url': link['url'],
                        'domain': link['domain'],
                        'search_title': link['title'],
                        'search_rank': i + 1,
                        'error': str(e)
                    })
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(2)
            
            # Step 3: Process and analyze content
            logger.info("📍 Step 3: Processing and analyzing content...")
            
            # Calculate statistics
            successful_extractions = [c for c in content_data if 'content' in c and not c.get('error')]
            failed_extractions = [c for c in content_data if c.get('error')]
            
            total_content_length = sum(c.get('content_length', 0) for c in successful_extractions)
            avg_content_length = total_content_length / len(successful_extractions) if successful_extractions else 0
            
            # Group by domain
            domain_stats = {}
            for content in successful_extractions:
                domain = content.get('domain', 'unknown')
                if domain not in domain_stats:
                    domain_stats[domain] = {
                        'count': 0,
                        'total_length': 0,
                        'pages': []
                    }
                domain_stats[domain]['count'] += 1
                domain_stats[domain]['total_length'] += content.get('content_length', 0)
                domain_stats[domain]['pages'].append(content.get('title', 'Untitled'))
            
            # Step 4: Generate Excel report
            logger.info("📍 Step 4: Generating comprehensive report...")
            
            # Prepare data for Excel
            excel_data = []
            for content in content_data:
                excel_data.append({
                    'Search Rank': content.get('search_rank', 'N/A'),
                    'Domain': content.get('domain', 'N/A'),
                    'URL': content.get('url', 'N/A'),
                    'Search Title': content.get('search_title', 'N/A'),
                    'Page Title': content.get('title', 'N/A'),
                    'Meta Description': content.get('meta_description', 'N/A'),
                    'Content Length': content.get('content_length', 0),
                    'Content Preview': content.get('content', '')[:500] + '...' if content.get('content') else 'N/A',
                    'Status': 'Success' if content.get('content') else 'Failed',
                    'Error': content.get('error', 'N/A'),
                    'Extracted At': content.get('extracted_at', 'N/A')
                })
            
            # Create Excel report
            excel_result = self.excel_tool._run(f"create_excel data:{json.dumps(excel_data)}")
            
            logger.info("🎉 Workflow completed successfully!")
            logger.info(f"Search query: {self.search_query}")
            logger.info(f"Total links found: {len(links)}")
            logger.info(f"Successful extractions: {len(successful_extractions)}")
            logger.info(f"Failed extractions: {len(failed_extractions)}")
            logger.info(f"Total content extracted: {total_content_length:,} characters")
            logger.info(f"Average content length: {avg_content_length:,.0f} characters")
            logger.info(f"Excel report: {excel_result}")
            
            return {
                'search_query': self.search_query,
                'total_links': len(links),
                'successful_extractions': len(successful_extractions),
                'failed_extractions': len(failed_extractions),
                'total_content_length': total_content_length,
                'avg_content_length': avg_content_length,
                'domain_stats': domain_stats,
                'content_data': content_data,
                'excel_result': excel_result
            }
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            raise


# Main execution
async def main():
    """Main function to run the Google search and web scraping workflow"""
    
    # Example search queries - modify as needed
    SEARCH_QUERIES = [
        "laptops under 40000 flipkart",
    ]
    
    print("🔧 Google Search and Web Scraping Crew")
    print("=" * 50)
    
    # You can modify this to accept user input
    search_query = SEARCH_QUERIES[0]  # Change index or use input()
    
    print(f"🔍 Search Query: {search_query}")
    print("=" * 50)
    
    crew = GoogleScrapingCrew(search_query)
    
    try:
        results = await crew.run_workflow()
        
        print("\n" + "="*60)
        print("📊 WORKFLOW SUMMARY")
        print("="*60)
        print(f"🔍 Search Query: {results['search_query']}")
        print(f"✅ Total links found: {results['total_links']}")
        print(f"✅ Successful extractions: {results['successful_extractions']}")
        print(f"❌ Failed extractions: {results['failed_extractions']}")
        print(f"📄 Total content extracted: {results['total_content_length']:,} characters")
        print(f"📊 Average content length: {results['avg_content_length']:,.0f} characters")
        print(f"📋 Excel report generated: {results['excel_result']}")
        
        # Display domain statistics
        print("\n📈 Domain Statistics:")
        for domain, stats in results['domain_stats'].items():
            print(f"  • {domain}: {stats['count']} pages, {stats['total_length']:,} chars")
        
        # Display sample content
        print("\n📋 Sample Extracted Content:")
        for i, content in enumerate(results['content_data'][:3]):
            if content.get('content'):
                print(f"\n{i+1}. {content.get('title', 'Untitled')}")
                print(f"   URL: {content.get('url', 'N/A')}")
                print(f"   Domain: {content.get('domain', 'N/A')}")
                print(f"   Content length: {content.get('content_length', 0):,} characters")
                print(f"   Preview: {content.get('content', '')[:200]}...")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    # Install required packages first
    print("📦 Required packages:")
    print("pip install crewai playwright pandas openpyxl")
    print("playwright install")
    print("\n" + "="*50)
    
    # Run the workflow
    asyncio.run(main())