export type Connection = { apiUrl: string; apiKey: string };

const URL_KEY = "nova.apiUrl";
const THEME_KEY = "nova.theme";
const LANG_KEY = "nova.lang";
const SPEAK_KEY = "nova.speak";
const KEY_KEY = "nova.apiKey";

export type Theme = "dark" | "light";
export type Lang = "tr" | "en";

export function loadPreferences() {
  const apiUrl = localStorage.getItem(URL_KEY) || "http://127.0.0.1:8001";
  const theme = (localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark") as Theme;
  const lang = (localStorage.getItem(LANG_KEY) === "en" ? "en" : "tr") as Lang;
  const speak = localStorage.getItem(SPEAK_KEY) === "1";
  const apiKey = sessionStorage.getItem(KEY_KEY) || "";
  return { apiUrl, apiKey, theme, lang, speak };
}

export function storePreferences(values: { apiUrl: string; theme: Theme; lang: Lang; speak: boolean; apiKey: string }) {
  localStorage.setItem(URL_KEY, values.apiUrl.replace(/\/$/, ""));
  localStorage.setItem(THEME_KEY, values.theme);
  localStorage.setItem(LANG_KEY, values.lang);
  localStorage.setItem(SPEAK_KEY, values.speak ? "1" : "0");
  if (values.apiKey) sessionStorage.setItem(KEY_KEY, values.apiKey);
  else sessionStorage.removeItem(KEY_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(connection: Connection, path: string, init: RequestInit = {}): Promise<T> {
  if (!connection.apiKey) throw new ApiError(401, "API anahtarı gerekli.");
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("X-API-Key", connection.apiKey);
  let response: Response;
  try {
    response = await fetch(`${connection.apiUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Bağlantı kurulamadı.");
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch { /* keep status */ }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}
