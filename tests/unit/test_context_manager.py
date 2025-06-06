#!/usr/bin/env python3
"""
Tests for ContextManager
"""
import pytest
from ctf_agent.context_manager import ContextManager


class TestContextManager:
    """Test cases for ContextManager"""
    
    def setup_method(self):
        """Setup test configuration"""
        self.config = {
            'context': {
                'max_tokens': 1000,
                'compression_threshold': 0.8,
                'min_messages': 3
            }
        }
        self.manager = ContextManager(self.config)
    
    def test_add_message(self):
        """Test adding messages to context"""
        self.manager.add_message("user", "Hello")
        self.manager.add_message("assistant", "Hi there!")
        
        messages = self.manager.get_messages()
        # Should have system prompt + 2 messages
        assert len(messages) >= 3
    
    def test_importance_calculation(self):
        """Test CTF importance scoring"""
        # Flag should have highest importance
        flag_importance = self.manager._calculate_importance("I found flag{test123}")
        assert flag_importance == 1.0
        
        # Exploit should have high importance
        exploit_importance = self.manager._calculate_importance("Found SQL injection vulnerability")
        assert exploit_importance >= 0.9
        
        # Normal text should have base importance
        normal_importance = self.manager._calculate_importance("This is normal text")
        assert normal_importance == 0.5
    
    def test_flag_extraction(self):
        """Test flag extraction from content"""
        content = "Found the flag: flag{test123} in the database"
        self.manager.add_message("user", content)
        
        assert "flag{test123}" in self.manager.discovered_flags
        assert len(self.manager.important_findings) > 0
    
    def test_ip_extraction(self):
        """Test IP extraction from content"""
        content = "Target server is at 192.168.1.100:80"
        self.manager.add_message("user", content)
        
        # Check if IP was extracted as finding
        ip_findings = [f for f in self.manager.important_findings if f['type'] == 'network']
        assert len(ip_findings) > 0
    
    def test_context_compression(self):
        """Test context compression"""
        # Add many messages to trigger compression
        for i in range(20):
            self.manager.add_message("user", f"Message {i} with some content")
            self.manager.add_message("assistant", f"Response {i}")
        
        # Should trigger compression
        if self.manager.should_compress():
            initial_count = len(self.manager.messages)
            self.manager.compress()
            final_count = len(self.manager.messages)
            
            assert final_count < initial_count
            assert self.manager.compressed_summary is not None
    
    def test_ctf_patterns(self):
        """Test CTF pattern recognition"""
        test_cases = [
            ("flag{test123}", "flag"),
            ("CVE-2023-1234", "vulnerability"),
            ("192.168.1.1", "ip_port"),
            ("exploit payload", "exploit"),
            ("username: admin, password: test", "credentials"),
            ("nmap scan results", "command")
        ]
        
        for content, expected_pattern in test_cases:
            pattern = self.manager.CTF_PATTERNS[expected_pattern]
            assert pattern.search(content), f"Pattern {expected_pattern} should match {content}"
    
    def test_clear_context(self):
        """Test clearing context"""
        self.manager.add_message("user", "Test message")
        self.manager.clear()
        
        assert len(self.manager.messages) == 0
        assert self.manager.compressed_summary is None
    
    def test_export_findings(self):
        """Test exporting CTF findings"""
        self.manager.add_message("user", "Found flag{test123} at 192.168.1.1")
        
        findings = self.manager.export_findings()
        
        assert 'flags' in findings
        assert 'findings' in findings
        assert 'stats' in findings
        assert len(findings['flags']) > 0
    
    def test_stats_generation(self):
        """Test statistics generation"""
        self.manager.add_message("user", "Test message")
        
        stats = self.manager.get_stats()
        
        assert 'message_count' in stats
        assert 'total_tokens' in stats
        assert 'compression_ratio' in stats
        assert stats['message_count'] > 0