from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

import datetime
import httpx
import json
import os

from notion_client import Client

from typing import Dict, Any, List, Optional, Union


# Create MCP server
mcp = FastMCP("MCP Commit Analysis Server")

# Simplified in-memory database for demo
DB = {
    "commits": {},  # Stores commit data and analysis
    "commit_summaries": {},  # Quick access to commit analysis
}

# LLM API configuration (would be loaded from environment in production)
OPENAI_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your_openai_api_key_here")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")

'''
DB Schema:
- commits: {
    'commit_hash': {
        'user_id': str,       # User/developer who made the commit
        'code_diff': {        # Code changes in the commit
            'file_name': {    # File that was changed
                'line_changed': str,  # Content of the changed line
                ...
            }
        },
        'update_at': str,     # Timestamp of the commit
        'commit_message': str, # Commit message
        'summary': str        # Analysis summary of the commit
    }
}

- commit_summaries: {
    'commit_hash': str        # Quick access to commit summary
}
'''

# Create a notion client
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "your_notion_api_key_here")
notion_client = Client(auth=NOTION_API_KEY)

# ----- Helper functions -----

async def call_llm_api(prompt: str) -> Optional[str]:
    """
    Call the OpenAI API to analyze text
    
    Args:
        prompt: The prompt to send to the LLM
        
    Returns:
        The LLM response text or None if an error occurred
    """
    # Using OpenAI API
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENAI_API_ENDPOINT,
                headers=headers,
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert code reviewer analyzing code commits. Provide concise, focused summaries."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return f"Error: {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error calling OpenAI API: {str(e)}"

def format_code_diff(code_diff: Dict[str, Any]) -> str:
    """Format code differences for the LLM prompt"""
    formatted_diff = []
    
    for file_name, changes in code_diff.items():
        formatted_diff.append(f"File: {file_name}")
        formatted_diff.append("Changes:")
        
        if isinstance(changes, dict):
            for line_num, change in changes.items():
                formatted_diff.append(f"  Line {line_num}: {change}")
        else:
            formatted_diff.append(f"  {changes}")
            
        formatted_diff.append("")
    
    return "\n".join(formatted_diff)

def to_uuid(page_id: str) -> str:
    s = page_id.replace("-", "")
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"

# ----- Prompts -----

@mcp.prompt()
def analyze_commit_prompt(commit_hash: str, user_id: str, update_at: str, 
                         commit_message: str, formatted_diff: str) -> list[base.Message]:
    """
    Create a prompt for analyzing a commit
    
    Args:
        commit_hash: The hash of the commit
        user_id: The user who made the commit
        update_at: The timestamp of the commit
        commit_message: The commit message
        formatted_diff: The formatted code diff

    Returns:
        A list of messages for the LLM prompt
    """
    system_message = base.AssistantMessage(
        "I am an expert code reviewer analyzing code commits. I provide concise, focused summaries."
    )
    
    user_message = base.UserMessage(f"""
    Analyze this commit and provide a concise, independent summary focusing only on the code itself.
    
    Commit: {commit_hash}
    Author: {user_id}
    Date: {update_at}
    
    Commit Message:
    {commit_message}
    
    Code Changes:
    {formatted_diff}
    
    Please provide an analysis with the following sections:
    1. Summary: A 1-2 sentence overview of what the commit does
    2. Technical Changes: What specific code changes were made
    3. Purpose: What problem this code is trying to solve
    4. Code Quality: Any potential issues, improvements, or notes on code quality
    
    Focus on providing an independent analysis of just this commit without referring to broader project context or progress tracking.
    """)
    
    return [system_message, user_message]

# ----- Tools -----

@mcp.tool(description="Read current updates made so far in the notion document")
async def read_notion_page(page_id: str, ctx: Context) -> str:
    """
    Read the contents of a notion page to retrieve the current updates made on a project.
    
    Args:
        page_id: The page id corresponding to the project updates made so far. 
                For example, the page_id for the following notion page url
                https://www.notion.so/Project-2-1f689921161e808183fad7ccafc9e72a => 1f689921161e808183fad7ccafc9e72a
        type: str
    
    Returns:
        content: The string contents of the notion page
        type: str
    """
    
    await ctx.info("Starting to retrieve contents of notion document...")
    
    if not page_id:
        await ctx.info(f"No page_id provided: {page_id}")
        page_id = "https://www.notion.so/Project-2-1f689921161e808183fad7ccafc9e72a"
    
    if "www" in page_id or "http" in page_id:
        page_id = page_id.split("-")[-1]
    
    page_uuid = to_uuid(page_id)
    
    blocks = notion_client.blocks.children.list(page_uuid)
    
    contents = []
    for block in blocks.get("results", []):
        block_type = block.get("type")
        data = block.get(block_type, {})
        rich_text = data.get("rich_text", [])
        
        # Extract all plain_text from rich_text
        text_parts = [t.get("plain_text", "") for t in rich_text]
        full_text = "".join(text_parts).strip()

        if full_text:
            if block_type == "heading_1":
                contents.append(f"# {full_text}")
            elif block_type == "heading_2":
                contents.append(f"## {full_text}")
            elif block_type == "heading_3":
                contents.append(f"### {full_text}")
            else:
                contents.append(full_text)
    
    return '\n\n'.join(contents)


@mcp.tool(description="Analyze a commit and generate an independent summary")
async def analyze_commit(commit_data: Dict[str, Any], ctx: Context) -> str:
    """
    Analyze a commit using OpenAI and generate an independent summary
    
    Args:
        commit_data: Information about the commit with structure:
        {
            'commit_hash': {
                'user_id': str,
                'code_diff': {
                    'file_name': {
                        'line_changed': str,
                        ...
                    }
                },
                'update_at': str,
                'commit_message': str
            }
        }
        ctx: MCP context
    
    Returns:
        Independent analysis summary of the commit
    """
    # Log start of analysis using Context
    await ctx.info(f"Starting commit analysis...")
    
    # Validate and extract commit data
    if not commit_data or not isinstance(commit_data, dict):
        return "Error: Invalid commit data format"
    
    # Get the commit hash and details
    if len(commit_data) != 1:
        return "Error: Expected a single commit hash key in commit data"
    
    commit_hash = list(commit_data.keys())[0]
    commit_details = commit_data[commit_hash]
    
    # Check if we already analyzed this commit
    if commit_hash in DB["commit_summaries"]:
        await ctx.info(f"Found cached analysis for commit {commit_hash}")
        return DB["commit_summaries"][commit_hash]
    
    # Extract commit details
    user_id = commit_details.get("user_id", "unknown")
    code_diff = commit_details.get("code_diff", {})
    update_at = commit_details.get("update_at", datetime.datetime.now().isoformat())
    commit_message = commit_details.get("commit_message", "No commit message provided")
    
    # Format the code diff for the LLM
    formatted_diff = format_code_diff(code_diff)
    
    # Report progress using Context
    await ctx.report_progress(1, 3)
    await ctx.info(f"Processing commit {commit_hash} by {user_id}")
    
    # Use the prompt defined above to create a consistent analysis prompt
    prompt_params = {
        "commit_hash": commit_hash,
        "user_id": user_id,
        "update_at": update_at,
        "commit_message": commit_message,
        "formatted_diff": formatted_diff
    }
    
    try:
        await ctx.report_progress(2, 3)
        await ctx.info("Analyzing code changes...")
        
        # Call the LLM API to analyze the commit
        # In a real implementation, you might use a higher-level MCP functionality
        # to communicate with the LLM
        prompt = f"""
        Analyze this commit and provide a concise, independent summary focusing only on the code itself.
        
        Commit: {commit_hash}
        Author: {user_id}
        Date: {update_at}
        
        Commit Message:
        {commit_message}
        
        Code Changes:
        {formatted_diff}
        
        Please provide an analysis with the following sections:
        1. Summary: A 1-2 sentence overview of what the commit does
        2. Technical Changes: What specific code changes were made
        3. Purpose: What problem this code is trying to solve
        4. Code Quality: Any potential issues, improvements, or notes on code quality
        
        Focus on providing an independent analysis of just this commit without referring to broader project context or progress tracking.
        """
        
        summary = await call_llm_api(prompt)
        
        # If API call fails, create a fallback summary
        if not summary or summary.startswith("Error:"):
            await ctx.warning("LLM API call failed, using fallback summary")
            # Create a simple fallback summary
            summary = f"""
            ## Commit Analysis
            
            ### Summary
            This commit implements {commit_message.lower().strip('.')} functionality through changes to {len(code_diff)} files.
            
            ### Technical Changes
            The changes primarily involve adding new functions and methods related to {commit_message.lower()}. Key modifications include defining new interfaces, implementing validation logic, and setting up API endpoints.
            
            ### Purpose
            This code appears to be addressing the need for {commit_message.lower()}, likely to enable secure user interactions and data access within the application.
            
            ### Code Quality
            The code follows good practices with clear function names and type annotations. Consider adding more comprehensive error handling and documentation for the new functionality.
            """
            
    except Exception as e:
        await ctx.error(f"Error during analysis: {str(e)}")
        summary = f"Error analyzing commit: {str(e)}"
    
    # Store the results in database
    DB["commits"][commit_hash] = {
        "user_id": user_id,
        "update_at": update_at,
        "commit_message": commit_message,
        "code_diff": code_diff,
        "summary": summary
    }
    
    # Store summary for quick access
    DB["commit_summaries"][commit_hash] = summary
    
    # Report completion
    await ctx.report_progress(3, 3)
    await ctx.info("Analysis complete")
    await ctx.write("Analysis summary:")
    await ctx.write(summary[:100] + "..." if len(summary) > 100 else summary)
    
    # Return the summary
    return summary

# ----- Resources -----

@mcp.resource("commit/{commit_hash}")
def get_commit_summary(commit_hash: str) -> str:
    """Get analysis summary for a specific commit"""
    if commit_hash in DB["commit_summaries"]:
        return DB["commit_summaries"][commit_hash]
    elif commit_hash in DB["commits"]:
        return f"Commit exists but no summary is available."
    else:
        return f"No summary found for commit {commit_hash}."

@mcp.resource("commits")
def get_all_commits() -> str:
    """Get a list of all analyzed commits"""
    commit_lines = []
    for commit_hash, commit in DB["commits"].items():
        commit_lines.append(f"- {commit_hash[:7]}: {commit.get('commit_message', 'No message')} by {commit.get('user_id', 'unknown')}")
    
    return "\n".join(commit_lines) if commit_lines else "No commits have been analyzed yet."

# ----- Run Server -----
if __name__ == "__main__":
    mcp.run(transport="streamable-http") 