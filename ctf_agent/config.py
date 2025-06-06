#!/usr/bin/env python3
"""
Configuration management with hardware detection
Automatically optimizes settings based on system capabilities
"""
import os
import json
import platform
import psutil
import multiprocessing
from pathlib import Path
from typing import Dict, Any, Optional

from .utils import get_logger


class ConfigManager:
    """Manages configuration with hardware-aware defaults"""
    
    # Performance tiers based on hardware
    PERFORMANCE_TIERS = {
        'high': {
            'context': {
                'max_tokens': 8192,
                'compression_threshold': 0.85,
                'min_messages': 6
            },
            'command': {
                'timeout': 60,
                'max_output_size': 500000,
                'allow_sudo': False
            },
            'ai': {
                'provider_priority': ['ollama', 'anthropic', 'openai', 'gemini'],
                'stream': True,
                'retry_count': 3
            },
            'recommended_models': [
                'ollama:llama3.2:3b',
                'ollama:deepseek-coder:6.7b',
                'ollama:codellama:7b'
            ]
        },
        'medium': {
            'context': {
                'max_tokens': 4096,
                'compression_threshold': 0.75,
                'min_messages': 4
            },
            'command': {
                'timeout': 45,
                'max_output_size': 200000,
                'allow_sudo': False
            },
            'ai': {
                'provider_priority': ['ollama', 'openai', 'anthropic'],
                'stream': True,
                'retry_count': 2
            },
            'recommended_models': [
                'ollama:llama3.2:1b',
                'ollama:phi3:mini',
                'ollama:gemma:2b'
            ]
        },
        'basic': {
            'context': {
                'max_tokens': 2048,
                'compression_threshold': 0.7,
                'min_messages': 3
            },
            'command': {
                'timeout': 30,
                'max_output_size': 100000,
                'allow_sudo': False
            },
            'ai': {
                'provider_priority': ['ollama', 'openai'],
                'stream': True,
                'retry_count': 1
            },
            'recommended_models': [
                'ollama:llama3.2:1b',
                'ollama:tinyllama:1.1b'
            ]
        },
        'minimal': {
            'context': {
                'max_tokens': 1024,
                'compression_threshold': 0.6,
                'min_messages': 2
            },
            'command': {
                'timeout': 20,
                'max_output_size': 50000,
                'allow_sudo': False
            },
            'ai': {
                'provider_priority': ['ollama'],
                'stream': True,
                'retry_count': 1
            },
            'recommended_models': [
                'ollama:tinyllama:1.1b'
            ]
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        self.logger = get_logger(__name__)
        self.config_path = config_path or self._get_default_config_path()
        self.config = {}
        
        # Detect hardware
        self.hardware_info = self._detect_hardware()
        self.performance_tier = self._determine_performance_tier()
        
        # Load configuration
        self._load_config()
        
        self.logger.info(f"Config initialized - Performance tier: {self.performance_tier}")
    
    def _get_default_config_path(self) -> Path:
        """Get default configuration file path"""
        # Try multiple locations
        locations = [
            Path.home() / '.config' / 'termsage' / 'config.json',
            Path.home() / '.termsage' / 'config.json',
            Path('./config/termsage.json'),
            Path('./termsage.json')
        ]
        
        # Return first existing or first option
        for path in locations:
            if path.exists():
                return path
        
        # Create default location
        default = locations[0]
        default.parent.mkdir(parents=True, exist_ok=True)
        return default
    
    def _detect_hardware(self) -> Dict[str, Any]:
        """Detect system hardware capabilities"""
        hardware = {
            'cpu': {
                'cores': multiprocessing.cpu_count(),
                'physical_cores': psutil.cpu_count(logical=False),
                'frequency': 0
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'total_gb': round(psutil.virtual_memory().total / (1024**3), 2)
            },
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'python_version': platform.python_version()
            }
        }
        
        # Try to get CPU frequency
        try:
            freq = psutil.cpu_freq()
            if freq:
                hardware['cpu']['frequency'] = freq.current
        except:
            pass
        
        # Check for GPU (basic check)
        hardware['gpu'] = self._detect_gpu()
        
        self.logger.info(f"Hardware detected: {hardware['cpu']['cores']} cores, {hardware['memory']['total_gb']}GB RAM")
        
        return hardware
    
    def _detect_gpu(self) -> Dict[str, Any]:
        """Basic GPU detection"""
        gpu_info = {'available': False, 'type': 'none'}
        
        try:
            # Check for NVIDIA
            nvidia_check = os.popen('nvidia-smi --query-gpu=name --format=csv,noheader').read().strip()
            if nvidia_check:
                gpu_info = {'available': True, 'type': 'nvidia', 'name': nvidia_check}
                return gpu_info
        except:
            pass
        
        try:
            # Check for AMD
            amd_check = os.popen('rocm-smi --showproductname').read().strip()
            if 'GPU' in amd_check:
                gpu_info = {'available': True, 'type': 'amd'}
                return gpu_info
        except:
            pass
        
        # Check for Apple Silicon
        if platform.system() == 'Darwin' and platform.machine() == 'arm64':
            gpu_info = {'available': True, 'type': 'apple_silicon'}
        
        return gpu_info
    
    def _determine_performance_tier(self) -> str:
        """Determine performance tier based on hardware"""
        cpu_cores = self.hardware_info['cpu']['cores']
        ram_gb = self.hardware_info['memory']['total_gb']
        has_gpu = self.hardware_info['gpu']['available']
        
        # High tier: 8+ cores, 16GB+ RAM, or GPU
        if (cpu_cores >= 8 and ram_gb >= 16) or has_gpu:
            return 'high'
        
        # Medium tier: 4+ cores, 8GB+ RAM
        elif cpu_cores >= 4 and ram_gb >= 8:
            return 'medium'
        
        # Basic tier: 2+ cores, 4GB+ RAM
        elif cpu_cores >= 2 and ram_gb >= 4:
            return 'basic'
        
        # Minimal tier: Everything else
        else:
            return 'minimal'
    
    def _load_config(self):
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.logger.info(f"Loaded config from: {self.config_path}")
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
                self.config = {}
        
        # Apply defaults based on performance tier
        tier_defaults = self.PERFORMANCE_TIERS[self.performance_tier].copy()
        
        # Merge with loaded config (loaded config takes precedence)
        self.config = self._merge_configs(tier_defaults, self.config)
        
        # Add hardware info and tier
        self.config['hardware'] = self.hardware_info
        self.config['performance_tier'] = self.performance_tier
        
        # Set default model based on tier
        if 'default_model' not in self.config:
            self.config['default_model'] = tier_defaults['recommended_models'][0]
        
        # Save config
        self._save_config()
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configurations"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _save_config(self):
        """Save current configuration to file"""
        try:
            # Create directory if needed
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save config
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.info(f"Saved config to: {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration values"""
        self.config = self._merge_configs(self.config, updates)
        self._save_config()
    
    def get_recommended_models(self) -> list:
        """Get recommended models for this system"""
        return self.PERFORMANCE_TIERS[self.performance_tier]['recommended_models']
    
    def print_system_info(self):
        """Print system information"""
        print(f"""
🖥️  System Information:
  CPU: {self.hardware_info['cpu']['cores']} cores ({self.hardware_info['cpu']['physical_cores']} physical)
  RAM: {self.hardware_info['memory']['total_gb']} GB
  GPU: {self.hardware_info['gpu']['type']}
  Platform: {self.hardware_info['platform']['system']} {self.hardware_info['platform']['machine']}
  
⚡ Performance Tier: {self.performance_tier.upper()}
  Max Context: {self.config['context']['max_tokens']} tokens
  Recommended Models: {', '.join(self.get_recommended_models())}
""")