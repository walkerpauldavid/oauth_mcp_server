# Device Authentication MCP Server

A Model Context Protocol (MCP) server for device authentication operations.

## Features

- **MCP Integration** - Compatible with Claude Desktop and other MCP clients
- **Logging** - File and console logging with configurable levels
- **Environment Configuration** - Secure configuration via .env file

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone or navigate to the project directory:
```bash
cd device_auth_mcp_server
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   - Copy `.env` file and update with your configuration
   - Set `LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR)
   - Add your specific API keys and configuration

## Configuration

### .env File

```bash
# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=device_auth_mcp_server.log

# Add your configuration here
```

### Claude Desktop Configuration

Add to your Claude Desktop config file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "device-auth-server": {
      "command": "C:\\Users\\demoadm\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["C:\\Users\\demoadm\\Documents\\Code\\device_auth_mcp_server\\server.py"],
      "env": {
        "PYTHONPATH": "C:\\Users\\demoadm\\Documents\\Code\\device_auth_mcp_server"
      }
    }
  }
}
```

## Available Tools

### Utility Functions

- **`ping`** - Health check endpoint to verify server is running
- **`get_server_info`** - Get server information and configuration

### Add Your Tools Here

Add your device authentication tools in `server.py`:

```python
@mcp.tool()
async def your_tool_name(param1: str, param2: int) -> str:
    """Tool description."""
    # Your implementation here
    pass
```

## Running the Server

### Standalone

```bash
python server.py
```

### Via Claude Desktop

The server will start automatically when Claude Desktop launches.

## Logging

Logs are written to both file and console:
- **Default log file**: `device_auth_mcp_server.log` in project directory
- **Format**: `timestamp - logger_name - level - message`
- **Configurable**: Set `LOG_LEVEL` in `.env` file

## Project Structure

```
device_auth_mcp_server/
├── server.py           # Main MCP server implementation
├── .env               # Environment configuration (not in git)
├── .gitignore        # Git ignore rules
├── README.md         # This file
└── requirements.txt  # Python dependencies
```

## Development

### Adding New Tools

1. Add the tool function in `server.py` with `@mcp.tool()` decorator
2. Add type hints for parameters and return value
3. Add comprehensive docstring
4. Test the tool using Claude Desktop or MCP Inspector

### Testing

Create test scripts in a `tests/` directory following the pattern from omada_mcp_server.

## Security Notes

- Never commit `.env` file - contains sensitive credentials
- Log files (`.log`) are excluded from git
- Store all secrets in environment variables

## License

[Add your license information here]

## Support

For issues or questions, please open an issue on GitHub.
