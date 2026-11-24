import { FormEvent, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, api, loadPreferences, storePreferences, type Lang, type Theme } from "./api";
import { text } from "./i18n";

type View = "chat" | "memory" | "gmail" | "contacts" | "calendar" | "search" | "integrations" | "automation" | "social" | "settings";
type ChatMessage = { id: string; role: "user" | "assistant"; content: string; language?: string | null };
type SessionRow = { session_id: string | null; messages: number; updated_at: string | null; preview: string };

const views: View[] = ["chat", "memory", "gmail", "contacts", "calendar", "search", "integrations", "automation", "social", "settings"];

function encodeWav(chunks: Float32Array[], sampleRate: number) {
  const merged = new Float32Array(chunks.reduce((sum, chunk) => sum + chunk.length, 0));
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  const targetRate = 16000;
  const length = Math.max(1, Math.floor(merged.length * targetRate / sampleRate));
  const pcm = new Int16Array(length);
  for (let index = 0; index < length; index += 1) {
    const sourceIndex = Math.min(merged.length - 1, Math.floor(index * sampleRate / targetRate));
    const value = Math.max(-1, Math.min(1, merged[sourceIndex] || 0));
    pcm[index] = value < 0 ? value * 0x8000 : value * 0x7fff;
  }
  const buffer = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buffer);
  const write = (at: number, text: string) => { for (let i = 0; i < text.length; i += 1) view.setUint8(at + i, text.charCodeAt(i)); };
  write(0, "RIFF");
  view.setUint32(4, 36 + pcm.length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, targetRate, true);
  view.setUint32(28, targetRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, pcm.length * 2, true);
  for (let index = 0; index < pcm.length; index += 1) view.setInt16(44 + index * 2, pcm[index], true);
  return new Blob([buffer], { type: "audio/wav" });
}

