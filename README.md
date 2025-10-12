# OAuth MCP Server

A Model Context Protocol (MCP) server for OAuth 2.0 authentication operations.

## Overview

This server provides comprehensive OAuth 2.0 authentication support for MCP applications, implementing both:
- **OAuth 2.0 Device Authorization Grant Flow (RFC 8628)** - User-delegated authentication
- **OAuth 2.0 Client Credentials Flow (RFC 6749)** - App-only authentication

## Features

- **Dual Authentication Flows** - Support for both Device Code and Client Credentials flows
- **Token Management** - Automatic token caching and expiry handling
- **MCP Integration** - Compatible with Claude Desktop and other MCP clients
- **Comprehensive Logging** - File and console logging with configurable levels
- **Secure Configuration** - Environment-based configuration via .env file

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Azure AD tenant (or other OAuth 2.0 provider)

## Installation

1. Navigate to the project directory:
```bash
cd oauth_mcp_server
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
   - Set authentication credentials (TENANT_ID, CLIENT_ID, CLIENT_SECRET)
   - Choose authentication method (CLIENT_CREDENTIALS or DEVICE_CODE)

## Configuration

### .env File

```bash
# =============================================================================
# OAuth MCP Server Configuration
# =============================================================================

# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FILE=oauth_mcp_server.log

# Azure OAuth2 Authentication Configuration
TENANT_ID=your-tenant-id-here
CLIENT_ID=your-client-id-here
CLIENT_SECRET=your-client-secret-here
ACCESS_TOKEN_URL=https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token

# OAuth2 Scope
OAUTH2_SCOPE=api://your-api-id/.default

# Authentication Method (CLIENT_CREDENTIALS or DEVICE_CODE)
AUTH_METHOD=CLIENT_CREDENTIALS
```

### Authentication Methods

#### Client Credentials Flow
Best for server-to-server automation with no user interaction.

```bash
AUTH_METHOD=CLIENT_CREDENTIALS
```

Required environment variables:
- `TENANT_ID`
- `CLIENT_ID`
- `CLIENT_SECRET`
- `OAUTH2_SCOPE`

#### Device Code Flow
Best for interactive use with user authentication.

```bash
AUTH_METHOD=DEVICE_CODE
```

Required environment variables:
- `TENANT_ID`
- `CLIENT_ID`
- `OAUTH2_SCOPE`

### Claude Desktop Configuration

Add to your Claude Desktop config file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "oauth-server": {
      "command": "C:\\Users\\YourUser\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["C:\\Users\\YourUser\\Documents\\Code\\oauth_mcp_server\\server.py"],
      "env": {
        "PYTHONPATH": "C:\\Users\\YourUser\\Documents\\Code\\oauth_mcp_server"
      }
    }
  }
}
```

## Available Tools

### Utility Functions

- **`ping`** - Health check endpoint to verify server is running
- **`get_server_info`** - Get server information and configuration

### Device Code Flow Functions

- **`start_device_auth`** - Initiate device authentication flow (Step 1)
- **`complete_device_auth`** - Complete authentication and retrieve token (Step 2)
- **`device_auth_flow`** - One-step device authentication (blocking)
- **`read_bearer_token`** - Read saved bearer token from file

### Client Credentials Flow Functions

- **`get_azure_token`** - Get bearer token using Client Credentials flow
- **`get_azure_token_info`** - Get detailed token information
- **`test_azure_token`** - Test token by making authenticated API call
- **`check_auth_config`** - Check and validate authentication configuration

## Usage Examples

### Using Client Credentials Flow

```python
# In Claude Desktop, tokens are acquired automatically
# Just call the function and it handles authentication

# Get a token
token = get_azure_token()

# Get token details
info = get_azure_token_info()

# Test the token
result = test_azure_token()
```

### Using Device Code Flow

```python
# Step 1: Start device authentication
auth_info = start_device_auth()
# Follow the displayed instructions to complete authentication in browser

# Step 2: Complete authentication after user signs in
token_info = complete_device_auth()
# Token is returned in the response

# Use the token in subsequent API calls
bearer_token = token_info['access_token']
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
- **Default log file**: `oauth_mcp_server.log` in project directory
- **Format**: `timestamp - logger_name - level - message`
- **Configurable**: Set `LOG_LEVEL` in `.env` file

## Project Structure

```
oauth_mcp_server/
├── server.py           # Main MCP server implementation
├── .env               # Environment configuration (not in git)
├── .gitignore        # Git ignore rules
├── README.md         # This file
├── test_token.bat    # Token testing utility (Windows)
└── requirements.txt  # Python dependencies
```

## Integration with Omada MCP Server

This server is designed to work alongside the `omada_mcp_server`. The OAuth token acquisition functions have been migrated from `omada_mcp_server` to this dedicated OAuth server.

**Workflow:**
1. Use `oauth_mcp_server` to obtain authentication tokens
2. Pass tokens to `omada_mcp_server` functions as `bearer_token` parameter

Example:
```python
# Get token from oauth_mcp_server
token = get_azure_token()

# Use token with omada_mcp_server
get_pending_approvals(
    impersonate_user='user@domain.com',
    bearer_token=token
)
```

## Security Notes

- **Never commit `.env` file** - contains sensitive credentials
- **Log files (`.log`)** are excluded from git
- **Store all secrets in environment variables**
- **Tokens are cached in memory only** - not saved to disk by default
- **Tokens are automatically refreshed** when expired (Client Credentials flow)

## Testing

### Test Token Acquisition (Windows)

```bash
test_token.bat
```

This script uses curl to test OAuth token acquisition directly.

## Development

### Adding New Tools

1. Add the tool function in `server.py` with `@mcp.tool()` decorator
2. Add type hints for parameters and return value
3. Add comprehensive docstring
4. Test the tool using Claude Desktop or MCP Inspector

## Migration Notes

OAuth token functions have been migrated from `omada_mcp_server` to this dedicated OAuth server:

**Migrated Functions:**
- `AzureOAuth2Client` class
- `get_cached_token()` function
- `get_token_from_device_code_file()` function
- `get_azure_token()` MCP tool
- `get_azure_token_info()` MCP tool
- `test_azure_token()` MCP tool
- `check_auth_config()` MCP tool (now `check_auth_config()`)

**Preserved in omada_mcp_server:**
- `_prepare_graphql_request()` - now requires bearer_token parameter
- `_execute_graphql_request()` - now requires bearer_token parameter

## Troubleshooting

### Token Acquisition Fails

1. Check `.env` file has correct credentials
2. Verify `TENANT_ID`, `CLIENT_ID`, and `CLIENT_SECRET` are set
3. Check `OAUTH2_SCOPE` matches your API configuration
4. Review logs in `oauth_mcp_server.log`

### Device Code Flow Times Out

1. Default timeout is 5 minutes - complete authentication quickly
2. Use `start_device_auth()` + `complete_device_auth()` for better control
3. Check network connectivity to Azure endpoints

## License

[Add your license information here]

## Support

For issues or questions, please open an issue on GitHub or contact the development team.
