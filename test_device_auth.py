#!/usr/bin/env python3
"""
Test script for OAuth Device Authorization Grant Flow.

This script tests the device authentication flow without needing MCP.
"""

import asyncio
from server import device_auth_flow, read_bearer_token

async def main():
    print("=" * 80)
    print("OAuth Device Authorization Grant Flow Test")
    print("=" * 80)
    print()

    # Run the device auth flow
    print("Starting device authentication flow...")
    print()

    result = await device_auth_flow()
    print(result)
    print()

    # Try to read the token
    print("=" * 80)
    print("Reading saved bearer token...")
    print("=" * 80)
    print()

    token_result = read_bearer_token()
    print(token_result)

if __name__ == "__main__":
    asyncio.run(main())