function sessionToken() {
  return `s${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function voiceTag(language?: string | null) {
  if (language === "tr") return "tr-TR";
  if (language === "en") return "en-US";
  return "";
}

function speakText(value: string, language?: string | null) {
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(value);
  const tag = voiceTag(language);
  if (tag) {
    utterance.lang = tag;
    const voice = window.speechSynthesis.getVoices().find((item) => item.lang.toLowerCase().startsWith(tag.slice(0, 2)));
    if (voice) utterance.voice = voice;
  }
  window.speechSynthesis.speak(utterance);
}

export default function App() {
  const initial = useMemo(() => loadPreferences(), []);
  const [theme, setTheme] = useState<Theme>(initial.theme);
  const [lang, setLang] = useState<Lang>(initial.lang);
  const [apiUrl, setApiUrl] = useState(initial.apiUrl);
  const [apiKey, setApiKey] = useState(initial.apiKey);
  const [speakReplies, setSpeakReplies] = useState(initial.speak);
  const [view, setView] = useState<View>("chat");
  const [online, setOnline] = useState<"unknown" | "ok" | "down">("unknown");
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(sessionToken);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const capture = useRef<Float32Array[]>([]);
  const cancelVoice = useRef(false);
  const t = text(lang);
  const connection = { apiUrl, apiKey };

  useEffect(() => { setError(""); }, [view]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.lang = lang;
    storePreferences({ apiUrl, theme, lang, speak: speakReplies, apiKey });
  }, [apiUrl, theme, lang, speakReplies, apiKey]);

  useEffect(() => {
    if (!apiKey) {
      setOnline("unknown");
      return;
    }
    let stop = false;
    const ping = async () => {
      try {
        await api(connection, "/health");
        if (!stop) setOnline("ok");
      } catch {
        if (!stop) setOnline("down");
      }
    };
    void ping();
    const timer = window.setInterval(() => void ping(), 15000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [apiUrl, apiKey]);

  async function loadSessions() {
    const body = await api<{ sessions: SessionRow[] }>(connection, "/memory/sessions");
    setSessions(body.sessions);
  }

  async function openSession(id: string | null) {
    const next = id || "default";
    setSessionId(next);
    setView("chat");
    const query = id ? `?limit=50&session_id=${encodeURIComponent(id)}` : "?limit=50";
    const body = await api<{ messages: { role: "user" | "assistant"; content: string }[] }>(connection, `/memory/history${query}`);
    setMessages(body.messages.map((item, index) => ({ id: `${next}-${index}`, role: item.role, content: item.content })));
  }

  async function send(content = draft.trim()) {
    if (!content || busy) return;
    setDraft("");
    setError("");
    setMessages((prev) => [...prev, { id: `${Date.now()}-u`, role: "user", content }]);
    setBusy(true);
    try {
      const body = await api<{ reply: string; language?: string | null }>(connection, "/chat", {
        method: "POST",
        body: JSON.stringify({ message: content, session_id: sessionId }),
      });
      setMessages((prev) => [...prev, { id: `${Date.now()}-a`, role: "assistant", content: body.reply, language: body.language }]);
      if (speakReplies) speakText(body.reply, body.language);
      void loadSessions().catch(() => undefined);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "İstek tamamlanamadı.");
    } finally {
      setBusy(false);
    }
  }

  async function speakMessage(value: string, known?: string | null) {
    if (known === "tr" || known === "en") {
      speakText(value, known);
      return;
    }
    try {
      const body = await api<{ language?: string | null }>(connection, "/language", {
        method: "POST",
        body: JSON.stringify({ text: value }),
      });
      speakText(value, body.language);
    } catch {
      speakText(value);
    }
  }

  async function onTalkStart() {
    if (recording) return;
    cancelVoice.current = false;
    setError("");
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = media;
      capture.current = [];
      const context = new AudioContext();
      audioContext.current = context;
      const source = context.createMediaStreamSource(media);
      const processor = context.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        capture.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      const silent = context.createGain();
      silent.gain.value = 0;
      source.connect(processor);
      processor.connect(silent);
      silent.connect(context.destination);
      recorder.current = { stop() { processor.disconnect(); source.disconnect(); } } as MediaRecorder;
      setRecording(true);
    } catch {
      setError(lang === "tr" ? "Mikrofon izni verilmedi." : "Microphone permission was denied.");
    }
  }

  function onTalkEnd() {
    if (!recorder.current && capture.current.length === 0) return;
    recorder.current?.stop();
    recorder.current = null;
    const samples = capture.current;
    const rate = audioContext.current?.sampleRate || 48000;
    void audioContext.current?.close();
    audioContext.current = null;
    capture.current = [];
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    setRecording(false);
    if (cancelVoice.current || samples.length === 0) return;
    const blob = encodeWav(samples, rate);
    void api<{ text: string }>(connection, "/voice/transcribe", {
      method: "POST",
      body: blob,
      headers: { "Content-Type": "audio/wav" },
    })
      .then((body) => { setDraft(body.text); void send(body.text); })
      .catch((exc: unknown) => setError(exc instanceof Error ? exc.message : "Ses çevrilemedi."));
  }

  const statusLabel = !apiKey ? t.keyMissing : online === "ok" ? t.connected : t.disconnected;

  return (
    <div className="min-h-screen bg-[#f6f3fb] text-[#1a1028] dark:bg-ink dark:text-[#f4eefe]">
      <header className="flex items-center justify-between gap-3 border-b border-black/10 px-4 py-3 dark:border-white/10">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-iris">local</p>
          <h1 className="text-xl font-semibold">{t.app}</h1>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-3 py-1 text-xs ${online === "ok" ? "bg-emerald-500/20" : "bg-white/10"}`}>{statusLabel}</span>
          <button className="rounded-full border border-current/20 px-3 py-1 text-sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "Light" : "Dark"}</button>
          <button className="rounded-full border border-current/20 px-3 py-1 text-sm" onClick={() => setLang(lang === "tr" ? "en" : "tr")}>{lang === "tr" ? "EN" : "TR"}</button>
        </div>
      </header>
      <div className="grid min-h-[calc(100vh-65px)] lg:grid-cols-[220px_1fr]">
        <nav className="flex gap-2 overflow-x-auto border-b border-black/10 p-3 lg:flex-col lg:border-b-0 lg:border-r dark:border-white/10">
          {views.map((item) => (
            <button key={item} className={`rounded-xl px-3 py-2 text-left text-sm ${view === item ? "bg-iris text-white" : "hover:bg-black/5 dark:hover:bg-white/10"}`} onClick={() => setView(item)}>
              {t[item]}
            </button>
          ))}
        </nav>
        <main className="min-w-0 p-4">
          {error && <p className="mb-3 rounded-xl bg-rose-500/15 px-3 py-2 text-sm">{error}</p>}
          {view === "chat" && (
            <section className="grid gap-4 lg:grid-cols-[240px_1fr]">
              <aside className="rounded-2xl border border-black/10 p-3 dark:border-white/10">
                <button className="mb-3 w-full rounded-xl bg-plum px-3 py-2 text-sm text-white" onClick={() => { setSessionId(sessionToken()); setMessages([]); }}>{t.newChat}</button>
                <p className="mb-2 text-xs uppercase tracking-wider opacity-60">{t.history}</p>
                <button className="mb-2 text-xs underline" onClick={() => loadSessions().catch((exc: unknown) => setError(exc instanceof Error ? exc.message : ""))}>{t.refresh}</button>
                <div className="space-y-2">
                  {sessions.map((item) => (
                    <button key={item.session_id || "default"} className="block w-full rounded-xl bg-black/5 px-2 py-2 text-left text-sm dark:bg-white/5" onClick={() => openSession(item.session_id).catch((exc: unknown) => setError(exc instanceof Error ? exc.message : ""))}>
                      <span className="line-clamp-2">{item.preview || item.session_id || "default"}</span>
                    </button>
                  ))}
                </div>
              </aside>
              <div className="flex min-h-[70vh] flex-col">
                <div className={`nova-orb ${recording ? "is-live" : ""}`} aria-hidden="true"><span /></div>
                <div className="flex-1 space-y-3">
                  {messages.length === 0 && <p className="pt-16 text-center opacity-60">{t.empty}</p>}
                  {messages.map((item) => (
                    <article key={item.id} className={`rise max-w-[85%] rounded-2xl px-4 py-3 ${item.role === "user" ? "ml-auto bg-iris text-white" : "bg-white dark:bg-white/5"}`}>
                      {item.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>{item.content}</ReactMarkdown> : <p className="whitespace-pre-wrap">{item.content}</p>}
                      {item.role === "assistant" && (
                        <div className="mt-2 flex gap-3 text-xs opacity-80">
                          <button onClick={() => navigator.clipboard.writeText(item.content)}>{t.copy}</button>
                          <button onClick={() => void speakMessage(item.content, item.language)}>{t.speak}</button>
                          <button onClick={() => window.speechSynthesis.cancel()}>{t.stop}</button>
                        </div>
                      )}
                    </article>
                  ))}
                  {busy && <p className="text-sm opacity-70">{t.loading}</p>}
                </div>
                <form className="mt-4 flex gap-2" onSubmit={(event: FormEvent) => { event.preventDefault(); void send(); }}>
                  <button type="button" className="rounded-xl border border-current/20 px-3" onClick={() => { cancelVoice.current = true; window.speechSynthesis.cancel(); onTalkEnd(); }}>{t.cancel}</button>
                  <button type="button" className={`relative rounded-xl px-3 ${recording ? "bg-rose-600 text-white" : "bg-black/5 dark:bg-white/10"}`} onPointerDown={() => void onTalkStart()} onPointerUp={onTalkEnd} onPointerLeave={onTalkEnd}>
                    {recording && <span className="voice-ring absolute inset-0 rounded-xl border border-rose-300" />}
                    {recording ? t.listening : t.hold}
                  </button>
                  <input className="flex-1 rounded-xl border border-black/10 bg-transparent px-3 py-3 dark:border-white/10" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={t.placeholder} />
                  <button className="rounded-xl bg-iris px-4 text-white" disabled={busy}>{t.send}</button>
                </form>
              </div>
            </section>
          )}
          {view === "memory" && <MemoryPanel connection={connection} label={t} onError={setError} />}
          {view === "gmail" && <GmailPanel connection={connection} label={t} onError={setError} />}
          {view === "contacts" && <ContactsPanel connection={connection} label={t} onError={setError} />}
          {view === "calendar" && <CalendarPanel connection={connection} label={t} onError={setError} />}
          {view === "search" && <SearchPanel connection={connection} label={t} onError={setError} />}
          {view === "integrations" && <IntegrationsPanel connection={connection} label={t} onError={setError} />}
          {view === "social" && <SocialPanel connection={connection} label={t} onError={setError} />}
          {view === "automation" && <AutomationPanel connection={connection} label={t} onError={setError} onUse={(prompt) => { setDraft(prompt); setView("chat"); }} />}
          {view === "settings" && (
            <form className="mx-auto max-w-lg space-y-3" onSubmit={(event) => { event.preventDefault(); storePreferences({ apiUrl, theme, lang, speak: speakReplies, apiKey }); }}>
              <label className="block text-sm">API URL<input className="mt-1 w-full rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={apiUrl} onChange={(event) => setApiUrl(event.target.value)} /></label>
              <label className="block text-sm">X-API-Key<input className="mt-1 w-full rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" type="password" value={apiKey} autoComplete="off" onChange={(event) => setApiKey(event.target.value)} /></label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={speakReplies} onChange={(event) => setSpeakReplies(event.target.checked)} />{t.speak}</label>
              <p className="text-sm opacity-70">{lang === "tr" ? "Anahtar yalnız bu sekmenin oturumunda durur. Uzak erişim varsayılan olarak kapalıdır." : "The key stays in this tab session. Remote access stays off by default."}</p>
              <button className="rounded-xl bg-iris px-4 py-2 text-white">{t.save}</button>
            </form>
          )}
        </main>
      </div>
    </div>
  );
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const value = String(children ?? "");
  return (
    <span className="relative block">
      <button className="absolute right-2 top-2 text-xs" onClick={() => navigator.clipboard.writeText(value)}>copy</button>
      <code className="block overflow-x-auto rounded-xl bg-black/80 p-3 text-sm text-white">{children}</code>
    </span>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rise mx-auto max-w-3xl space-y-3"><h2 className="text-lg font-semibold">{title}</h2>{children}</section>;
}

