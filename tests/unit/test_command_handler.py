#!/usr/bin/env python3
"""
Tests for CommandHandler
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from ctf_agent.command_handler import CommandHandler, CommandResult


class TestCommandHandler:
    """Test cases for CommandHandler"""
    
    def setup_method(self):
        """Setup test configuration"""
        self.config = {
            'command': {
                'timeout': 30,
                'max_output_size': 1000,
                'allow_sudo': False,
                'working_dir': '/tmp'
            }
        }
        self.handler = CommandHandler(self.config)
    
    def test_dangerous_command_detection(self):
        """Test detection of dangerous commands"""
        dangerous_commands = [
            'rm -rf /',
            'dd if=/dev/zero of=/dev/sda',
            'chmod -R 000 /',
            ':(){ :|:& };:',  # Fork bomb
            'sudo rm -rf /'
        ]
        
        for cmd in dangerous_commands:
            validation = self.handler._validate_command(cmd)
            assert not validation['safe'], f"Command should be blocked: {cmd}"
    
    def test_safe_command_detection(self):
        """Test detection of safe commands"""
        safe_commands = [
            'ls -la',
            'nmap -sV 192.168.1.1',
            'python3 script.py',
            'curl https://example.com',
            'echo "test"'
        ]
        
        for cmd in safe_commands:
            validation = self.handler._validate_command(cmd)
            assert validation['safe'], f"Command should be allowed: {cmd}"
    
    def test_ctf_tool_allowance(self):
        """Test that CTF tools are always allowed"""
        ctf_commands = [
            'nmap -A -T5 target.com',
            'gobuster dir -u http://target.com -w /usr/share/wordlists/common.txt',
            'sqlmap -u "http://target.com/page?id=1" --dump',
            'hydra -l admin -P passwords.txt ssh://target.com'
        ]
        
        for cmd in ctf_commands:
            validation = self.handler._validate_command(cmd)
            assert validation['safe'], f"CTF command should be allowed: {cmd}"
    
    @pytest.mark.asyncio
    async def test_command_execution_success(self):
        """Test successful command execution"""
        result = await self.handler.execute('echo "test"')
        
        assert result.success
        assert "test" in result.output
        assert result.return_code == 0
    
    @pytest.mark.asyncio
    async def test_command_execution_failure(self):
        """Test failed command execution"""
        result = await self.handler.execute('false')  # Command that always fails
        
        assert not result.success
        assert result.return_code != 0
    
    @pytest.mark.asyncio
    async def test_dangerous_command_blocking(self):
        """Test that dangerous commands are blocked"""
        result = await self.handler.execute('rm -rf /')
        
        assert not result.success
        assert "blocked" in result.error.lower()
        assert result.return_code == -1
    
    def test_sudo_blocking_when_disabled(self):
        """Test sudo commands are blocked when disabled"""
        validation = self.handler._validate_command('sudo apt update')
        assert not validation['safe']
    
    def test_safe_commands_list(self):
        """Test getting safe commands list"""
        safe_commands = self.handler.get_safe_commands()
        assert 'nmap' in safe_commands
        assert 'gobuster' in safe_commands
        assert 'hydra' in safe_commands
    
    def test_add_safe_command(self):
        """Test adding new safe command"""
        self.handler.add_safe_command('custom-tool')
        safe_commands = self.handler.get_safe_commands()
        assert 'custom-tool' in safe_commands