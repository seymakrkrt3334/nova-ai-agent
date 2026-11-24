export type Relation = "anne" | "baba";
export type Delivery = "none" | "dial" | "call" | "compose" | "launch" | "alarm" | "timer" | "reminder";
export type Pending = { type: "call" | "whatsapp"; relation: Relation; message: string; language: "tr" | "en" } | null;

export type PhoneAction = {
  type: "wake" | "chat" | "call" | "whatsapp" | "launch" | "alarm" | "timer" | "reminder" | "cancel";
  status: "ready" | "confirmation_required" | "cancelled";
  language: "tr" | "en" | null;
  relation?: Relation;
  message?: string;
  app?: string;
  packageName?: string;
  hour?: number;
  minute?: number;
  seconds?: number;
  dayOffset?: number;
  reply: string;
  delivery: Delivery;
  uploadsAudio: false;
  placesCall: boolean;
  sendsWhatsapp: false;
};

const RELATIONS: Record<Relation, string[]> = {
  anne: ["annemi", "annemin", "annem", "anne", "mommy", "mom", "mother"],
  baba: ["babami", "babamin", "babam", "baba", "daddy", "dad", "father"],
};

const APPS: Record<string, string> = {
  instagram: "com.instagram.android",
  whatsapp: "com.whatsapp",
  telefon: "com.android.dialer",
  phone: "com.android.dialer",
  mesajlar: "com.google.android.apps.messaging",
  messages: "com.google.android.apps.messaging",
  kamera: "com.android.camera2",
  camera: "com.android.camera2",
  ayarlar: "com.android.settings",
  settings: "com.android.settings",
};

const YES = new Set(["evet", "onayliyorum", "onayliyorum", "yes", "confirm"]);
const PLACE = new Set(["hemen ara", "place the call"]);
const NO = new Set(["hayir", "iptal", "vazgec", "no", "cancel"]);