function MemoryPanel({ connection, label, onError }: PanelProps) {
  const [rows, setRows] = useState<{ id: number; content: string; category: string }[]>([]);
  const [query, setQuery] = useState("");
  async function refresh() {
    try {
      const body = await api<{ memories: { id: number; content: string; category: string }[] }>(connection, "/memory/list");
      setRows(body.memories);
    } catch (exc) { onError(exc instanceof Error ? exc.message : ""); }
  }
  return (
    <Panel title={label.memory}>
      <div className="flex gap-2">
        <button className="rounded-xl bg-iris px-3 py-2 text-sm text-white" onClick={() => void refresh()}>{label.refresh}</button>
        <input className="flex-1 rounded-xl border border-black/10 bg-transparent px-3 dark:border-white/10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={label.search} />
        <button className="rounded-xl border px-3" onClick={() => api<{ memories: { id: number; content: string; category: string }[] }>(connection, "/memory/search", { method: "POST", body: JSON.stringify({ query, limit: 8 }) }).then((body) => setRows(body.memories)).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.search}</button>
      </div>
      {rows.map((row) => (
        <article key={row.id} className="rounded-2xl border border-black/10 p-3 dark:border-white/10">
          <p>{row.content}</p>
          <p className="mt-1 text-xs opacity-60">{row.category}</p>
          <button className="mt-2 text-xs" onClick={() => api(connection, `/memory/${row.id}`, { method: "DELETE" }).then(refresh).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.delete}</button>
        </article>
      ))}
    </Panel>
  );
}

