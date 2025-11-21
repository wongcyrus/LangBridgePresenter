"""Agent configuration and initialization."""
import os
from google.adk.agents import config_agent_utils
from google.adk.runners import InMemoryRunner


def create_agent():
    """Create and return an ADK agent from YAML config."""
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(
        current_dir, "presenter_agent", "root_agent.yaml"
    )
    
    # Load the agent from the config file using utility function
    agent = config_agent_utils.from_config(config_file_path)
    
    return agent


# Create runner (reusable across requests)
agent = create_agent()
runner = InMemoryRunner(
    agent=agent,
    app_name='langbridge_message_generator',
)
