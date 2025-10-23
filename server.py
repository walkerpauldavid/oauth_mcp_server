#!/usr/bin/env python3
"""
OAuth MCP Server

A Model Context Protocol (MCP) server for OAuth 2.0 authentication operations.
Implements:
- OAuth 2.0 Device Authorization Grant Flow (RFC 8628) for user-delegated auth
- OAuth 2.0 Client Credentials Flow (RFC 6749) for app-only auth
"""

import os
import logging
import json
import asyncio
import httpx
from typing import Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configure logging system
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "oauth_mcp_server.log")

# Convert to absolute path if relative path provided
if not os.path.isabs(LOG_FILE):
    # Use the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    LOG_FILE = os.path.join(script_dir, LOG_FILE)

# Create logs directory if it doesn't exist
log_dir = os.path.dirname(LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging with both file and console handlers
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Writing logs to: {os.path.abspath(LOG_FILE)}")

# Initialize FastMCP server
mcp = FastMCP("OAuth MCP Server")

# Register MCP Prompts for workflow guidance
from prompts import register_prompts
register_prompts(mcp)

@mcp.tool()
def ping() -> str:
    """Health check endpoint to verify the server is running."""
    logger.info("Ping function called - responding with pong")
    return "pong"


# =============================================================================
# OAuth 2.0 Client Credentials Flow (Client to Server Authentication)
# =============================================================================

class AzureOAuth2Client:
    """OAuth 2.0 Client Credentials flow for app-only authentication."""

    def __init__(self):
        self.tenant_id = os.getenv("TENANT_ID")
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.access_token_url = os.getenv("ACCESS_TOKEN_URL")

        # Validate required environment variables
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing required environment variables: TENANT_ID, CLIENT_ID, CLIENT_SECRET")

        # If ACCESS_TOKEN_URL is not provided, construct the standard Azure endpoint
        if not self.access_token_url:
            self.access_token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    async def get_access_token(self, scope: str = None) -> Dict[str, Any]:
        """
        Get an OAuth2 access token using client credentials flow.

        Args:
            scope: The scope for the access token (default reads from OAUTH2_SCOPE env var)

        Returns:
            Dict containing token information
        """
        # Use environment variable scope if none provided
        if scope is None:
            scope = os.getenv("OAUTH2_SCOPE", "api://08eeb6a4-4aee-406f-baa5-4922993f09f3/.default")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.access_token_url,
                    headers=headers,
                    data=data,
                    timeout=30.0
                )
                response.raise_for_status()

                token_data = response.json()

                # Add expiry timestamp for caching
                expires_in = token_data.get("expires_in", 3600)
                from datetime import datetime, timedelta
                token_data["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer

                return token_data

            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text

                raise Exception(f"HTTP {e.response.status_code}: {error_detail}")
            except Exception as e:
                raise Exception(f"Token request failed: {str(e)}")


# Initialize OAuth2 client and cached token
_cached_token = None

try:
    oauth_client = AzureOAuth2Client()
except ValueError as e:
    logger.warning(f"OAuth2 client initialization failed: {e}")
    oauth_client = None


# COMMENTED OUT: File-based token storage is deprecated - tokens are now handled in conversation context
# async def get_token_from_device_code_file() -> Dict[str, Any]:
#     """
#     Get bearer token from device code authentication file.
#
#     Returns:
#         Dict containing token information with access_token and expires_at
#
#     Raises:
#         Exception if token file not found or invalid
#     """
#     token_file = os.getenv("DEVICE_CODE_TOKEN_FILE", "bearer_token.txt")
#
#     # Convert to absolute path if relative
#     if not os.path.isabs(token_file):
#         script_dir = os.path.dirname(os.path.abspath(__file__))
#         token_file = os.path.join(script_dir, token_file)
#
#     if not os.path.exists(token_file):
#         raise Exception(
#             f"Device code token file not found: {token_file}\n"
#             f"Please run device authentication flow first using the device_auth_mcp_server"
#         )
#
#     try:
#         with open(token_file, 'r') as f:
#             token_data = json.load(f)
#
#         # Validate token structure
#         if "access_token" not in token_data:
#             raise Exception("Invalid token file: missing access_token field")
#
#         # Calculate expires_at if not present
#         if "expires_at" not in token_data:
#             if "expires_in" in token_data:
#                 # Assume token was just created
#                 expires_in = token_data.get("expires_in", 3600)
#                 token_data["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
#             else:
#                 # Default to 1 hour expiry with 5 min buffer
#                 token_data["expires_at"] = datetime.now() + timedelta(seconds=3300)
#         elif isinstance(token_data["expires_at"], str):
#             # Convert string timestamp to datetime if needed
#             token_data["expires_at"] = datetime.fromisoformat(token_data["expires_at"])
#
#         logger.debug(f"Loaded device code token from {token_file}")
#         return token_data
#
#     except json.JSONDecodeError as e:
#         raise Exception(f"Invalid JSON in token file {token_file}: {str(e)}")
#     except Exception as e:
#         raise Exception(f"Error reading device code token file: {str(e)}")


async def get_cached_token(scope: str = None) -> Dict[str, Any]:
    """
    Get a cached token or fetch a new one if expired.

    Uses AUTH_METHOD environment variable to determine authentication flow:
    - DEVICE_CODE: User delegated token via OAuth 2.0 Device Flow (default)
    - CLIENT_CREDENTIALS: OAuth 2.0 Client Credentials flow for app-only auth

    Args:
        scope: OAuth2 scope for the token

    Returns:
        Dict containing token information with access_token

    Raises:
        Exception if AUTH_METHOD=DEVICE_CODE (token must be passed as parameter)
    """
    global _cached_token

    # Get authentication method from environment (default to DEVICE_CODE for user-delegated auth)
    auth_method = os.getenv("AUTH_METHOD", "DEVICE_CODE").upper()

    # Use environment variable scope if none provided
    if scope is None:
        scope = os.getenv("OAUTH2_SCOPE", "https://graph.microsoft.com/.default")

    # Check if we have a valid cached token
    if (_cached_token and
        "expires_at" in _cached_token and
        datetime.now() < _cached_token["expires_at"]):
        logger.debug(f"Using cached token (auth_method={auth_method})")
        return _cached_token

    logger.info(f"Token expired or not cached, acquiring new token using {auth_method}")

    # Fetch new token based on auth method
    if auth_method == "DEVICE_CODE":
        raise Exception(
            "AUTH_METHOD is set to DEVICE_CODE - automatic token acquisition is disabled.\n"
            "Device Code flow requires user delegated authentication.\n"
            "Please pass the bearer_token parameter directly to the function.\n\n"
            "Workflow:\n"
            "1. Run 'start device authentication' to get user code\n"
            "2. Complete authentication at microsoft.com/devicelogin\n"
            "3. Run 'complete device authentication' to get bearer token\n"
            "4. Pass token to this function using bearer_token parameter\n\n"
            "Example: bearer_token='eyJ0eXAiOiJKV1QiLCJhbGc...'"
        )
    elif auth_method == "CLIENT_CREDENTIALS":
        if not oauth_client:
            raise Exception("OAuth2 client not initialized. Check CLIENT_SECRET environment variable.")

        _cached_token = await oauth_client.get_access_token(scope)
        logger.info("New token acquired and cached via CLIENT_CREDENTIALS")
        return _cached_token
    else:
        raise Exception(
            f"Invalid AUTH_METHOD: {auth_method}\n"
            f"Must be 'CLIENT_CREDENTIALS' or 'DEVICE_CODE'"
        )


@mcp.tool()
def get_server_info() -> str:
    """Get information about the OAuth MCP Server."""
    auth_method = os.getenv("AUTH_METHOD", "DEVICE_CODE").upper()
    info = {
        "name": "OAuth MCP Server",
        "version": "1.0.0",
        "description": "MCP server for OAuth 2.0 authentication (Device Code & Client Credentials flows)",
        "auth_method": auth_method,
        "log_level": LOG_LEVEL,
        "log_file": os.path.abspath(LOG_FILE),
        "supported_flows": [
            "OAuth 2.0 Device Authorization Grant (RFC 8628)",
            "OAuth 2.0 Client Credentials (RFC 6749)"
        ]
    }
    return str(info)

# OAuth 2.0 Device Authorization Grant Flow Implementation

async def initiate_device_flow() -> Dict[str, Any]:
    """
    Step 1: Initiate the device authorization flow.

    Returns device_code, user_code, verification_uri, and other parameters.
    """
    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")
    scope = os.getenv("OAUTH2_SCOPE", "api://08eeb6a4-4aee-406f-baa5-4922993f09f3/.default")

    if not tenant_id or not client_id:
        raise ValueError("TENANT_ID and CLIENT_ID must be set in .env file")

    device_auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"

    logger.info(f"Initiating device flow for client_id: {client_id}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            device_auth_url,
            data={
                "client_id": client_id,
                "scope": scope
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            logger.error(f"Device flow initiation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to initiate device flow: {response.text}")

        result = response.json()
        logger.info(f"Device flow initiated successfully. User code: {result.get('user_code')}")
        return result


async def poll_for_token(device_code: str, interval: int = 5, max_attempts: int = 60) -> Dict[str, Any]:
    """
    Step 2: Poll the token endpoint until the user completes authentication.

    Args:
        device_code: The device code from initiate_device_flow
        interval: Polling interval in seconds (default: 5)
        max_attempts: Maximum number of polling attempts (default: 60 = 5 minutes)

    Returns:
        Token response including access_token
    """
    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    logger.info(f"Starting token polling (interval: {interval}s, max_attempts: {max_attempts})")
    logger.debug(f"Token URL: {token_url}")
    logger.debug(f"Client ID: {client_id}")
    logger.debug(f"Device code (first 10 chars): {device_code[:10]}...")

    async with httpx.AsyncClient() as client:
        for attempt in range(max_attempts):
            logger.debug(f"Polling attempt {attempt + 1}/{max_attempts}")

            response = await client.post(
                token_url,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": client_id,
                    "device_code": device_code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            result = response.json()

            # Log all non-200 responses for debugging
            if response.status_code != 200:
                logger.debug(f"Token endpoint returned {response.status_code}: {result}")

            if response.status_code == 200:
                # Success! We got the token
                logger.info("✅ Token acquired successfully!")
                return result

            # Check for specific errors
            error = result.get("error", "")

            if error == "authorization_pending":
                # User hasn't completed authentication yet, keep polling
                logger.debug("Authorization pending, waiting...")
                await asyncio.sleep(interval)
                continue
            elif error == "slow_down":
                # Server asked us to slow down, increase interval
                interval += 5
                logger.warning(f"Server requested slow down, increasing interval to {interval}s")
                await asyncio.sleep(interval)
                continue
            elif error == "authorization_declined":
                logger.error("User declined the authorization")
                raise Exception("User declined the authorization")
            elif error == "expired_token":
                logger.error("Device code expired")
                raise Exception("Device code expired, please restart the flow")
            else:
                logger.error(f"Token polling failed: {error} - {result.get('error_description', '')}")
                raise Exception(f"Token acquisition failed: {error}")

        raise Exception(f"Token polling timed out after {max_attempts} attempts")


# COMMENTED OUT: File-based token storage is deprecated - tokens are now handled in conversation context
# def save_bearer_token(token_data: Dict[str, Any], filename: str = "bearer_token.txt") -> str:
#     """
#     Save the bearer token to a text file.
#
#     Args:
#         token_data: The token response from poll_for_token
#         filename: The filename to save to (default: bearer_token.txt)
#
#     Returns:
#         Path to the saved file
#     """
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     file_path = os.path.join(script_dir, filename)
#
#     access_token = token_data.get("access_token", "")
#
#     with open(file_path, 'w') as f:
#         f.write(access_token)
#
#     logger.info(f"Bearer token saved to: {file_path}")
#     return file_path


@mcp.tool()
async def start_device_auth() -> str:
    """
    STEP 1: Start the OAuth 2.0 Device Authorization Flow and get the user code.

    This function initiates the device flow and returns instructions for the user.
    After the user completes authentication, call complete_device_auth() to get the token.

    Returns:
        JSON with device code, user code, verification URL, and instructions
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting OAuth 2.0 Device Authorization Grant Flow")
        logger.info("=" * 80)

        device_info = await initiate_device_flow()

        user_code = device_info.get("user_code")
        device_code = device_info.get("device_code")
        verification_uri = device_info.get("verification_uri")
        expires_in = device_info.get("expires_in", 900)
        interval = device_info.get("interval", 5)

        # Save device_code to file so complete_device_auth can use it
        script_dir = os.path.dirname(os.path.abspath(__file__))
        device_code_file = os.path.join(script_dir, "device_code.txt")
        with open(device_code_file, 'w') as f:
            f.write(json.dumps({
                "device_code": device_code,
                "interval": interval,
                "expires_in": expires_in
            }))

        # Build user instructions
        instructions = f"""
DEVICE AUTHENTICATION REQUIRED

Please complete these steps:

1. Go to: {verification_uri}
2. Enter code: {user_code}
3. Sign in with your Microsoft credentials

Code expires in: {expires_in} seconds ({int(expires_in/60)} minutes)

After you complete authentication, ask me to "complete device authentication" to retrieve the token.
"""

        response = {
            "status": "pending",
            "message": instructions,
            "user_code": user_code,
            "verification_uri": verification_uri,
            "expires_in": expires_in,
            "next_step": "After authenticating, call complete_device_auth() to retrieve the token"
        }

        logger.info(f"Device flow initiated. User code: {user_code}")
        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Failed to start device auth flow: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }, indent=2)


@mcp.tool()
async def complete_device_auth() -> str:
    """
    STEP 2: Complete the device authentication and retrieve the bearer token.

    Call this function AFTER the user has completed authentication in their browser.
    This will poll for the token and save it to bearer_token.txt.

    Returns:
        JSON with token information or error
    """
    try:
        # Read device_code from file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        device_code_file = os.path.join(script_dir, "device_code.txt")

        if not os.path.exists(device_code_file):
            return json.dumps({
                "status": "error",
                "message": "Device code not found. Please run start_device_auth() first.",
                "error_type": "FileNotFoundError"
            }, indent=2)

        with open(device_code_file, 'r') as f:
            device_data = json.loads(f.read())

        device_code = device_data.get("device_code")
        interval = device_data.get("interval", 5)

        logger.info("Polling for token...")

        # Poll for token
        token_data = await poll_for_token(device_code, interval, max_attempts=5)

        # Save bearer token - COMMENTED OUT: Token stays in conversation context only
        # token_file = save_bearer_token(token_data)

        # Clean up device code file
        os.remove(device_code_file)

        # Prepare response with FULL access token for use in conversation
        response = {
            "status": "success",
            "message": "Device authentication completed successfully! Use the access_token below in your function calls.",
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope", ""),
            "access_token": token_data.get("access_token", "")  # FULL token returned
        }

        logger.info("=" * 80)
        logger.info("Device authentication completed successfully!")
        logger.info("Token returned in response (not saved to file)")
        logger.info("=" * 80)

        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Failed to complete device auth: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }, indent=2)


@mcp.tool()
async def device_auth_flow() -> str:
    """
    Execute the complete OAuth 2.0 Device Authorization Grant Flow (ONE-STEP VERSION).

    WARNING: This function will block while waiting for user authentication (up to 5 minutes).
    For better user experience, use start_device_auth() and complete_device_auth() separately.

    This function will:
    1. Initiate the device flow and get a user code
    2. Display the user code and verification URL
    3. Poll for the token while waiting for user to complete authentication
    4. Save the bearer token to bearer_token.txt

    Returns:
        JSON string with status and token information
    """
    try:
        # Step 1: Initiate device flow
        logger.info("=" * 80)
        logger.info("Starting OAuth 2.0 Device Authorization Grant Flow (One-Step)")
        logger.info("=" * 80)

        device_info = await initiate_device_flow()

        user_code = device_info.get("user_code")
        device_code = device_info.get("device_code")
        verification_uri = device_info.get("verification_uri")
        expires_in = device_info.get("expires_in", 900)
        interval = device_info.get("interval", 5)

        # Build instructions for response
        instructions = f"""
DEVICE AUTHENTICATION REQUIRED

Please complete authentication NOW:

1. Go to: {verification_uri}
2. Enter code: {user_code}
3. Sign in with your credentials

Code expires in: {expires_in} seconds
Polling for token (this may take up to 5 minutes)...
"""

        logger.info(instructions)

        # Step 2: Poll for token (with shorter timeout for responsiveness)
        try:
            token_data = await poll_for_token(device_code, interval, max_attempts=60)

            # Step 3: Save bearer token - COMMENTED OUT: Token stays in conversation context only
            # token_file = save_bearer_token(token_data)

            # Prepare success response with FULL access token
            response = {
                "status": "success",
                "message": "Device authentication completed successfully! Use the access_token below in your function calls.",
                "instructions_shown": instructions,
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_in": token_data.get("expires_in"),
                "scope": token_data.get("scope", ""),
                "access_token": token_data.get("access_token", "")  # FULL token returned
            }

            logger.info("✅ Device authentication flow completed!")
            logger.info("Token returned in response (not saved to file)")

            return json.dumps(response, indent=2)

        except Exception as poll_error:
            # Return the instructions even if polling fails
            return json.dumps({
                "status": "pending",
                "message": "Authentication instructions displayed, but token polling failed or timed out",
                "instructions": instructions,
                "user_code": user_code,
                "verification_uri": verification_uri,
                "error": str(poll_error),
                "suggestion": "Try using start_device_auth() and complete_device_auth() for better control"
            }, indent=2)

    except Exception as e:
        logger.error(f"Device authentication flow failed: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }, indent=2)


# =============================================================================
# Client Credentials OAuth Tools
# =============================================================================

@mcp.tool()
async def get_azure_token(scope: str = None) -> str:
    """
    Get an Azure OAuth2 Bearer token using CLIENT CREDENTIALS flow only.

    IMPORTANT: This function only works when AUTH_METHOD=CLIENT_CREDENTIALS.
    For Device Code flow (user authentication), use start_device_auth() and complete_device_auth() instead.

    Args:
        scope: OAuth2 scope (default: from OAUTH2_SCOPE env var or Microsoft Graph API)

    Returns:
        Bearer token string or error message
    """
    try:
        token_data = await get_cached_token(scope)
        bearer_token = f"Bearer {token_data['access_token']}"
        return bearer_token
    except Exception as e:
        return f"Error getting token: {str(e)}"


@mcp.tool()
async def get_azure_token_info(scope: str = None) -> str:
    """
    Get detailed Azure OAuth2 token information including expiry.

    Args:
        scope: OAuth2 scope (default: from OAUTH2_SCOPE env var or Microsoft Graph API)

    Returns:
        JSON string with token details
    """
    try:
        token_data = await get_cached_token(scope)

        # Get authentication method
        auth_method = os.getenv("AUTH_METHOD", "DEVICE_CODE").upper()

        # Prepare response data (excluding sensitive information)
        info = {
            "auth_method": auth_method,
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "expires_at": token_data.get("expires_at").isoformat() if "expires_at" in token_data else None,
            "scope": token_data.get("scope"),
            "access_token_preview": f"{token_data['access_token'][:20]}..." if "access_token" in token_data else None,
            "cached": _cached_token is not None
        }

        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error getting token info: {str(e)}"


@mcp.tool()
async def test_azure_token(api_endpoint: str = "https://graph.microsoft.com/v1.0/me",
                          scope: str = "https://graph.microsoft.com/.default") -> str:
    """
    Test the Azure token by making an authenticated API call.

    Args:
        api_endpoint: API endpoint to test (default: Microsoft Graph /me)
        scope: OAuth2 scope for the token

    Returns:
        API response or error message
    """
    try:
        # Get the token
        token_data = await get_cached_token(scope)
        bearer_token = f"Bearer {token_data['access_token']}"

        # Make test API call
        headers = {
            "Authorization": bearer_token,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(api_endpoint, headers=headers, timeout=30.0)

            if response.status_code == 200:
                return f"Token test successful!\nStatus: {response.status_code}\nResponse: {response.text[:500]}..."
            else:
                return f"Token test failed!\nStatus: {response.status_code}\nResponse: {response.text}"

    except Exception as e:
        return f"Error testing token: {str(e)}"


@mcp.tool()
async def check_auth_config() -> str:
    """
    Check and display current authentication configuration.

    Shows which authentication method is configured (CLIENT_CREDENTIALS or DEVICE_CODE)
    and validates the configuration for that method.

    Returns:
        JSON string with authentication configuration details
    """
    try:
        auth_method = os.getenv("AUTH_METHOD", "DEVICE_CODE").upper()

        config = {
            "auth_method": auth_method,
            "tenant_id": os.getenv("TENANT_ID", "NOT_SET"),
            "client_id": os.getenv("CLIENT_ID", "NOT_SET"),
            "oauth2_scope": os.getenv("OAUTH2_SCOPE", "NOT_SET"),
        }

        if auth_method == "CLIENT_CREDENTIALS":
            config["client_secret_set"] = bool(os.getenv("CLIENT_SECRET"))
            config["access_token_url"] = os.getenv("ACCESS_TOKEN_URL", "NOT_SET")

            # Validate required settings
            missing = []
            if not os.getenv("CLIENT_SECRET"):
                missing.append("CLIENT_SECRET")
            if config["tenant_id"] == "NOT_SET":
                missing.append("TENANT_ID")
            if config["client_id"] == "NOT_SET":
                missing.append("CLIENT_ID")

            if missing:
                config["status"] = "INVALID"
                config["error"] = f"Missing required environment variables: {', '.join(missing)}"
            else:
                config["status"] = "VALID"

        elif auth_method == "DEVICE_CODE":
            config["status"] = "VALID"
            config["note"] = "Device Code mode: Automatic token acquisition disabled. Must pass bearer_token parameter."
            config["workflow"] = [
                "1. Run 'start device authentication'",
                "2. Complete authentication at microsoft.com/devicelogin",
                "3. Run 'complete device authentication' to get token",
                "4. Pass token as parameter to functions"
            ]
            config["usage_example"] = "Pass bearer_token='eyJ0...' as parameter to functions that need authentication"
            config["token_source"] = "conversation_context (no file storage)"

        else:
            config["status"] = "INVALID"
            config["error"] = f"Invalid AUTH_METHOD '{auth_method}'. Must be 'CLIENT_CREDENTIALS' or 'DEVICE_CODE'"

        # Check if token is currently cached
        config["token_cached"] = _cached_token is not None
        if _cached_token and "expires_at" in _cached_token:
            config["cached_token_expires_at"] = _cached_token["expires_at"].isoformat()
            config["cached_token_valid"] = datetime.now() < _cached_token["expires_at"]

        return json.dumps(config, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "ERROR",
            "error": str(e),
            "error_type": type(e).__name__
        }, indent=2)


# COMMENTED OUT: File-based token storage is deprecated - tokens are now handled in conversation context
# @mcp.tool()
# def read_bearer_token() -> str:
#     """
#     Read the bearer token from bearer_token.txt file.
#
#     Returns:
#         JSON string with the bearer token
#     """
#     try:
#         script_dir = os.path.dirname(os.path.abspath(__file__))
#         file_path = os.path.join(script_dir, "bearer_token.txt")
#
#         if not os.path.exists(file_path):
#             return json.dumps({
#                 "status": "error",
#                 "message": "Bearer token file not found. Run device_auth_flow first.",
#                 "file_path": file_path
#             }, indent=2)
#
#         with open(file_path, 'r') as f:
#             token = f.read().strip()
#
#         return json.dumps({
#             "status": "success",
#             "token": token,
#             "token_preview": token[:50] + "..." if len(token) > 50 else token,
#             "file_path": file_path
#         }, indent=2)
#
#     except Exception as e:
#         logger.error(f"Failed to read bearer token: {str(e)}")
#         return json.dumps({
#             "status": "error",
#             "message": str(e),
#             "error_type": type(e).__name__
#         }, indent=2)

if __name__ == "__main__":
    # Run the server
    auth_method = os.getenv("AUTH_METHOD", "DEVICE_CODE").upper()
    logger.info("=" * 80)
    logger.info("Starting OAuth MCP Server...")
    logger.info(f"Authentication Method: {auth_method}")
    logger.info("=" * 80)
    mcp.run()
