"""
Course Agent using Firecrawl for universal web scraping
Works with ANY university website!
"""

from google import genai
from google.genai import types
from typing import Dict, Optional
from firecrawl_scraper import UniversalCourseScraper
import time
import os
from dotenv import load_dotenv


class UniversalCourseAgent:
    """
    AI Agent that works with ANY university course catalogue
    using Firecrawl for intelligent web scraping
    """
    
    def __init__(self, gemini_key: str, firecrawl_key: str, model: str = "gemini-2.5-flash"):
        """
        Initialize the agent with API keys
        
        Args:
            gemini_key: Google Gemini API key
            firecrawl_key: Firecrawl API key
            model: Gemini model to use
        """
        # Initialize Gemini with new API
        self.client = genai.Client(api_key=gemini_key)
        self.model_name = model
        print(f"✅ Gemini initialized with {model}")
        
        # Initialize Firecrawl scraper
        self.scraper = UniversalCourseScraper(api_key=firecrawl_key)
        print(f"✅ Firecrawl scraper initialized")
        
        self.conversation_history = []
        self.course_cache = {}
        self.last_request_time = 0
        self.min_request_interval = 12  # Rate limiting
        
        print(f"⚠️  Note: Free tier limits - Gemini: 5 req/min, Firecrawl: check your plan")
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            print(f"⏳ Rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        return """You are a knowledgeable Course Information Assistant that helps university students.

Your role:
- Provide accurate information about courses based on scraped web data
- Answer questions clearly and concisely
- Help students understand course requirements, content, and prerequisites
- Be honest when information is incomplete
- Cite the source website when providing information

Guidelines:
- Use a friendly, supportive tone
- Format information clearly with bullet points when appropriate
- Don't make up information - only use what's in the scraped data
- Acknowledge when data is incomplete or unclear
- Always mention the information comes from the official course catalogue"""
    
    def _format_course_data(self, course_data: Dict) -> str:
        """Format scraped course data for AI"""
        if not course_data:
            return "No course data available."
        
        if "error" in course_data:
            return f"Error: {course_data['error']}"
        
        formatted = f"""
SCRAPED COURSE INFORMATION:

Course Code: {course_data.get('code', 'N/A')}
Source URL: {course_data.get('source_url', 'N/A')}

"""
        
        if course_data.get('title'):
            formatted += f"Title: {course_data['title']}\n\n"
        
        if course_data.get('credits'):
            formatted += f"Credits: {course_data['credits']}\n\n"
        
        if course_data.get('description'):
            formatted += f"Description:\n{course_data['description']}\n\n"
        
        if course_data.get('prerequisites'):
            formatted += f"Prerequisites:\n{course_data['prerequisites']}\n\n"
        
        if course_data.get('corequisites'):
            formatted += f"Corequisites:\n{course_data['corequisites']}\n\n"
        
        # Include full markdown content for comprehensive context
        if course_data.get('markdown_content'):
            formatted += f"\nFull Course Page Content (Markdown):\n{course_data['markdown_content']}\n"
        
        return formatted
    
    def search_and_ask(self, university: str, course_code: str, question: str) -> str:
        """
        Search for a course and answer a question
        
        Args:
            university: University key (e.g., "ualberta", "stanford")
            course_code: Course code (e.g., "CMPUT 174")
            question: User's question
            
        Returns:
            AI-generated response
        """
        cache_key = f"{university}:{course_code}".upper()
        
        # Check cache
        if cache_key in self.course_cache:
            print(f"📦 Using cached data for {course_code}")
            course_data = self.course_cache[cache_key]
        else:
            # Scrape with Firecrawl
            print(f"🔥 Scraping {course_code} from {university}...")
            course_data = self.scraper.scrape_course_by_code(university, course_code)
            
            # Cache result
            if course_data and "error" not in course_data:
                self.course_cache[cache_key] = course_data
        
        # Ask AI
        return self.ask(question, course_data, f"{university}:{course_code}")
    
    def ask(self, question: str, course_data: Optional[Dict] = None, course_ref: str = "") -> str:
        """
        Ask a question about scraped course data
        
        Args:
            question: User's question
            course_data: Scraped course data
            course_ref: Course reference for history
            
        Returns:
            AI-generated response
        """
        try:
            if not course_data:
                return "No course data available. Please scrape a course first."
            
            if "error" in course_data:
                return f"Error: {course_data['error']}\n\nPlease check the university key and course code."
            
            # Wait for rate limit
            self._wait_for_rate_limit()
            
            # Format data
            course_context = self._format_course_data(course_data)
            system_prompt = self._build_system_prompt()
            
            # Build prompt
            full_prompt = f"""{system_prompt}

{course_context}

User Question: {question}
Provide a helpful, accurate response based on the scraped course information above."""
        
            # Get AI response
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                answer = response.text
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    return "⚠️ Rate limit exceeded. Wait 1 minute and try again."
                raise e
            
            # Store history
            self.conversation_history.append({
                "question": question,
                "answer": answer,
                "course": course_ref
            })
            
            return answer
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def clear_cache(self):
        """Clear course cache"""
        self.course_cache = {}
        print("🗑️  Cache cleared")


class ScraperAdapter:
    """
    Adapter to make UniversalCourseScraper compatible with CourseAgentWrapper
    """
    def __init__(self, universal_scraper: UniversalCourseScraper, default_university: str = "ualberta"):
        self.universal_scraper = universal_scraper
        self.default_university = default_university
    
    def search_course(self, course_code: str) -> Dict:
        """
        Search for a course using the default university
        
        Args:
            course_code: Course code (e.g., "CMPUT 174")
            
        Returns:
            Course data dictionary
        """
        return self.universal_scraper.scrape_course_by_code(self.default_university, course_code)


class CourseAgent:
    """
    Course Agent wrapper that provides a simpler interface
    Compatible with MainCoordinator and CourseAgentWrapper
    """
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Initialize the agent with API key
        
        Args:
            api_key: Google Gemini API key
            model: Gemini model to use
        """
        # Load environment variables to get Firecrawl key
        load_dotenv()
        firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
        
        if not firecrawl_key:
            raise ValueError("FIRECRAWL_API_KEY not found in .env file. Please add it.")
        
        # Initialize the universal agent
        self.universal_agent = UniversalCourseAgent(
            gemini_key=api_key,
            firecrawl_key=firecrawl_key,
            model=model
        )
        
        # Create adapter for scraper
        self.scraper = ScraperAdapter(self.universal_agent.scraper, default_university="ualberta")
        
        # Expose other attributes
        self.conversation_history = self.universal_agent.conversation_history
        self.course_cache = self.universal_agent.course_cache
    
    def ask(self, question: str, course_data: Optional[Dict] = None, course_code: str = "") -> str:
        """
        Ask a question about course data
        
        Args:
            question: User's question
            course_data: Course data dictionary
            course_code: Course code for reference
            
        Returns:
            AI-generated response
        """
        return self.universal_agent.ask(question, course_data, course_code)
    
    def clear_history(self):
        """Clear conversation history"""
        self.universal_agent.clear_history()
    
    def clear_cache(self):
        """Clear course cache"""
        self.universal_agent.clear_cache()