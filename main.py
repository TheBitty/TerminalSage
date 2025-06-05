#!/usr/bin/env python3
# ctf-agent.py
import asyncio
import sys
import os
import subprocess
import readline
import atexit
from pathlib import Path
from typing import Optional, List
import ollama

class TermAgent:
    def _init_(self):
        self.chat_mode = False # our switch to enable model chat... agent will always start in command mode 
        self.ollama_client = ollama.Client()
        self.model = None
        self.available_models = [] # will get populated through (ollama list ) command 
        self.chat_history = [] # this needs to be watched! overload this and it will slow down the agent!!!
        self.setup_readline()

    def setup_readline(self):
    
