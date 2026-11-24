import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Animated, KeyboardAvoidingView, Modal, PermissionsAndroid, Platform, Pressable, ScrollView, StatusBar as NativeStatusBar, StyleSheet, Text, TextInput, View } from "react-native";
import { Audio } from "expo-av";
import * as Speech from "expo-speech";
import { StatusBar } from "expo-status-bar";
import { interpret, pendingFrom, type Pending } from "./src/assistant/commands";
import { nativeAssistant } from "./src/assistant/native";
import { assessApiUrl, tailscaleApiUrl } from "./src/assistant/network";
import { detectLanguage, request, sendMessage, testConnection, type ConnectionState } from "./src/services/api";
import { loadConfig, newSession, saveConfig, type MobileConfig } from "./src/services/storage";

type Screen = "chat" | "history" | "memory" | "gmail" | "contacts" | "calendar" | "search" | "automation" | "social" | "voice" | "settings";
type Bubble = { id: string; role: "user" | "assistant"; content: string; language?: string | null; failed?: boolean; retryText?: string };
type LinkState = ConnectionState | "checking";

const menuScreens: Screen[] = ["history", "memory", "gmail", "contacts", "calendar", "search", "automation", "social", "settings"];
const labels = {
  tr: {
    chat: "Sohbet", history: "Geçmiş", memory: "Hafıza", gmail: "Gmail", contacts: "Kişiler", calendar: "Takvim", search: "Arama", automation: "Otomasyon", social: "Sosyal", voice: "Ses", settings: "Ayarlar",
    send: "Gönder", hold: "Basılı tut", stop: "Durdur", empty: "NOVA'ya yazın", key: "API anahtarı", menu: "Menü", test: "Bağlantıyı dene", retry: "Yeniden dene",
    connected: "Bağlı", disconnected: "Bağlı değil", checking: "Kontrol ediliyor", unauthorized: "Anahtar reddedildi", missing: "Anahtar gerekli", rejected: "Adres reddedildi",
    useTailscale: "Tailscale adresini kullan", newChat: "Yeni sohbet", talk: "Konuş", mic: "Mikrofon", back: "Sohbet",
    assistant: "Varsayılan asistan ol", listenOn: "Kilit ekranı dinlemesini aç", listenOff: "Dinlemeyi kapat", turkishVoice: "Türkçe ses verisini yükle",
    voiceHint: "Mikrofon tek seferlik dinler. Ses kaydı sürekli yüklenmez. NOVA, Hi NOVA ve Hey NOVA yerelde tanınır.",
    theme: "Tema", language: "Dil",
  },
  en: {
    chat: "Chat", history: "History", memory: "Memory", gmail: "Gmail", contacts: "Contacts", calendar: "Calendar", search: "Search", automation: "Automation", social: "Social", voice: "Voice", settings: "Settings",
    send: "Send", hold: "Hold", stop: "Stop", empty: "Message NOVA", key: "API key", menu: "Menu", test: "Test connection", retry: "Retry",
    connected: "Connected", disconnected: "Disconnected", checking: "Checking", unauthorized: "Key rejected", missing: "Key required", rejected: "Address rejected",
    useTailscale: "Use Tailscale address", newChat: "New chat", talk: "Talk", mic: "Microphone", back: "Chat",
    assistant: "Become the default assistant", listenOn: "Enable locked-screen listening", listenOff: "Stop listening", turkishVoice: "Install Turkish voice data",
    voiceHint: "The microphone listens once. Audio is not uploaded continuously. NOVA, Hi NOVA, and Hey NOVA are recognized locally.",
    theme: "Theme", language: "Language",
  },
};

function palette(dark: boolean) {
  return dark
    ? { bg: "#07060d", text: "#f6f1ff", muted: "#b7a8cf", card: "#1c122b", user: "#6d28d9", input: "#241833", line: "#3a2758", danger: "#fb7185", nav: "#100818" }
    : { bg: "#f7f4fb", text: "#1b1228", muted: "#6d5c82", card: "#ffffff", user: "#6d28d9", input: "#ffffff", line: "#e6def2", danger: "#be123c", nav: "#ffffff" };
}

