# prompts.py - MCP Prompts for OAuth MCP Server
#
# Prompts help guide Claude through OAuth authentication workflows

def register_prompts(mcp):
    """Register all MCP prompts with the FastMCP server."""

    @mcp.prompt()
    def device_code_auth_workflow():
        """
        Complete guide for Device Code authentication flow.

        This is the recommended authentication method for interactive use
        with Claude Desktop.
        """
        return """I'll guide you through Device Code authentication to get a bearer token.

**Device Code Flow (User Authentication)**

This method allows you to authenticate as a specific user with your Microsoft account.

**Step 1: Start Device Authentication**
Command: start_device_auth()

This will return:
- A user code (e.g., "A1B2C3D4")
- A verification URL (https://microsoft.com/devicelogin)
- Expiration time (usually 15 minutes)

**Step 2: Authenticate in Browser**
1. Open https://microsoft.com/devicelogin in your browser
2. Enter the user code provided
3. Sign in with your Microsoft credentials
4. Approve the requested permissions
5. Wait for confirmation

**Step 3: Complete Authentication**
Command: complete_device_auth()

This returns your bearer token in the response.
The token:
- Is valid for ~1 hour
- Represents YOU (user-delegated permissions)
- Stays in this conversation context
- Should be passed to Omada functions

**Step 4: Use Your Token**
Pass the token to Omada functions:
```
get_pending_approvals(
    impersonate_user="your.email@domain.com",
    bearer_token="eyJ0eXAiOiJKV1Q..."
)
```

**Ready to start?**
Type: "start device authentication"
"""

    @mcp.prompt()
    def client_credentials_auth_workflow():
        """
        Guide for Client Credentials authentication flow.

        This is for app-only scenarios where no user interaction is needed.
        """
        return """I'll guide you through Client Credentials authentication.

**Client Credentials Flow (App-Only Authentication)**

This method authenticates as an application, not a user.

**When to Use:**
- Automated scripts
- Server-to-server operations
- No user interaction available
- Service accounts

**Requirements:**
Your .env file must have:
```
AUTH_METHOD=CLIENT_CREDENTIALS
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
OAUTH2_SCOPE=api://your-app-id/.default
```

**How to Use:**
Command: get_azure_token()

This automatically:
1. Reads credentials from .env
2. Authenticates with Azure AD
3. Returns a bearer token

The token:
- Represents the APPLICATION (not a user)
- Valid for ~1 hour
- Cached automatically
- No user interaction needed

**Important:**
- Client Credentials tokens have APP permissions only
- For USER permissions, use Device Code flow instead
- Set impersonate_user parameter when calling Omada functions

**Current Configuration:**
Check your AUTH_METHOD in .env:
- CLIENT_CREDENTIALS = automatic app authentication
- DEVICE_CODE = requires manual user authentication

Type "get azure token" to authenticate with client credentials.
"""

    @mcp.prompt()
    def troubleshooting_auth():
        """
        Common authentication troubleshooting tips.
        """
        return """Here are solutions to common authentication issues:

**Issue: "Device code has expired"**
Solution: Device codes expire after 15 minutes. Start a fresh auth:
1. Run: start_device_auth() (get new code)
2. Complete auth in browser within 15 minutes
3. Run: complete_device_auth()

**Issue: "Authorization pending - user hasn't completed authentication"**
Solution: You haven't finished the browser authentication yet:
1. Check you entered the code correctly at microsoft.com/devicelogin
2. Complete the sign-in process
3. Wait for browser confirmation
4. Then run: complete_device_auth()

**Issue: "Polling too quickly"**
Solution: Wait a few seconds between complete_device_auth() attempts:
- Device code flow has rate limiting
- Wait 5-10 seconds between retry attempts

**Issue: "AUTH_METHOD is DEVICE_CODE - automatic token acquisition disabled"**
This is EXPECTED behavior:
- With DEVICE_CODE mode, you MUST pass bearer_token parameter
- Device Code requires human interaction (can't be automatic)
- Workflow: start_device_auth() → browser auth → complete_device_auth() → use token

Solution:
1. Complete device code flow (see device_code_auth_workflow prompt)
2. Use the returned token for all operations

**Issue: "Missing CLIENT_ID or CLIENT_SECRET"**
Solution for Client Credentials mode:
- Check your .env file has all required fields:
  - TENANT_ID
  - CLIENT_ID
  - CLIENT_SECRET
  - OAUTH2_SCOPE
- Restart the server after updating .env

**Issue: "Token expired"**
Solution:
- Tokens last ~1 hour
- Get a new token:
  - Device Code: Run complete_device_auth()
  - Client Credentials: Run get_azure_token()

**Issue: "Which authentication method should I use?"**
- **Device Code**: For YOU authenticating as yourself (recommended for Claude Desktop)
- **Client Credentials**: For automated scripts/applications

**Still stuck?**
Check the log file: oauth_mcp_server.log
Enable debug logging: Set LOG_LEVEL=DEBUG in .env
"""

    print("Registered 3 MCP prompts: device_code_auth_workflow, client_credentials_auth_workflow, troubleshooting_auth")
