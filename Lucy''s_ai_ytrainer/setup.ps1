# Ollama Coding Agent Installer Wizard for Windows
$ProjectName = "Ollama-Coding-Agent"
Write-Host "==========================================" -ForegroundColor Green
Write-Host "      OLLAMA CODING AGENT SYSTEM SETUP    " -ForegroundColor Green
Write-Host "      Setting up: $ProjectName" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Green

# 1. Verify Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonVersion = (python --version 2>&1)
    Write-Host "[OK] $PythonVersion detected." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Python is missing! Please install Python 3.10+ and add it to your PATH." -ForegroundColor Red
    pause
    exit
}

# 2. Verify Ollama
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $OllamaVersion = (ollama --version)
    Write-Host "[OK] $OllamaVersion detected." -ForegroundColor Green
} else {
    Write-Host "[WARNING] Ollama CLI is missing! Please install Ollama from https://ollama.com/" -ForegroundColor Yellow
}

# 3. Create Virtual Environment
if (-not (Test-Path ".venv")) {
    Write-Host "[STEP] Creating Python Virtual Environment (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
} else {
    Write-Host "[OK] Virtual environment exists." -ForegroundColor Green
}

# 4. Install Dependencies
Write-Host "[STEP] Installing dependencies from requirements.txt..." -ForegroundColor Cyan
& ".\.venv\Scripts\pip" install -r requirements.txt

# 5. Check if Ollama is running and build the model
Write-Host "[STEP] Building Ollama custom model 'ollama-coder'..." -ForegroundColor Cyan
$ollamaRunning = $false
try {
    # Check if Ollama API is reachable
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    $ollamaRunning = $true
} catch {
    Write-Host "[WARNING] Ollama server is not running at http://localhost:11434." -ForegroundColor Yellow
    Write-Host "[INFO] Attempting to start Ollama in the background..." -ForegroundColor Cyan
    Start-Process -FilePath "ollama" -ArgumentList "serve" -NoNewWindow
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        $ollamaRunning = $true
    } catch {}
}

if ($ollamaRunning) {
    Write-Host "[STEP] Ensuring base model is copied (avoiding Windows path colon bug)..." -ForegroundColor Cyan
    ollama cp gemma3:1b gemma3-local 2>$null
    Write-Host "[STEP] Running 'ollama create ollama-coder -f Modelfile'..." -ForegroundColor Cyan
    ollama create ollama-coder -f Modelfile
    Write-Host "[OK] Custom model 'ollama-coder' successfully registered!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Could not connect to Ollama. Skipping model building." -ForegroundColor Yellow
    Write-Host "[INFO] You can build it manually later with: ollama create ollama-coder -f Modelfile" -ForegroundColor Cyan
}

Write-Host "==========================================" -ForegroundColor Green
Write-Host " SETUP COMPLETE: Launching Coding Agent..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

& ".\.venv\Scripts\python" agent.py $args
