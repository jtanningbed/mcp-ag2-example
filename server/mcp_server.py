"""
Base MCP Server Implementation.

This module provides a base class for implementing MCP servers with common functionality
for handling resources, tools, and responses.
"""

from typing import Optional, Dict, Any
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from pydantic import BaseModel


class BaseMCPServer:
    """Base class for MCP servers with common functionality.

    This class provides the foundation for building MCP servers with standardized
    handling of resources, tools, and response formatting.

    Attributes:
        _name: Name of the MCP server
        _server: Underlying MCP server instance
    """

    def __init__(self, name: str):
        self._name = name
        self._server = Server(self._name)

    def format_response(self, response: BaseModel) -> TextContent:
        """Format a Pydantic model response as TextContent"""
        return TextContent(
            type="text",
            text=response.model_dump_json(indent=2)
        )

    def format_error(self, error: Exception) -> TextContent:
        """Format an error as TextContent"""
        return TextContent(
            type="text",
            text=str(error)
        )
