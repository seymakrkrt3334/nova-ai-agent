@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "VOICE_STT_PROVIDER=whisper"
set "VOICE_STT_COMMAND=%~dp0backend\.venv\Scripts\python.exe %~dp0voice\transcribe_wav.py"

echo NOVA yerel servisleri kontrol ediliyor.
docker start nova-vector-db >nul 2>&1

powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 echo Ollama yanit vermiyor. Sohbet icin Ollama'yi yerelde baslatin.

powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:8001/health -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { if ($_.Exception.Response) { exit 0 } else { exit 1 } }"
if errorlevel 1 (
  echo API baslatiliyor.
  start "NOVA API" /D "%~dp0backend" cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
) else (
  echo API zaten ayakta.
)

set "NOVA_EXE="
for %%F in ("%~dp0desktop\release\*.exe") do set "NOVA_EXE=%%~fF"
if defined NOVA_EXE (
  echo Masaustu uygulamasi baslatiliyor.
  start "NOVA UI" "%NOVA_EXE%"
) else (
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
  if errorlevel 1 (
    echo Gelistirme arayuzu baslatiliyor.
    start "NOVA UI" /D "%~dp0desktop" cmd /c "npm run dev"
  ) else (
    echo Arayuz zaten ayakta.
  )
)

ping -n 4 127.0.0.1 >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:8001/health -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { if ($_.Exception.Response) { exit 0 } else { exit 1 } }"
if errorlevel 1 (
  echo API saglik kontrolu basarisiz.
  exit /b 1
)
echo NOVA hazir.
exit /b 0
