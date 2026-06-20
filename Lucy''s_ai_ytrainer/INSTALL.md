# Ollama Coding Agent Installer Guide

This guide describes how to configure the coding agent dependencies, build the custom Ollama model, and start the agent interface.

## Prerequisites
- **Python 3.10+** (Ensure it is added to your environment `PATH`)
- **Ollama** installed and running (from [ollama.com](https://ollama.com))

## Quick Start

### Windows
Run the PowerShell script wrapper:
```powershell
.\start.bat
```
Or run the PowerShell script directly:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### macOS / Linux
Run the shell script installer:
```bash
chmod +x setup.sh
./setup.sh
```

## What the Installer Does
1. Checks for Python and Ollama CLI.
2. Allocates a Python Virtual Environment (`.venv`) locally.
3. Installs requirements from `requirements.txt`.
4. Contacts Ollama and registers the custom `ollama-coder` model using the local `Modelfile`.
5. Launches the interactive command-line agent (`agent.py`).
