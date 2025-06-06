#!/usr/bin/env python3
"""
Multi-provider AI model management
Supports Ollama (local), OpenAI, Anthropic, Google Gemini with automatic fallback
"""
import os
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
import json

from .utils import get_logger

# Try importing various AI libraries
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], model: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """Send chat messages and get response"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class OllamaProvider(AIProvider):
    """Ollama provider for local models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(f"{__name__}.Ollama")
        self.config = config
        self.client = None
        
        if OLLAMA_AVAILABLE:
            try:
                self.client = ollama.Client()
                self.logger.info("Ollama provider initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Ollama: {e}")
    
    async def chat(self, messages: List[Dict[str, str]], model: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """Chat with Ollama model"""
        if not self.client:
            raise Exception("Ollama not available")
        
        try:
            response = self.client.chat(
                model=model,
                messages=messages,
                stream=stream
            )
            
            if stream:
                for chunk in response:
                    yield chunk['message']['content']
            else:
                yield response['message']['content']
                
        except Exception as e:
            self.logger.error(f"Ollama chat error: {e}")
            raise
    
    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        if not self.client:
            return []
        
        try:
            response = self.client.list()
            models = []
            
            if hasattr(response, 'models'):
                for model in response.models:
                    if hasattr(model, 'model'):
                        models.append(model.model)
                    elif hasattr(model, 'name'):
                        models.append(model.name)
            
            return models
        except Exception as e:
            self.logger.error(f"Failed to list Ollama models: {e}")
            return []
    
    async def is_available(self) -> bool:
        """Check if Ollama is available"""
        return self.client is not None and len(await self.list_models()) > 0


class OpenAIProvider(AIProvider):
    """OpenAI provider for GPT models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(f"{__name__}.OpenAI")
        self.config = config
        self.client = None
        
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY') or config.get('openai', {}).get('api_key')
            if api_key:
                openai.api_key = api_key
                self.client = openai
                self.logger.info("OpenAI provider initialized")
            else:
                self.logger.warning("OpenAI API key not found")
    
    async def chat(self, messages: List[Dict[str, str]], model: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """Chat with OpenAI model"""
        if not self.client:
            raise Exception("OpenAI not available")
        
        try:
            response = await asyncio.to_thread(
                self.client.ChatCompletion.create,
                model=model,
                messages=messages,
                stream=stream
            )
            
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield response.choices[0].message.content
                
        except Exception as e:
            self.logger.error(f"OpenAI chat error: {e}")
            raise
    
    async def list_models(self) -> List[str]:
        """List available OpenAI models"""
        # Return commonly available models
        return ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"]
    
    async def is_available(self) -> bool:
        """Check if OpenAI is available"""
        return self.client is not None


class AIModelManager:
    """Manages multiple AI providers with fallback"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config
        self.providers: Dict[str, AIProvider] = {}
        
        # Initialize providers
        self._init_providers()
        
        # Set provider priority
        self.provider_priority = config.get('ai', {}).get('provider_priority', [
            'ollama',  # Local first for privacy
            'anthropic',
            'openai',
            'gemini'
        ])
        
        self.logger.info(f"AI Model Manager initialized with providers: {list(self.providers.keys())}")
    
    def _init_providers(self):
        """Initialize available providers"""
        # Ollama (local models)
        if OLLAMA_AVAILABLE:
            self.providers['ollama'] = OllamaProvider(self.config)
        
        # OpenAI
        if OPENAI_AVAILABLE:
            self.providers['openai'] = OpenAIProvider(self.config)
        
        # Add more providers as needed...
    
    async def chat(self, messages: List[Dict[str, str]], model: str = None, stream: bool = True) -> AsyncGenerator[str, None]:
        """Chat with AI using specified or best available model"""
        # Parse model specification (provider:model)
        if model and ':' in model:
            provider_name, model_name = model.split(':', 1)
        else:
            provider_name = None
            model_name = model or self.config.get('default_model', 'llama3.2:1b')
        
        # Try specified provider first
        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
            if await provider.is_available():
                try:
                    async for chunk in provider.chat(messages, model_name, stream):
                        yield chunk
                    return
                except Exception as e:
                    self.logger.warning(f"Provider {provider_name} failed: {e}")
        
        # Fallback to other providers
        for provider_name in self.provider_priority:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if await provider.is_available():
                    try:
                        # Use default model for this provider if needed
                        if not model_name:
                            model_name = self._get_default_model(provider_name)
                        
                        async for chunk in provider.chat(messages, model_name, stream):
                            yield chunk
                        return
                    except Exception as e:
                        self.logger.warning(f"Provider {provider_name} failed: {e}")
                        continue
        
        raise Exception("No AI providers available")
    
    async def list_models(self) -> Dict[str, List[str]]:
        """List all available models from all providers"""
        models = {}
        
        for name, provider in self.providers.items():
            if await provider.is_available():
                provider_models = await provider.list_models()
                if provider_models:
                    models[name] = provider_models
        
        return models
    
    async def is_available(self) -> bool:
        """Check if any AI provider is available"""
        for provider in self.providers.values():
            if await provider.is_available():
                return True
        return False
    
    async def check_availability(self) -> bool:
        """Check and report AI availability"""
        available_count = 0
        
        for name, provider in self.providers.items():
            if await provider.is_available():
                available_count += 1
                self.logger.info(f" {name} provider available")
            else:
                self.logger.info(f"L {name} provider not available")
        
        return available_count > 0
    
    async def is_model_available(self, model_spec: str) -> bool:
        """Check if a specific model is available"""
        if ':' not in model_spec:
            # Check all providers
            for provider in self.providers.values():
                models = await provider.list_models()
                if model_spec in models:
                    return True
        else:
            # Check specific provider
            provider_name, model_name = model_spec.split(':', 1)
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                models = await provider.list_models()
                return model_name in models
        
        return False
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for a provider"""
        defaults = {
            'ollama': 'llama3.2:1b',
            'openai': 'gpt-3.5-turbo',
            'anthropic': 'claude-3-sonnet',
            'gemini': 'gemini-pro'
        }
        return defaults.get(provider, 'default')