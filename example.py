"""
Example script demonstrating MCP-enabled AutoGen agent capabilities.

This script showcases the integration between AutoGen agents and MCP servers,
demonstrating both sequential and parallel operations using tools and resources.
"""

import asyncio
import os
from mcp_agent import MCPAssistantAgent
from autogen import ConversableAgent, UserProxyAgent


async def example():
    """Run an example interaction with an MCP-enabled AutoGen agent."""

    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)

    # Configure the assistant
    assistant = MCPAssistantAgent(
        name="mcp_assistant",
        system_message=_get_system_message(),
        mcp_server_command="uv",
        mcp_server_args=["run", "-m", "server.local_file_server"],
        llm_config={
            "config_list": [
                {
                    "model": "gpt-4o",
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                }
            ]
        },
        code_execution_config={"work_dir": "workspace", "use_docker": False},
    )

    # Configure the executor
    executor = UserProxyAgent(
        name="executor",
        human_input_mode="NEVER",
        code_execution_config={"work_dir": "data", "use_docker": False},
        function_map={
            "read_resource": assistant.read_resource,
            "call_tool": assistant.call_tool,
            "list_tools": assistant.list_tools,
        },
    )

    # Run the example interaction
    await executor.a_initiate_chat(assistant, message=_get_test_prompt(), max_turns=5)


def _get_system_message() -> str:
    """Get the system message for the assistant."""
    return """You are an intelligent assistant with access to both Resources and Tools through the MCP (Model Context Protocol) interface:

    Resources (for accessing content):
    - Use read_resource for accessing file contents via URIs (e.g., "storage://local/config.txt")
    - Resources represent actual data and content you can read
    - Resource URIs follow the pattern: storage://local/{/path}

    Tools (for performing operations):
    - Discover available tools using list_tools
    - Each tool has:
    * A unique name (e.g., "write_file")
    * A description of its purpose
    * A schema defining its required arguments
    - To use a tool:
    1. First call list_tools to discover available tools and their parameters
    2. Then call_tool with:
        * name: The tool's name (e.g., "write_file")
        * args: An object matching the tool's parameter schema

    Best Practices:
    1. Always discover tools first - don't assume which tools are available
    2. Use the exact parameter structure defined in each tool's schema
    3. Tools are server-specific - different servers may provide different capabilities
    4. Use Resources for reading content, Tools for actions and modifications

    Example workflow:
    1. List available tools to discover capabilities
    2. Match tool parameters exactly to their schemas
    3. Use tools and resources appropriately for your task
    """


def _get_test_prompt() -> str:
    """Get the test prompt for demonstrating tool usage."""
    return """Please perform the following tasks:

    1. Create three files named 'config1.txt', 'config2.txt', and 'config3.txt', each containing a different configuration number (1, 2, and 3 respectively)
    2. Then read all three files simultaneously to verify their contents
    3. Finally, create a summary.txt file containing the total number of config files created

    This will demonstrate both sequential operations (when needed) and parallel operations (when beneficial).
    """


if __name__ == "__main__":
    asyncio.run(example())
