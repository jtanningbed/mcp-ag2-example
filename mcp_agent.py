"""
MCP-enabled AutoGen Assistant Agent.

This module provides an extension of AutoGen's AssistantAgent that can interact with
MCP (Model Context Protocol) servers, enabling dynamic tool discovery and resource access.
"""

from autogen import AssistantAgent
from typing import Dict, Optional, List, Any, Union
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class MCPAssistantAgent(AssistantAgent):
    """An AutoGen assistant agent with MCP capabilities.

    This agent extends the standard AutoGen AssistantAgent with the ability to:
    - Discover and use tools dynamically from MCP servers
    - Access resources through the MCP protocol
    - Handle both synchronous and asynchronous operations

    Attributes:
        server_params (StdioServerParameters): Configuration for the MCP server connection
        session (Optional[ClientSession]): Active MCP client session when connected
    """

    def __init__(
        self,
        name: str,
        system_message: str,
        mcp_server_command: str,
        mcp_server_args: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the MCP-enabled assistant agent.

        Args:
            name: Name of the agent
            system_message: System message defining agent behavior
            mcp_server_command: Command to start the MCP server
            mcp_server_args: Optional arguments for the MCP server
            **kwargs: Additional arguments passed to AssistantAgent
        """
        super().__init__(name=name, system_message=system_message, **kwargs)
        self.server_params = StdioServerParameters(
            command=mcp_server_command, args=mcp_server_args or []
        )

        @self.register_for_llm(description="Read content from a MCP resource")
        async def read_resource(uri: str) -> str:
            """Read content from an MCP resource.

            Args:
                uri: The URI of the resource (format: storage://local/path)

            Returns:
                str: The content of the resource

            Raises:
                Exception: If reading the resource fails
            """
            try:
                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await session.read_resource(uri)
            except Exception as e:
                return f"Error reading resource: {str(e)}"

        @self.register_for_llm(description="Call a tool to perform an operation")
        async def call_tool(name: str, args: dict) -> Any:
            """Call an MCP tool with the specified arguments.

            Args:
                name: Name of the tool to call
                args: Arguments to pass to the tool

            Returns:
                Any: The result of the tool operation

            Raises:
                Exception: If the tool call fails
            """
            try:
                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(name, args)
                        if not result:
                            return {"status": "success"}
                        return result
            except Exception as e:
                return f"Error calling tool: {str(e)}"

        @self.register_for_llm(description="List available tools")
        async def list_tools() -> list[dict[str, Any]]:
            """Discover available tools from the MCP server.

            Returns:
                list[dict[str, Any]]: List of available tools and their schemas

            Raises:
                Exception: If tool discovery fails
            """
            try:
                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await session.list_tools()
            except Exception as e:
                print(f"Error listing tools: {e}")
                raise

        self.read_resource = read_resource
        self.call_tool = call_tool
        self.list_tools = list_tools
