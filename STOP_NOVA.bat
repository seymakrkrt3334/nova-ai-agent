@echo off
setlocal
chcp 65001 >nul
echo NOVA API ve arayuz pencereleri kapatiliyor.
taskkill /FI "WINDOWTITLE eq NOVA API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq NOVA UI*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq NOVA AI*" /T /F >nul 2>&1
taskkill /IM "NOVA AI.exe" /F >nul 2>&1
taskkill /IM "NOVA AI 1.0.0.exe" /F >nul 2>&1
echo Veritabani konteyneri ve Docker hacmi durdurulmadi.
exit /b 0
