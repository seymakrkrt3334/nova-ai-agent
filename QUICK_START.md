# NOVA quick start

NOVA stays on this computer. PostgreSQL is not opened to the public network.

## Start

1. Ollama should be running locally. Models: `llama3.2` and the embedding model `nomic-embed-text`.
2. If the `nova-vector-db` container is stopped, `START_NOVA.bat` starts it with `docker start`. It does not recreate the volume.
3. `START_NOVA.bat` starts the API on port `8001` only when it is not already up. If `desktop\release\NOVA AI 1.0.0.exe` exists, it opens that package. Otherwise it opens the development interface at `127.0.0.1:5173`.
4. A health check that returns `401` without a key means the API is up. Connection refused is a failure.
5. In Settings, enter the API address and the `X-API-Key`. The key stays in the tab session. The packaged interface is at `http://127.0.0.1:4173`.

Stop with `STOP_NOVA.bat`. That command closes NOVA windows. It does not delete the database container or its volume.

Desktop shortcut: `powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1`

## Daily use

- Chat history is stored with a session id. Long-term memory is searched across sessions.
- For Gmail, contacts, and calendar, `python scripts/authorize_google.py gmail` from the `backend` folder prints the steps. The browser does not open unless you pass `--launch`.
- Hold the microphone button to talk. Releasing it sends a WAV recording to local Whisper. Cancel stops the recording and speech. There is no continuous listening.
- The interface language defaults to English. Replies follow the language of the message.

## Phone

Dependencies are installed in `mobile` and the type check passed. The API address and key are in SecureStore. The phone records M4A; local FFmpeg converts it before recognition. Spoken replies use Expo Speech.

A physical phone cannot reach `127.0.0.1`. Use the Tailscale address of this computer in the phone settings. PostgreSQL stays on `127.0.0.1:5434` and is not opened to the tailnet. Details are in `SECURITY.md` and `MANUAL_TESTS.md`.
