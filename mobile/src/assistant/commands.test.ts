import assert from "node:assert/strict";
import { interpret, pendingFrom } from "./commands.ts";
import { assessApiUrl } from "./network.ts";
import { selectedModel } from "./models.ts";

const call = interpret("annemi ara");
assert.equal(call.type, "call");
assert.equal(call.status, "confirmation_required");
assert.equal(call.relation, "anne");
assert.equal(call.language, "tr");
assert.equal(call.placesCall, false);
assert.equal(call.uploadsAudio, false);
assert.equal(call.sendsWhatsapp, false);

const confirmed = interpret("evet", pendingFrom(call));
assert.equal(confirmed.delivery, "dial");
assert.equal(confirmed.placesCall, false);

const immediate = interpret("hemen ara", pendingFrom(call));
assert.equal(immediate.delivery, "call");
assert.equal(immediate.placesCall, true);

const mom = interpret("call mom");
assert.equal(mom.relation, "anne");
assert.equal(mom.language, "en");
assert.equal(mom.status, "confirmation_required");

const whatsapp = interpret("babamın whatsappına merhaba yaz");
assert.equal(whatsapp.type, "whatsapp");
assert.equal(whatsapp.relation, "baba");
assert.equal(whatsapp.sendsWhatsapp, false);
assert.equal(whatsapp.status, "confirmation_required");
const draft = interpret("yes", pendingFrom(whatsapp));
assert.equal(draft.delivery, "compose");
assert.equal(draft.sendsWhatsapp, false);

assert.equal(interpret("no", pendingFrom(call)).type, "cancel");
assert.equal(interpret("what is the weather", pendingFrom(call)).type, "chat");
assert.equal(interpret("hey nova").type, "wake");
assert.equal(interpret("hey nova open instagram").type, "launch");
assert.equal(interpret("hey nova open instagram").packageName, "com.instagram.android");
assert.equal(interpret("hey nova open instagram").uploadsAudio, false);

const timer = interpret("5 dakika zamanlayıcı kur");
assert.equal(timer.type, "timer");
assert.equal(timer.seconds, 300);
assert.equal(timer.language, "tr");

const alarm = interpret("set an alarm for 7:30");
assert.equal(alarm.type, "alarm");
assert.equal(alarm.hour, 7);
assert.equal(alarm.minute, 30);
assert.equal(alarm.language, "en");

const reminder = interpret("yarın saat 9'da ilacı hatırlat");
assert.equal(reminder.type, "reminder");
assert.equal(reminder.dayOffset, 1);
assert.equal(reminder.hour, 9);
assert.equal(reminder.language, "tr");

assert.equal(assessApiUrl("http://127.0.0.1:8001").kind, "local");
assert.equal(assessApiUrl("https://nova.tailnet.ts.net").kind, "tailscale");
assert.equal(assessApiUrl("http://100.64.0.2:8001").kind, "tailscale");
assert.equal(assessApiUrl("http://100.127.242.84:8001").kind, "tailscale");
assert.equal(assessApiUrl("http://0.0.0.0:8001").ok, false);
assert.equal(assessApiUrl("https://example.com").ok, false);
assert.equal(selectedModel().id, "platform-speech-and-rules");
assert.equal(selectedModel().downloads, false);

console.log("phone-commands-ok");
