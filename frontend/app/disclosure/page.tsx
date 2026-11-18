"use client";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Toast } from "@/components/ui";
import { api } from "@/lib/api";

export default function Disclosure() {
  const { user } = useUser();
  const [d, setD] = useState<any>(null);
  const [toast, setToast] = useState({ msg: "", kind: "ok" as "ok" | "error" });
  const load = () => api("/disclosure").then(setD).catch((e) => setToast({ msg: e.message, kind: "error" }));
  useEffect(() => { if (user) load(); }, [user]);
  const set = async (body: any) => {
    try { await api("/settings", { method: "PUT", body }); await load(); setToast({ msg: "Setting saved", kind: "ok" }); }
    catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
  };
  if (!d) return <Shell><p className="text-sm text-slate-600">Loading…</p></Shell>;
  const owner = user?.role === "owner";
  return (
    <Shell>
      <h1 className="mb-5 text-3xl font-extrabold">AI and external-service disclosure</h1>
      <p className="mt-2 max-w-3xl text-sm">{d.ai_note}</p>
      <div className="mt-2">{d.llm_enabled ? <Chip tone="blue">External model: {d.provider} / {d.model}</Chip> : <Chip tone="amber">No external AI configured: heuristic fallback only</Chip>}</div>

      <h2 className="mb-2 mt-6 text-lg font-bold">Services and the data each receives</h2>
      <div className="card overflow-x-auto p-0"><table className="w-full"><thead><tr><th className="th">Service</th><th className="th">Data</th><th className="th">External</th></tr></thead>
        <tbody>{d.services.map((s: any) => <tr key={s.name}><td className="td font-semibold">{s.name}</td><td className="td">{s.data}</td><td className="td">{s.external ? <Chip tone="red">YES</Chip> : <Chip tone="green">No</Chip>}</td></tr>)}</tbody></table></div>

      <h2 className="mb-2 mt-6 text-lg font-bold">Privacy controls</h2>
      <div className="card max-w-3xl space-y-3 text-sm">
        <p>Emails, phone numbers, Aadhaar, PAN and card numbers are replaced by tokens before any text is sent to an external model.</p>
        <label className="flex items-start gap-2"><input type="checkbox" disabled={!owner} checked={d.retention_delete_after_approval} onChange={(e) => set({ retention_delete_after_approval: e.target.checked })} />
          <span><b>Delete content after approval.</b> Files and text are removed when an asset is approved; the Proof Pack and audit log are kept.</span></label>
        <label className="flex items-start gap-2"><input type="checkbox" disabled={!owner || !d.llm_enabled} checked={d.images_to_llm} onChange={(e) => set({ images_to_llm: e.target.checked })} />
          <span><b>Allow images to be read by the AI vision model.</b> Off by default because pixels cannot be redacted. {!d.llm_enabled && "(No model configured.)"}</span></label>
        {!owner && <p className="text-xs text-slate-700">Only the guideline owner can change these settings.</p>}
      </div>

      <h2 className="mb-2 mt-6 text-lg font-bold">Calls by purpose</h2>
      <div className="card overflow-x-auto p-0">{d.calls_by_purpose.length === 0 ? <p className="p-4 text-sm">No external calls have been made.</p> : (
        <table className="w-full"><thead><tr><th className="th">Purpose</th><th className="th">Calls</th><th className="th">Items redacted</th></tr></thead>
          <tbody>{d.calls_by_purpose.map((c: any) => <tr key={c.purpose}><td className="td">{c.purpose}</td><td className="td">{c.calls}</td><td className="td">{c.redactions}</td></tr>)}</tbody></table>)}</div>
      <h2 className="mb-2 mt-6 text-lg font-bold">Recent calls</h2>
      <div className="card overflow-x-auto p-0">{d.calls.length === 0 ? <p className="p-4 text-sm">None.</p> : (
        <table className="w-full"><thead><tr><th className="th">Time</th><th className="th">Model</th><th className="th">Purpose</th><th className="th">Asset</th><th className="th">Chars sent</th><th className="th">Redactions</th><th className="th">Status</th></tr></thead>
          <tbody>{d.calls.map((c: any, i: number) => <tr key={i}><td className="td">{c.ts.replace("T", " ")}</td><td className="td">{c.provider}/{c.model}</td><td className="td">{c.purpose}</td><td className="td">{c.asset_id ?? "-"}</td><td className="td">{c.chars}</td><td className="td">{c.redactions}</td><td className="td">{c.status}</td></tr>)}</tbody></table>)}</div>
      <Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} />
    </Shell>
  );
}
