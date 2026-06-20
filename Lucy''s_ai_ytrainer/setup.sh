#!/bin/bash
# Ollama Coding Agent Installer Wizard for Unix/macOS
PROJECT_NAME="Ollama-Coding-Agent"
echo "=========================================="
echo "      OLLAMA CODING AGENT SYSTEM SETUP    "
echo "      Setting up: $PROJECT_NAME"
echo "=========================================="

# 1. Verify Python
if command -v python3 >/dev/null 2>&1; then
    echo "[OK] $(python3 --version) detected."
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    echo "[OK] $(python --version) detected."
    PYTHON_CMD="python"
else
    echo "[ERROR] Python is missing! Please install Python 3.10+ and add it to your PATH."
    exit 1
fi

# 2. Verify Ollama
if command -v ollama >/dev/null 2>&1; then
    echo "[OK] $(ollama --version) detected."
else
    echo "[WARNING] Ollama CLI is missing! Please install Ollama from https://ollama.com/"
fi

# 3. Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[STEP] Creating Python Virtual Environment (.venv)..."
    $PYTHON_CMD -m venv .venv
else
    echo "[OK] Virtual environment exists."
fi

# 4. Install Dependencies
echo "[STEP] Installing dependencies from requirements.txt..."
source .venv/bin/activate
pip install -r requirements.txt

# 5. Check if Ollama is running and build the model
echo "[STEP] Building Ollama custom model 'ollama-coder'..."
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "[STEP] Ensuring base model is copied (avoiding Windows path colon bug)..."
    ollama cp gemma3:1b gemma3-local >/dev/null 2>&1
    echo "[STEP] Running 'ollama create ollama-coder -f Modelfile'..."
    ollama create ollama-coder -f Modelfile
    echo "[OK] Custom model 'ollama-coder' successfully registered!"
else
    echo "[WARNING] Ollama server is not running. Attempting to start in background..."
    ollama serve >/dev/null 2>&1 &
    sleep 3
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "[STEP] Ensuring base model is copied (avoiding Windows path colon bug)..."
        ollama cp gemma3:1b gemma3-local >/dev/null 2>&1
        ollama create ollama-coder -f Modelfile
        echo "[OK] Custom model 'ollama-coder' successfully registered!"
    else
        echo "[WARNING] Could not connect to Ollama. Skipping model building."
        echo "[INFO] You can build it manually later with: ollama create ollama-coder -f Modelfile"
    fi
fi

echo "=========================================="
echo " SETUP COMPLETE: Launching Coding Agent..."
echo "=========================================="

python agent.py "$@"
