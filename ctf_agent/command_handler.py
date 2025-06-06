#!/usr/bin/env python3
"""
Safe command execution handler
Validates commands, prevents dangerous operations, and executes safely
"""
import asyncio
import subprocess
import shlex
import os
import re
from typing import Dict, Any, List, Optional, NamedTuple
from pathlib import Path

from .utils import get_logger


class CommandResult(NamedTuple):
    """Result of command execution"""
    success: bool
    output: str
    error: str
    return_code: int
    command: str


class CommandHandler:
    """Handles safe command execution with validation"""
    
    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        # File system destruction
        r'rm\s+-rf\s+/',
        r'rm\s+-rf\s+~',
        r'rm\s+-rf\s+\*',
        r'rm\s+-rf\s+\.',
        r'find.*-delete',
        r'find.*-exec.*rm',
        
        # Disk operations
        r'dd\s+if=/dev/(zero|random|urandom)',
        r'dd.*of=/dev/[sh]d[a-z]',
        r'mkfs',
        r'format\s+[cC]:',
        
        # System modification
        r'chmod\s+-R\s+000',
        r'chmod\s+000\s+/',
        r'chown\s+-R.*:.*/',
        
        # Fork bombs and resource exhaustion
        r':\(\)\s*\{\s*:\|:&\s*\};:',  # Classic fork bomb
        r'while\s*true.*do.*done',
        r'yes\s*\|',
        
        # Dangerous redirects
        r'>\s*/dev/[sh]d[a-z]',
        r'>\s*/proc/',
        r'>\s*/sys/',
        
        # Network attacks (to prevent accidental DoS)
        r'hping3.*--flood',
        r'nmap.*-[sS][sS].*-T5',  # Aggressive scanning
    ]
    
    # Sudo patterns that need extra validation
    SUDO_PATTERNS = [
        r'sudo\s+rm',
        r'sudo\s+dd',
        r'sudo\s+mkfs',
        r'sudo\s+chmod',
        r'sudo\s+chown',
        r'sudo\s+-i',
        r'sudo\s+su',
    ]
    
    # CTF-safe commands that should always be allowed
    SAFE_CTF_TOOLS = [
        'nmap', 'gobuster', 'dirb', 'nikto', 'sqlmap',
        'hydra', 'john', 'hashcat', 'burpsuite', 'metasploit',
        'gdb', 'radare2', 'r2', 'objdump', 'strings', 'file',
        'binwalk', 'exiftool', 'steghide', 'stegsolve',
        'wireshark', 'tcpdump', 'netcat', 'nc', 'socat',
        'curl', 'wget', 'python', 'python3', 'ruby', 'perl',
        'gcc', 'g++', 'make', 'cmake', 'git', 'docker'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize command handler with configuration"""
        self.logger = get_logger(__name__)
        self.config = config
        
        # Command settings
        self.timeout = config.get('command', {}).get('timeout', 30)
        self.max_output_size = config.get('command', {}).get('max_output_size', 100000)
        self.allow_sudo = config.get('command', {}).get('allow_sudo', False)
        self.working_dir = config.get('command', {}).get('working_dir', os.getcwd())
        
        # Compile dangerous patterns
        self.dangerous_regex = [re.compile(pattern, re.I) for pattern in self.DANGEROUS_PATTERNS]
        self.sudo_regex = [re.compile(pattern, re.I) for pattern in self.SUDO_PATTERNS]
        
        self.logger.info("Command handler initialized")
    
    async def execute(self, command: str) -> CommandResult:
        """Execute a command safely"""
        # Validate command
        validation = self._validate_command(command)
        if not validation['safe']:
            self.logger.warning(f"Blocked dangerous command: {command}")
            return CommandResult(
                success=False,
                output="",
                error=f"L Command blocked: {validation['reason']}",
                return_code=-1,
                command=command
            )
        
        # Log command execution
        self.logger.info(f"Executing command: {command}")
        
        try:
            # Prepare command
            if os.name == 'nt':  # Windows
                # Use shell=True on Windows
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.working_dir
                )
            else:  # Unix-like
                # Use shell for complex commands, but try to be safer
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.working_dir,
                    # Limit resources
                    preexec_fn=self._limit_resources if hasattr(os, 'setrlimit') else None
                )
            
            # Execute with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    success=False,
                    output="",
                    error="⏰ Command timed out",
                    return_code=-1,
                    command=command
                )
            
            # Decode output
            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')
            
            # Truncate if too large
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size] + "\n... (output truncated)"
            if len(error) > self.max_output_size:
                error = error[:self.max_output_size] + "\n... (error truncated)"
            
            # Print output
            if output:
                print(output)
            if error and process.returncode != 0:
                print(f"❌ Error: {error}")
            
            return CommandResult(
                success=process.returncode == 0,
                output=output,
                error=error,
                return_code=process.returncode,
                command=command
            )
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return CommandResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                return_code=-1,
                command=command
            )
    
    def _validate_command(self, command: str) -> Dict[str, Any]:
        """Validate command for safety"""
        command_lower = command.lower().strip()
        
        # Check for empty command
        if not command_lower:
            return {'safe': False, 'reason': 'Empty command'}
        
        # Check dangerous patterns
        for pattern in self.dangerous_regex:
            if pattern.search(command):
                return {'safe': False, 'reason': 'Potentially destructive command detected'}
        
        # Check sudo usage
        if not self.allow_sudo:
            for pattern in self.sudo_regex:
                if pattern.search(command):
                    return {'safe': False, 'reason': 'Sudo commands are disabled for safety'}
        
        # Special validation for specific commands
        # Allow CTF tools even with aggressive flags
        first_word = command_lower.split()[0]
        if first_word in self.SAFE_CTF_TOOLS:
            return {'safe': True, 'reason': 'CTF tool allowed'}
        
        # Additional checks for piped commands
        if '|' in command:
            # Check each part of the pipe
            parts = command.split('|')
            for part in parts:
                validation = self._validate_command(part.strip())
                if not validation['safe']:
                    return validation
        
        # Check for shell bombs
        if command.count('&') > 5 or command.count(';') > 5:
            return {'safe': False, 'reason': 'Too many command separators'}
        
        # Check for suspicious redirects
        if re.search(r'>\s*/dev/|>\s*/proc/|>\s*/sys/', command):
            return {'safe': False, 'reason': 'Dangerous output redirection'}
        
        return {'safe': True, 'reason': 'Command validated'}
    
    def _limit_resources(self):
        """Limit process resources (Unix only)"""
        try:
            import resource
            
            # Limit CPU time (60 seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
            
            # Limit memory (1GB)
            resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
            
            # Limit number of processes
            resource.setrlimit(resource.RLIMIT_NPROC, (100, 100))
            
        except Exception:
            # Resource limiting not available
            pass
    
    def get_safe_commands(self) -> List[str]:
        """Get list of safe CTF commands"""
        return self.SAFE_CTF_TOOLS.copy()
    
    def add_safe_command(self, command: str):
        """Add a command to the safe list"""
        if command not in self.SAFE_CTF_TOOLS:
            self.SAFE_CTF_TOOLS.append(command)
            self.logger.info(f"Added {command} to safe commands")
    
    def set_working_directory(self, path: str):
        """Change working directory for commands"""
        if os.path.isdir(path):
            self.working_dir = path
            self.logger.info(f"Changed working directory to: {path}")
        else:
            raise ValueError(f"Invalid directory: {path}")