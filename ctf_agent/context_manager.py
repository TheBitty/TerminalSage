#!/usr/bin/env python3
"""
Smart context management for CTF conversations
Handles compression, prioritization, and CTF-specific importance
"""
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque

from .utils import get_logger, estimate_tokens


class ContextManager:
    """Intelligent context manager for conversation history"""
    
    # CTF-specific patterns to prioritize
    CTF_PATTERNS = {
        'flag': re.compile(r'(flag\{[^}]+\}|CTF\{[^}]+\}|HTB\{[^}]+\})', re.I),
        'exploit': re.compile(r'(exploit|payload|shellcode|buffer overflow|SQL injection)', re.I),
        'vulnerability': re.compile(r'(CVE-\d{4}-\d+|vulnerability|vuln|RCE|LFI|XSS|SSRF)', re.I),
        'credentials': re.compile(r'(password|username|creds|token|api[_\s]?key)', re.I),
        'ip_port': re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'),
        'hash': re.compile(r'([a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64})'),
        'command': re.compile(r'(nmap|gobuster|hydra|sqlmap|burp|metasploit|john|hashcat)', re.I),
        'discovery': re.compile(r'(found|discovered|detected|vulnerable|exposed|open port)', re.I)
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize context manager with configuration"""
        self.logger = get_logger(__name__)
        self.config = config
        
        # Context settings
        self.max_tokens = config.get('context', {}).get('max_tokens', 4000)
        self.compression_threshold = config.get('context', {}).get('compression_threshold', 0.8)
        self.min_messages = config.get('context', {}).get('min_messages', 4)
        
        # Message storage
        self.messages: List[Dict[str, Any]] = []
        self.compressed_summary: Optional[str] = None
        
        # CTF-specific tracking
        self.important_findings: List[Dict[str, Any]] = []
        self.discovered_flags: List[str] = []
        self.exploits: List[str] = []
        
        # System prompt for CTF focus
        self.system_prompt = {
            "role": "system",
            "content": """You are TermSage, a specialized CTF (Capture The Flag) assistant.
Your expertise includes:
- Penetration testing and exploitation techniques
- Reverse engineering and binary analysis
- Web application security testing
- Cryptography and steganography
- Network analysis and enumeration
- Common CTF tools (nmap, burp suite, gdb, radare2, etc.)

Always provide practical, actionable advice focused on CTF challenges.
Prioritize security and ethical hacking practices."""
        }
        
        self.logger.info("Context manager initialized")
    
    def add_message(self, role: str, content: str):
        """Add a message to context with importance scoring"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "importance": self._calculate_importance(content),
            "tokens": estimate_tokens(content)
        }
        
        self.messages.append(message)
        
        # Extract CTF-specific findings
        self._extract_findings(content)
        
        self.logger.debug(f"Added {role} message with importance {message['importance']}")
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get messages for AI consumption"""
        # Always include system prompt
        messages = [self.system_prompt]
        
        # Add compressed summary if exists
        if self.compressed_summary:
            messages.append({
                "role": "system",
                "content": f"Previous conversation summary:\n{self.compressed_summary}"
            })
        
        # Add recent messages
        for msg in self.messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def should_compress(self) -> bool:
        """Check if context should be compressed"""
        total_tokens = sum(msg.get('tokens', 0) for msg in self.messages)
        return total_tokens > (self.max_tokens * self.compression_threshold)
    
    def compress(self):
        """Compress context while preserving CTF-critical information"""
        if len(self.messages) <= self.min_messages:
            return
        
        self.logger.info("Compressing context to maintain performance")
        
        # Separate messages by importance
        critical_messages = []
        normal_messages = []
        
        for msg in self.messages:
            if msg.get('importance', 0) >= 0.7:
                critical_messages.append(msg)
            else:
                normal_messages.append(msg)
        
        # Create summary of normal messages
        summary_parts = []
        
        # Add discovered flags
        if self.discovered_flags:
            summary_parts.append(f"Discovered flags: {', '.join(self.discovered_flags)}")
        
        # Add key exploits
        if self.exploits:
            summary_parts.append(f"Successful exploits: {', '.join(self.exploits[:5])}")
        
        # Add important findings
        if self.important_findings:
            findings = [f["summary"] for f in self.important_findings[:10]]
            summary_parts.append(f"Key findings: {'; '.join(findings)}")
        
        # Summarize normal messages
        if normal_messages:
            topics = self._extract_topics(normal_messages)
            summary_parts.append(f"Discussed topics: {', '.join(topics)}")
        
        self.compressed_summary = "\n".join(summary_parts)
        
        # Keep only recent critical messages
        self.messages = critical_messages[-self.min_messages:]
        
        self.logger.info(f"Compressed {len(normal_messages)} messages, kept {len(self.messages)} critical ones")
    
    def _calculate_importance(self, content: str) -> float:
        """Calculate message importance for CTF context"""
        importance = 0.5  # Base importance
        
        # Check for CTF patterns
        for pattern_name, pattern in self.CTF_PATTERNS.items():
            if pattern.search(content):
                if pattern_name == 'flag':
                    importance = 1.0  # Flags are always critical
                elif pattern_name in ['exploit', 'vulnerability']:
                    importance = max(importance, 0.9)
                elif pattern_name in ['credentials', 'discovery']:
                    importance = max(importance, 0.8)
                else:
                    importance = max(importance, 0.7)
        
        # Boost importance for code blocks
        if '```' in content or '    ' in content:
            importance = max(importance, 0.7)
        
        # Boost for specific tools mentioned
        tool_count = len(self.CTF_PATTERNS['command'].findall(content))
        if tool_count > 0:
            importance = max(importance, 0.6 + (tool_count * 0.1))
        
        return min(importance, 1.0)
    
    def _extract_findings(self, content: str):
        """Extract CTF-specific findings from content"""
        # Extract flags
        flags = self.CTF_PATTERNS['flag'].findall(content)
        for flag in flags:
            if flag not in self.discovered_flags:
                self.discovered_flags.append(flag)
                self.important_findings.append({
                    "type": "flag",
                    "value": flag,
                    "summary": f"Flag found: {flag}",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Extract exploits
        if self.CTF_PATTERNS['exploit'].search(content):
            exploit_summary = content[:100] + "..." if len(content) > 100 else content
            self.exploits.append(exploit_summary)
        
        # Extract IPs and ports
        ip_matches = self.CTF_PATTERNS['ip_port'].findall(content)
        for ip in ip_matches:
            self.important_findings.append({
                "type": "network",
                "value": ip,
                "summary": f"Network target: {ip}",
                "timestamp": datetime.now().isoformat()
            })
    
    def _extract_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract main topics from messages"""
        topics = set()
        
        for msg in messages:
            content = msg.get('content', '')
            
            # Extract tool names
            tools = self.CTF_PATTERNS['command'].findall(content)
            topics.update(tools)
            
            # Extract vulnerability types
            vulns = self.CTF_PATTERNS['vulnerability'].findall(content)
            topics.update(vulns)
            
            # Add general categories
            if 'web' in content.lower():
                topics.add('web exploitation')
            if 'reverse' in content.lower():
                topics.add('reverse engineering')
            if 'crypto' in content.lower():
                topics.add('cryptography')
            if 'forensics' in content.lower():
                topics.add('forensics')
        
        return list(topics)[:5]  # Return top 5 topics
    
    def clear(self):
        """Clear all context"""
        self.messages.clear()
        self.compressed_summary = None
        self.logger.info("Context cleared")
    
    def set_messages(self, messages: List[Dict[str, Any]]):
        """Set messages from saved session"""
        self.messages = []
        for msg in messages:
            if msg.get('role') != 'system':  # Skip system messages
                self.add_message(msg['role'], msg['content'])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics"""
        total_tokens = sum(msg.get('tokens', 0) for msg in self.messages)
        
        return {
            "message_count": len(self.messages),
            "total_tokens": total_tokens,
            "compression_ratio": total_tokens / self.max_tokens,
            "discovered_flags": len(self.discovered_flags),
            "exploits_found": len(self.exploits),
            "important_findings": len(self.important_findings)
        }
    
    def export_findings(self) -> Dict[str, Any]:
        """Export all CTF findings"""
        return {
            "flags": self.discovered_flags,
            "exploits": self.exploits,
            "findings": self.important_findings,
            "stats": self.get_stats()
        }