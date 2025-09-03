#!/usr/bin/env python3
"""
BlackDuck CLI entry point
"""

import sys
import argparse
import os
import logging

def main():
    """Main CLI entry point for BlackDuck"""
    parser = argparse.ArgumentParser(
        prog='blackduck',
        description='BlackDuck Hub REST API CLI'
    )
    
    parser.add_argument(
        '--mcp',
        action='store_true',
        help='Launch MCP (Model Context Protocol) server'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'blackduck {get_version()}'
    )
    
    args = parser.parse_args()
    
    if args.mcp:
        launch_mcp_server()
    else:
        show_usage()

def get_version():
    """Get package version"""
    try:
        from .__version__ import __version__
        return __version__
    except ImportError:
        return 'unknown'

def show_usage():
    """Show basic usage information"""
    print("BlackDuck Hub REST API CLI")
    print()
    print("Usage:")
    print("  blackduck --mcp     Launch MCP server")
    print("  blackduck --version Show version")
    print()
    print("For MCP server usage:")
    print("  Set environment variables:")
    print("    BLACKDUCK_URL")
    print("    BLACKDUCK_TOKEN")

def launch_mcp_server():
    """Launch the MCP server"""
    try:
        from .mcp_server import run_mcp_server
        run_mcp_server()
    except ImportError as e:
        print(f"Error: MCP server dependencies not available: {e}", file=sys.stderr)
        print("Install with: pip install fastmcp", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error launching MCP server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()