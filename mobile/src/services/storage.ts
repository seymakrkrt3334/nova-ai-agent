import * as SecureStore from "expo-secure-store";

const URL_KEY = "nova_api_url";
const KEY_KEY = "nova_api_key";
const SESSION_KEY = "nova_session_id";

export type MobileConfig = { apiUrl: string; apiKey: string; sessionId: string };

export async function loadConfig(): Promise<MobileConfig> {
  const [apiUrl, apiKey, sessionId] = await Promise.all([
    SecureStore.getItemAsync(URL_KEY),
    SecureStore.getItemAsync(KEY_KEY),
    SecureStore.getItemAsync(SESSION_KEY),
  ]);
  return {
    apiUrl: apiUrl || "http://127.0.0.1:8001",
    apiKey: apiKey || "",
    sessionId: sessionId || newSession(),
  };
}

export async function saveConfig(config: MobileConfig) {
  await SecureStore.setItemAsync(URL_KEY, config.apiUrl.replace(/\/$/, ""));
  if (config.apiKey) await SecureStore.setItemAsync(KEY_KEY, config.apiKey);
  else await SecureStore.deleteItemAsync(KEY_KEY);
  await SecureStore.setItemAsync(SESSION_KEY, config.sessionId);
}

export function newSession() {
  return `m${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}
