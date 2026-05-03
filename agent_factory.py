"""
Shared agent initialization for CLI and web API entry points.
"""

import os

from dotenv import load_dotenv

from course_agent import CourseAgent
from instructor_agent import InstructorAgent, InstructorAgentHandler
from root_agent import CourseAgentWrapper, RootAgent


def create_root_agent() -> RootAgent:
    """
    Build and register the multi-agent system from environment variables.

    Required:
        GOOGLE_API_KEY
        FIRECRAWL_API_KEY

    Returns:
        Initialized RootAgent with available sub-agents registered.
    """
    load_dotenv()

    gemini_key = os.getenv("GOOGLE_API_KEY")
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")

    if not gemini_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured.")

    if not firecrawl_key:
        raise RuntimeError("FIRECRAWL_API_KEY is not configured.")

    root = RootAgent(gemini_key=gemini_key)

    course_agent = CourseAgent(api_key=gemini_key)
    course_agent_wrapper = CourseAgentWrapper(course_agent, root)
    root.register_agent(
        agent_name="CourseAgent",
        agent_instance=course_agent_wrapper,
        description="Answers course questions, prerequisites, difficulty, and summaries using live web data.",
    )

    instructor_agent = InstructorAgent(
        gemini_api_key=gemini_key,
        firecrawl_api_key=firecrawl_key,
    )
    instructor_agent_handler = InstructorAgentHandler(instructor_agent, root)
    root.register_agent(
        agent_name="InstructorAgent",
        agent_instance=instructor_agent_handler,
        description="Provides live information about professors from RateMyProfessors using Firecrawl.",
    )

    return root
