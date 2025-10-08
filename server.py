#!/usr/bin/env python3
"""
Device Authentication MCP Server

A Model Context Protocol (MCP) server for device authentication operations.
Implements OAuth 2.0 Device Authorization Grant Flow (RFC 8628).
"""

import os
import logging
import json
import asyncio
import httpx
from typing import Dict, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configure logging system
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "device_auth_mcp_server.log")

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
mcp = FastMCP("Device Authentication Server")

@mcp.tool()
def ping() -> str:
    """Health check endpoint to verify the server is running."""
    logger.info("Ping function called - responding with pong")
    return "pong"

@mcp.tool()
def get_server_info() -> str:
    """Get information about the Device Authentication MCP Server."""
    info = {
        "name": "Device Authentication MCP Server",
        "version": "0.1.0",
        "description": "MCP server for device authentication operations",
        "log_level": LOG_LEVEL,
        "log_file": os.path.abspath(LOG_FILE)
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


def save_bearer_token(token_data: Dict[str, Any], filename: str = "bearer_token.txt") -> str:
    """
    Save the bearer token to a text file.

    Args:
        token_data: The token response from poll_for_token
        filename: The filename to save to (default: bearer_token.txt)

    Returns:
        Path to the saved file
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    access_token = token_data.get("access_token", "")

    with open(file_path, 'w') as f:
        f.write(access_token)

    logger.info(f"Bearer token saved to: {file_path}")
    return file_path


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


@mcp.tool()
def read_bearer_token() -> str:
    """
    Read the bearer token from bearer_token.txt file.

    Returns:
        JSON string with the bearer token
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "bearer_token.txt")

        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": "Bearer token file not found. Run device_auth_flow first.",
                "file_path": file_path
            }, indent=2)

        with open(file_path, 'r') as f:
            token = f.read().strip()

        return json.dumps({
            "status": "success",
            "token": token,
            "token_preview": token[:50] + "..." if len(token) > 50 else token,
            "file_path": file_path
        }, indent=2)

    except Exception as e:
        logger.error(f"Failed to read bearer token: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }, indent=2)

if __name__ == "__main__":
    # Run the server
    logger.info("Starting Device Authentication MCP Server...")
    mcp.run()
