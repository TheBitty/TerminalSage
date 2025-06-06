#!/usr/bin/env python3
# simple_ctf_agent.py - Your starting point
import sys
import os

# Auto-activate virtual environment if it exists
def activate_venv():
    """Automatically activate virtual environment if found"""
    # Check for venv in current directory
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv')
    
    if os.path.exists(venv_path):
        # Check if we're already in a virtual environment
        if sys.prefix == sys.base_prefix:
            print("🔄 Activating virtual environment...")
            
            # Get the python executable from the venv
            if sys.platform == "win32":
                python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
            else:
                python_exe = os.path.join(venv_path, 'bin', 'python')
            
            # Re-execute the script with the venv's python
            if os.path.exists(python_exe):
                os.execv(python_exe, [python_exe] + sys.argv)
        else:
            print("✅ Virtual environment active")
    else:
        print("⚠️  No virtual environment found. Consider creating one:")
        print("    python3 -m venv venv")
        print("    pip install ollama")

# Activate venv before imports that might need it
activate_venv()

# Now import the rest after venv is activated
import asyncio
import subprocess
from typing import Optional, List, Dict

try:
    import ollama
except ImportError:
    print("❌ ollama module not found!")
    print("📦 Install it with: pip install ollama")
    print("   or if using venv: ./venv/bin/pip install ollama")
    sys.exit(1)


