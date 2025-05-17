# MCP Commit Analysis Server

A Model Context Protocol (MCP) server that analyzes code commits and generates independent summaries using OpenAI GPT-4.

## Features

- Generate independent commit analysis summaries using OpenAI
- Uses MCP prompts for consistent analysis templates
- Leverages MCP Context for progress tracking and logging
- Simple API for submitting commits and retrieving summaries
- Cached results for quick access to previously analyzed commits

## Prerequisites

- Python 3.9+
- `uv` package manager (recommended)
- OpenAI API key

## Installation

1. Set up a Python virtual environment with uv:
   ```bash
   uv venv
   source .venv/bin/activate  # On Unix/Mac
   # or
   .venv\Scripts\activate     # On Windows
   ```

2. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```

   Or use pip:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your OpenAI API key:
   ```bash
   # For Unix/Mac
   export OPENAI_API_KEY=your_api_key_here
   export OPENAI_MODEL=gpt-4  # Optional, defaults to gpt-4
   
   # For Windows
   set OPENAI_API_KEY=your_api_key_here
   set OPENAI_MODEL=gpt-4  # Optional, defaults to gpt-4
   ```

## Running the MCP Server

Start the MCP server:
```bash
python mcp_server.py
```

The server will be available at:
- Streamable HTTP: http://localhost:8000/mcp

## MCP Implementation Details

This server follows the MCP specification by correctly implementing:

1. **Prompts**: Defining reusable prompts with the `@mcp.prompt()` decorator
2. **Context**: Leveraging the `Context` object for:
   - Progress reporting (`ctx.report_progress`)
   - Logging (`ctx.info`, `ctx.warning`, `ctx.error`)
   - User feedback (`ctx.write`)
3. **Tools**: Implementing tools with the `@mcp.tool()` decorator
4. **Resources**: Exposing data through the `@mcp.resource()` decorator

## Commit Analysis Features

The MCP server provides a tool to analyze commit data, which:

1. Takes commit information including code changes and metadata
2. Uses MCP prompts to generate consistent analysis templates
3. Reports progress during analysis through the MCP Context
4. Generates a comprehensive summary broken down into sections:
   - Summary: A brief overview of the commit
   - Technical Changes: Details about the code modifications
   - Purpose: The problem the code is solving
   - Code Quality: Comments on code quality, potential issues, or improvements

### Commit Data Structure

The commit data should follow this structure:
```json
{
  "commit_hash": {
    "user_id": "developer_name",
    "code_diff": {
      "file_name": {
        "line_number": "code_content",
        ...
      },
      "another_file": "simple description"
    },
    "update_at": "ISO timestamp",
    "commit_message": "Commit message"
  }
}
```

## Testing the Server

Use the provided test script to try the commit analysis functionality:

```bash
# Run all tests
python test_commit_analysis.py --all

# Analyze the first sample commit
python test_commit_analysis.py --commit1

# Analyze the second sample commit
python test_commit_analysis.py --commit2

# List all analyzed commits
python test_commit_analysis.py --list

# View available prompts
python test_commit_analysis.py --prompts
```

## Using the MCP Server

The server exposes the following components:

### Prompts

- `analyze_commit_prompt`: Creates a consistent template for commit analysis

### Tools

- `analyze_commit`: Analyzes a commit and generates an independent summary

### Resources

- `commit/{commit_hash}`: Get summary for a specific commit
- `commits`: List all analyzed commits

## Testing with MCP CLI

You can use the MCP CLI to test the server:

```bash
# Connect to the server
mcp connect http://localhost:8000/mcp

# List available prompts
mcp prompts list

# List available tools
mcp tools list

# Call the commit analysis tool (using a JSON file with commit data)
mcp tools call analyze_commit "$(cat sample_commit.json)"

# Read a commit summary
mcp resources read commit/abc123

# List all analyzed commits
mcp resources read commits
```

## OpenAI Integration

The server uses OpenAI's API for commit analysis. In production:

1. Set your API key as an environment variable `OPENAI_API_KEY`
2. Optionally set `OPENAI_MODEL` to specify which model to use (defaults to gpt-4)

## Database Structure

The server uses a simplified in-memory database with the following structure:

```python
DB = {
    "commits": {
        # Commit hash -> commit data
        "commit_hash": {
            "user_id": "developer_name",
            "code_diff": { ... },
            "update_at": "timestamp",
            "commit_message": "message",
            "summary": "Generated summary"
        }
    },
    
    "commit_summaries": {
        # Commit hash -> summary text (for quick lookup)
        "commit_hash": "summary text"
    }
}
```

## Next Steps

This MCP server can be extended with:
1. GitHub webhook integration to automatically analyze commits
2. Persistent storage instead of in-memory database
3. Additional tools for analyzing multiple commits together

## License

MIT