export function fold(text: string): string {
  return text
    .replaceAll("İ", "i")
    .replaceAll("I", "ı")
    .replaceAll("ı", "i")
    .replaceAll("ş", "s")
    .replaceAll("Ş", "s")
    .replaceAll("ğ", "g")
    .replaceAll("Ğ", "g")
    .replaceAll("ü", "u")
    .replaceAll("Ü", "u")
    .replaceAll("ö", "o")
    .replaceAll("Ö", "o")
    .replaceAll("ç", "c")
    .replaceAll("Ç", "c")
    .toLowerCase()
    .replace(/[^a-z0-9:']+/g, " ")
    .trim();
}

export function utteranceLanguage(text: string): "tr" | "en" | null {
  if (/[çğıöşüÇĞİÖŞÜ]/.test(text)) return "tr";
  const tokens = new Set(fold(text).split(" ").filter(Boolean));
  const turkish = ["ara", "anne", "annem", "annemi", "baba", "babam", "babami", "alarm", "hatirlat", "dakika", "evet", "hayir", "tamam", "iptal", "ac", "mesaj", "yarin", "saat"].filter((word) => tokens.has(word)).length;
  const english = ["call", "mom", "dad", "mother", "father", "open", "alarm", "timer", "minute", "message", "whatsapp", "yes", "confirm", "cancel", "please", "remind", "hey", "hi", "instagram", "set", "for"].filter((word) => tokens.has(word)).length;
  if (turkish > english) return "tr";
  if (english > turkish) return "en";
  return null;
}

function relationIn(text: string): Relation | undefined {
  const tokens = new Set(text.split(" "));
  let found: { relation: Relation; length: number } | undefined;
  for (const relation of Object.keys(RELATIONS) as Relation[]) {
    for (const word of RELATIONS[relation]) {
      if (tokens.has(word) && (!found || word.length > found.length)) found = { relation, length: word.length };
    }
  }
  return found?.relation;
}

function stripWake(text: string): { woke: boolean; rest: string } {
  if (text === "hey nova" || text === "hi nova" || text === "nova") return { woke: true, rest: "" };
  for (const phrase of ["hey nova ", "hi nova ", "nova "]) {
    if (text.startsWith(phrase)) return { woke: true, rest: text.slice(phrase.length).trim() };
  }
  return { woke: false, rest: text };
}

function clock(text: string): { hour: number; minute: number } | undefined {
  const match = text.match(/(?:saat\s*)?(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?/);
  if (!match) return undefined;
  let hour = Number(match[1]);
  const minute = Number(match[2] || "0");
  if (match[3] === "pm" && hour < 12) hour += 12;
  if (match[3] === "am" && hour === 12) hour = 0;
  if (hour > 23 || minute > 59) return undefined;
  return { hour, minute };
}

function duration(text: string): number | undefined {
  const match = text.match(/(\d+)\s*(saniye|second|seconds|dakika|minute|minutes|dk|min)/);
  if (!match) return undefined;
  const amount = Number(match[1]);
  const unit = match[2];
  const seconds = unit.startsWith("s") ? amount : amount * 60;
  if (seconds < 1 || seconds > 24 * 60 * 60) return undefined;
  return seconds;
}

function appIn(text: string): { name: string; packageName: string } | undefined {
  for (const name of Object.keys(APPS)) {
    if (text.split(" ").includes(name)) return { name, packageName: APPS[name] };
  }
  return undefined;
}

function base(language: "tr" | "en" | null, reply: string, extra: Partial<PhoneAction> = {}): PhoneAction {
  return {
    type: "chat",
    status: "ready",
    language,
    reply,
    delivery: "none",
    uploadsAudio: false,
    placesCall: false,
    sendsWhatsapp: false,
    ...extra,
  };
}

function label(relation: Relation, language: "tr" | "en" | null): string {
  if (language === "en") return relation === "anne" ? "mom" : "dad";
  return relation === "anne" ? "annen" : "baban";
}

export function interpret(utterance: string, pending: Pending = null): PhoneAction {
  const language = utteranceLanguage(utterance);
  const folded = fold(utterance);
  const { woke, rest } = stripWake(folded);
  const command = rest || (woke ? "" : folded);
  if (pending && (YES.has(command) || PLACE.has(command))) {
    const immediate = PLACE.has(command);
    const name = label(pending.relation, pending.language);
    if (pending.type === "call") {
      return base(pending.language, pending.language === "en" ? `Opening the call for ${name}.` : `${name} için arama açılıyor.`, {
        type: "call",
        relation: pending.relation,
        delivery: immediate ? "call" : "dial",
        placesCall: immediate,
      });
    }
    return base(pending.language, pending.language === "en"
      ? `Opening WhatsApp with a draft for ${name}. You still confirm sending inside WhatsApp.`
      : `${name} için WhatsApp taslağı açılıyor. Gönderimi WhatsApp içinde siz onaylarsınız.`, {
      type: "whatsapp",
      relation: pending.relation,
      message: pending.message,
      delivery: "compose",
    });
  }
  if (pending && NO.has(command)) {
    return base(language, language === "en" ? "Cancelled." : "Vazgeçtim.", { type: "cancel", status: "cancelled" });
  }
  if (woke && !command) return base(language, "NOVA.", { type: "wake" });

  const relation = relationIn(command);
  const app = appIn(command);
  const time = clock(command);
  const seconds = duration(command);
  const whatsapp = command.includes("whatsapp");
  const call = !whatsapp && (command.includes(" ara") || command.startsWith("ara ") || command.includes("call") || command.includes("phone"));
  const launch = !call && !whatsapp && (command.includes(" ac") || command.startsWith("ac ") || command.includes("open") || command.includes("baslat"));
  const alarm = command.includes("alarm");
  const timer = !alarm && (command.includes("zamanlayici") || command.includes("timer") || seconds !== undefined && (command.includes("dakika") || command.includes("minute") || command.includes("saniye") || command.includes("second")));
  const reminder = command.includes("hatirlat") || command.includes("remind");

  if (call && relation) {
    const name = label(relation, language);
    return base(language, language === "en" ? `Call ${name}? Say yes to confirm.` : `${name} aransın mı? Onay için evet deyin.`, {
      type: "call",
      status: "confirmation_required",
      relation,
    });
  }
  if (whatsapp && relation) {
    const name = label(relation, language);
    const message = command.replace(/whatsapp|annemi|annem|anne|babami|babam|baba|mom|dad|mother|father|yaz|mesaj|message|gonder|send/g, " ").replace(/\s+/g, " ").trim();
    return base(language, language === "en"
      ? `Prepare a WhatsApp draft for ${name}? Sending stays inside WhatsApp.`
      : `${name} için WhatsApp taslağı hazırlansın mı? Gönderim WhatsApp içinde kalır.`, {
      type: "whatsapp",
      status: "confirmation_required",
      relation,
      message,
    });
  }
  if (launch && app) {
    return base(language, language === "en" ? `Opening ${app.name}.` : `${app.name} açılıyor.`, {
      type: "launch",
      app: app.name,
      packageName: app.packageName,
      delivery: "launch",
    });
  }
  if (alarm && time) {
    const stamp = `${time.hour}:${String(time.minute).padStart(2, "0")}`;
    return base(language, language === "en" ? `Sending ${stamp} to the clock app.` : `${stamp} alarmı saat uygulamasına iletiliyor.`, {
      type: "alarm",
      hour: time.hour,
      minute: time.minute,
      delivery: "alarm",
    });
  }
  if (timer && seconds) {
    return base(language, language === "en" ? `Setting a ${seconds}-second timer.` : `${seconds} saniyelik zamanlayıcı kuruluyor.`, {
      type: "timer",
      seconds,
      delivery: "timer",
    });
  }
  if (reminder) {
    return base(language, language === "en" ? "Saving the reminder on this phone." : "Hatırlatma bu telefonda kaydediliyor.", {
      type: "reminder",
      message: command,
      hour: time?.hour,
      minute: time?.minute,
      dayOffset: command.includes("yarin") || command.includes("tomorrow") ? 1 : 0,
      delivery: "reminder",
    });
  }
  return base(language, "", { type: "chat" });
}

export function pendingFrom(action: PhoneAction): Pending {
  if (action.status !== "confirmation_required" || (action.type !== "call" && action.type !== "whatsapp") || !action.relation) return null;
  return { type: action.type, relation: action.relation, message: action.message || "", language: action.language || "tr" };
}
