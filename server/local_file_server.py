"""
Local File System MCP Server.

This module implements an MCP server that provides access to the local file system,
enabling file operations through the Model Context Protocol (MCP).

The server provides:
1. Resource-based file reading via storage://local/{/path}
2. Tool-based file writing via write_file tool
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from server.mcp_server import BaseMCPServer
from mcp.types import (
    Resource, 
    Tool, 
    ResourceTemplate, 
    CallToolResult, 
    TextContent
)
from pydantic import AnyUrl, BaseModel, ValidationError
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WriteFileParams(BaseModel):
    """Parameters for writing to a file"""

    path: str
    content: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"path": "test.txt", "content": "Hello World"}]
        }
    }


class WriteFileResponse(BaseModel):
    """Response from writing to a file"""

    path: str
    bytes_written: int
    modified_at: datetime


class LocalFileServer(BaseMCPServer):
    """MCP server implementation for local file system operations.
    
    This server provides MCP-compatible access to the local file system,
    supporting both resource-based file reading and tool-based file writing.
    All operations are restricted to the specified base_path for security.
    """

    def __init__(self, base_path: Optional[str] = None):
        """Initialize the local file server.
        
        Args:
            base_path: Optional base directory for file operations.
                      Defaults to current working directory.
        """
        try:
            self.base_path = Path(base_path or os.getcwd()).resolve()
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True)
                logger.info(f"Created base directory: {self.base_path}")

            super().__init__("local-file-server")
            logger.info(f"LocalFileServer initialized with base path: {self.base_path}")

            # Register handlers during initialization
            self._register_handlers()
        except Exception as e:
            logger.error(f"Failed to initialize LocalFileServer: {e}")
            raise

    def _register_handlers(self):
        """Register all MCP protocol handlers."""
        try:
            # Resource handlers
            @self._server.list_resources()
            async def handle_list_resources():
                """List available resources in the file system."""
                return [
                    Resource(
                    uri="storage://local/",
                    name="Local Document Store",
                    description="A local document store",
                    mimeType="text/plain",
                    )
                ]

            @self._server.list_resource_templates()
            async def handle_list_resource_templates():
                """List available resource templates."""
                return [
                    ResourceTemplate(
                        uriTemplate="storage://local/{/path}",
                        name="Local Document Store",
                        description="A local document store",
                        mimeType="text/plain",
                        )
                ]

            @self._server.read_resource()
            async def handle_read_resource(uri: str) -> str:
                """Read a resource from the file system.
                
                Args:
                    uri: URI of the resource to read (format: storage://local/path)
                
                Returns:
                    str: Content of the resource
                
                Raises:
                    FileNotFoundError: If the resource doesn't exist
                    ValueError: If the URI is invalid
                """
                try:
                    uri_str = str(uri)
                    if not uri_str.startswith("storage://local/"):
                        raise ValueError(f"Invalid URI format: {uri}")

                    path = uri_str.split("storage://local/")[1]
                    full_path = (self.base_path / path).resolve()

                    # Security check - ensure path is within base_path
                    if not str(full_path).startswith(str(self.base_path)):
                        raise ValueError(f"Access denied: Path {path} is outside base directory")

                    if not full_path.exists():
                        raise FileNotFoundError(f"Resource not found: {path}")

                    with open(full_path, "r") as f:
                        content = f.read()
                        logger.debug(f"Successfully read resource: {path}")
                        return content
                except Exception as e:
                    logger.error(f"Error reading resource {uri}: {e}")
                    raise

            # Tool handlers
            @self._server.list_tools()
            async def handle_list_tools():
                """List available tools for file operations."""
                return [
                    Tool(
                        name="write_file",
                        description=(
                            "Write content to a file. Path is relative to server's "
                            "base directory."
                        ),
                        inputSchema=WriteFileParams.model_json_schema()
                    )
                ]

            @self._server.call_tool()
            async def handle_call_tool(
                name: str, 
                arguments: dict | None
            ) -> list[TextContent]:
                """Handle tool invocation with proper response formatting.
                
                Args:
                    name: Name of the tool to call
                    arguments: Arguments for the tool
                
                Returns:
                    list[TextContent]: Tool execution results
                """
                try:
                    tool_handlers = {
                        "write_file": self._write_file,
                    }

                    if name not in tool_handlers:
                        raise ValueError(f"Unknown tool: {name}")

                    handler = tool_handlers[name]
                    model_map = {
                        "write_file": WriteFileParams,
                    }

                    input_model = model_map[name]
                    try:
                        validated_args = input_model.model_validate(arguments or {})
                    except ValidationError as e:
                        logger.error(f"Validation error for tool {name}: {e}")
                        return [self.format_error(e)]

                    try:
                        result = await handler(validated_args)
                        logger.info(f"Successfully executed tool {name}")
                        return [self.format_response(result)]
                    except Exception as e:
                        logger.error(f"Error executing tool {name}: {e}")
                        return [self.format_error(e)]

                except Exception as e:
                    logger.error(f"Unexpected error in tool handler: {e}")
                    return [self.format_error(e)]

            logger.info("Successfully registered all MCP handlers")
        except Exception as e:
            logger.error(f"Failed to register handlers: {e}")
            raise

    async def _write_file(self, params: WriteFileParams) -> WriteFileResponse:
        """Write content to a file"""
        full_path = self.base_path / params.path
        try:
            with open(full_path, "w") as f:
                f.write(params.content)
            stats = full_path.stat()
            return WriteFileResponse(
                path=params.path,
                bytes_written=stats.st_size,
                modified_at=datetime.fromtimestamp(stats.st_mtime),
            )
        except Exception as e:
            raise RuntimeError(f"Failed to write file: {e}")


async def run():
    """Run the MCP server using stdio transport.
    
    This function initializes and runs the server, handling command-line arguments
    and setting up the stdio communication channel.
    """
    import argparse
    from mcp.server.stdio import stdio_server

    parser = argparse.ArgumentParser(description="Local File System MCP Server")
    parser.add_argument(
        "--path", 
        type=str, 
        default="./data",
        help="Base directory for file operations (default: ./data)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    args = parser.parse_args()

    # Update log level if specified
    logger.setLevel(getattr(logging, args.log_level))
    
    try:
        logger.info(f"Starting LocalFileServer with path: {args.path}")
        local_server = LocalFileServer(args.path)
        
        async with stdio_server() as streams:
            logger.info("Server started, waiting for connections...")
            await local_server._server.run(
                streams[0], 
                streams[1], 
                local_server._server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    import asyncio
    try: 
        asyncio.run(run())
    except Exception as e:
        logger.critical(f"Fatal server error: {e}")
        raise
