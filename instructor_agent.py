"""
Instructor Agent - Analyzes professor ratings from RateMyProfessors
Uses ONLY Firecrawl for live scraping - NO MOCK DATA
"""

from google import genai
from typing import Dict
from instructor_scraper import InstructorScraper
import time


class InstructorAgent:
    """
    AI Agent that provides information about professors/instructors
    Scrapes live data from RateMyProfessors using Firecrawl
    """
    
    def __init__(self, gemini_api_key: str, firecrawl_api_key: str, model: str = "gemini-2.5-flash"):
        """
        Initialize the Instructor Agent
        
        Args:
            gemini_api_key: Google Gemini API key
            firecrawl_api_key: Firecrawl API key
            model: Gemini model to use
        """
        # Initialize Gemini
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_name = model
        
        # Initialize the scraper (Firecrawl)
        self.scraper = InstructorScraper(firecrawl_api_key)
        
        # Rate limiting tracking
        self.last_request_time = 0
        self.min_request_interval = 12  # seconds between requests (5 req/min = 12 sec)
        
        print(f"✅ InstructorAgent initialized with {model} (Firecrawl LIVE mode)")
    
    def _wait_for_rate_limit(self):
        """Wait if needed to respect rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            print(f"⏳ Rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent"""
        return """You are a helpful Professor Information Assistant for university students.

Your role is to:
- Provide accurate information about professors based on live RateMyProfessors data
- Help students understand teaching styles, course difficulty, and professor ratings
- Summarize student feedback in a balanced, objective way
- Highlight both strengths and potential concerns
- Be honest about limitations (if no data available)
- Always mention that data is from RateMyProfessors and may not be complete

Focus on helping students make informed course decisions.
"""
    
    def _format_instructor_data(self, instructor_data: Dict) -> str:
        """Format instructor data for the AI prompt"""
        formatted = f"""
PROFESSOR INFORMATION FROM RATEMYPROFESSORS:

Professor Name: {instructor_data.get('name', 'Unknown')}
University: {instructor_data.get('university', 'Unknown')}

RATINGS:
- Overall Rating: {instructor_data.get('overall_rating', 'N/A')}/5.0
- Difficulty: {instructor_data.get('difficulty', 'N/A')}/5.0
- Would Take Again: {instructor_data.get('would_take_again', 'N/A')}%
- Number of Ratings: {instructor_data.get('num_ratings', 0)}

"""
        
        # Add recent reviews if available
        if instructor_data.get('recent_reviews'):
            formatted += "RECENT STUDENT REVIEWS:\n"
            for i, review in enumerate(instructor_data['recent_reviews'][:5], 1):
                formatted += f"Review {i}: {review}\n\n"
        
        # Add top tags if available
        if instructor_data.get('top_tags'):
            formatted += "STUDENT TAGS/DESCRIPTORS:\n"
            for tag in instructor_data['top_tags']:
                formatted += f"  - {tag}\n"
            formatted += "\n"
        
        # Add profile URL
        if instructor_data.get('profile_url'):
            formatted += f"RateMyProfessors Profile: {instructor_data['profile_url']}\n\n"
        
        # Include full markdown content for comprehensive analysis
        if instructor_data.get('raw_markdown'):
            formatted += "FULL RATEMYPROFESSORS PROFILE CONTENT:\n"
            formatted += f"{instructor_data['raw_markdown'][:4000]}\n\n"  # First 4000 chars
        
        formatted += "Source: Live data scraped from RateMyProfessors.com\n"
        
        return formatted
    
    def analyze_instructor(self, professor_name: str, question: str, university: str = "University of Alberta", rmp_url: str = None) -> str:
        """
        Scrape and analyze an instructor from RateMyProfessors
        
        Args:
            professor_name: Name of professor
            question: User's question about the professor
            university: University name
            rmp_url: Optional direct RateMyProfessors URL (more reliable)
            
        Returns:
            AI-generated analysis of the professor
        """
        try:
            # If direct URL provided, use that (more reliable)
            if rmp_url:
                print(f"🔗 Using provided RMP URL: {rmp_url}")
                instructor_data = self.scraper.scrape_by_url(rmp_url)
                instructor_data['name'] = professor_name
                instructor_data['university'] = university
            else:
                # Otherwise search by name
                print(f"📊 Scraping RateMyProfessors for {professor_name}...")
                instructor_data = self.scraper.search_professor(professor_name, university)
            
            if "error" in instructor_data:
                error_msg = f"I couldn't find information about Professor {professor_name} at {university} on RateMyProfessors. {instructor_data['error']}\n\n"
                error_msg += "This could mean:\n"
                error_msg += "- The professor is not listed on RateMyProfessors\n"
                error_msg += "- The professor has no profile or ratings yet\n"
                error_msg += "- The name/university combination doesn't match available profiles\n\n"
                error_msg += "Try providing:\n"
                error_msg += "- A different spelling of the name\n"
                error_msg += "- A more specific university name\n"
                error_msg += "- The direct RateMyProfessors profile URL if you have it\n"
                return error_msg
            
            # Add the name/university to the data
            instructor_data['name'] = professor_name
            instructor_data['university'] = university
            
            # Wait for rate limits
            self._wait_for_rate_limit()
            
            # Build prompt
            system_prompt = self._build_system_prompt()
            instructor_context = self._format_instructor_data(instructor_data)
            
            full_prompt = f"""{system_prompt}

{instructor_context}

USER QUESTION: {question}

Please provide a helpful, balanced response based on the RateMyProfessors data above. Be specific and cite the information provided."""
            
            # Get AI response
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            
            return response.text
            
        except Exception as e:
            return f"Error analyzing instructor: {str(e)}"


