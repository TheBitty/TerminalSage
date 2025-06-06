#!/usr/bin/env python3
"""
Core CTF Agent implementation
Handles main terminal loop, mode switching, and coordination
"""
import asyncio
import sys
import os
import readline
import atexit
from pathlib import Path
from typing import Optional, Dict, Any
import json

from .ai_models import AIModelManager
from .command_handler import CommandHandler
from .context_manager import ContextManager
from .config import ConfigManager
from .utils import get_logger, format_prompt


class CTFAgent:
    """Main CTF Agent class - coordinates all components"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize CTF Agent with configuration"""
        self.logger = get_logger(__name__)
        
        # Load configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # Initialize components
        self.ai_manager = AIModelManager(self.config)
        self.command_handler = CommandHandler(self.config)
        self.context_manager = ContextManager(self.config)
        
        # Agent state
        self.chat_mode = False
        self.running = True
        self.current_model = self.config.get('default_model', 'ollama:deepseek-r1:8b')
        
        # Setup readline for better terminal experience
        self._setup_readline()
        
        self.logger.info("CTF Agent initialized successfully")
    
    def _setup_readline(self):
        """Configure readline for command history and completion"""
        # Set up history file
        history_file = Path.home() / '.termsage_history'
        
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        
        # Save history on exit
        atexit.register(readline.write_history_file, history_file)
        
        # Configure readline
        readline.set_history_length(1000)
        readline.parse_and_bind('tab: complete')
        
        # Set up auto-completion
        readline.set_completer(self._completer)
        
    def _completer(self, text: str, state: int):
        """Auto-completion for commands"""
        commands = ['/help', '/chat', '/models', '/model', '/clear', 
                   '/config', '/exit', '/quit', '/history', '/save', '/load']
        
        # Filter matching commands
        options = [cmd for cmd in commands if cmd.startswith(text)]
        
        if state < len(options):
            return options[state]
        return None
    
    async def run(self):
        """Main agent loop"""
        self.logger.info("Starting CTF Agent main loop")
        
        # Print welcome message
        self._print_welcome()
        
        # Check AI availability
        if not await self.ai_manager.check_availability():
            print("⚠️  No AI models available. Some features will be limited.")
            print("   Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh")
        
        # Main loop
        while self.running:
            try:
                # Get prompt based on mode
                prompt = format_prompt(self.chat_mode)
                
                # Get user input
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Process input
                await self._process_input(user_input)
                
            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                print(f"❌ Error: {e}")
    
    async def _process_input(self, user_input: str):
        """Process user input based on current mode"""
        # Handle special commands (start with /)
        if user_input.startswith('/'):
            await self._handle_special_command(user_input)
            return
        
        # Chat mode
        if self.chat_mode:
            await self._handle_chat(user_input)
        else:
            # Command mode - check for ? suffix
            if user_input.endswith('?') and len(user_input) > 1:
                # Get AI suggestions for command
                await self._get_command_suggestion(user_input[:-1])
            else:
                # Execute command
                await self._execute_command(user_input)
    
    async def _handle_special_command(self, command: str):
        """Handle special / commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == '/help':
            self._print_help()
        
        elif cmd == '/chat':
            self.chat_mode = not self.chat_mode
            mode = "chat" if self.chat_mode else "command"
            print(f"📝 Switched to {mode} mode")
            if self.chat_mode:
                print("💡 Tip: I'm specialized in CTF and security tasks!")
        
        elif cmd == '/models':
            await self._list_models()
        
        elif cmd == '/model':
            if args:
                await self._switch_model(args)
            else:
                print(f"📍 Current model: {self.current_model}")
        
        elif cmd == '/clear':
            self.context_manager.clear()
            print("🧹 Context cleared")
        
        elif cmd == '/config':
            self._show_config()
        
        elif cmd == '/history':
            self._show_history()
        
        elif cmd == '/save':
            self._save_session(args or "session.json")
        
        elif cmd == '/load':
            self._load_session(args or "session.json")
        
        elif cmd in ['/exit', '/quit']:
            self.running = False
            print("👋 Goodbye!")
        
        else:
            print(f"❓ Unknown command: {command}")
            print("   Type /help for available commands")
    
    async def _handle_chat(self, message: str):
        """Handle chat mode interaction"""
        try:
            # Add message to context
            self.context_manager.add_message("user", message)
            
            # Show thinking indicator
            print("🤔 Thinking...", end='', flush=True)
            
            # Get AI response
            response_generator = self.ai_manager.chat(
                messages=self.context_manager.get_messages(),
                model=self.current_model,
                stream=True
            )
            
            # Clear thinking indicator
            print("\r", end='')
            
            # Stream response
            print("🤖 ", end='', flush=True)
            full_response = ""
            
            async for chunk in response_generator:
                print(chunk, end='', flush=True)
                full_response += chunk
            
            print("\n")
            
            # Add response to context
            self.context_manager.add_message("assistant", full_response)
            
            # Check context size
            if self.context_manager.should_compress():
                print("💡 Compressing context to maintain performance...")
                self.context_manager.compress()
                
        except Exception as e:
            print(f"\r❌ Chat error: {e}")
            self.logger.error(f"Chat error: {e}")
    
    async def _get_command_suggestion(self, command: str):
        """Get AI suggestion for a command"""
        try:
            print(f"💡 Getting help for: {command}")
            
            prompt = f"""As a CTF assistant, help with this command: {command}
            
