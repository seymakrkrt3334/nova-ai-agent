# NOVA security notes

These notes come from code review and automated tests. This is not a live penetration test. They were written without reading secret files.

## Authentication

Every API endpoint requires `X-API-Key`. Comparison is constant-time. If the key is unset the service returns 503. A wrong key returns 401. The desktop key is in `sessionStorage`. The mobile key is in Expo SecureStore. Scripts do not contain the key.

## CORS

Allowed origins are `http://127.0.0.1:5173`, `http://localhost:5173`, `http://127.0.0.1:4173`, and `http://localhost:4173`. Methods are GET, POST, PATCH, and DELETE. Headers are `Content-Type` and `X-API-Key`. There is no wildcard origin. The Electron package serves the interface only at `127.0.0.1:4173`.

## Secrets and OAuth

`.env`, `credentials.json`, and `token*.json` are not committed. The settings object renders as `Settings(redacted)`. The Google script does not open a browser or request a write scope unless `--launch` is passed. The Gmail read path does not open a browser from the scheduler when a token is missing. Token file contents are not shown on the status endpoint.

## SQL and SSRF

Queries are parameterized. Web reads reject private networks, local addresses, and metadata endpoints. Social send URLs are fixed official hostnames and redirects are not followed. Chat ids are limited to a restricted character set.

## Tools and prompt injection

The model can select only registered tools. There is no send-email tool. Tool output goes into the summary as data. A social draft does not treat inbound text as instructions. The default draft does not call the model.

## Automation

Automatic execution is enabled only when `authorize` is set at creation time and the matching scope is read-only. Writes and unapproved jobs wait for confirmation. The same window key does not run twice. Revoking permission turns the automatic flag off. The scheduler does not put the job prompt in the response body.

## Memory

Personal information is not saved without explicit consent. Memory search is independent of the session. Chat history can be limited to a session. History rows with the system role are not sent to the model again.

## Network

The desktop app calls the API at `127.0.0.1:8001`. PostgreSQL listens on `127.0.0.1:5434`. Ollama listens on `127.0.0.1:11434`. A phone reaches the API only through the private Tailscale network, and the Windows firewall allow rule is limited to `100.64.0.0/10`. PostgreSQL and Ollama are not opened to the phone. No public port is opened for WhatsApp or Instagram webhooks.

## Dependencies

The Electron install reported 29 advisories in the desktop tree: 4 moderate, 24 high, and 1 critical. The mobile Expo install showed 51 advisories. `npm audit fix --force` was not run. The Whisper base model and the unsigned Electron package were downloaded. The package has no code signature. Windows SmartScreen may warn.
