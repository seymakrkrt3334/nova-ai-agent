const TAILSCALE = /^100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./;

export const tailscaleApiUrl = "http://100.127.242.84:8001";

export function assessApiUrl(value: string): { ok: boolean; kind: "local" | "tailscale" | "rejected" } {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return { ok: false, kind: "rejected" };
  }
  if (url.username || url.password) return { ok: false, kind: "rejected" };
  const host = url.hostname.toLowerCase();
  if (host === "0.0.0.0" || host === "::") return { ok: false, kind: "rejected" };
  if (host === "127.0.0.1" || host === "localhost") return { ok: true, kind: "local" };
  if (host.endsWith(".ts.net") && url.protocol === "https:") return { ok: true, kind: "tailscale" };
  if (TAILSCALE.test(host) && (url.protocol === "http:" || url.protocol === "https:")) return { ok: true, kind: "tailscale" };
  return { ok: false, kind: "rejected" };
}
