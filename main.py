#!/usr/bin/env python3
"""
TermSage - AI-Powered CTF Terminal Assistant
Main entry point for the application
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ctf_agent.agent import CTFAgent
from ctf_agent.utils import check_dependencies, setup_logging, print_banner


async def main():
    """Main entry point for TermSage"""
    try:
        # Setup logging
        setup_logging()
        
        # Print banner
        print_banner()
        
        # Check dependencies
        if not check_dependencies():
            print("❌ Missing dependencies. Please run: pip install -r requirements.txt")
            return 1
        
        # Create and run agent
        agent = CTFAgent()
        await agent.run()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    # Use asyncio.run for proper cleanup
    exit_code = asyncio.run(main())
    sys.exit(exit_code)