class SimpleCTFAgent:
    def __init__(self):
        self.chat_mode = False
        self.model = "deepseek-r1:8b"  # Updated to match your installed model
        self.chat_history = []
        self.ollama_client = None
        self.available_models = []
        
        # CTF-focused system message
        self.system_message = {
            'role': 'system',
            'content': """You are a CTF (Capture The Flag) assistant specializing in cybersecurity. 
            Help with penetration testing, exploit development, reverse engineering, and CTF challenges. 
            Provide practical advice on tools like nmap, burp suite, gdb, radare2, and common CTF techniques."""
        }
        
        # More comprehensive dangerous commands
        self.dangerous_patterns = [
            'rm -rf /', 'rm -rf ~', 'rm -rf *',
            'dd if=/dev/zero', 'dd if=/dev/random',
            'format', 'mkfs', 
            ':(){ :|:& };:',  # Fork bomb
            'mv /* /dev/null',
            'chmod -R 000',
            'chown -R',
            'sudo rm -rf',
            '> /dev/sda'
        ]

        # Try to connect to Ollama
        self.check_ollama_connection()

    def check_ollama_connection(self):
        """Check and establish Ollama connection"""
        try:
            self.ollama_client = ollama.Client()
            response = self.ollama_client.list()

            # Debug: print the response to see its structure
            # print(f"DEBUG: Response type: {type(response)}")
            # print(f"DEBUG: Response: {response}")

            # Handle the response structure properly
            if isinstance(response, dict) and 'models' in response:
                self.available_models = [m.get('name', m.get('model', '')) for m in response['models']]
            elif hasattr(response, 'models'):
                # Handle response as object with models attribute
                self.available_models = []
                for m in response.models:
                    if hasattr(m, 'model'):
                        self.available_models.append(m.model)
                    elif hasattr(m, 'name'):
                        self.available_models.append(m.name)
                    elif isinstance(m, dict):
                        self.available_models.append(m.get('name', m.get('model', '')))
                    else:
                        self.available_models.append(str(m))
            elif isinstance(response, list):
                # Handle response as direct list of models
                self.available_models = [m.get('name', m.get('model', '')) if isinstance(m, dict) else str(m) for m in response]
            else:
                # Fallback for different response formats
                self.available_models = []

            if not self.available_models:
                print("⚠️  No models found. Pull one with: ollama pull deepseek-r1:8b")
                self.ollama_client = None
                return

            print(f"✅ Ollama connected. Available models: {', '.join(self.available_models)}")

            # Verify model exists with updated preferences from info.md
            if self.model not in self.available_models:
                print(f"⚠️  Model {self.model} not found.")
                # Try models in order of preference from info.md
                for fallback in ['deepseek-r1:8b', 'deepseek-coder', 'codellama', 'llama3', 'llama2']:
                    if fallback in self.available_models:
                        self.model = fallback
                        print(f"📍 Using fallback model: {self.model}")
                        return
                # Just use first available
                if self.available_models:
                    self.model = self.available_models[0]
                    print(f"📍 Using model: {self.model}")
        except Exception as e:
            print(f"⚠️  Could not connect to Ollama: {e}")
            print("    Make sure Ollama is running: ollama serve")
            self.ollama_client = None

        print("\n🔧 Simple CTF Agent Started!")
        print("Commands: /chat (toggle), /clear, /models, /exit, /help")
        print("Add ? to any command for AI suggestions (e.g., nmap?)")
        print("Try: ls, /chat, or any command\n")
        
        # Performance tip for large models
        if self.model and 'r1' in self.model:
            print("💡 Note: deepseek-r1 models are large and may be slow.")
            print("   For faster responses, try: ollama pull llama3.2:1b\n")

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
                    await self.chat_with_ai(user_input)
                else:
                    # Check for command suggestions with ?
                    if user_input.endswith('?') and len(user_input) > 1:
                        await self.get_command_suggestion(user_input[:-1])
                    else:
                        await self.run_command(user_input)

            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                print("\nGoodbye!")
                break

    async def get_command_suggestion(self, command: str):
        """Get AI suggestions for a command"""
        if not self.ollama_client:
            print("❌ Ollama not available for suggestions. Start it with: ollama serve")
            return
            
        try:
            print(f"🤔 Getting suggestions for: {command}")
            
            # Create a focused prompt for command suggestions
            messages = [
                self.system_message,
                {
                    'role': 'user',
                    'content': f"""I need help with the command: {command}
                    Please provide:
                    1. What this command does
                    2. Common usage examples for CTF/security work
                    3. Useful flags and options
                    4. Safety considerations
                    Keep it concise and practical."""
                }
            ]
            
            response = self.ollama_client.chat(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            print("\n💡 Suggestion:\n")
            for chunk in response:
                print(chunk['message']['content'], end='', flush=True)
            print("\n")
            
        except Exception as e:
            print(f"❌ Could not get suggestion: {e}")

    async def chat_with_ai(self, message: str):
        """Handle AI chat interactions"""
        if not self.ollama_client:
            print("❌ Ollama not available. Start it with: ollama serve")
            return

        try:
            # Initialize chat history with system message if empty
            if len(self.chat_history) == 0:
                self.chat_history.append(self.system_message)
                
            # Add user message to history
            self.chat_history.append({'role': 'user', 'content': message})

            print("🤔 Thinking...", end='', flush=True)
            
            # Track if we've started receiving response
            first_chunk = True

            # Get AI response with streaming
            response = self.ollama_client.chat(
                model=self.model,
                messages=self.chat_history,
                stream=True
            )

            # Print response as it streams
            full_response = ""

            for chunk in response:
                if first_chunk:
                    print("\r🤖 ", end='', flush=True)  # Clear "Thinking..." message
                    first_chunk = False
                    
                chunk_text = chunk['message']['content']
                print(chunk_text, end='', flush=True)
                full_response += chunk_text

            print("\n")

            # Add to history
            self.chat_history.append({'role': 'assistant', 'content': full_response})

            # Context management with CTF-specific awareness
            if len(self.chat_history) > 20:
                print("💡 Tip: Use /clear to reset chat history if responses slow down")
                # In future: implement smart compression that preserves CTF findings

        except Exception as e:
            print(f"❌ Chat error: {e}")
            print("Tip: Make sure Ollama is running and model is pulled")

    def handle_special_command(self, command):
        """Handle /commands"""
        if command == '/chat':
            self.chat_mode = not self.chat_mode
            mode = "chat" if self.chat_mode else "command"
            print(f"Switched to {mode} mode")

            # Re-check ollama when entering chat mode
            if self.chat_mode and not self.ollama_client:
                print("🔄 Checking Ollama connection...")
                self.check_ollama_connection()

        elif command == '/clear':
            self.chat_history = []
            print("🧹 Chat history cleared")

        elif command == '/models':
            # Show available models
            if self.ollama_client:
                try:
                    response = self.ollama_client.list()
                    models = []
                    
                    if isinstance(response, dict) and 'models' in response:
                        models = response['models']
                    elif hasattr(response, 'models'):
                        models = response.models
                    
                    if models:
                        print("Available models:")
                        for m in models:
                            if hasattr(m, 'model'):
                                name = m.model
                            elif hasattr(m, 'name'):
                                name = m.name
                            elif isinstance(m, dict):
                                name = m.get('name', m.get('model', 'unknown'))
                            else:
                                name = str(m)
                            
                            marker = "✓" if name == self.model else " "
                            print(f"  {marker} {name}")
                    else:
                        print("No models found. Pull one with: ollama pull deepseek-r1:8b")
                except Exception as e:
                    print(f"❌ Could not list models: {e}")
            else:
                print("❌ Ollama not connected")

        elif command == '/exit':
            print("Goodbye!")
            exit(0)

        elif command.startswith('/model '):
            # Switch model
            new_model = command[7:].strip()
            if new_model in self.available_models:
                self.model = new_model
                print(f"✅ Switched to model: {self.model}")
                # Clear chat history when switching models
                self.chat_history = []
                print("🧹 Chat history cleared for new model")
            else:
                print(f"❌ Model '{new_model}' not found")
                print(f"Available models: {', '.join(self.available_models)}")
                
        elif command == '/help':
            print("""
🔧 Simple CTF Agent Commands:
/chat       - Toggle chat mode
/clear      - Clear chat history
/models     - List available models
/model <name> - Switch to a different model
/exit       - Exit
/help       - This help

Command mode: 
  - Run any shell command
  - Add ? for AI suggestions (e.g., nmap?, gobuster?)
  
Chat mode: Talk with AI about CTF strategies

💡 Performance tip: For faster responses, try smaller models:
   ollama pull llama3.2:1b
   ollama pull phi3:mini
            """)
        else:
            print(f"Unknown command: {command}")

    async def run_command(self, command: str):
        """Run shell commands with safety checks and AI assistance on failure"""
        try:
            # Enhanced safety check
            if self.is_dangerous_command(command):
                print("❌ Dangerous command blocked!")
                print("💡 This command could damage your system.")
                return

            print(f"🔧 Running: {command}")

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
                
            # AI assistance for failed commands
            if result.returncode != 0 and self.ollama_client:
                print("\n💡 Command failed. Getting AI assistance...")
                await self.get_failure_help(command, result.stderr)

        except subprocess.TimeoutExpired:
            print("⏰ Command timed out!")
        except Exception as e:
            print(f"Error: {e}")
            if self.ollama_client:
                await self.get_failure_help(command, str(e))

    def is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous"""
        cmd_lower = command.lower()
        
        # Check against dangerous patterns
        for pattern in self.dangerous_patterns:
            if pattern.lower() in cmd_lower:
                return True
                
        # Additional checks for sudo/su with dangerous commands
        if 'sudo' in cmd_lower or 'su -c' in cmd_lower:
            for pattern in self.dangerous_patterns:
                if pattern.lower() in cmd_lower:
                    return True
                    
        return False

    async def get_failure_help(self, command: str, error: str):
        """Get AI help when a command fails"""
        try:
            messages = [
                self.system_message,
                {
                    'role': 'user',
                    'content': f"""The command failed: {command}
                    Error: {error}
                    
                    Please provide:
                    1. Why it might have failed
                    2. How to fix it
                    3. Alternative commands that might work
                    Keep it brief and practical for CTF work."""
                }
            ]
            
            response = self.ollama_client.chat(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            print("\n🛠️  Troubleshooting:\n")
            for chunk in response:
                print(chunk['message']['content'], end='', flush=True)
            print("\n")
            
        except Exception as e:
            print(f"Could not get help: {e}")


# Simple entry point
async def main():
    agent = SimpleCTFAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
