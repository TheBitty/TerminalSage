#!/usr/bin/env python3
# simple_ctf_agent.py - Your starting point

import asyncio
import subprocess
import os

class SimpleCTFAgent:
    def __init__(self):
        self.chat_mode = False
        print("🔧 Simple CTF Agent Started!")
        print("Commands: /chat (toggle), /exit, /help")
        print("Try: ls, /chat, or any command\n")
    
    async def run(self):
        """Main loop - keep it simple"""
        while True:
            try:
                # Simple prompt
                if self.chat_mode:
                    prompt = "🤖 chat> "
                else:
                    prompt = "⚡ > "
                
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    self.handle_special_command(user_input)
                elif self.chat_mode:
                    print("💭 Chat mode - AI integration coming next!")
                    print("    For now, type /chat to go back to command mode")
                else:
                    self.run_command(user_input)
                    
            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                print("\nGoodbye!")
                break
    
    def handle_special_command(self, command):
        """Handle /commands"""
        if command == '/chat':
            self.chat_mode = not self.chat_mode
            mode = "chat" if self.chat_mode else "command"
            print(f"Switched to {mode} mode")
        
        elif command == '/exit':
            print("Goodbye!")
            exit(0)
        
        elif command == '/help':
            print("""
🔧 Simple CTF Agent Commands:
/chat  - Toggle chat mode (AI coming soon!)
/exit  - Exit
/help  - This help

Command mode: Run any shell command
Chat mode: Talk with AI (coming next!)
            """)
        else:
            print(f"Unknown command: {command}")
    
    def run_command(self, command):
        """Run shell commands - basic version"""
        try:
            print(f"🔧 Running: {command}")
            
            # Basic safety - prevent really dangerous stuff
            dangerous = ['rm -rf /', 'dd if=/dev/zero', 'format']
            if any(bad in command for bad in dangerous):
                print("❌ Dangerous command blocked!")
                return
            
            # Run the command
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            # Show output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Command timed out!")
        except Exception as e:
            print(f"Error: {e}")

# Simple entry point
async def main():
    agent = SimpleCTFAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
