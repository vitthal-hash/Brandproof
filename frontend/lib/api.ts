export type Json = any;

export function getToken(): string {
  return typeof window === "undefined" ? "" : localStorage.getItem("bp_token") || "";
}

export async function api(path: string, opts: { method?: string; body?: Json; form?: FormData; blob?: boolean } = {}): Promise<Json> {
  const headers: Record<string, string> = {};
  const t = getToken();
  if (t) headers["Authorization"] = "Bearer " + t;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }
  const res = await fetch("/api" + path, { method: opts.method || (body ? "POST" : "GET"), headers, body });
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
