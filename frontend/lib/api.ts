export type Json = any;

export function getToken(): string {
  return typeof window === "undefined" ? "" : localStorage.getItem("bp_token") || "";
}

// Reading data is safe to repeat, so a GET that gets no answer for 25 s is abandoned and tried again (3 attempts).
// Saves are only repeated when the hosting layer answered 502/503/504 (see below), never after a normal answer.
const GET_TIMEOUT_MS = 25000;
const GET_ATTEMPTS = 3;
// The free server sleeps or restarts now and then and answers 502/503/504 while it wakes. Those answers come from the
// hosting layer, so a save sent during that window did not complete. Wait a little and send it again (up to 4 tries).
const WAKE_CODES = [502, 503, 504];
const WAKE_WAITS_MS = [3000, 6000, 10000];
async function sendWithWakeRetry(url: string, init: RequestInit): Promise<Response> {
  for (let attempt = 0; ; attempt++) {
    let res: Response | null = null;
    try { res = await fetch(url, init); } catch { res = null; }
    if (res && !WAKE_CODES.includes(res.status)) return res;
    if (attempt >= WAKE_WAITS_MS.length) {
      if (res) return res;
      throw new Error("The server is not answering. Please wait a minute and try again.");
    }
    await new Promise((r) => setTimeout(r, WAKE_WAITS_MS[attempt]));
  }
}

async function send(url: string, init: RequestInit, canRepeat: boolean): Promise<Response> {
  if (!canRepeat) return sendWithWakeRetry(url, init);
  for (let attempt = 1; ; attempt++) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), GET_TIMEOUT_MS);
    try {
      const r = await fetch(url, { ...init, signal: ctl.signal });
      if (!WAKE_CODES.includes(r.status) || attempt >= GET_ATTEMPTS) return r;   // 502/503/504: the server is waking, try again
    }
    catch { if (attempt >= GET_ATTEMPTS) throw new Error("The server is not answering. Please check your connection and try again."); }
    finally { clearTimeout(timer); }
    await new Promise((r) => setTimeout(r, attempt * 2000));
  }
}

export async function api(path: string, opts: { method?: string; body?: Json; form?: FormData; blob?: boolean } = {}): Promise<Json> {
  const headers: Record<string, string> = {};
  const t = getToken();
  if (t) headers["Authorization"] = "Bearer " + t;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }
  const method = opts.method || (body ? "POST" : "GET");
  const res = await send("/api" + path, { method, headers, body }, method === "GET");
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/login")) {
    localStorage.removeItem("bp_token"); localStorage.removeItem("bp_user");
    window.location.href = "/login";
    throw new Error("Please sign in again");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch { /* ignore */ }
    throw new Error(msg);
  }
  if (opts.blob) return res.blob();
  return res.json();
}

export const ROLE_LABEL: Record<string, string> = {
  creator: "Creator", external: "External contributor", manager: "Brand manager", reviewer: "Authorised reviewer", owner: "Guideline owner",
};