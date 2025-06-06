#!/usr/bin/env python3
"""
TermSage - AI-Powered CTF Terminal Assistant
A comprehensive terminal environment with AI assistance for CTF and security work
"""

__version__ = "1.0.0"
__author__ = "TermSage Team"
__description__ = "AI-Powered CTF Terminal Assistant"

from .agent import CTFAgent
from .ai_models import AIModelManager
from .command_handler import CommandHandler, CommandResult
from .context_manager import ContextManager
from .config import ConfigManager
from .utils import (
    get_logger,
    setup_logging,
    print_banner,
    check_dependencies,
    find_kali_tools,
    extract_flags,
    validate_ip,
    validate_port
)

__all__ = [
    'CTFAgent',
    'AIModelManager',
    'CommandHandler',
    'CommandResult',
    'ContextManager',
    'ConfigManager',
    'get_logger',
    'setup_logging',
    'print_banner',
    'check_dependencies',
    'find_kali_tools',
    'extract_flags',
    'validate_ip',
    'validate_port'
]