import { Platform } from "react-native";
import type { PhoneAction } from "./commands";

type RawNova = {
  listen: () => Promise<{ text: string }>;
  perform: (request: string) => Promise<{ ok: boolean; detail: string }>;
  speak: (text: string, language: string) => Promise<{ ok: boolean; turkishVoice: boolean }>;
  requestAssistant: () => Promise<{ ok: boolean }>;
  setBackgroundListening: (enabled: boolean) => Promise<{ ok: boolean }>;
  installTurkishVoice: () => Promise<{ ok: boolean }>;
};

function load(): RawNova | null {
  if (Platform.OS !== "android") return null;
  try {
    const { requireNativeModule } = require("expo-modules-core") as { requireNativeModule: (name: string) => RawNova };
    return requireNativeModule("NovaAssistant");
  } catch {
    return null;
  }
}

export function nativeAssistant() {
  const raw = load();
  if (!raw) return null;
  return {
    listen: () => raw.listen(),
    perform: (action: PhoneAction) => raw.perform(JSON.stringify(action)),
    speak: (text: string, language: string) => raw.speak(text, language),
    requestAssistant: () => raw.requestAssistant(),
    setBackgroundListening: (enabled: boolean) => raw.setBackgroundListening(enabled),
    installTurkishVoice: () => raw.installTurkishVoice(),
  };
}
