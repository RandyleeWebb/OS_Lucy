@echo off
setlocal EnableDelayedExpansion
color 0A
title LucyVerse OS - System Boot

:: ============================================================
::  LUCYVERSE OS - MASTER STARTUP SCRIPT
::  Starts: Ollama, Docker services, Node/Vite UI
::  Ports:  3000 (UI), 6379 (Redis), 8000 (Icecast),
::          8001 (API), 8002 (Generator), 8003 (CapMgr),
::          8004 (SelfExt), 8005 (ToolReg), 8006 (Planner),
::          8007 (Scheduler), 8010 (Emma), 11434 (Ollama)
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "DOCKER=docker"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "ENV_FILE=%SCRIPT_DIR%.env.local"

:: ── Firewall ports list (opened automatically) ──────────────
set "PORTS=3000 6379 8000 8001 8002 8003 8004 8005 8006 8007 8010 11434"

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║           L U C Y V E R S E   O S   B O O T          ║
echo  ║                  Randy Webb  -  v2.0                  ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────────────────────
:: 0. CREATE DIRS
:: ─────────────────────────────────────────────────────────────
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%SCRIPT_DIR%data" mkdir "%SCRIPT_DIR%data"
if not exist "%SCRIPT_DIR%generated" mkdir "%SCRIPT_DIR%generated"

:: ─────────────────────────────────────────────────────────────
:: 1. OPEN FIREWALL PORTS
:: ─────────────────────────────────────────────────────────────
echo [1/6] Opening firewall ports...
for %%P in (%PORTS%) do (
    netsh advfirewall firewall show rule name="LucyVerse-%%P" >nul 2>&1
    if errorlevel 1 (
        netsh advfirewall firewall add rule name="LucyVerse-%%P" ^
            dir=in action=allow protocol=TCP localport=%%P >nul 2>&1
        echo       + Port %%P opened
    ) else (
        echo       ~ Port %%P already open
    )
)
echo       Done.
echo.

:: ─────────────────────────────────────────────────────────────
:: 2. CHECK / START OLLAMA
:: ─────────────────────────────────────────────────────────────
echo [2/6] Checking Ollama...

:: Check if ollama is reachable
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo       Ollama not running. Attempting to start...
    where ollama >nul 2>&1
    if errorlevel 1 (
        echo       [WARN] ollama.exe not found in PATH.
        echo       Install from https://ollama.com or add to PATH.
        echo       Lucy will fall back to Gemini for chat.
    ) else (
        start "Ollama Server" /min cmd /c "ollama serve >> "%LOG_DIR%\ollama.log" 2>&1"
        echo       Waiting for Ollama to boot...
        timeout /t 5 /nobreak >nul
        :: Verify
        curl -s http://localhost:11434/api/tags >nul 2>&1
        if errorlevel 1 (
            echo       [WARN] Ollama still not responding - continuing without it.
        ) else (
            echo       Ollama running on :11434
        )
    )
) else (
    echo       Ollama already running on :11434
)

:: Pull models if needed (runs in background, non-blocking)
echo       Ensuring llama3 model available ^(background^)...
start "" /min cmd /c "ollama pull llama3 >> "%LOG_DIR%\ollama_pull.log" 2>&1"

echo.

:: ─────────────────────────────────────────────────────────────
:: 3. CHECK DOCKER + START COMPOSE STACK
:: ─────────────────────────────────────────────────────────────
echo [3/6] Starting Docker services...

%DOCKER% info >nul 2>&1
if errorlevel 1 (
    echo       Docker Desktop not running. Launching...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo       Waiting 20 seconds for Docker Engine...
    timeout /t 20 /nobreak >nul
    %DOCKER% info >nul 2>&1
    if errorlevel 1 (
        echo       [ERROR] Docker still not available. Cannot start backend services.
        echo       Please start Docker Desktop manually and re-run this script.
        goto :skip_docker
    )
)

