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
        self.anthropic = anthropic.Anthropic(api_key=api_key)
        self.notion_api_key = notion_api_key
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self):
        """Connect to an MCP server

        """
        # command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={
                "OPENAPI_MCP_HEADERS": "{\"Authorization\":\"Bearer " + self.notion_api_key + "\",\"Notion-Version\":\"2022-06-28\"}"
            }, 
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8000,
                    messages=messages,
                    tools=available_tools
                )

                final_text.append(response.content[0].text)

        return final_text
    
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

        page_ids = ['1f689921-161e-8081-83fa-d7ccafc9e72a']
        
        # Create the system prompt
        system_prompt = f"""
        You are an assistant that helps update task lists in Notion based on project summaries.
        When given a summary of recent work, you should:
        1. Here's the list of page ids in Notion: {str(page_ids)}
        2. Add the summary to the page with the given id
        """

        # system_prompt = "create a new page title project alpha and add some random tasks to it"
        
        # Create the initial user message with the summary
        user_message = f"Here's a summary of recent project work: \n\n{summary}"

        # user_message = ""
        
        # Start the conversation
        final_text = await self.process_query(system_prompt + "\n" + user_message)
        
        print("Final text:", final_text)

if __name__ == "__main__":
    # Example usage
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    notion_api_key = os.environ.get("NOTION_API_KEY")

    if not api_key or not notion_api_key:
        print("Error: Please set ANTHROPIC_API_KEY and NOTION_API_KEY environment variables")
        exit(1)
    
    client = MCPClient(api_key, notion_api_key)
    
    # Example summary of recent work
    summary = """
    This week, we made significant progress on A. The team successfully designed 
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
        

    asyncio.run(main())