import datetime
import httpx
import json
import os

from notion_client import Client

from typing import Dict, Any, List, Optional, Union


# Create a notion client
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "your_notion_api_key_here")
notion_client = Client(auth=NOTION_API_KEY)


def to_uuid(page_id: str) -> str:
    s = page_id.replace("-", "")
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"


def read_notion_page(page_id: str) -> str:
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
    
    print("Starting ...")
    
    if not page_id:
        return "Error: no page_id provided"
    
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


def main():
    print("Hello from mcp-server-demo!")
    
    result = read_notion_page("https://www.notion.so/Project-2-1f689921161e808183fad7ccafc9e72a")
    print(result)


if __name__ == "__main__":
    main()
