#!/usr/bin/env python3
"""
Tests for utility functions
"""
import pytest
from ctf_agent.utils import (
    validate_ip, validate_port, extract_flags, 
    parse_nmap_output, estimate_tokens, format_file_size
)


class TestUtils:
    """Test cases for utility functions"""
    
    def test_validate_ip(self):
        """Test IP address validation"""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "127.0.0.1",
            "255.255.255.255",
            "0.0.0.0"
        ]
        
        invalid_ips = [
            "256.1.1.1",
            "192.168.1",
            "192.168.1.1.1",
            "abc.def.ghi.jkl",
            ""
        ]
        
        for ip in valid_ips:
            assert validate_ip(ip), f"Should be valid: {ip}"
        
        for ip in invalid_ips:
            assert not validate_ip(ip), f"Should be invalid: {ip}"
    
    def test_validate_port(self):
        """Test port validation"""
        valid_ports = ["1", "80", "443", "8080", "65535"]
        invalid_ports = ["0", "65536", "abc", "", "-1"]
        
        for port in valid_ports:
            assert validate_port(port), f"Should be valid: {port}"
        
        for port in invalid_ports:
            assert not validate_port(port), f"Should be invalid: {port}"
    
    def test_extract_flags(self):
        """Test flag extraction"""
        text = """
        Found multiple flags:
        flag{first_flag_here}
        CTF{second_flag}
        HTB{third_flag}
        picoCTF{fourth_flag}
        """
        
        flags = extract_flags(text)
        
        assert len(flags) >= 4
        assert "flag{first_flag_here}" in flags
        assert "CTF{second_flag}" in flags
        assert "HTB{third_flag}" in flags
        assert "picoCTF{fourth_flag}" in flags
    
    def test_parse_nmap_output(self):
        """Test nmap output parsing"""
        nmap_output = """
        22/tcp   open  ssh     OpenSSH 8.0
        80/tcp   open  http    Apache httpd 2.4.41
        443/tcp  open  https   Apache httpd 2.4.41
        3306/tcp open  mysql   MySQL 8.0.25
        """
        
        result = parse_nmap_output(nmap_output)
        
        assert len(result['open_ports']) == 4
        assert 'ssh' in result['services']
        assert 'http' in result['services']
        assert 'mysql' in result['services']
    
    def test_estimate_tokens(self):
        """Test token estimation"""
        short_text = "Hello"
        long_text = "This is a much longer text with many more words to test token estimation"
        
        short_tokens = estimate_tokens(short_text)
        long_tokens = estimate_tokens(long_text)
        
        assert short_tokens > 0
        assert long_tokens > short_tokens
        assert short_tokens < 5  # Should be small for short text
    
    def test_format_file_size(self):
        """Test file size formatting"""
        test_cases = [
            (0, "0B"),
            (1023, "1023.0B"),
            (1024, "1.0KB"),
            (1024 * 1024, "1.0MB"),
            (1024 * 1024 * 1024, "1.0GB")
        ]
        
        for size_bytes, expected in test_cases:
            result = format_file_size(size_bytes)
            assert result == expected, f"Expected {expected}, got {result}"