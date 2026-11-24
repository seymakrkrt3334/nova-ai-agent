"""Print the official Google setup steps.

This script does not open a browser unless you pass --launch yourself.
NOVA does not run that flag automatically and does not widen existing scopes.
"""
import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.google_scopes import (  # noqa: E402
    CALENDAR_READONLY_SCOPES,
    CONTACTS_READONLY_SCOPES,
    GMAIL_READONLY_SCOPES,
)

SERVICES = {
    "gmail": {
        "api": "Gmail API",
        "scopes": GMAIL_READONLY_SCOPES,
        "token": "token.json",
        "console": "https://console.cloud.google.com/apis/library/gmail.googleapis.com",
    },
    "contacts": {
        "api": "People API",
        "scopes": CONTACTS_READONLY_SCOPES,
        "token": "token_contacts.json",
        "console": "https://console.cloud.google.com/apis/library/people.googleapis.com",
    },
    "calendar": {
        "api": "Google Calendar API",
        "scopes": CALENDAR_READONLY_SCOPES,
        "token": "token_calendar.json",
        "console": "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="NOVA Google authorization steps")
    parser.add_argument("service", choices=sorted(SERVICES))
    parser.add_argument("--launch", action="store_true", help="Start the local browser flow on purpose")
    args = parser.parse_args()
    chosen = SERVICES[args.service]
    print(f"API: {chosen['api']}")
    print("Scope:")
    for scope in chosen["scopes"]:
        print(f"  {scope}")
    print(f"Console: {chosen['console']}")
    print("1. In the Google Cloud project, enable only this API.")
    print("2. Choose Desktop app as the OAuth client type.")
    print("3. Save the downloaded file as backend/credentials.json.")
    print(f"4. The token is written to backend/{chosen['token']}.")
    print("This command does not request a write scope. There is no email sending.")
    if not args.launch:
        print("The browser was not opened. Run the command yourself with --launch to open it.")
        return 0
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials = BACKEND_DIR / "credentials.json"
    if not credentials.is_file():
        print("credentials.json was not found. The browser was not opened.")
        return 1
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials), chosen["scopes"])
    creds = flow.run_local_server(port=0)
    token_path = BACKEND_DIR / chosen["token"]
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print("Authorization was saved. The token contents were not shown.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
