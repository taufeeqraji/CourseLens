"""
Universal course scraper using Firecrawl API
Works with ANY university website!
"""

from firecrawl import FirecrawlApp
from typing import Dict, Optional
import re


class UniversalCourseScraper:
    """
    Universal course scraper that works with any university website
    using Firecrawl API
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the scraper with Firecrawl API key
        
        Args:
            api_key: Firecrawl API key (get from https://firecrawl.dev)
        """
        self.firecrawl = FirecrawlApp(api_key=api_key)
        
        # Pre-configured university URL patterns
        self.university_patterns = {
            "ualberta": {
                "name": "University of Alberta",
                "base_url": "https://apps.ualberta.ca/catalogue/course",
                "format": "{base_url}/{subject}/{number}",
                "example": "CMPUT 174"
            },
            "stanford": {
                "name": "Stanford University",
                "base_url": "https://explorecourses.stanford.edu",
                "format": "{base_url}/search?q={subject}+{number}",
                "example": "CS 229"
            },
            "mit": {
                "name": "MIT",
                "base_url": "http://catalog.mit.edu",
                "format": "{base_url}/subjects/{subject}/",
                "example": "6.006"
            },
            "utoronto": {
                "name": "University of Toronto",
                "base_url": "https://artsci.calendar.utoronto.ca",
                "format": "{base_url}/course/{subject}{number}h1",
                "example": "CSC148"
            }
        }
    
    def scrape_course(self, url: str, course_code: str = "") -> Dict:
        """
        Scrape a course page using Firecrawl
        
        Args:
            url: Full URL of the course page
            course_code: Optional course code for reference
            
        Returns:
            Dictionary with scraped course information
        """
        try:
            print(f"🔥 Scraping with Firecrawl: {url}")
            
            # Use Firecrawl to scrape the page
            # It automatically handles JavaScript, returns clean markdown
            result = self.firecrawl.scrape_url(
                url,
                params={
                    'formats': ['markdown', 'html'],
                    'onlyMainContent': True  # Extract only main content, skip navigation
                }
            )
            
            # Extract the clean markdown content
            markdown_content = result.get('markdown', '')
            html_content = result.get('html', '')
            
            # Parse the content to extract course information
            course_data = self._parse_course_content(
                markdown_content, 
                html_content, 
                url, 
                course_code
            )
            
            print(f"✅ Successfully scraped course data")
            return course_data
            
        except Exception as e:
            return {
                "error": f"Error scraping course: {str(e)}",
                "url": url
            }
    
    def scrape_course_by_code(self, university: str, course_code: str) -> Dict:
        """
        Scrape a course by university and course code
        
        Args:
            university: University identifier (e.g., "ualberta", "stanford")
            course_code: Course code (e.g., "CMPUT 174", "CS 229")
            
        Returns:
            Dictionary with course information
        """
        try:
            # Get university pattern
            if university.lower() not in self.university_patterns:
                return {
                    "error": f"University '{university}' not configured. Available: {list(self.university_patterns.keys())}"
                }
            
            pattern = self.university_patterns[university.lower()]
            
            # Parse course code
            parts = course_code.strip().split()
            if len(parts) < 2:
                # Try without space (e.g., "CSC148")
                match = re.match(r'([A-Z]+)(\d+)', course_code.strip().upper())
                if match:
                    subject = match.group(1)
                    number = match.group(2)
                else:
                    return {"error": "Invalid course code format"}
            else:
                subject = parts[0].upper()
                number = parts[1]
            
            # Build URL based on pattern
            base_url = pattern["base_url"]
            url = pattern["format"].format(
                base_url=base_url,
                subject=subject,
                number=number
            )
            
            print(f"🌐 University: {pattern['name']}")
            print(f"📚 Course: {course_code}")
            print(f"🔗 URL: {url}\n")
            
            # Scrape the course
            return self.scrape_course(url, f"{subject} {number}")
            
        except Exception as e:
            return {
                "error": f"Error building URL: {str(e)}"
            }
    
    def _parse_course_content(self, markdown: str, html: str, url: str, course_code: str) -> Dict:
        """
        Parse the scraped content to extract structured course information
        """
        course_data = {
            "code": course_code,
            "source_url": url,
            "markdown_content": markdown,  # Full markdown for AI to use
        }
        
        # Try to extract title (usually in first heading)
        title_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        if title_match:
            course_data['title'] = title_match.group(1).strip()
        
        # Try to extract credits
        credits_match = re.search(r'(\d+\.?\d*)\s*(credits?|units?)', markdown, re.IGNORECASE)
        if credits_match:
            course_data['credits'] = credits_match.group(1)
        
        # Extract prerequisites section
        prereq_match = re.search(
            r'prerequisite[s]?:?\s*(.+?)(?=\n\n|\n#|corequisite|$)',
            markdown,
            re.IGNORECASE | re.DOTALL
        )
        if prereq_match:
            course_data['prerequisites'] = prereq_match.group(1).strip()
        
        # Extract corequisites section
        coreq_match = re.search(
            r'corequisite[s]?:?\s*(.+?)(?=\n\n|\n#|$)',
            markdown,
            re.IGNORECASE | re.DOTALL
        )
        if coreq_match:
            course_data['corequisites'] = coreq_match.group(1).strip()
        
        # Extract description (usually first large paragraph)
        paragraphs = re.findall(r'\n\n(.{100,}?)\n\n', markdown)
        if paragraphs:
            course_data['description'] = paragraphs[0].strip()
        
        return course_data
    
    def list_supported_universities(self):
        """List all pre-configured universities"""
        print("🎓 Supported Universities:\n")
        for key, info in self.university_patterns.items():
            print(f"  • {info['name']}")
            print(f"    Key: '{key}'")
            print(f"    Example: {info['example']}")
            print()