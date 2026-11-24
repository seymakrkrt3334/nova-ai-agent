import { assessApiUrl } from "../assistant/network";
import type { MobileConfig } from "./storage";

export type ConnectionState = "connected" | "unauthorized" | "unreachable" | "rejected" | "missing-key";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
  }
}

export async function request<T>(config: MobileConfig, path: string, init: RequestInit = {}): Promise<T> {
  if (!config.apiKey) throw new ApiError("An API key is required.");
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  headers.set("X-API-Key", config.apiKey);
  let response: Response;
  try {
    response = await fetch(`${config.apiUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("The server could not be reached. Is Tailscale on, and is the address correct?");
  }
  if (response.status === 401 || response.status === 403) {
    throw new ApiError("The API key was rejected.");
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch { /* status only */ }
    throw new ApiError(detail);
  }
  return response.json() as Promise<T>;
}

export async function sendMessage(config: MobileConfig, message: string): Promise<{ reply: string; language: string | null }> {
  const data = await request<{ reply: string; language?: string | null }>(config, "/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: config.sessionId }),
  });
  return { reply: data.reply, language: data.language ?? null };
}

export async function testConnection(config: MobileConfig): Promise<ConnectionState> {
  if (!assessApiUrl(config.apiUrl).ok) return "rejected";
  if (!config.apiKey) return "missing-key";
  try {
    const response = await fetch(`${config.apiUrl.replace(/\/$/, "")}/health`, {
      headers: { "X-API-Key": config.apiKey },
    });
    if (response.ok) return "connected";
    if (response.status === 401 || response.status === 403) return "unauthorized";
    return "unreachable";
  } catch {
    return "unreachable";
  }
}

export async function detectLanguage(config: MobileConfig, text: string): Promise<string | null> {
  const data = await request<{ language?: string | null }>(config, "/language", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  return data.language ?? null;
}