echo       Docker OK. Bringing up compose stack...
pushd "%SCRIPT_DIR%"
%DOCKER% compose up -d --remove-orphans >> "%LOG_DIR%\docker.log" 2>&1
if errorlevel 1 (
    echo       [WARN] docker compose had errors - check logs\docker.log
) else (
    echo       All containers started.
)
popd

:skip_docker
echo.

:: ─────────────────────────────────────────────────────────────
:: 4. WAIT FOR CORE SERVICES
:: ─────────────────────────────────────────────────────────────
echo [4/6] Waiting for core services...

:: Define waitForPort subroutine here early to avoid "cannot find the batch label" when
:: CALL is issued inside parenthesized blocks or after conditional GOTO usage.
goto :skip_waitsub
:: ===== waitForPort subroutine =====
:waitForPort
set /a "_tries=0"
set /a "_max=%~3"
:wpLoop
powershell -Command "if (Test-NetConnection -ComputerName 'localhost' -Port %~1 -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo       %~2 ready on :%~1
    goto :eof
)
set /a "_tries+=1"
if !_tries! geq !_max! (
    echo       [WARN] %~2 not responding on :%~1 after %~3s - continuing anyway
    goto :eof
)
timeout /t 1 /nobreak >nul
goto :wpLoop
:: ===== end waitForPort subroutine =====

:skip_waitsub
call :waitForPort 6379 "Redis"        15
call :waitForPort 8010 "Emma"         30
call :waitForPort 8004 "SelfExt"      25
call :waitForPort 8003 "CapManager"   25
call :waitForPort 8001 "API"          20

echo.

:: ─────────────────────────────────────────────────────────────
:: 5. SETUP .env.local FOR NODE SERVER
:: ─────────────────────────────────────────────────────────────
echo [5/6] Configuring environment...

if not exist "%ENV_FILE%" (
    echo       Creating .env.local from template...
    (
        echo GEMINI_API_KEY=
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo OLLAMA_MODEL=llama3
        echo EMMA_URL=http://localhost:8010
        echo REDIS_URL=redis://localhost:6379
        echo CAPABILITY_MANAGER_URL=http://localhost:8003
        echo TOOL_REGISTRY_URL=http://localhost:8005
        echo PLANNER_URL=http://localhost:8006
        echo SCHEDULER_URL=http://localhost:8007
        echo SELF_EXTENSION_URL=http://localhost:8004
        echo EMMA_SECRET=lucy-secret
        echo PORT=3000
        echo NODE_ENV=development
    ) > "%ENV_FILE%"
    echo       .env.local created. Add your GEMINI_API_KEY if desired.
) else (
    echo       .env.local exists - skipping.
)

echo.

:: ─────────────────────────────────────────────────────────────
:: 6. START NODE/VITE UI
:: ─────────────────────────────────────────────────────────────
echo [6/6] Starting LucyVerse UI...

pushd "%SCRIPT_DIR%"

if not exist "node_modules" (
    echo       Installing npm dependencies...
    echo       Running npm install (this may take a few minutes)...
    call npm install --no-audit --no-fund >> "%LOG_DIR%\npm.log" 2>&1
    if errorlevel 1 (
        echo       [ERROR] npm install failed. Check logs\npm.log
        echo       Attempting to install without optional packages...
        call npm install --no-audit --no-fund --no-optional >> "%LOG_DIR%\npm_fallback.log" 2>&1
        if errorlevel 1 (
            echo       [ERROR] npm install fallback failed. See logs\npm_fallback.log
            echo       You may need to run npm install manually with a proper network/proxy.
            goto :end
        ) else (
            echo       npm install fallback succeeded.
        )
    )
)

echo       Launching server on http://localhost:3000
start "LucyVerse UI" cmd /k "npm run dev"
timeout /t 4 /nobreak >nul

popd

