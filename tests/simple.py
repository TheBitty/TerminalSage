#!/usr/bin/env python3
# simple_ctf_agent.py - Your starting point
import asyncio
import subprocess
import os
import ollama


class SimpleCTFAgent:
    def __init__(self):
        self.chat_mode = False
        self.model = "deepseek-r1:8b"
        self.chat_history = []
        self.ollama_client = None

        # Try to connect to Ollama
        self.check_ollama_connection()

    def check_ollama_connection(self):
        """Check and establish Ollama connection"""
        try:
            self.ollama_client = ollama.Client()
            response = self.ollama_client.list()

            # Handle the response structure properly
            if isinstance(response, dict) and 'models' in response:
                self.available_models = [m.get('name', m.get('model', '')) for m in response['models']]
            else:
                # Fallback for different response formats
                self.available_models = []

            if not self.available_models:
                print("⚠️  No models found. Pull one with: ollama pull llama2")
                self.ollama_client = None
                return

            print(f"✅ Ollama connected. Available models: {', '.join(self.available_models)}")

            # Verify model exists
            if self.model not in self.available_models:
                print(f"⚠️  Model {self.model} not found.")
                # Try some common models
                for fallback in ['llama2', 'llama3', 'codellama']:
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
        print("Try: ls, /chat, or any command\n")
        print("Commands: /chat (toggle), /clear, /exit, /help")
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
                    await self.chat_with_ai(user_input)
                else:
                    self.run_command(user_input)

            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                print("\nGoodbye!")
                break

    async def chat_with_ai(self, message: str):
        """Handle AI chat interactions"""
        if not self.ollama_client:
            print("❌ Ollama not available. Start it with: ollama serve")
            return

        try:
            # Add user message to history
            self.chat_history.append({'role': 'user', 'content': message})

            print("🤔 Thinking...")

            # Get AI response with streaming
            response = self.ollama_client.chat(
                model=self.model,
                messages=self.chat_history,
                stream=True
            )

            # Print response as it streams
            print("\n🤖 ", end='', flush=True)
            full_response = ""

            for chunk in response:
                chunk_text = chunk['message']['content']
                print(chunk_text, end='', flush=True)
                full_response += chunk_text

            print("\n")

            # Add to history
            self.chat_history.append({'role': 'assistant', 'content': full_response})

            # Simple context management - warn if getting long
            if len(self.chat_history) > 20:
                print("💡 Tip: Use /clear to reset chat history if responses slow down")

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
                    if isinstance(response, dict) and 'models' in response:
                        models = response['models']
                        if models:
                            print("Available models:")
                            for m in models:
                                name = m.get('name', m.get('model', 'unknown'))
                                marker = "✓" if name == self.model else " "
                                print(f"  {marker} {name}")
                        else:
                            print("No models found. Pull one with: ollama pull llama2")
                    else:
                        print("❌ Unexpected response format from Ollama")
                except Exception as e:
                    print(f"❌ Could not list models: {e}")
            else:
                print("❌ Ollama not connected")

        elif command == '/exit':
            print("Goodbye!")
            exit(0)

        elif command == '/help':
            print("""
🔧 Simple CTF Agent Commands:
/chat   - Toggle chat mode
/clear  - Clear chat history
/models - List available models
/exit   - Exit
/help   - This help

Command mode: Run any shell command
Chat mode: Talk with AI about CTF strategies
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