function GmailPanel({ connection, label, onError }: PanelProps) {
  const [rows, setRows] = useState<{ id: string; sender: string; subject: string; snippet: string; date: string }[]>([]);
  const [open, setOpen] = useState("");
  const [body, setBody] = useState("");
  async function load(path: string) {
    try {
      const data = await api<{ emails: typeof rows }>(connection, path);
      setRows(data.emails || []);
    } catch (exc) { onError(exc instanceof Error ? exc.message : ""); }
  }
  return (
    <Panel title={label.gmail}>
      <div className="flex gap-2">
        <button className="rounded-xl bg-iris px-3 py-2 text-sm text-white" onClick={() => void load("/gmail/inbox?limit=10")}>Inbox</button>
        <button className="rounded-xl border px-3" onClick={() => void load("/gmail/unread?limit=10")}>Unread</button>
      </div>
      {rows.map((row) => (
        <article key={row.id} className="rounded-2xl border border-black/10 p-3 dark:border-white/10">
          <p className="font-medium">{row.subject}</p>
          <p className="text-sm opacity-70">{row.sender} · {row.date}</p>
          <p className="mt-1 text-sm">{row.snippet}</p>
          <button className="mt-2 text-xs underline" onClick={() => api<{ email: { body?: string } }>(connection, `/gmail/message/${encodeURIComponent(row.id)}`).then((data) => { setOpen(row.id); setBody(data.email.body || ""); }).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.fullMail}</button>
          {open === row.id && <pre className="mt-2 whitespace-pre-wrap text-sm">{body}</pre>}
        </article>
      ))}
    </Panel>
  );
}

