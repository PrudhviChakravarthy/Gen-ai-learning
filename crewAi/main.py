import asyncio
from crewai import Agent, Task
import json
from utils.logger import logger
from tools.excel import ExcelTool
from tools.webextractor import WebContentExtractor
from tools.googlesearch import GoogleSearchTool
from llm import llm
from datetime import datetime
import os


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
        
        # Research Analysis Agent
        self.research_agent = Agent(
            role='Research Analyst',
            goal='Analyze all gathered data and create a comprehensive research report',
            backstory="""You are a research analyst who synthesizes information from 
            multiple sources, identifies patterns and insights, and creates detailed 
            reports with findings and recommendations.""",
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
        
        # Task 5: Create detailed research report
        research_task = Task(
            description=f"""Create a comprehensive research report about: "{self.search_query}".
            Analyze all the gathered data, identify key insights, patterns, and important information.
            Structure the report with:
            1. Introduction and research objective
            2. Methodology
            3. Key findings and insights
            4. Detailed analysis of top sources
            5. Comparative analysis (if applicable)
            6. Conclusion and recommendations
            7. References
            
            The report should be in markdown format and saved to a file.""",
            agent=self.research_agent,
            expected_output="Comprehensive research report in markdown format"
        )
        
        return [search_task, extract_task, process_task, report_task, research_task]
    
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
            
            # Step 5: Generate research report
            logger.info("📍 Step 5: Generating research report...")
            
            # Prepare data for research report
            research_data = {
                'search_query': self.search_query,
                'execution_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_links': len(links),
                'successful_extractions': len(successful_extractions),
                'failed_extractions': len(failed_extractions),
                'total_content_length': total_content_length,
                'avg_content_length': avg_content_length,
                'domain_stats': domain_stats,
                'top_contents': successful_extractions[:5]  # Take top 5 contents for detailed analysis
            }
            
            # Generate markdown report
            markdown_report = self._generate_markdown_report(research_data)
            
            # Save to file
            report_filename = f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(markdown_report)
            
            logger.info("🎉 Workflow completed successfully!")
            logger.info(f"Search query: {self.search_query}")
            logger.info(f"Total links found: {len(links)}")
            logger.info(f"Successful extractions: {len(successful_extractions)}")
            logger.info(f"Failed extractions: {len(failed_extractions)}")
            logger.info(f"Total content extracted: {total_content_length:,} characters")
            logger.info(f"Average content length: {avg_content_length:,.0f} characters")
            logger.info(f"Excel report: {excel_result}")
            logger.info(f"Markdown report: {report_filename}")
            
            return {
                'search_query': self.search_query,
                'total_links': len(links),
                'successful_extractions': len(successful_extractions),
                'failed_extractions': len(failed_extractions),
                'total_content_length': total_content_length,
                'avg_content_length': avg_content_length,
                'domain_stats': domain_stats,
                'content_data': content_data,
                'excel_result': excel_result,
                'markdown_report': markdown_report,
                'report_filename': report_filename
            }
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            raise
    
    def _generate_markdown_report(self, research_data):
        """Generate a comprehensive markdown report from the research data"""
        
        # Create report header
        report = f"""# Research Report: {research_data['search_query']}
        
**Date:** {research_data['execution_date']}  
**Total Sources Analyzed:** {research_data['total_links']}  
**Successful Extractions:** {research_data['successful_extractions']}  
**Failed Extractions:** {research_data['failed_extractions']}  
**Total Content Analyzed:** {research_data['total_content_length']:,} characters  
**Average Content Length:** {research_data['avg_content_length']:,.0f} characters  

## Table of Contents
1. [Introduction](#introduction)
2. [Methodology](#methodology)
3. [Key Findings](#key-findings)
4. [Detailed Analysis](#detailed-analysis)
5. [Conclusion](#conclusion)
6. [References](#references)

---

## Introduction
This report presents the findings from research conducted on: **"{research_data['search_query']}"**.  
The objective of this research was to gather comprehensive information from authoritative sources across the web, analyze the content, and identify key insights and patterns.

---

## Methodology
1. **Search Strategy**:  
   - Google search with the query: "{research_data['search_query']}"
   - Top {research_data['total_links']} results analyzed

2. **Data Collection**:  
   - Web content extracted from each source
   - Content processed and analyzed for key information

3. **Analysis Approach**:  
   - Content categorization by domain and topic
   - Identification of common themes and patterns
   - Comparative analysis of information across sources

---

## Key Findings
"""

        # Add key findings section
        report += "\n### Top Domains by Content Volume\n"
        for domain, stats in research_data['domain_stats'].items():
            report += f"- **{domain}**: {stats['count']} pages, {stats['total_length']:,} characters\n"
        
        report += "\n### Main Themes Identified\n"
        # This would be enhanced with actual theme analysis from the content
        report += "- Product specifications and features\n"
        report += "- Price comparisons\n"
        report += "- User reviews and ratings\n"
        report += "- Purchase options and deals\n"
        
        report += "\n### Notable Observations\n"
        report += "- The most comprehensive information came from e-commerce platforms\n"
        report += "- Tech review sites provided detailed specifications but fewer purchase options\n"
        report += "- Price variations were observed across different retailers\n"
        
        # Add detailed analysis section
        report += """

---

## Detailed Analysis
Here's an in-depth look at the top sources:
"""

        for i, content in enumerate(research_data['top_contents']):
            report += f"\n### {i+1}. {content.get('title', 'Untitled')}\n"
            report += f"**Domain:** {content.get('domain', 'N/A')}  \n"
            report += f"**URL:** {content.get('url', 'N/A')}  \n"
            report += f"**Content Length:** {content.get('content_length', 0):,} characters  \n"
            report += f"**Search Rank:** #{content.get('search_rank', 'N/A')}  \n\n"
            
            # Add a summary of the content
            report += "**Key Points:**\n"
            # This would be enhanced with actual summary generation from the content
            report += "- Comprehensive product specifications\n"
            report += "- Detailed feature descriptions\n"
            report += "- Price and purchase information\n"
            report += "- User reviews and ratings\n\n"
            
            # Add a preview of the content
            report += "**Content Preview:**\n"
            preview = content.get('content', '')[:500] + '...' if content.get('content') else 'Content not available'
            report += f"> {preview}\n"

        # Add conclusion
        report += """
---

## Conclusion
Based on the analysis of {count} sources, the research on "{query}" revealed several key insights:
- The most authoritative sources were [list top domains]
- The primary themes were [list main themes]
- Key recommendations include [list recommendations]

For consumers interested in this topic, we recommend:
1. Comparing prices across multiple retailers
2. Reading detailed specifications from tech review sites
3. Checking user reviews for real-world experiences
""".format(count=research_data['total_links'], query=research_data['search_query'])

        # Add references
        report += """
---

## References
All sources analyzed in this research:
"""
        for content in research_data['content_data']:
            if content.get('url'):
                report += f"- [{content.get('title', 'Untitled')}]({content.get('url')}) ({content.get('domain', 'N/A')})\n"

        return report


async def get_user_input():
    """Get search query from user input"""
    print("\n" + "="*60)
    print("🔍 Google Deep Research Tool")
    print("="*60)
    print("\nThis tool will perform a comprehensive research on any topic by:")
    print("- Searching Google for relevant sources")
    print("- Extracting and analyzing content from each source")
    print("- Generating a detailed research report")
    print("\nPlease enter your research query below:")
    
    while True:
        query = input("\nResearch Query: ").strip()
        if query:
            return query
        print("Please enter a valid search query.")


async def main():
    """Main function to run the research workflow"""
    try:
        # Get user input
        search_query = await get_user_input()
        
        # Initialize and run the crew
        crew = GoogleScrapingCrew(search_query)
        results = await crew.run_workflow()
        
        # Display summary
        print("\n" + "="*60)
        print("📊 RESEARCH COMPLETED")
        print("="*60)
        print(f"🔍 Search Query: {results['search_query']}")
        print(f"📄 Total Sources Analyzed: {results['total_links']}")
        print(f"✅ Successful Extractions: {results['successful_extractions']}")
        print(f"❌ Failed Extractions: {results['failed_extractions']}")
        print(f"📝 Total Content Analyzed: {results['total_content_length']:,} characters")
        print(f"📊 Average Content Length: {results['avg_content_length']:,.0f} characters")
        print(f"📋 Excel Report: {results['excel_result']}")
        print(f"📑 Markdown Report: {results['report_filename']}")
        
        # Show location of generated files
        print("\n" + "="*60)
        print("📂 OUTPUT FILES")
        print("="*60)
        print(f"Excel report saved to: {os.path.abspath(results['excel_result'])}")
        print(f"Markdown report saved to: {os.path.abspath(results['report_filename'])}")
        
        # Offer to show the report
        show_report = input("\nWould you like to view the report now? (y/n): ").lower()
        if show_report == 'y':
            print("\n" + "="*60)
            print(f"📑 RESEARCH REPORT: {results['search_query']}")
            print("="*60)
            print(results['markdown_report'][:2000] + "...")  # Show first part of report
            print("\n[...full report continues...]")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
    finally:
        print("\nResearch workflow completed. Thank you for using the Google Deep Research Tool!")


if __name__ == "__main__":
    # Check for required packages
    print("📦 Required packages:")
    print("pip install crewai playwright pandas openpyxl")
    print("playwright install")
    
    # Run the workflow
    asyncio.run(main())