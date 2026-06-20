@echo off
REM Lucy's Cleanup Script (Windows)
REM Safely removes old containers and frees up resources

cls
echo.
echo 🧹 Lucy's Docker Cleanup Utility
echo ================================
echo.

echo WARNING: This will stop and remove containers!
echo.
echo Choose an option:
echo   1) Remove only EXITED containers (safe)
echo   2) Remove ALL containers from old Lucy setup
echo   3) Full cleanup: Remove all containers + images + volumes
echo   4) Cancel
echo.

set /p choice="Enter choice (1-4): "

if "%choice%"=="1" goto cleanup_exited
if "%choice%"=="2" goto cleanup_old
if "%choice%"=="3" goto cleanup_full
if "%choice%"=="4" goto cancel
goto invalid

:cleanup_exited
echo.
echo 🛑 Stopping exited containers...
for /f "tokens=*" %%i in ('docker ps -a --filter "status=exited" --quiet') do (
    docker rm %%i 2>nul
    echo   Removed: %%i
)
echo ✅ Exited containers removed
goto done

:cleanup_old
echo.
echo 🛑 Stopping all containers from old Lucy setup...
docker stop api capability_manager evolutionary-prompt scheduler planner tool_registry trusted-executor-v2 trusted-executor self_extension weather proxy liquidsoap icecast safeguard 2>nul

echo 🗑️  Removing old containers...
docker rm -f api capability_manager evolutionary-prompt scheduler planner tool_registry trusted-executor-v2 trusted-executor self_extension weather proxy liquidsoap icecast safeguard 2>nul

echo ✅ Old containers removed
goto done

:cleanup_full
echo.
echo ⚠️  FULL CLEANUP - This is irreversible!
set /p confirm="Type 'YES' to confirm: "
if not "%confirm%"=="YES" goto cancel

echo.
echo 🛑 Stopping all containers...
docker compose down --remove-orphans 2>nul
docker stop $(docker ps -aq) 2>nul

echo 🗑️  Removing all containers...
docker rm -f $(docker ps -aq) 2>nul

echo 🗑️  Removing dangling images...
docker image prune -f 2>nul

echo 🗑️  Removing unused volumes...
docker volume prune -f 2>nul

echo ✅ Full cleanup complete
echo.
echo 📊 Remaining resources:
docker system df
goto done

:invalid
echo ❌ Invalid choice
goto done

:cancel
echo ⏹️  Cleanup cancelled
goto done

:done
echo.
pause
