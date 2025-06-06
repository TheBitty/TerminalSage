#!/usr/bin/env python3
"""
Utility functions for TermSage
Common helpers, logging, and support functions
"""
import os
import sys
import logging
import re
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
import importlib.util


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get configured logger instance"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create handler
        handler = logging.StreamHandler()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        logger.setLevel(level)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger


def setup_logging(debug: bool = False):
    """Setup global logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count"""
    # Very rough approximation: ~4 characters per token
    return len(text) // 4


def format_prompt(chat_mode: bool) -> str:
    """Format terminal prompt based on mode"""
    if chat_mode:
        return "🤖 chat> "
    else:
        return "⚡ > "


def print_banner():
    """Print TermSage banner"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                    🛡️  TermSage v1.0 🛡️                   ║
║            AI-Powered CTF Terminal Assistant             ║
╚══════════════════════════════════════════════════════════╝

🎯 Specialized for: CTF, pentesting, reverse engineering
🤖 AI Models: Multiple providers with automatic fallback
🔒 Safety: Built-in command validation
⚡ Performance: Smart context management & hardware detection

Starting up...
"""
    print(banner)


def check_dependencies() -> bool:
    """Check if required dependencies are available"""
    logger = get_logger(__name__)
    
    required_packages = [
        'psutil',  # For hardware detection
    ]
    
    optional_packages = {
        'ollama': 'Local AI models',
        'openai': 'OpenAI GPT models',
        'anthropic': 'Anthropic Claude models',
    }
    
    missing_required = []
    
    # Check required packages
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_required.append(package)
    
    # Report on optional packages
    available_providers = []
    for package, description in optional_packages.items():
        try:
            importlib.import_module(package)
            available_providers.append(f"✅ {description}")
        except ImportError:
            available_providers.append(f"❌ {description}")
    
    # Log provider status
    logger.info("AI Provider availability:")
    for status in available_providers:
        logger.info(f"  {status}")
    
    if missing_required:
        logger.error(f"Missing required packages: {missing_required}")
        return False
    
    return True


def find_kali_tools() -> List[str]:
    """Find available Kali Linux tools"""
    kali_tools = [
        # Network scanning
        'nmap', 'masscan', 'zmap',
        
        # Web application
        'gobuster', 'dirb', 'nikto', 'sqlmap', 'wfuzz', 'ffuf',
        
        # Exploitation
        'msfconsole', 'msfvenom', 'searchsploit',
        
        # Password attacks
        'hydra', 'john', 'hashcat',
        
        # Reverse engineering
        'gdb', 'radare2', 'r2', 'objdump', 'strings', 'file',
        
        # Forensics
        'binwalk', 'foremost', 'volatility',
        
        # Network tools
        'wireshark', 'tcpdump', 'netcat', 'nc', 'socat',
        
        # General
        'curl', 'wget', 'git', 'python3'
    ]
    
    available_tools = []
    
    for tool in kali_tools:
        if check_command_exists(tool):
            available_tools.append(tool)
    
    return available_tools


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH"""
    try:
        subprocess.run(['which', command], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def validate_ip(ip: str) -> bool:
    """Validate IP address format"""
    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(pattern, ip))


def validate_port(port: str) -> bool:
    """Validate port number"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except ValueError:
        return False


def parse_nmap_output(output: str) -> Dict[str, Any]:
    """Parse nmap output for key information"""
    result = {
        'open_ports': [],
        'services': [],
        'os_detection': None,
        'vulnerability_scripts': []
    }
    
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Parse open ports
        if '/tcp' in line or '/udp' in line:
            parts = line.split()
            if len(parts) >= 3 and 'open' in parts[1]:
                port_info = {
                    'port': parts[0],
                    'state': parts[1],
                    'service': parts[2] if len(parts) > 2 else 'unknown'
                }
                result['open_ports'].append(port_info)
                result['services'].append(parts[2] if len(parts) > 2 else 'unknown')
        
        # Parse OS detection
        if 'OS details:' in line:
            result['os_detection'] = line.replace('OS details:', '').strip()
    
    return result


def extract_flags(text: str) -> List[str]:
    """Extract CTF flags from text"""
    # Common flag patterns
    patterns = [
        r'flag\{[^}]+\}',
        r'CTF\{[^}]+\}',
        r'HTB\{[^}]+\}',
        r'ICTF\{[^}]+\}',
        r'picoCTF\{[^}]+\}',
    ]
    
    flags = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        flags.extend(matches)
    
    return list(set(flags))  # Remove duplicates


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def get_terminal_size() -> tuple:
    """Get terminal size (width, height)"""
    try:
        import shutil
        return shutil.get_terminal_size()
    except:
        return (80, 24)  # Default size


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename or 'unnamed'