"""Agent configuration and initialization."""
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner


def create_agent():
    """Create and return an ADK agent for message generation."""
    return Agent(
        model="gemini-2.5-flash-lite",
        name='message_generator',
        description=(
            "A creative assistant that generates "
            "classroom messages and greetings."
        ),
        instruction=(
            "You are a creative assistant that generates warm, "
            "friendly, and appropriate messages for classroom settings. "
            "Generate messages that are welcoming, encouraging, "
            "and culturally sensitive."
        ),
    )


# Create runner (reusable across requests)
agent = create_agent()
runner = InMemoryRunner(
    agent=agent,
    app_name='xiaoice_message_generator',
)