:: ─────────────────────────────────────────────────────────────
:: 7. SMOKE TESTS (HTTP) - quick verification using PowerShell / curl.exe
:: ─────────────────────────────────────────────────────────────
echo [7/7] Running quick smoke tests against local UI and Emma (via proxy)
set "SMOKE_LOG=%LOG_DIR%\smoke_tests.log"
echo Smoke test started at %DATE% %TIME% > "%SMOKE_LOG%"

:: Use PowerShell Invoke-RestMethod where possible to avoid curl alias issues
powershell -Command "try { Write-Output '--- UI /health ---'; $h = Invoke-RestMethod -Uri 'http://localhost:3000/health' -Method GET -Headers @{'x-secret-key'='lucy-secret'}; $h | ConvertTo-Json -Depth 5 } catch { Write-Output 'HEALTH CHECK FAILED: ' + $_.Exception.Message; exit 1 }" >> "%SMOKE_LOG%" 2>&1 || echo Health check failed - see %SMOKE_LOG%

:: Create a temporary terminal session and run a one-shot command
for /f "delims=" %%S in ('powershell -Command "try { $r=Invoke-RestMethod -Uri 'http://localhost:3000/terminal/session' -Method POST -Headers @{'x-secret-key'='lucy-secret'} -ContentType 'application/json' -Body '{}'; Write-Output $r.session_id } catch { Write-Output '' }"') do set SESSION_ID=%%S
if "%SESSION_ID%"=="" (
    echo Failed to create terminal session (empty session id) >> "%SMOKE_LOG%"
) else (
    echo Created session %SESSION_ID% >> "%SMOKE_LOG%"
    powershell -Command "try { $o=Invoke-RestMethod -Uri 'http://localhost:3000/terminal/exec' -Method POST -Headers @{'x-secret-key'='lucy-secret'} -ContentType 'application/json' -Body (@{ command = 'echo smoke-test && uname -a' } | ConvertTo-Json); $o | ConvertTo-Json -Depth 5 } catch { Write-Output 'EXEC FAILED: ' + $_.Exception.Message; exit 1 }" >> "%SMOKE_LOG%" 2>&1 || echo Exec failed >> "%SMOKE_LOG%"
    :: Close the session
    powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:3000/terminal/session/%SESSION_ID%/close' -Method POST -Headers @{'x-secret-key'='lucy-secret'} -ContentType 'application/json' -Body '{}'; Write-Output 'closed' } catch { Write-Output 'CLOSE FAILED: ' + $_.Exception.Message }" >> "%SMOKE_LOG%" 2>&1
)

echo Smoke tests logged to %SMOKE_LOG%

:: ─────────────────────────────────────────────────────────────
:: DONE
:: ─────────────────────────────────────────────────────────────
echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║  LucyVerse OS ONLINE                                  ║
echo  ║                                                       ║
echo  ║  UI        http://localhost:3000                      ║
echo  ║  Emma      http://localhost:8010/docs                 ║
echo  ║  Ollama    http://localhost:11434                     ║
echo  ║  Icecast   http://localhost:8000                      ║
echo  ║                                                       ║
echo  ║  Logs:  .\logs\                                       ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.

:: Open browser
start "" "http://localhost:3000"

goto :end

:: ─────────────────────────────────────────────────────────────
:: SUBROUTINE: wait for port
::   %1 = port  %2 = label  %3 = max_seconds
:: ─────────────────────────────────────────────────────────────
:waitForPort
set /a "_tries=0"
set /a "_max=%~3"
:wpLoop
curl -s http://localhost:%~1 >nul 2>&1
if not errorlevel 1 (
    echo       %~2 ready on :%~1
    goto :eof
)
set /a "_tries+=1"
if !_tries! geq !_max! (
    echo       [WARN] %~2 not responding on :%~1 after %~3s - continuing anyway
    goto :eof
)
timeout /t 1 /nobreak >nul
goto :wpLoop

:end
endlocal