function ContactsPanel({ connection, label, onError }: PanelProps) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<{ name: string; emails: string[] }[]>([]);
  return (
    <Panel title={label.contacts}>
      <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); api<{ contacts: typeof rows }>(connection, `/contacts?q=${encodeURIComponent(query)}&limit=20`).then((data) => setRows(data.contacts)).catch((exc: unknown) => onError(exc instanceof ApiError ? exc.message : "")); }}>
        <input className="flex-1 rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={query} onChange={(event) => setQuery(event.target.value)} />
        <button className="rounded-xl bg-iris px-3 text-white">{label.refresh}</button>
      </form>
      {rows.map((row) => <p key={row.name} className="rounded-xl bg-black/5 px-3 py-2 dark:bg-white/5">{row.name} · {row.emails.join(", ")}</p>)}
    </Panel>
  );
}

function CalendarPanel({ connection, label, onError }: PanelProps) {
  const [events, setEvents] = useState<{ id: string; summary: string; start: string }[]>([]);
  const [summary, setSummary] = useState("");
  const [when, setWhen] = useState("");
  const [proposal, setProposal] = useState("");
  return (
    <Panel title={label.calendar}>
      <button className="rounded-xl bg-iris px-3 py-2 text-sm text-white" onClick={() => api<{ events: typeof events }>(connection, "/calendar/upcoming?days=7").then((data) => setEvents(data.events)).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.refresh}</button>
      {events.map((event) => <p key={event.id || event.summary} className="rounded-xl bg-black/5 px-3 py-2 dark:bg-white/5">{event.start} · {event.summary}</p>)}
      <form className="space-y-2" onSubmit={(event) => { event.preventDefault(); api<{ code?: string; detail?: string }>(connection, "/calendar/propose", { method: "POST", body: JSON.stringify({ action: "create", summary, when }) }).then((data) => setProposal(JSON.stringify(data))).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : "")); }}>
        <input className="w-full rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={summary} onChange={(event) => setSummary(event.target.value)} placeholder={label.calendar} />
        <input className="w-full rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={when} onChange={(event) => setWhen(event.target.value)} placeholder="when" />
        <button className="rounded-xl border px-3 py-2">{label.save}</button>
      </form>
      {proposal && <p className="text-sm">{proposal}</p>}
    </Panel>
  );
}

function SearchPanel({ connection, label, onError }: PanelProps) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<{ title: string; url: string; snippet?: string }[]>([]);
  return (
    <Panel title={label.search}>
      <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); api<{ results: typeof rows }>(connection, `/web/search?q=${encodeURIComponent(query)}`).then((data) => setRows(data.results)).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : "")); }}>
        <input className="flex-1 rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={query} onChange={(event) => setQuery(event.target.value)} />
        <button className="rounded-xl bg-iris px-3 text-white">{label.search}</button>
      </form>
      {rows.map((row) => (
        <a key={row.url} className="block rounded-xl border border-black/10 p-3 dark:border-white/10" href={row.url} target="_blank" rel="noreferrer">
          <p className="font-medium">{row.title}</p>
          <p className="text-xs text-iris">{row.url}</p>
        </a>
      ))}
    </Panel>
  );
}

function IntegrationsPanel({ connection, label, onError }: PanelProps) {
  const [rows, setRows] = useState<[string, string][]>([]);
  const [loading, setLoading] = useState(false);
  return (
    <Panel title={label.integrations}>
      <button className="rounded-xl bg-iris px-3 py-2 text-sm text-white" onClick={() => {
        setLoading(true);
        api<Record<string, unknown>>(connection, "/integrations/status")
          .then((data) => setRows(Object.entries(data).map(([name, value]) => [name, JSON.stringify(value)])))
          .catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))
          .finally(() => setLoading(false));
      }}>{loading ? label.loading : label.refresh}</button>
      {rows.map(([name, detail]) => <p key={name} className="rounded-xl bg-black/5 px-3 py-2 text-sm dark:bg-white/5">{name}: {detail}</p>)}
    </Panel>
  );
}

