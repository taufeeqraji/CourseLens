import os
from dotenv import load_dotenv
from root_agent import RootAgent
from course_agent import CourseAgent
from instructor_agent import InstructorAgent, InstructorAgentHandler

load_dotenv()

# Initialize once (important)
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")
FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY")

root = RootAgent(gemini_key=GEMINI_KEY)

course_agent = CourseAgent(api_key=GEMINI_KEY)
root.register_agent(
    agent_name="CourseAgent",
    agent_instance=course_agent,
    description="Course info, prerequisites, difficulty, summaries"
)

if FIRECRAWL_KEY:
    instructor_agent = InstructorAgent(
        gemini_api_key=GEMINI_KEY,
        firecrawl_api_key=FIRECRAWL_KEY
    )
    instructor_handler = InstructorAgentHandler(instructor_agent, root)

    root.register_agent(
        agent_name="InstructorAgent",
        agent_instance=instructor_handler,
        description="Professor ratings and reviews via RateMyProfessors"
    )


def chat(message: str) -> str:
    """
    ADK entrypoint
    """
    return root.execute(message)
