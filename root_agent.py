"""
Root Agent - Orchestrates all sub-agents
This is the main coordinator that decides which specialized agent to call
"""

from google import genai
from typing import Dict, List, Optional, Any
import json
import time


class AgentTool:
    """
    Wrapper to make sub-agents callable as tools
    """
    def __init__(self, agent, name: str, description: str):
        self.agent = agent
        self.name = name
        self.description = description
    
    def __call__(self, *args, **kwargs):
        """Make the agent callable"""
        return self.agent(*args, **kwargs)


class RootAgent:
    """
    Root Agent that orchestrates all sub-agents
    Decides which agent to call based on user query
    """
    
    def __init__(self, gemini_key: str, model: str = "gemini-2.5-flash"):
        """
        Initialize the root agent
        
        Args:
            gemini_key: Google Gemini API key
            model: Model to use
        """
        self.client = genai.Client(api_key=gemini_key)
        self.model_name = model
        
        # Storage
        self.course_cache = {}  # Stores scraped course data
        self.conversation_history = []  # Full conversation history
        self.current_context = {
            "selected_courses": [],  # Currently selected courses
            "last_action": None,
            "user_preferences": {}
        }
        
        # Sub-agents will be registered here
        self.sub_agents = {}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 12
        
        print(f"✅ Root Agent initialized with {model}")
    
    def register_agent(self, agent_name: str, agent_instance: Any, description: str):
        """
        Register a sub-agent with the coordinator
        
        Args:
            agent_name: Name of the agent (e.g., "CourseAgent")
            agent_instance: The agent instance
            description: What this agent does
        """
        self.sub_agents[agent_name] = {
            "instance": agent_instance,
            "description": description,
            "calls": 0  # Track how many times this agent is called
        }
        print(f"✅ Registered sub-agent: {agent_name}")
    
    def _build_coordinator_prompt(self, user_query: str) -> str:
        """
        Build the prompt for the root agent to decide which sub-agent to call
        """
        # Build available agents description
        agents_info = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.sub_agents.items()
        ])
        
        # Build current context
        context_info = f"""
CURRENT CONTEXT:
- Cached Courses: {list(self.course_cache.keys()) if self.course_cache else "None"}
- Selected Courses: {self.current_context['selected_courses'] if self.current_context['selected_courses'] else "None"}
- Last Action: {self.current_context['last_action'] or "None"}
"""
        
        # Build conversation history (last 3 exchanges)
        history_text = ""
        if self.conversation_history:
            recent = self.conversation_history[-6:]  # Last 3 Q&A pairs
            history_text = "RECENT CONVERSATION:\n" + "\n".join([
                f"{'User' if i % 2 == 0 else 'Assistant'}: {msg['content']}"
                for i, msg in enumerate(recent)
            ])
        
        prompt = f"""You are the Root Course Advisor Agent. Your role is to help university students by orchestrating specialized agents.

AVAILABLE AGENTS:
{agents_info}

{context_info}

{history_text}

USER QUERY: {user_query}

INSTRUCTIONS:
1. Analyze the user's query and context
2. Extract professor name AND university (both required for InstructorAgent)
3. Decide which agent(s) to call and in what order
4. Return a JSON plan with the following structure:

{{
    "reasoning": "Brief explanation of your decision",
    "agent_to_call": "Name of the agent to call (or 'none' if you can answer directly)",
    "parameters": {{
        "course_code": "...",  // For CourseAgent - extract course code like "CMPUT 174"
        "professor_name": "...",  // For InstructorAgent - extract full name without titles
        "university": "...",  // For InstructorAgent - extract FULL university name
        "question": "..."  // The specific question to ask
    }},
    "direct_response": "If no agent needed, provide response here"
}}

CRITICAL RULES FOR INSTRUCTOR QUERIES:
- Extract professor name WITHOUT titles (e.g., "Richard Sutton" not "Professor Richard Sutton")
- Extract FULL university name (e.g., "University of Alberta" not just "Alberta")
- If university NOT mentioned: set university to null or "unknown"
- If professor name NOT clear: set professor_name to null or "unknown"
- Common university patterns:
  * "at [University]" → extract university
  * "from [University]" → extract university
  * "[University]'s Professor" → extract university
  * No university mentioned → set to null

EXTRACTION EXAMPLES:
✅ "Tell me about Professor Richard Sutton at University of Alberta"
   → professor_name: "Richard Sutton", university: "University of Alberta"

✅ "How is Andrew Ng from Stanford?"
   → professor_name: "Andrew Ng", university: "Stanford University"

✅ "What are Mike Horowitz's ratings?"
   → professor_name: "Mike Horowitz", university: null (not specified)

✅ "Tell me about Richard Sutton"
   → professor_name: "Richard Sutton", university: null (not specified)

❌ "Professor at Alberta"
   → professor_name: null, university: "Alberta" (too vague)

RULES FOR COURSE QUERIES:
- Extract course code (e.g., "CMPUT 174", "MATH 100")
- Default university is "University of Alberta" for course queries
- Call CourseAgent for any course-related questions

GENERAL RULES:
- Always extract information carefully
- Set to null if information is missing or unclear
- The agent wrapper will request missing information from the user

Return ONLY the JSON, no other text."""

        return prompt
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            print(f"⏳ Rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def route_query(self, user_query: str) -> Dict:
        """
        Main routing function - decides which agent to call
        
        Args:
            user_query: User's question
            
        Returns:
            Dictionary with routing decision
        """
        try:
            self._wait_for_rate_limit()
            
            # Get coordinator's decision
            prompt = self._build_coordinator_prompt(user_query)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Clean up markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            decision = json.loads(response_text)
            
            return decision
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse coordinator response as JSON: {e}")
            print(f"Response was: {response_text[:200]}")
            # Fallback: try to extract agent name from text
            return {
                "reasoning": "Fallback routing",
                "agent_to_call": "CourseAgent",  # Default to course agent
                "parameters": {"question": user_query},
                "direct_response": None
            }
        except Exception as e:
            return {
                "reasoning": f"Error: {str(e)}",
                "agent_to_call": "none",
                "parameters": {},
                "direct_response": f"I encountered an error: {str(e)}"
            }
    
    def execute(self, user_query: str) -> str:
        """
        Execute a user query by routing to appropriate agent
        
        Args:
            user_query: User's question
            
        Returns:
            Final response to user
        """
        print(f"\n🤔 Analyzing query: '{user_query}'")
        
        # Get routing decision
        decision = self.route_query(user_query)
        
        print(f"💭 Reasoning: {decision.get('reasoning', 'No reasoning provided')}")
        
        agent_name = decision.get('agent_to_call', 'none')
        
        # Store in history
        self.conversation_history.append({
            "role": "user",
            "content": user_query
        })
        
        # Execute based on decision
        if agent_name == 'none' or agent_name not in self.sub_agents:
            # Coordinator responds directly
            response = decision.get('direct_response', 
                                   "I'm not sure how to help with that. Try asking about a specific course.")
            print(f"💬 Coordinator responding directly")
        else:
            # Call the specified agent
            print(f"🤖 Calling {agent_name}...")
            
            agent_info = self.sub_agents[agent_name]
            agent = agent_info['instance']
            params = decision.get('parameters', {})
            
            # Track agent call
            agent_info['calls'] += 1
            
            # Call the agent
            try:
                response = agent.handle_query(**params)
                self.current_context['last_action'] = f"Called {agent_name}"
            except Exception as e:
                response = f"Error calling {agent_name}: {str(e)}"
        
        # Store response in history
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        return response
    
    def get_stats(self) -> Dict:
        """Get statistics about agent usage"""
        return {
            "total_conversations": len(self.conversation_history) // 2,
            "cached_courses": len(self.course_cache),
            "agent_calls": {
                name: info['calls'] 
                for name, info in self.sub_agents.items()
            }
        }
    
    def clear_cache(self):
        """Clear course cache"""
        self.course_cache = {}
        print("🗑️  Course cache cleared")
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.current_context = {
            "selected_courses": [],
            "last_action": None,
            "user_preferences": {}
        }
        print("🗑️  Conversation history cleared")


class CourseAgentWrapper:
    """
    Wrapper for CourseAgent to make it compatible with coordinator
    """
    def __init__(self, course_agent, coordinator):
        self.course_agent = course_agent
        self.coordinator = coordinator
    
    def handle_query(self, course_code: str = None, question: str = None, **kwargs) -> str:
        """
        Handle a query routed from the coordinator
        
        Args:
            course_code: Course code to query
            question: Question to ask
            
        Returns:
            Response from the agent
        """
        if not course_code or not question:
            return "Error: course_code and question are required"
        
        # Check if course is in coordinator's cache
        if course_code.upper() in self.coordinator.course_cache:
            print(f"📦 Using cached data for {course_code}")
            course_data = self.coordinator.course_cache[course_code.upper()]
        else:
            # Scrape the course
            print(f"🌐 Scraping {course_code}...")
            course_data = self.course_agent.scraper.search_course(course_code)
            
            # Cache in coordinator
            if course_data and "error" not in course_data:
                self.coordinator.course_cache[course_code.upper()] = course_data
                if course_code.upper() not in self.coordinator.current_context['selected_courses']:
                    self.coordinator.current_context['selected_courses'].append(course_code.upper())
        
        # Get answer from course agent
        response = self.course_agent.ask(question, course_data, course_code)
        
        return response