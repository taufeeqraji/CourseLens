"""
Main Interactive CLI using Root Agent
Updated to work with:
- CourseAgent
- InstructorAgent + InstructorAgentHandler (Firecrawl live scraping)
"""

import os
from dotenv import load_dotenv
from colorama import init, Fore

from root_agent import RootAgent, CourseAgentWrapper
from course_agent import CourseAgent
from instructor_agent import InstructorAgent, InstructorAgentHandler


# Initialize colorama
init(autoreset=True)


def print_header():
    """Print welcome header"""
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}   Course Insight Platform - AI Multi-Agent System")
    print(f"{Fore.CYAN}{'='*70}\n")
    print(f"{Fore.YELLOW}🤖 Intelligent Routing with Multiple Specialized Agents")
    print(f"{Fore.GREEN}💡 Powered by: Google Gemini AI + Firecrawl\n")


def print_help():
    """Print help message"""
    print(f"{Fore.YELLOW}What you can ask:")
    print(f"{Fore.GREEN}  Course Questions:")
    print(f"{Fore.WHITE}    - What is CMPUT 174 about?")
    print(f"{Fore.WHITE}    - Tell me about prerequisites for MATH 100")
    print(f"{Fore.WHITE}    - How difficult is ENGG 100?")
    print()

    print(f"{Fore.GREEN}  Instructor Questions (Live RateMyProfessors data):")
    print(f"{Fore.WHITE}    - Tell me about Professor [Name]")
    print(f"{Fore.WHITE}    - What are [Professor]'s ratings?")
    print(f"{Fore.WHITE}    - How is [Professor] as a teacher?")
    print()

    print(f"{Fore.YELLOW}Commands:")
    print(f"{Fore.GREEN}  stats          {Fore.WHITE}- Show system statistics")
    print(f"{Fore.GREEN}  cache          {Fore.WHITE}- Show cached data")
    print(f"{Fore.GREEN}  agents         {Fore.WHITE}- List available agents")
    print(f"{Fore.GREEN}  clear          {Fore.WHITE}- Clear conversation history")
    print(f"{Fore.GREEN}  help           {Fore.WHITE}- Show this help message")
    print(f"{Fore.GREEN}  quit/exit      {Fore.WHITE}- Exit the program")
    print()


def show_stats(root: RootAgent):
    """Show basic system stats"""
    print(f"\n{Fore.YELLOW}📈 System Statistics")
    print(f"{Fore.CYAN}{'-'*60}")
    print(f"{Fore.WHITE}Agents registered: {len(root.sub_agents)}")
    print(f"{Fore.WHITE}Conversation turns stored: {len(root.conversation_history)}")
    print(f"{Fore.WHITE}Cached courses: {len(root.course_cache)}")
    print(f"{Fore.CYAN}{'-'*60}\n")


def show_cache(root: RootAgent):
    """Show cached course codes"""
    print(f"\n{Fore.YELLOW}📦 Cache")
    print(f"{Fore.CYAN}{'-'*60}")
    if not root.course_cache:
        print(f"{Fore.WHITE}(empty)")
    else:
        for k in sorted(root.course_cache.keys()):
            print(f"{Fore.GREEN}• {k}")
    print(f"{Fore.CYAN}{'-'*60}\n")


def list_agents(root: RootAgent):
    """List registered agents"""
    print(f"\n{Fore.YELLOW}🤖 Available Agents:")
    for agent_name, info in root.sub_agents.items():
        print(f"{Fore.GREEN}  • {agent_name}")
        print(f"{Fore.WHITE}    {info['description']}")
        print(f"{Fore.CYAN}    Calls: {info['calls']}")
    print()


def main():
    """Main function"""
    load_dotenv()

    gemini_key = os.getenv("GOOGLE_API_KEY")
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")

    if not gemini_key:
        print(f"{Fore.RED}Error: GOOGLE_API_KEY not found in .env file")
        print(f"{Fore.YELLOW}Add GOOGLE_API_KEY=... to your .env\n")
        return

    print_header()
    print(f"{Fore.CYAN}Initializing Multi-Agent System...")

    try:
        # Root agent
        root = RootAgent(gemini_key=gemini_key)

        # Always initialize CourseAgent
        print(f"{Fore.CYAN}Initializing CourseAgent...")
        course_agent = CourseAgent(api_key=gemini_key)
        course_agent_wrapper = CourseAgentWrapper(course_agent, root)

        root.register_agent(
            agent_name="CourseAgent",
            agent_instance=course_agent_wrapper,
            description="Answers course questions, prerequisites, difficulty, and summaries using live web data."
        )

        # Initialize InstructorAgent only if Firecrawl key exists
        if firecrawl_key:
            print(f"{Fore.CYAN}Initializing InstructorAgent...")
            instructor_agent = InstructorAgent(
                gemini_api_key=gemini_key,
                firecrawl_api_key=firecrawl_key
            )

            instructor_agent_handler = InstructorAgentHandler(instructor_agent, root)

            root.register_agent(
                agent_name="InstructorAgent",
                agent_instance=instructor_agent_handler,
                description="Provides live information about professors from RateMyProfessors using Firecrawl."
            )

            print(f"{Fore.GREEN}✓ System initialized successfully!\n")
            print(f"{Fore.YELLOW}📊 Active Agents: CourseAgent, InstructorAgent (LIVE data)\n")
        else:
            print(f"{Fore.GREEN}✓ System initialized with CourseAgent only\n")
            print(f"{Fore.YELLOW}📊 Active Agents: CourseAgent\n")
            print(f"{Fore.YELLOW}💡 Add FIRECRAWL_API_KEY to .env to enable InstructorAgent\n")

    except Exception as e:
        print(f"{Fore.RED}✗ Error initializing system: {e}")
        return

    print_help()
    print(f"{Fore.CYAN}The root agent will automatically route your questions to the right agent.\n")

    while True:
        try:
            user_input = input(f"{Fore.WHITE}You: ").strip()
            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd in ["quit", "exit", "q"]:
                print(f"\n{Fore.CYAN}Thank you for using Course Insight Platform!")
                break

            if cmd == "help":
                print()
                print_help()
                continue

            if cmd == "agents":
                list_agents(root)
                continue

            if cmd == "stats":
                show_stats(root)
                continue

            if cmd == "cache":
                show_cache(root)
                continue

            if cmd == "clear":
                root.clear_history()
                print()
                continue

            # Normal query
            print(f"{Fore.CYAN}Root Agent: ", end="")
            print(f"{Fore.WHITE}Analyzing...", end="\r")

            response = root.execute(user_input)

            # Print response
            print(f"{Fore.CYAN}Root Agent: {Fore.WHITE}{response}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Fore.CYAN}Thank you for using Course Insight Platform!")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {str(e)}\n")


if __name__ == "__main__":
    main()
