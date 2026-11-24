# NOVA architecture

The desktop Vite interface, the Electron package, and the Expo mobile client talk to the local FastAPI service with `X-API-Key`. The service uses Ollama (`llama3.2` and `nomic-embed-text`) and a local pgvector memory store. Gmail connects with a read-only OAuth scope. CORS allows the local origins on ports `5173` and `4173`. Electron serves static files only on `127.0.0.1:4173`.

A `/chat` request first separates an explicit memory save from a pending calendar confirmation. For other messages the model chooses at most three steps from the validated catalog: chat, memory, read-only Gmail, web, contacts, and a calendar proposal. A Gmail query is not free text. Tool output goes to the summary as data, not as instructions. Web addresses are not opened on private networks or metadata endpoints.

The Gmail scope stays `gmail.readonly`. Contacts expect `contacts.readonly`, and calendar reads expect `calendar.readonly`, each in its own token file. The calendar write scope `calendar.events` is defined but is not requested automatically. A change does not reach the service without a confirmation code. There is no email sending.

Recording starts only from a push-to-talk action. The desktop sends 16 kHz WAV. Whisper.cpp runs the multilingual base model on the CPU. Phone M4A is converted locally with FFmpeg before recognition. Speech uses the browser engine or Expo Speech and can be stopped. Automation rows live in the `automations` table. A due job becomes `awaiting_confirmation`; approval moves the prompt into chat and does not run the tool by itself.

The social layer recognizes only the official Bot API, WhatsApp Business Cloud API, and Instagram Messaging API. Sending requires confirmation. A personal inbox is not read.

A read-only automation runs on the scheduler only when the permission and scope matched at creation time. Writes stay on confirmation. The same time window does not run again.

The interface language defaults to English. Each reply uses the language detected for that turn. Phone access is limited to a private network such as Tailscale. PostgreSQL is not published publicly.