function SocialPanel({ connection, label, onError }: PanelProps) {
  const [facts, setFacts] = useState<{ platform: string; restriction: string; cost: string; account: string }[]>([]);
  const [draft, setDraft] = useState("");
  const [chatId, setChatId] = useState("");
  const [platform, setPlatform] = useState("telegram");
  const [confirm, setConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  return (
    <Panel title={label.social}>
      <button className="rounded-xl bg-iris px-3 py-2 text-sm text-white" onClick={() => {
        setLoading(true);
        api<{ platforms: typeof facts }>(connection, "/social/platforms")
          .then((data) => setFacts(data.platforms))
          .catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))
          .finally(() => setLoading(false));
      }}>{loading ? label.loading : label.refresh}</button>
      {facts.map((item) => (
        <article key={item.platform} className="rounded-2xl border border-black/10 p-3 text-sm dark:border-white/10">
          <p className="font-medium">{item.platform}</p>
          <p>{item.account}</p>
          <p className="opacity-70">{item.restriction}</p>
          <p className="opacity-70">{item.cost}</p>
        </article>
      ))}
      <textarea className="min-h-24 w-full rounded-xl border border-black/10 bg-transparent p-3 dark:border-white/10" value={draft} onChange={(event) => setDraft(event.target.value)} />
      <div className="flex flex-wrap gap-2">
        <select className="rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={platform} onChange={(event) => setPlatform(event.target.value)}>
          <option value="telegram">Telegram</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="instagram">Instagram</option>
        </select>
        <input className="rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={chatId} onChange={(event) => setChatId(event.target.value)} placeholder="chat id" />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={confirm} onChange={(event) => setConfirm(event.target.checked)} />{label.confirmSend}</label>
        <button className="rounded-xl bg-plum px-3 text-white" onClick={() => api<{ draft: string }>(connection, "/social/draft", { method: "POST", body: JSON.stringify({ text: draft || "merhaba", use_model: false }) }).then((data) => setDraft(data.draft)).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.save}</button>
        <button className="rounded-xl bg-iris px-3 text-white" onClick={() => {
          if (!confirm) { onError(label.confirmSend); return; }
          api(connection, "/social/send", { method: "POST", body: JSON.stringify({ platform, chat_id: chatId, text: draft, confirm: true }) }).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""));
        }}>{label.send}</button>
      </div>
    </Panel>
  );
}

type Job = { id: number; name: string; prompt: string; interval_minutes: number; status: string; next_run_at: string | null };

function AutomationPanel({ connection, label, onError, onUse }: PanelProps & { onUse: (prompt: string) => void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [minutes, setMinutes] = useState(60);
  const [notes, setNotes] = useState<{ id: number; name: string }[]>([]);
  async function refresh() {
    const body = await api<{ automations: Job[] }>(connection, "/automations");
    setJobs(body.automations);
  }
  return (
    <Panel title={label.automation}>
      <div className="flex gap-2">
        <button className="rounded-xl bg-iris px-3 py-2 text-sm text-white" onClick={() => refresh().catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.refresh}</button>
        <button className="rounded-xl border px-3" onClick={() => api<{ notifications: { id: number; name: string }[] }>(connection, "/automations/tick", { method: "POST" }).then((data) => setNotes(data.notifications)).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.check}</button>
      </div>
      <form className="grid gap-2 md:grid-cols-4" onSubmit={(event) => { event.preventDefault(); api(connection, "/automations", { method: "POST", body: JSON.stringify({ name, prompt, interval_minutes: minutes }) }).then(() => refresh()).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : "")); }}>
        <input className="rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={name} onChange={(event) => setName(event.target.value)} placeholder="name" />
        <input className="rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="prompt" />
        <input className="rounded-xl border border-black/10 bg-transparent px-3 py-2 dark:border-white/10" type="number" min={5} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} />
        <button className="rounded-xl bg-plum text-white">{label.save}</button>
      </form>
      {notes.map((note) => <p key={note.id} className="text-sm">{note.name}</p>)}
      {jobs.map((job) => (
        <article key={job.id} className="rounded-2xl border border-black/10 p-3 dark:border-white/10">
          <p className="font-medium">{job.name}</p>
          <p className="text-sm opacity-70">{job.status} · {job.interval_minutes}m · {job.next_run_at || "-"}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <button onClick={() => api(connection, `/automations/${job.id}/status`, { method: "POST", body: JSON.stringify({ status: job.status === "paused" ? "active" : "paused" }) }).then(refresh).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{job.status === "paused" ? label.resume : label.pause}</button>
            <button onClick={() => api<{ prompt: string }>(connection, `/automations/${job.id}/approve`, { method: "POST", body: JSON.stringify({ confirm: true }) }).then((data) => onUse(data.prompt)).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.approve}</button>
            <button onClick={() => api(connection, `/automations/${job.id}`, { method: "DELETE" }).then(refresh).catch((exc: unknown) => onError(exc instanceof Error ? exc.message : ""))}>{label.delete}</button>
          </div>
        </article>
      ))}
    </Panel>
  );
}

type PanelProps = {
  connection: { apiUrl: string; apiKey: string };
  label: ReturnType<typeof text>;
  onError: (value: string) => void;
};