function statusText(state: LinkState, lang: "tr" | "en") {
  const copy = labels[lang];
  if (state === "connected") return copy.connected;
  if (state === "checking") return copy.checking;
  if (state === "unauthorized") return copy.unauthorized;
  if (state === "missing-key") return copy.missing;
  if (state === "rejected") return copy.rejected;
  return copy.disconnected;
}

function VoiceOrb({ active, onPress }: { active: boolean; onPress: () => void }) {
  const scale = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(scale, { toValue: active ? 1.12 : 1.05, duration: 900, useNativeDriver: true }),
      Animated.timing(scale, { toValue: 1, duration: 900, useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [active, scale]);
  return (
    <Pressable onPress={onPress} style={styles.orbWrap}>
      <Animated.View style={[styles.orbGlow, { transform: [{ scale }] }]} />
      <Animated.View style={[styles.orb, active && styles.orbOn, { transform: [{ scale }] }]} />
    </Pressable>
  );
}

function TypingDots() {
  const opacity = useRef(new Animated.Value(0.3)).current;
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(opacity, { toValue: 1, duration: 450, useNativeDriver: true }),
      Animated.timing(opacity, { toValue: 0.3, duration: 450, useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [opacity]);
  return <Animated.Text style={[styles.typing, { opacity }]}>• • •</Animated.Text>;
}

export default function App() {
  const [config, setConfig] = useState<MobileConfig | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [lang, setLang] = useState<"tr" | "en">("en");
  const [screen, setScreen] = useState<Screen>("chat");
  const [menu, setMenu] = useState(false);
  const [messages, setMessages] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rows, setRows] = useState<string[]>([]);
  const [recording, setRecording] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [link, setLink] = useState<LinkState>("checking");
  const recorder = useRef<Audio.Recording | null>(null);
  const scroller = useRef<ScrollView>(null);
  const copy = labels[lang];
  const dark = theme === "dark";
  const colors = palette(dark);
  const topInset = Platform.OS === "android" ? (NativeStatusBar.currentHeight ?? 28) : 0;

  useEffect(() => {
    void loadConfig().then((next) => {
      setConfig(next);
      void probe(next);
    });
  }, []);

  async function probe(next: MobileConfig) {
    setLink("checking");
    setLink(await testConnection(next));
  }

  async function update(next: MobileConfig) {
    setConfig(next);
    await saveConfig(next);
    await probe(next);
  }

  async function say(text: string, language?: string | null) {
    const native = nativeAssistant();
    if (native) {
      await native.speak(text, language || "");
      return;
    }
    Speech.speak(text, { language: language === "en" ? "en-US" : language === "tr" ? "tr-TR" : undefined });
  }

  async function submit(text = input.trim(), speakAfter = false) {
    if (!config || !text || loading) return;
    setInput("");
    setError("");
    setMessages((prev) => [...prev, { id: `${Date.now()}-u`, role: "user", content: text }]);
    setLoading(true);
    try {
      const result = await sendMessage(config, text);
      setMessages((prev) => [...prev, { id: `${Date.now()}-a`, role: "assistant", content: result.reply, language: result.language }]);
      setLink("connected");
      if (speakAfter && result.reply) await say(result.reply, result.language);
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : (lang === "tr" ? "İstek tamamlanamadı." : "The request could not be completed.");
      setMessages((prev) => [...prev, { id: `${Date.now()}-e`, role: "assistant", content: message, failed: true, retryText: text }]);
      setLink(message.includes("anahtar") || message.toLowerCase().includes("key") ? "unauthorized" : "unreachable");
    } finally {
      setLoading(false);
    }
  }

  async function handleUtterance(text: string) {
    const action = interpret(text, pending);
    setPending(pendingFrom(action));
    if (action.type === "chat") {
      await submit(text, true);
      return;
    }
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-u`, role: "user", content: text },
      { id: `${Date.now()}-a`, role: "assistant", content: action.reply, language: action.language },
    ]);
    setScreen("chat");
    const native = nativeAssistant();
    if (action.delivery !== "none") {
      if (!native) {
        setError(lang === "tr" ? "Arama, kişi, alarm ve uygulama açma NOVA APK içinde çalışır." : "Calls, contacts, alarms, and app launching run in the NOVA APK.");
      } else {
        if (Platform.OS === "android") {
          await PermissionsAndroid.requestMultiple([
            PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
            PermissionsAndroid.PERMISSIONS.READ_CONTACTS,
            PermissionsAndroid.PERMISSIONS.CALL_PHONE,
            PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
          ]);
        }
        const result = await native.perform(action);
        if (!result.ok) setError(result.detail);
      }
    }
    if (action.reply) await say(action.reply, action.language);
  }

  async function load(path: string, pick: (body: Record<string, unknown>) => string[]) {
    if (!config) return;
    setError("");
    try {
      const body = await request<Record<string, unknown>>(config, path);
      setRows(pick(body));
      setLink("connected");
    } catch (exc) {
      setRows([]);
      setError(exc instanceof Error ? exc.message : (lang === "tr" ? "İstek tamamlanamadı." : "The request could not be completed."));
    }
  }

  async function startTalk() {
    const native = nativeAssistant();
    if (native) {
      setRecording(true);
      try {
        const heard = await native.listen();
        await handleUtterance(heard.text);
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : (lang === "tr" ? "Ses dinlenemedi." : "Listening failed."));
      } finally {
        setRecording(false);
      }
      return;
    }
    const permission = await Audio.requestPermissionsAsync();
    if (!permission.granted) {
      setError(lang === "tr" ? "Mikrofon izni verilmedi." : "Microphone permission was denied.");
      return;
    }
    await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true, staysActiveInBackground: false });
    const next = new Audio.Recording();
    await next.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
    await next.startAsync();
    recorder.current = next;
    setRecording(true);
  }

  async function stopTalk() {
    const current = recorder.current;
    if (!current || !config) return;
    recorder.current = null;
    setRecording(false);
    await current.stopAndUnloadAsync();
    const uri = current.getURI();
    if (!uri) return;
    try {
      const file = await fetch(uri);
      const blob = await file.blob();
      const body = await request<{ text: string; language?: string | null }>(config, "/voice/transcribe", {
        method: "POST",
        body: blob,
        headers: { "Content-Type": "audio/m4a" },
      });
      await handleUtterance(body.text);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : (lang === "tr" ? "Ses çevrilemedi." : "The recording could not be transcribed."));
    }
  }

  async function speakReply(item: Bubble) {
    let language = item.language;
    if (language !== "tr" && language !== "en" && config) {
      try {
        language = await detectLanguage(config, item.content);
      } catch {
        language = null;
      }
    }
    await say(item.content, language);
  }

  function openMenuScreen(next: Screen) {
    setMenu(false);
    setRows([]);
    setScreen(next);
  }

  if (!config) {
    return (
      <View style={[styles.page, styles.boot, { paddingTop: topInset }]}>
        <ActivityIndicator color="#7c3aed" />
      </View>
    );
  }

  const dot = link === "connected" ? "#34d399" : link === "checking" ? "#fbbf24" : "#fb7185";

  return (
    <KeyboardAvoidingView style={[styles.page, { backgroundColor: colors.bg, paddingTop: topInset }]} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <StatusBar style={dark ? "light" : "dark"} />
      <View style={styles.header}>
        <View>
          <Text style={[styles.title, { color: colors.text }]}>NOVA</Text>
          <View style={styles.statusRow}>
            <View style={[styles.dot, { backgroundColor: dot }]} />
            <Text style={[styles.status, { color: colors.muted }]}>{statusText(link, lang)}</Text>
          </View>
        </View>
        {screen !== "chat" && screen !== "voice" ? (
          <Pressable onPress={() => setScreen("chat")}><Text style={styles.link}>{copy.back}</Text></Pressable>
        ) : null}
      </View>
      {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}

      <View style={styles.body}>
        {screen === "chat" && (
          <ScrollView ref={scroller} style={styles.fill} contentContainerStyle={styles.thread} onContentSizeChange={() => scroller.current?.scrollToEnd({ animated: true })}>
            {messages.length === 0 && <Text style={[styles.muted, { color: colors.muted }]}>{copy.empty}</Text>}
            {messages.map((item) => (
              <View key={item.id} style={[styles.bubble, item.role === "user" ? styles.userBubble : { backgroundColor: colors.card }]}>
                <Text style={[styles.bubbleText, { color: item.role === "user" ? "#fff" : colors.text }]}>{item.content}</Text>
                {item.role === "assistant" && !item.failed && (
                  <View style={styles.row}>
                    <Pressable onPress={() => void speakReply(item)}><Text style={styles.link}>{copy.voice}</Text></Pressable>
                    <Pressable onPress={() => Speech.stop()}><Text style={styles.link}>{copy.stop}</Text></Pressable>
                  </View>
                )}
                {item.failed && item.retryText ? (
                  <Pressable onPress={() => void submit(item.retryText, false)}><Text style={styles.link}>{copy.retry}</Text></Pressable>
                ) : null}
              </View>
            ))}
            {loading && <View style={[styles.bubble, { backgroundColor: colors.card }]}><TypingDots /></View>}
          </ScrollView>
        )}

        {screen === "voice" && (
          <ScrollView contentContainerStyle={styles.voicePage}>
            <Text style={[styles.muted, { color: colors.muted, textAlign: "center" }]}>{copy.voiceHint}</Text>
            <VoiceOrb active={recording} onPress={() => void startTalk()} />
            <View style={styles.row}>
              <Pressable style={styles.action} onPressIn={() => void startTalk()} onPressOut={() => void stopTalk()}><Text style={styles.actionText}>{recording ? copy.stop : copy.mic}</Text></Pressable>
              <Pressable style={styles.action} onPress={() => void startTalk()}><Text style={styles.actionText}>{copy.talk}</Text></Pressable>
            </View>
            <Pressable style={styles.quiet} onPress={() => void nativeAssistant()?.requestAssistant()}><Text style={{ color: colors.text }}>{copy.assistant}</Text></Pressable>
            <Pressable style={styles.quiet} onPress={() => void nativeAssistant()?.setBackgroundListening(true)}><Text style={{ color: colors.text }}>{copy.listenOn}</Text></Pressable>
            <Pressable style={styles.quiet} onPress={() => void nativeAssistant()?.setBackgroundListening(false)}><Text style={{ color: colors.text }}>{copy.listenOff}</Text></Pressable>
            <Pressable style={styles.quiet} onPress={() => void nativeAssistant()?.installTurkishVoice()}><Text style={{ color: colors.text }}>{copy.turkishVoice}</Text></Pressable>
          </ScrollView>
        )}

        {screen !== "chat" && screen !== "voice" && (
          <ScrollView contentContainerStyle={styles.feature}>
            {screen === "history" && <Pressable style={styles.action} onPress={() => load(`/memory/history?limit=40&session_id=${encodeURIComponent(config.sessionId)}`, (body) => ((body.messages as { role: string; content: string }[]) || []).map((item) => `${item.role}: ${item.content}`))}><Text style={styles.actionText}>{copy.history}</Text></Pressable>}
            {screen === "memory" && <Pressable style={styles.action} onPress={() => load("/memory/list", (body) => ((body.memories as { category: string; content: string }[]) || []).map((item) => `${item.category}: ${item.content}`))}><Text style={styles.actionText}>{copy.memory}</Text></Pressable>}
            {screen === "gmail" && <Pressable style={styles.action} onPress={() => load("/gmail/inbox?limit=10", (body) => ((body.emails as { subject: string; sender: string }[]) || []).map((item) => `${item.subject} — ${item.sender}`))}><Text style={styles.actionText}>{copy.gmail}</Text></Pressable>}
            {screen === "contacts" && <Pressable style={styles.action} onPress={() => load("/contacts?limit=20", (body) => ((body.contacts as { name: string }[]) || []).map((item) => item.name))}><Text style={styles.actionText}>{copy.contacts}</Text></Pressable>}
            {screen === "calendar" && <Pressable style={styles.action} onPress={() => load("/calendar/upcoming?days=7", (body) => ((body.events as { start: string; summary: string }[]) || []).map((item) => `${item.start} ${item.summary}`))}><Text style={styles.actionText}>{copy.calendar}</Text></Pressable>}
            {screen === "search" && <SearchBox onSearch={(query) => load(`/web/search?q=${encodeURIComponent(query)}`, (body) => ((body.results as { title: string; url: string }[]) || []).map((item) => `${item.title}\n${item.url}`))} />}
            {screen === "automation" && <Pressable style={styles.action} onPress={() => load("/automations", (body) => ((body.automations as { name: string; status: string }[]) || []).map((item) => `${item.name} · ${item.status}`))}><Text style={styles.actionText}>{copy.automation}</Text></Pressable>}
            {screen === "social" && <Pressable style={styles.action} onPress={() => load("/social/platforms", (body) => ((body.platforms as { platform: string; restriction: string }[]) || []).map((item) => `${item.platform}: ${item.restriction}`))}><Text style={styles.actionText}>{copy.social}</Text></Pressable>}
            {screen === "settings" && (
              <View style={{ gap: 10 }}>
                <Text style={[styles.muted, { color: colors.muted }]}>{assessApiUrl(config.apiUrl).ok ? statusText(link, lang) : copy.rejected}</Text>
                <TextInput style={[styles.input, { backgroundColor: colors.input, color: colors.text, borderColor: colors.line }]} value={config.apiUrl} autoCapitalize="none" autoCorrect={false} onChangeText={(apiUrl) => setConfig({ ...config, apiUrl })} placeholder={tailscaleApiUrl} placeholderTextColor={colors.muted} />
                <TextInput style={[styles.input, { backgroundColor: colors.input, color: colors.text, borderColor: colors.line }]} value={config.apiKey} secureTextEntry autoCapitalize="none" autoCorrect={false} onChangeText={(apiKey) => setConfig({ ...config, apiKey })} placeholder={copy.key} placeholderTextColor={colors.muted} />
                <Pressable style={styles.action} onPress={() => void update(config)}><Text style={styles.actionText}>{copy.test}</Text></Pressable>
                <Pressable style={styles.quiet} onPress={() => void update({ ...config, apiUrl: tailscaleApiUrl })}><Text style={{ color: colors.text }}>{copy.useTailscale}</Text></Pressable>
                <Pressable style={styles.quiet} onPress={() => void update({ ...config, sessionId: newSession() })}><Text style={{ color: colors.text }}>{copy.newChat}</Text></Pressable>
                <View style={styles.row}>
                  <Pressable onPress={() => setTheme(dark ? "light" : "dark")}><Text style={styles.link}>{copy.theme}: {theme}</Text></Pressable>
                  <Pressable onPress={() => setLang(lang === "tr" ? "en" : "tr")}><Text style={styles.link}>{copy.language}: {lang.toUpperCase()}</Text></Pressable>
                </View>
                <Text style={[styles.muted, { color: colors.muted }]}>{lang === "tr" ? "PostgreSQL ve Ollama telefona açılmaz. Sohbet yalnız bu API adresine gider." : "PostgreSQL and Ollama stay closed to the phone. Chat uses only this API address."}</Text>
              </View>
            )}
            {rows.map((row) => <Text key={row} style={[styles.card, { color: colors.text, backgroundColor: colors.card }]}>{row}</Text>)}
          </ScrollView>
        )}
      </View>

      {screen === "chat" && (
        <View style={[styles.composer, { borderTopColor: colors.line }]}>
          <TextInput style={[styles.input, styles.composerInput, { backgroundColor: colors.input, color: colors.text, borderColor: colors.line }]} value={input} onChangeText={setInput} placeholder={copy.empty} placeholderTextColor={colors.muted} />
          <Pressable style={styles.mic} onPressIn={() => void startTalk()} onPressOut={() => void stopTalk()}><Text style={styles.actionText}>{recording ? "●" : "🎤"}</Text></Pressable>
          <Pressable style={styles.send} onPress={() => void submit()}><Text style={styles.actionText}>{copy.send}</Text></Pressable>
        </View>
      )}

      <View style={[styles.nav, { backgroundColor: colors.nav, borderTopColor: colors.line }]}>
        <Pressable style={styles.navItem} onPress={() => setScreen("chat")}><Text style={[styles.navText, screen === "chat" && { color: dark ? "#f5f3ff" : "#5b21b6" }]}>{copy.chat}</Text></Pressable>
        <Pressable style={styles.navItem} onPress={() => setScreen("voice")}><Text style={styles.navOrb}>●</Text><Text style={[styles.navText, screen === "voice" && { color: dark ? "#f5f3ff" : "#5b21b6" }]}>{copy.voice}</Text></Pressable>
        <Pressable style={styles.navItem} onPress={() => setMenu(true)}><Text style={styles.navText}>{copy.menu}</Text></Pressable>
      </View>

      <Modal visible={menu} transparent animationType="fade" onRequestClose={() => setMenu(false)}>
        <View style={styles.modal}>
          <View style={[styles.drawer, { backgroundColor: colors.bg, paddingTop: topInset + 16 }]}>
            <Text style={[styles.title, { color: colors.text }]}>NOVA</Text>
            {menuScreens.map((item) => (
              <Pressable key={item} style={styles.menuItem} onPress={() => openMenuScreen(item)}>
                <Text style={{ color: colors.text, fontSize: 16 }}>{copy[item]}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable style={styles.scrim} onPress={() => setMenu(false)} />
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

function SearchBox({ onSearch }: { onSearch: (query: string) => void }) {
  const [query, setQuery] = useState("");
  return (
    <View style={styles.row}>
      <TextInput style={[styles.input, { flex: 1 }]} value={query} onChangeText={setQuery} />
      <Pressable style={styles.action} onPress={() => onSearch(query)}><Text style={styles.actionText}>Web</Text></Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1 },
  boot: { alignItems: "center", justifyContent: "center", backgroundColor: "#07060d" },
  fill: { flex: 1 },
  header: { height: 64, paddingHorizontal: 18, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  title: { fontSize: 22, fontWeight: "700", letterSpacing: 0.4 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 2 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  status: { fontSize: 12 },
  error: { marginHorizontal: 18, marginBottom: 6, fontSize: 13 },
  body: { flex: 1 },
  thread: { paddingHorizontal: 16, paddingBottom: 16, gap: 10 },
  bubble: { maxWidth: "86%", borderRadius: 18, paddingHorizontal: 14, paddingVertical: 10 },
  userBubble: { alignSelf: "flex-end", backgroundColor: "#6d28d9", borderBottomRightRadius: 6 },
  bubbleText: { fontSize: 16, lineHeight: 22 },
  typing: { color: "#c4b5fd", fontSize: 18, letterSpacing: 2 },
  row: { flexDirection: "row", alignItems: "center", gap: 12, marginTop: 8 },
  link: { color: "#c4b5fd", fontWeight: "600" },
  muted: { fontSize: 14, lineHeight: 20 },
  composer: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 12, paddingVertical: 8, borderTopWidth: StyleSheet.hairlineWidth },
  input: { borderWidth: 1, borderColor: "#d9d0e6", borderRadius: 16, paddingHorizontal: 14, paddingVertical: 10, fontSize: 16 },
  composerInput: { flex: 1, maxHeight: 48 },
  mic: { width: 44, height: 44, borderRadius: 22, backgroundColor: "#4c1d95", alignItems: "center", justifyContent: "center" },
  send: { height: 44, borderRadius: 22, backgroundColor: "#6d28d9", paddingHorizontal: 14, alignItems: "center", justifyContent: "center" },
  action: { borderRadius: 14, backgroundColor: "#6d28d9", paddingHorizontal: 16, paddingVertical: 12, alignItems: "center" },
  actionText: { color: "#fff", fontWeight: "700" },
  quiet: { borderRadius: 14, paddingHorizontal: 14, paddingVertical: 12 },
  nav: { height: 64, borderTopWidth: StyleSheet.hairlineWidth, flexDirection: "row", alignItems: "center" },
  navItem: { flex: 1, alignItems: "center", justifyContent: "center", height: 64 },
  navText: { color: "#a78bfa", fontSize: 12, fontWeight: "600" },
  navOn: { color: "#f5f3ff" },
  navOrb: { color: "#7c3aed", fontSize: 18, lineHeight: 20 },
  voicePage: { alignItems: "center", padding: 20, gap: 12 },
  orbWrap: { width: 180, height: 180, alignItems: "center", justifyContent: "center", marginVertical: 12 },
  orbGlow: { position: "absolute", width: 168, height: 168, borderRadius: 84, backgroundColor: "#7c3aed", opacity: 0.28 },
  orb: { width: 128, height: 128, borderRadius: 64, backgroundColor: "#5b21b6" },
  orbOn: { backgroundColor: "#a855f7" },
  feature: { padding: 16, gap: 10 },
  card: { borderRadius: 14, padding: 12, fontSize: 14, lineHeight: 20 },
  modal: { flex: 1, flexDirection: "row" },
  drawer: { width: 280, paddingTop: 48, paddingHorizontal: 18, gap: 4 },
  menuItem: { paddingVertical: 14 },
  scrim: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)" },
});