Provide:
1. What this command does
2. Common CTF usage examples
3. Important flags/options
4. Safety considerations

Keep it concise and practical."""
            
            # Get suggestion
            response_generator = self.ai_manager.chat(
                messages=[
                    {"role": "system", "content": "You are a CTF and security expert assistant."},
                    {"role": "user", "content": prompt}
                ],
                model=self.current_model,
                stream=True
            )
            
            print("\n📚 Command Help:\n")
            async for chunk in response_generator:
                print(chunk, end='', flush=True)
            print("\n")
            
        except Exception as e:
            print(f"❌ Could not get suggestion: {e}")
    
    async def _execute_command(self, command: str):
        """Execute a shell command with safety checks"""
        result = await self.command_handler.execute(command)
        
        # If command failed and AI is available, offer help
        if not result.success and await self.ai_manager.is_available():
            print("\n💡 Command failed. Getting AI assistance...")
            
            prompt = f"""The command failed: {command}
Error: {result.error}

Please explain:
1. Why it failed
2. How to fix it
3. Alternative approaches

Keep it brief and practical for CTF work."""
            
            try:
                response_generator = self.ai_manager.chat(
                    messages=[
                        {"role": "system", "content": "You are a CTF and security expert assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.current_model,
                    stream=True
                )
                
                print("\n🛠️  Troubleshooting:\n")
                async for chunk in response_generator:
                    print(chunk, end='', flush=True)
                print("\n")
                
            except Exception as e:
                self.logger.error(f"Failed to get AI help: {e}")
    
    async def _list_models(self):
        """List available AI models"""
        models = await self.ai_manager.list_models()
        
        if not models:
            print("❌ No models available")
            return
        
        print("📦 Available models:")
        for provider, model_list in models.items():
            if model_list:
                print(f"\n  {provider}:")
                for model in model_list:
                    marker = "✓" if f"{provider}:{model}" == self.current_model else " "
                    print(f"    {marker} {model}")
    
    async def _switch_model(self, model_spec: str):
        """Switch to a different model"""
        # Add provider prefix if not present
        if ':' not in model_spec:
            model_spec = f"ollama:{model_spec}"
        
        if await self.ai_manager.is_model_available(model_spec):
            self.current_model = model_spec
            self.context_manager.clear()  # Clear context when switching models
            print(f"✅ Switched to model: {self.current_model}")
            print("🧹 Context cleared for new model")
        else:
            print(f"❌ Model not available: {model_spec}")
            print("   Use /models to see available options")
    
    def _show_config(self):
        """Display current configuration"""
        print("⚙️  Current Configuration:")
        print(json.dumps(self.config, indent=2))
    
    def _show_history(self):
        """Show command history"""
        print("📜 Recent commands:")
        history_length = readline.get_current_history_length()
        start = max(0, history_length - 20)
        
        for i in range(start, history_length):
            print(f"  {i}: {readline.get_history_item(i + 1)}")
    
    def _save_session(self, filename: str):
        """Save current session"""
        try:
            session = {
                'context': self.context_manager.get_messages(),
                'model': self.current_model,
                'chat_mode': self.chat_mode
            }
            
            with open(filename, 'w') as f:
                json.dump(session, f, indent=2)
            
            print(f"💾 Session saved to: {filename}")
        except Exception as e:
            print(f"❌ Failed to save session: {e}")
    
    def _load_session(self, filename: str):
        """Load a saved session"""
        try:
            with open(filename, 'r') as f:
                session = json.load(f)
            
            self.context_manager.set_messages(session.get('context', []))
            self.current_model = session.get('model', self.current_model)
            self.chat_mode = session.get('chat_mode', False)
            
            print(f"📂 Session loaded from: {filename}")
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
        except Exception as e:
            print(f"❌ Failed to load session: {e}")
    
    def _print_welcome(self):
        """Print welcome message"""
        print("""
╔══════════════════════════════════════════════════════════╗
║                    🛡️  TermSage v1.0 🛡️                   ║
║            AI-Powered CTF Terminal Assistant             ║
╚══════════════════════════════════════════════════════════╝

🎯 Specialized for: CTF, pentesting, reverse engineering
🤖 AI Models: Multiple providers with automatic fallback
🔒 Safety: Built-in command validation
⚡ Performance: Smart context management

Commands: /help, /chat, /models, /exit
Add '?' to any command for AI help (e.g., nmap?)
""")
    
    def _print_help(self):
        """Print help message"""
        print("""
🔧 TermSage Commands:

Mode Control:
  /chat          Toggle chat mode
  /clear         Clear conversation context

Model Management:
  /models        List available AI models
  /model <name>  Switch to a different model

Session Management:
  /save [file]   Save current session
  /load [file]   Load a saved session
  /history       Show command history

Configuration:
  /config        Show current configuration

Other:
  /help          Show this help
  /exit, /quit   Exit TermSage

Tips:
  • In command mode, add '?' to any command for AI suggestions
  • Use smaller models (1b, 3b) for faster responses
  • Context is automatically compressed to maintain performance
  • All Kali Linux tools are available in command mode
""")