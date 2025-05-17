#!/usr/bin/env python3
import os
import json
import anthropic
from typing import List, Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack


class MCPClient:
    def __init__(self, api_key: str, notion_api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        # self.notion_tool = NotionMCPTool(notion_api_key)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        """
        # command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    async def update_tasks_based_on_summary(self, summary: str) -> Dict[str, Any]:
        """
        Main function that takes a summary of recent changes and uses Anthropic's Claude
        to determine which tasks have been completed, then updates them in Notion.
        """
        # Define our tools for the model
        response = await self.session.list_tools()
        tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        # Create the system prompt
        system_prompt = """
        You are an assistant that helps update task lists in Notion based on project summaries.
        When given a summary of recent work, you should:
        1. Get the list of all Notion pages
        2. For each page, get the details including tasks
        3. Analyze the summary to determine which tasks have been completed
        4. Update the status of completed tasks
        
        Be thorough in your analysis. For each task, explain your reasoning for marking it as complete.
        """
        
        # Create the initial user message with the summary
        user_message = f"Here's a summary of recent project work. Please update the appropriate Notion tasks that have been completed:\n\n{summary}"
        
        # Start the conversation
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ],
            tools=tools
        )
        
        print(response.content)
        
        # Return the updated tasks
        return {
            "message": response.content
        }

if __name__ == "__main__":
    # Example usage
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    notion_api_key = os.environ.get("NOTION_API_KEY")

    api_key = "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"
    notion_api_key = "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"
    
    if not api_key or not notion_api_key:
        print("Error: Please set ANTHROPIC_API_KEY and NOTION_API_KEY environment variables")
        exit(1)
    
    client = MCPClient(api_key, notion_api_key)
    
    # Example summary of recent work
    summary = """
    This week, we made significant progress on Project Alpha. The team successfully designed 
    and implemented the database schema with all required tables and relationships. We also 
    created all the API endpoints as specified in the documentation, although we're still 
    working on finalizing authentication which is about 70% complete.
    
    For Project Beta, we completed the technology research phase and identified the stack 
    we'll be using for the prototype. The prototype itself is still in development.
    """
    
    import asyncio

    async def main():
        # Update tasks based on the summary
        await client.connect_to_server()
        result = await client.update_tasks_based_on_summary(summary)

        print(result)
        
        # Print the results
        print("Updated tasks:")
        for task in result["updated_tasks"]:
            print(f"- {task['description']} (Completed: {task['completed']})")

    asyncio.run(main())