# NOVA status snapshot

Date of this snapshot: 2026-11-18. Secret files were not read. Database rows were not deleted. The Docker volume was not recreated. Services were not opened to the public network. The OAuth browser was not opened. No email or social message was sent.

This file records that checkpoint. Later work continued: a release APK, Tailscale, a Turkish Windows voice, and the mobile interface. The repository is still in progress.

## Installed at that checkpoint

- Whisper.cpp CPU binary at `voice/unpack/Release/whisper-cli.exe`. The multilingual `ggml-base.bin` was downloaded and verified with SHA1 `465707469ff3a37a2b9b8d8f89f2f99de7299dac`.
- Local recognition was wired with `VOICE_STT_PROVIDER=whisper` and `voice/transcribe_wav.py`. The command uses `-l auto -t 4 -ng`: automatic language, 4 threads, GPU off.
- Electron 33.2.1 and electron-builder were installed. Portable package: `desktop/release/NOVA AI 1.0.0.exe`. Signing was skipped because no signing identity exists; the package is unsigned.
- The desktop shortcut `NOVA AI.lnk` points at `START_NOVA.bat`.
- Expo dependencies were installed in `mobile`. `npx tsc --noEmit` exited 0.

## Tested

- `python -m pytest tests -q` → 54 passed at that checkpoint. Gmail, Ollama, the database, and social sending were mocked.
- The desktop production build `vite build` and the Electron package exited 0.
- `/health` without a key returned 401. Ollama `/api/tags` returned 200. Models present then: `llama3.2:latest`, `nomic-embed-text:latest`, `gemma2:2b`, `gemma2:latest`, `qwen2.5:latest`. No model was loaded in memory at the time of the check.
- `nova-vector-db` accepted connections on `127.0.0.1:5434`. Counts: 4 memories, 22 conversations, 0 automations, 0 social messages. No rows were deleted.
- Windows SAPI voices then: `en-US Microsoft David Desktop`, `en-US Microsoft Zira Desktop`. A short English sentence was spoken.
- The packaged interface returned 200 at `http://127.0.0.1:4173`. Language switching, settings, and the integrations screen without a key were checked in the browser. Email content was not requested.

## Verified live

- A public JFK sample was transcribed to English: “And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.”
- `START_NOVA.bat` exited 0, did not restart an API that was already up, and opened the desktop package.
- `STOP_NOVA.bat` closes NOVA windows. It does not stop the database container or delete its volume.
- The shortcut target was in place.

## Blocked at that checkpoint

- A Turkish Windows voice was not installed yet. That is a system-wide change and needs approval.
- Turkish speech had not been tried live with a Turkish recording. The model is multilingual and language selection is automatic.
- The phone records M4A. At that point local Whisper accepted only WAV, FLAC, MP3, and OGG.
- Live Google contacts, calendar, and Gmail data were not verified until you run the browser grant. The scopes are read-only.
- Tailscale was not installed at that checkpoint. PostgreSQL and FastAPI were not opened to the public network.
- An Android APK had not been produced. Java 17 and the SDK were present. `ANDROID_HOME` was unset and `adb` was not on PATH.
- An iOS build needs macOS and Xcode.
- A WhatsApp or Instagram inbox needs a public webhook. No port was opened.
- The desktop npm audit had 29 advisories. `npm audit fix --force` was not run.

## 16 GB memory

Chat is limited to `num_ctx` 4096, `num_predict` 400, and `num_thread` 8. Social drafts use a 2048 context. Whisper does not use the GPU. Extra Ollama models may sit on disk; chat needs `llama3.2` and embeddings need `nomic-embed-text`. Models were not deleted by this snapshot.

## Still manual

Run the Google, Gmail, and phone steps in `MANUAL_TESTS.md` yourself. Do not paste private content into this chat. Report only a status code and whether it worked.
