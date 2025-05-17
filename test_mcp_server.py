#!/usr/bin/env python3

import httpx
import json
import argparse
import asyncio
from typing import Dict, Any, List

# Configuration
MCP_SERVER_URL = "http://localhost:8000/mcp"

# Sample commit data
SAMPLE_COMMITS = [
    {
        "sha": "abc1234",
        "message": "Implement user authentication",
        "author": "developer1"
    },
    {
        "sha": "def5678",
        "message": "Add dashboard UI components",
        "author": "developer2"
    },
    {
        "sha": "ghi9012",
        "message": "Fix API integration issues",
        "author": "developer1"
    },
    {
        "sha": "jkl3456",
        "message": "Improve performance by 20%",
        "author": "developer3"
    }
]

# Sample queries
SAMPLE_QUERIES = [
    "What is the current project status?",
    "Which features have been completed?",
    "What is the current code quality?"
]

async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP tool with provided arguments"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "method": "tool/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            },
            timeout=30.0
        )
        
        # Check if the request was successful
        response.raise_for_status()
        return response.json()

async def read_mcp_resource(resource_uri: str) -> Dict[str, Any]:
    """Read an MCP resource"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "method": "resource/read",
                "params": {
                    "uri": resource_uri
                }
            },
            timeout=30.0
        )
        
        # Check if the request was successful
        response.raise_for_status()
        return response.json()

async def list_mcp_tools() -> Dict[str, Any]:
    """List available MCP tools"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "method": "tool/list"
            },
            timeout=30.0
        )
        
        # Check if the request was successful
        response.raise_for_status()
        return response.json()

async def list_mcp_resources() -> Dict[str, Any]:
    """List available MCP resources"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "method": "resource/list"
            },
            timeout=30.0
        )
        
        # Check if the request was successful
        response.raise_for_status()
        return response.json()

async def simulate_commits():
    """Simulate adding commits to the project"""
    print("\n=== Simulating Project Commits ===")
    
    for i, commit in enumerate(SAMPLE_COMMITS, 1):
        print(f"\nAdding commit {i}/{len(SAMPLE_COMMITS)}: {commit['message']}")
        
        # Call the update_project_progress tool
        result = await call_mcp_tool("update_project_progress", {"commit_data": commit})
        print(f"Result: {result.get('result', 'No result')}")
        
        # Small delay between commits
        await asyncio.sleep(1)

async def simulate_queries():
    """Simulate answering queries about the project"""
    print("\n=== Simulating Project Queries ===")
    
    for i, query in enumerate(SAMPLE_QUERIES, 1):
        print(f"\nQuery {i}/{len(SAMPLE_QUERIES)}: {query}")
        
        # Call the answer_project_query tool
        result = await call_mcp_tool("answer_project_query", {"query": query})
        print(f"Answer: {result.get('result', 'No answer')}")
        
        # Small delay between queries
        await asyncio.sleep(1)

async def check_resources():
    """Check all available resources"""
    print("\n=== Checking Project Resources ===")
    
    resources = ["project://summary", "project://commits", "project://progress"]
    
    for resource in resources:
        print(f"\nReading resource: {resource}")
        
        # Read the resource
        result = await read_mcp_resource(resource)
        content = result.get("result", {}).get("content", "No content")
        print(f"Content:\n{content}")
        
        # Small delay between resource reads
        await asyncio.sleep(1)

async def main():
    parser = argparse.ArgumentParser(description="Test MCP Project Tracking Server")
    parser.add_argument("--url", help="MCP server URL", default=MCP_SERVER_URL)
    parser.add_argument("--list-tools", action="store_true", help="List available tools")
    parser.add_argument("--list-resources", action="store_true", help="List available resources")
    parser.add_argument("--commits", action="store_true", help="Simulate commits")
    parser.add_argument("--queries", action="store_true", help="Simulate queries")
    parser.add_argument("--resources", action="store_true", help="Check resources")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Update MCP server URL if provided
    global MCP_SERVER_URL
    if args.url:
        MCP_SERVER_URL = args.url
    
    print(f"Using MCP server at: {MCP_SERVER_URL}")
    
    # List tools if requested
    if args.list_tools or args.all:
        tools_result = await list_mcp_tools()
        print("\n=== Available Tools ===")
        tools = tools_result.get("result", [])
        for tool in tools:
            print(f"- {tool.get('name')}: {tool.get('description')}")
    
    # List resources if requested
    if args.list_resources or args.all:
        resources_result = await list_mcp_resources()
        print("\n=== Available Resources ===")
        resources = resources_result.get("result", [])
        for resource in resources:
            print(f"- {resource.get('name')}: {resource.get('description')}")
    
    # Run simulations if requested
    if args.commits or args.all:
        await simulate_commits()
        
    if args.queries or args.all:
        await simulate_queries()
        
    if args.resources or args.all:
        await check_resources()
        
    # If no specific tests requested, show help
    if not any([args.list_tools, args.list_resources, args.commits, args.queries, args.resources, args.all]):
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 