# NOVA plan

A private, local-first personal assistant. This file holds the milestones and acceptance criteria. Existing database volumes, OAuth grants, and secret files are not changed by this plan.

## This round

Phases 1–12 are in the tree. The project is still in progress. The last full test at the written checkpoint was `python -m pytest tests -q` → 54 passed. Gmail, Ollama, contacts, calendar, web, and official social sending are mocked in tests. The multilingual Whisper base model and the unsigned Windows package are installed. An English sample recording was transcribed live. The OAuth browser was not opened. Database rows were not deleted. The Gmail scope is read-only.

## Phase 1 — Audit the current system and fix it safely

Acceptance criteria:

- Imports, dependencies, the schema, and endpoints are compared without reading secret file contents.
- `requirements.txt` lists the packages the running code uses. Unused remote-model packages are removed from the list.
- Settings are read in one place under the names `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`, `DATABASE_URL`, and `NOVA_API_KEY`. Settings output does not show secret values.
- A Gmail search with an empty, oversized, or invalid limit does not call the external service. Error responses do not leak detail.
- A memory vector is 768 finite numbers. Text and category limits match the schema.
- The schema file contains only `CREATE ... IF NOT EXISTS` and is not applied to the existing volume.
- Requests without an API key are rejected on `/health` and `/chat`.
- Tests use fakes instead of real Gmail, Ollama, and the database.

## Phase 2 — Tool registry and bounded execution

Acceptance criteria:

- The first catalog started with `chat`, `gmail_search`, `memory_search`, and `memory_save`. There is no send tool. Calendar writes are only proposed, and only with the confirmation code from a later phase.
- The model decision is validated as JSON. An unknown tool or broken JSON falls back to chat.
- A Gmail query is not accepted as free text. Location and time range are built from the user's wording. Subject and sender stay quoted.
- A "sent today" request is not forced into the inbox.
- The tool loop is at most 3 steps, then the result is summarized.
- The model cannot write memory without an explicit save request. On an explicit save, the stored text is the text the user wrote.
- The router does not see the email body. The summary prompt treats tool output as data, not as instructions.
- If the model service is down, the response is 503 and the internal error text is not returned to the client.

## Phase 3 — Durable memory

Acceptance criteria:

- Semantic search returns a distance threshold and source information.
- Conversations are stored, listed, and deleted by session id.
- Editing a record updates `updated_at`.
- The user can export memory and delete by category.
- External content is not executed as a memory instruction.

## Phase 4 — Gmail

Acceptance criteria:

- Pagination continues with a page token.
- The full message is fetched only on an explicit request and only with the read-only scope.
- Search, summary, and a reply draft are produced.
- Sending does not exist without a separate OAuth grant and user confirmation.

## Phase 5 — Contacts and calendar

Acceptance criteria:

- The narrowest Google scopes are used.
- Reads and drafts are free. Create, update, and delete require explicit confirmation.
- A scope change is not made without a separate approval.

## Phase 6 — Web search

Acceptance criteria:

- The provider is selected by a setting and the key is not committed.
- Results return with a source URL.
- Page content is not executed as instructions.

## Phase 7 — Desktop chat interface

Acceptance criteria:

- A dark purple chat that works on narrow and wide screens.
- Conversations, memory, integrations, and settings use the same API key.
- The interface does not persist secret values.

## Phase 8 — Expo mobile app

Acceptance criteria:

- The API address is configurable. A physical device does not use `localhost`.
- The API key is in secure storage.
- Chat, error, and empty states are tried end to end.

## Phase 9 — Local voice

Acceptance criteria:

- Text-to-speech and speech-to-text run with local engines on the platforms that support them.
- Recording starts from an explicit user action.

## Phase 10 — Scheduled jobs

Acceptance criteria:

- Jobs can be listed, paused, and deleted.
- A job with an external side effect requires confirmation.
- Run records do not dump secret content.

## Phase 11 — WhatsApp and Instagram

Acceptance criteria:

- Only official APIs are considered.
- An unofficial client, session takeover, or a bypass of a platform restriction is not implemented.
- An unsupported surface is documented and left alone.

## Phase 12 — Tests, install, and distribution

Acceptance criteria:

- Automated tests with mocked integrations can be run again.
- The install script does not create secret files and does not delete the existing volume.
- The distribution note does not recommend binding the service publicly.

## Phase 11 — Official social surfaces

Acceptance criteria:

- Only the Telegram Bot API, WhatsApp Business Cloud API, and Instagram Messaging API are defined.
- There is no unofficial client for personal accounts.
- Sending does not happen without explicit confirmation.
- Platform limits, account type, and possible cost stay in the document.

## Phase 12 — Daily use

Acceptance criteria:

- The interface, voice, automation, and integration status all use the same local API.
- A read-only automation runs only with the permission given at creation. A write needs a separate confirmation.
- The start script does not recreate an existing container.
- Secret files do not enter the report.

## Consciously deferred

- Recreating Docker volumes.
- Opening the OAuth browser or widening a scope.
- Sending email, contacts, calendar events, or social messages.
- Listening to the microphone continuously.
- Publishing the FastAPI or PostgreSQL port to everyone.
- Enabling a paid API.
