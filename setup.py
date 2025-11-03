from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="elevenlabs-mcp",
    version="0.9.0",
    author="ElevenLabs Team",
    author_email="jacek@elevenlabs.io",
    description="MCP server for ElevenLabs conversational AI agents and voice technology",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/elevenlabs/elevenlabs-mcp",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=[
        "elevenlabs>=1.0.0",
        "fastmcp>=0.2.0",
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "fuzzywuzzy>=0.18.0",
        "python-levenshtein>=0.21.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "elevenlabs-mcp=elevenlabs_mcp.server:main",
        ],
    },
)
