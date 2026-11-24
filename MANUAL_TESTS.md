# Manual test guide

Run this list on your own computer. Do not paste a private email, contact, calendar entry, chat, or key into the Cursor chat. Report only a status code, a screen name, and whether it worked.

## Local core

- [ ] `START_NOVA.bat` opens the API and the interface. `/health` without a key returns 401.
- [ ] After you enter your own key in Settings, the connection status becomes "Connected".
- [ ] A new conversation opens, a sentence is sent, a reply arrives, and it appears in the sidebar.
- [ ] Reopening the same session keeps the history. An older sentence does not leak into another session.
- [ ] A sentence saved with "remember this:" is found when asked in a new session.
- [ ] Clearing the key and sending shows an error, and private content does not land in the network log.

## Gmail, contacts, calendar

- [ ] `python scripts/authorize_google.py gmail` prints the steps without opening a browser.
- [ ] Before you run `--launch`, the Gmail screen shows 503 or a not-connected state.
- [ ] After the grant, "what arrived today" and "what I sent yesterday" return different results. Full text opens only from the button.
- [ ] Contacts and calendar return 403 without their own read-only grants.
- [ ] A calendar change shows a code. No record is created before you type the code.

## Voice

- [ ] Holding the button asks for the microphone and releasing it stops.
- [ ] Cancel cuts the recording and playback.
- [ ] On the desktop, a short Turkish sentence and a short English sentence become text. The English sample file was transcribed live.
- [ ] When reply speech is on, the spoken language matches the reply.
- [ ] The phone voice screen accepts an M4A recording after local conversion. The speech button reads the reply.

## Automation

- [ ] An unauthorized automatic job returns 422.
- [ ] When you create a daily Gmail summary, calendar reminder, briefing, web research, or reminder, you explicitly choose the scope and read-only access.
- [ ] When the time is due, a notification history row is created. The same window is not written twice.
- [ ] Revoking permission stops the job.
- [ ] No automatic job writes email or calendar.

## Social

- [ ] Platform cards say the personal inbox is not read.
- [ ] Sending does not happen while the confirmation box is off.
- [ ] Sending returns 409 when the Telegram bot token is missing.
- [ ] WhatsApp and Instagram show the business-account requirement, the cost warning, and that there is no public webhook.

## Google contacts and calendar

These steps open a browser. NOVA does not run them by itself. Before you grant extra OAuth permission, check that the scope is read-only.

1. In the `backend` folder, run `..\.venv\Scripts\python.exe scripts\authorize_google.py contacts`. The browser does not open. Read the People API line.
2. Only if you add `--launch` yourself does the browser open. Choose your account. The token is written to `token_contacts.json`. Do not open the file and do not paste its contents into chat.
3. Repeat the same two steps with `calendar`. The token is `token_calendar.json`. The scope must stay `calendar.readonly`.
4. Open the Contacts and Calendar screens in the app. Report only whether it worked. Do not paste a name, phone number, event title, or time.
5. A calendar change must not save before it shows a confirmation code. Typing the code also requires write permission. Do not grant that permission without a separate approval.

## Live Gmail check

1. `..\.venv\Scripts\python.exe scripts\authorize_google.py gmail` prints the steps without opening a browser.
2. `--launch` is only your decision. The scope must be `gmail.readonly`. The token is `token.json`. Do not share its contents.
3. Enter your own API key in Settings. Do not write the key in chat.
4. Send a short request for "what arrived today" and "what I sent yesterday". Tell Cursor only the status code and whether a result arrived. Do not paste the subject, sender, or body.
5. Full text opens only when you press the button. There is no send.

## Private phone access with Tailscale

1. Install the Tailscale client only with your own tailnet account. Do not bind PostgreSQL or Ollama to a public address.
2. PostgreSQL stays on `127.0.0.1:5434`. Do not open ports `5432`, `5433`, or `5434` to the tailnet or the internet.
3. The API may listen on port `8001` only when the firewall allows the Tailscale range `100.64.0.0/10`. Do not add a public allow rule.
4. On the phone, enter that tailnet address and the API key in Expo settings. The key stays in SecureStore. Do not write the address or the key in chat.
5. Send one chat from the phone. Report only whether it connected.

## Android package

A signed release APK is built with the local release keystore. That keystore is not in the repository. Java 17 and the Android SDK are required. `adb.exe` is inside the SDK. Trying a shell build:

```bat
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
set PATH=%ANDROID_HOME%\platform-tools;%PATH%
cd mobile\android
gradlew.bat assembleRelease
```

iOS needs macOS and Xcode.

## Shutdown

- [ ] `STOP_NOVA.bat` closes windows titled `NOVA API`, `NOVA UI`, or `NOVA AI`.
- [ ] `nova-vector-db` keeps running and its volume is not deleted. Record counts do not change.
