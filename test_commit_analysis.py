#!/usr/bin/env python3

import httpx
import json
import argparse
import asyncio
import os
from typing import Dict, Any

# Configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")

# Sample commit data
SAMPLE_COMMIT = {
    "abc123": {
        "user_id": "developer1",
        "code_diff": {
            "src/auth.py": {
                "45": "def validate_token(token: str) -> bool:",
                "46": "    # Check if token is valid",
                "47": "    return token.startswith('valid_')"
            },
            "src/api/users.py": {
                "112": "async def get_user_profile(user_id: int) -> Dict[str, Any]:",
                "113": "    # Fetch user profile from database",
                "114": "    profile = await db.users.get(user_id)",
                "115": "    return profile or {}"
            }
        },
        "update_at": "2023-06-15T14:30:22Z",
        "commit_message": "Implement user authentication and profile API"
    }
}

# Another sample commit with more complex changes
SAMPLE_COMMIT_2 = {
    "def456": {
        "user_id": "developer2",
        "code_diff": {
            "src/dashboard.py": "Added new dashboard component",
            "src/components/charts.py": {
                "23": "def render_performance_chart(data: List[float]) -> Chart:",
                "24": "    # Create a performance chart",
                "25": "    return Chart(data, type='line', color='blue')"
            },
            "src/api/metrics.py": {
                "67": "async def collect_metrics() -> Dict[str, float]:",
                "68": "    # Collect performance metrics from various sources",
                "69": "    cpu_usage = await system_monitor.get_cpu_usage()",
                "70": "    memory_usage = await system_monitor.get_memory_usage()",
                "71": "    return {'cpu': cpu_usage, 'memory': memory_usage}"
            }
        },
        "update_at": "2023-06-16T09:45:12Z",
        "commit_message": "Add performance monitoring dashboard"
    }
}

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
            timeout=60.0  # Longer timeout for LLM processing
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

async def list_mcp_prompts() -> Dict[str, Any]:
    """List available MCP prompts"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "method": "prompt/list"
            },
            timeout=30.0
        )
        
        # Check if the request was successful
        response.raise_for_status()
        return response.json()

async def analyze_commit():
    """Test the commit analysis functionality with OpenAI"""
    print("\n=== Analyzing Commit ===\n")
    
    print("Generating summary for commit...")
    result = await call_mcp_tool("analyze_commit", {"commit_data": SAMPLE_COMMIT})
    
    print("\nSummary Result:")
    if "result" in result:
        print(result["result"])
    else:
        print("No summary result returned")
    
    # Check the resources
    print("\nReading commit from resources...")
    commit_hash = list(SAMPLE_COMMIT.keys())[0]
    resource_result = await read_mcp_resource(f"commit/{commit_hash}")
    
    if "result" in resource_result and "content" in resource_result["result"]:
        print(f"Commit resource content: {resource_result['result']['content'][:100]}...")
        if len(resource_result['result']['content']) > 100:
            print("...")
    else:
        print("No resource content returned")

async def analyze_another_commit():
    """Test analyzing another commit"""
    print("\n=== Analyzing Another Commit ===\n")
    
    print("Generating summary for commit...")
    result = await call_mcp_tool("analyze_commit", {"commit_data": SAMPLE_COMMIT_2})
    
    print("\nSummary Result:")
    if "result" in result:
        print(result["result"])
    else:
        print("No summary result returned")

async def list_all_commits():
    """List all analyzed commits"""
    print("\n=== Listing All Analyzed Commits ===\n")
    
    result = await read_mcp_resource("commits")
    
    if "result" in result and "content" in result["result"]:
        print(result["result"]["content"])
    else:
        print("No commits available")

async def view_prompts():
    """List available prompts"""
    print("\n=== Available Prompts ===\n")
    
    result = await list_mcp_prompts()
    
    if "result" in result:
        prompts = result["result"]
        for prompt in prompts:
            print(f"Name: {prompt.get('name')}")
            print(f"Description: {prompt.get('description')}")
            print(f"Arguments: {prompt.get('arguments')}")
            print()
    else:
        print("No prompts available")

async def main():
    parser = argparse.ArgumentParser(description="Test MCP Commit Analysis")
    parser.add_argument("--url", help="MCP server URL", default=MCP_SERVER_URL)
    parser.add_argument("--commit1", action="store_true", help="Analyze first sample commit")
    parser.add_argument("--commit2", action="store_true", help="Analyze second sample commit")
    parser.add_argument("--list", action="store_true", help="List all analyzed commits")
    parser.add_argument("--prompts", action="store_true", help="List available prompts")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Update MCP server URL if provided
    global MCP_SERVER_URL
    if args.url:
        MCP_SERVER_URL = args.url
    
    print(f"Using MCP server at: {MCP_SERVER_URL}")
    
    # Run tests based on arguments
    if args.commit1 or args.all:
        await analyze_commit()
        
    if args.commit2 or args.all:
        await analyze_another_commit()
        
    if args.list or args.all:
        await list_all_commits()
    
    if args.prompts or args.all:
        await view_prompts()
        
    # If no specific tests requested, show help
    if not any([args.commit1, args.commit2, args.list, args.prompts, args.all]):
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 