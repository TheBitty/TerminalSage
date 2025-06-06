#!/usr/bin/env python3
"""
Setup script for TermSage
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
init_file = Path(__file__).parent / "ctf_agent" / "__init__.py"
version = "1.0.0"
for line in init_file.read_text().split('\n'):
    if line.startswith('__version__'):
        version = line.split('=')[1].strip().strip('"\'')
        break

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = "TermSage - AI-Powered CTF Terminal Assistant"
if readme_file.exists():
    long_description = readme_file.read_text()

setup(
    name="termsage",
    version=version,
    author="TermSage Team",
    author_email="contact@termsage.dev",
    description="AI-Powered CTF Terminal Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/termsage/termsage",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
    ],
    extras_require={
        "ai": [
            "ollama>=0.1.0",
            "openai>=1.0.0",
            "anthropic>=0.8.0",
            "google-generativeai>=0.3.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "coverage>=7.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
        "all": [
            "ollama>=0.1.0",
            "openai>=1.0.0",
            "anthropic>=0.8.0",
            "google-generativeai>=0.3.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "coverage>=7.0.0",
            "sphinx>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "termsage=main:main",
            "ts=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords="ctf security penetration-testing ai terminal assistant hacking",
    project_urls={
        "Bug Reports": "https://github.com/termsage/termsage/issues",
        "Source": "https://github.com/termsage/termsage",
        "Documentation": "https://termsage.readthedocs.io/",
    },
)