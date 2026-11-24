@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "VOICE_STT_PROVIDER=whisper"
set "VOICE_STT_COMMAND=%~dp0backend\.venv\Scripts\python.exe %~dp0voice\transcribe_wav.py"

echo Checking local NOVA services.
docker start nova-vector-db >nul 2>&1

powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 echo Ollama is not responding. Start Ollama locally for chat.

powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:8001/health -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { if ($_.Exception.Response) { exit 0 } else { exit 1 } }"
if errorlevel 1 (
  echo Starting the API.
  start "NOVA API" /D "%~dp0backend" cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
) else (
  echo The API is already running.
)

set "NOVA_EXE="
for %%F in ("%~dp0desktop\release\*.exe") do set "NOVA_EXE=%%~fF"
if defined NOVA_EXE (
  echo Starting the desktop app.
  start "NOVA UI" "%NOVA_EXE%"
) else (
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
  if errorlevel 1 (
    echo Starting the development interface.
    start "NOVA UI" /D "%~dp0desktop" cmd /c "npm run dev"
  ) else (
    echo The interface is already running.
  )
)

ping -n 4 127.0.0.1 >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:8001/health -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { if ($_.Exception.Response) { exit 0 } else { exit 1 } }"
if errorlevel 1 (
  echo The API health check failed.
  exit /b 1
)
echo NOVA is ready.
exit /b 0
