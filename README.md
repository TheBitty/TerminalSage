# 🛡️ TermSage - AI-Powered CTF Terminal Assistant

TermSage is a comprehensive AI-powered terminal environment specifically designed for CTF competitions, penetration testing, and cybersecurity research. It combines intelligent command execution with multi-provider AI integration to help security professionals work more efficiently.

## ✨ Key Features

- **🤖 Multi-AI Integration**: Supports Ollama (local), OpenAI, Anthropic, Google Gemini with automatic fallback
- **🎯 CTF-Specialized**: Built-in knowledge of security tools and techniques
- **🔒 Safety-First**: Smart command validation prevents dangerous operations
- **⚡ Performance-Adaptive**: Hardware detection with automatic optimization
- **🧠 Smart Context**: CTF-aware conversation management and finding extraction
- **🛠️ Tool Integration**: Works seamlessly with all Kali Linux security tools

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Ollama for local AI (recommended)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:1b

# Run TermSage
python3 main.py
```

## 💻 Usage Examples

```bash
# Get AI help for any command
⚡ > nmap?
📚 AI explains nmap usage for CTF scenarios

# Execute commands with automatic failure analysis
⚡ > gobuster dir -u http://target.com -w wordlist.txt
[If it fails, AI automatically provides troubleshooting]

# Chat mode for strategy discussions
⚡ > /chat
🤖 chat> I found SSH on port 22 and HTTP on 80. What should I try next?

# Session management
⚡ > /save my_ctf_session.json
⚡ > /load my_ctf_session.json
```

## 🎯 Built for CTF Professionals

- Automatic flag extraction and tracking
- Vulnerability pattern recognition  
- Exploit technique suggestions
- Network enumeration guidance
- Password attack strategies
- Binary analysis assistance

## 📦 Installation

See detailed installation and configuration in the setup guide.

## 🤝 Contributing

We welcome contributions! Please ensure all changes include tests and follow the existing code style.

## 📄 License

MIT License - see LICENSE for details.

---

**⚠️ For authorized security testing and CTF competitions only**