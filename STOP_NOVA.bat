@echo off
setlocal
chcp 65001 >nul
echo Closing the NOVA API and interface windows.
taskkill /FI "WINDOWTITLE eq NOVA API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq NOVA UI*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq NOVA AI*" /T /F >nul 2>&1
taskkill /IM "NOVA AI.exe" /F >nul 2>&1
taskkill /IM "NOVA AI 1.0.0.exe" /F >nul 2>&1
echo The database container and Docker volume were not stopped.
exit /b 0
