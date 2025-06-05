import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

class context_manager:
    """Intelligent context manager for convo history"""
    def _init_(self, max_tokens: int = 4000): # max_tokens should be able to get changed based on user input?