class InstructorAgentHandler:
    """
    Handles instructor-related queries and maintains conversation state
    """
    
    def __init__(self, instructor_agent, root_agent):
        self.instructor_agent = instructor_agent
        self.root_agent = root_agent
        
        # Conversation state
        self.pending_professor = None
        self.pending_university = None
        self.pending_question = None
    
    def handle_query(self, professor_name: str = None, question: str = None, university: str = None, **kwargs) -> str:
        """
        Handle instructor query with conversation flow
        """
        # If we have pending state, try to complete it
        if self.pending_question:
            if professor_name and not self.pending_professor:
                self.pending_professor = professor_name
            if university and not self.pending_university:
                self.pending_university = university
            
            # If we have both professor and university, proceed
            if self.pending_professor and self.pending_university:
                return self._search_and_analyze(self.pending_professor, self.pending_question, self.pending_university)
        
        # Extract information from current query
        if not professor_name and not university:
            # Need both details
            self.pending_question = question
            return self._request_both_details()
        
        if professor_name and not university:
            # Have professor, need university
            self.pending_professor = professor_name
            self.pending_question = question
            return self._request_university_for_professor(professor_name, question)
        
        if university and not professor_name:
            # Have university, need professor
            self.pending_university = university
            self.pending_question = question
            return self._request_professor_for_university(university, question)
        
        # Have both, proceed immediately
        return self._search_and_analyze(professor_name, question, university)
    
    def _request_both_details(self) -> str:
        """Ask user for professor name and university"""
        return """I'd be happy to help you with professor information! 

To find the right RateMyProfessors profile, I need:
1. The professor's full name
2. The university name

Example: "Dr. John Smith at University of Alberta"

What professor and university are you looking for?"""
    
    def _request_university_for_professor(self, professor_name: str, question: str) -> str:
        """Ask for university when professor name is provided"""
        return f"""I can help you with information about Professor {professor_name}!

Which university does Professor {professor_name} teach at?

Example: "University of Alberta" or "University of Calgary"

Please provide the university name:"""
    
    def _request_professor_for_university(self, university: str, question: str) -> str:
        """Ask for professor name when university is provided"""
        return f"""I can help you find professor information at {university}!

Which professor are you asking about?

Please provide the professor's full name:"""
    
    def _request_specific_university(self, professor_name: str, question: str, vague_university: str) -> str:
        """Ask for more specific university info"""
        return f"""I found multiple universities matching "{vague_university}".

For Professor {professor_name}, please specify the exact university name.
For example:
- University of Alberta
- University of Calgary  
- University of British Columbia

What's the full university name?"""
    
    def _search_and_analyze(self, professor_name: str, question: str, university: str) -> str:
        """
        Perform the actual search and analysis
        """
        # Clear pending state
        self.pending_professor = None
        self.pending_university = None
        self.pending_question = None
        
        # Show progress
        print("\n" + "="*60)
        print(f"📋 Searching with confirmed details:")
        print(f"👤 Professor: {professor_name}")
        print(f"🏫 University: {university}")
        print("="*60 + "\n")
        
        # Analyze using the agent
        return self.instructor_agent.analyze_instructor(professor_name, question, university)
