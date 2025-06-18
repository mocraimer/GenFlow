#!/usr/bin/env python3
"""
Quick start script for airflow-ai-bridge
Tests basic functionality without Airflow
"""

import asyncio
import sys

# Check Python version
if sys.version_info < (3, 11) or sys.version_info >= (3, 12):
    print("❌ Error: Python 3.11 is required")
    print(f"Found: Python {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)

print("🚀 Testing airflow-ai-bridge installation...")

try:
    from airflow_ai_bridge import (
        MCPServerConfig,
        MCPClient,
        mcp_agent,
        __version__
    )
    print(f"✅ Successfully imported airflow-ai-bridge v{__version__}")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Please install: pip install -e .")
    sys.exit(1)


async def test_mcp_client():
    """Test basic MCP client functionality"""
    print("\n📋 Testing MCP Client...")
    
    # Test with echo command (available on all systems)
    config = MCPServerConfig(
        command="echo",
        args=["Hello from MCP"],
        timeout=5.0
    )
    
    client = MCPClient(config)
    
    try:
        print("  - Connecting to test server...")
        await client.connect()
        print("  ✅ Connected successfully")
        
        print("  - Listing tools...")
        tools = await client.list_tools()
        print(f"  ✅ Found {len(tools)} tools")
        
        await client.disconnect()
        print("  ✅ Disconnected successfully")
        
    except Exception as e:
        print(f"  ⚠️  Test server error (this is expected): {e}")
        print("  💡 To test with real MCP servers, install one like mcp-server-filesystem")


def test_decorator():
    """Test decorator functionality"""
    print("\n📋 Testing Decorators...")
    
    @mcp_agent(
        model="gpt-4o",
        system_prompt="You are a helpful assistant"
    )
    def my_task():
        return "Hello from decorated task"
    
    print("  ✅ Decorator applied successfully")
    result = my_task()
    print(f"  ✅ Task executed: {result}")


def main():
    """Run all tests"""
    print(f"\n🐍 Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Run async test
    asyncio.run(test_mcp_client())
    
    # Run sync tests
    test_decorator()
    
    print("\n✨ All tests completed!")
    print("\nNext steps:")
    print("1. Install an MCP server: npm install -g mcp-server-filesystem")
    print("2. Check out the examples/ directory")
    print("3. Read the documentation in README.md")


if __name__ == "__main__":
    main()