"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty, Toast } from "@/components/ui";
import { api } from "@/lib/api";
import { ScheduleCard } from "@/components/FactImport";

export default function Stale() {
  const { user } = useUser();
  const [rows, setRows] = useState<any[] | null>(null);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState({ msg: "", kind: "ok" as "ok" | "error" });
  const load = () => api("/stale").then(setRows).catch((e) => setToast({ msg: e.message, kind: "error" }));
  useEffect(() => { if (user) load(); }, [user]);
  const scan = async () => {
    setBusy(true);
    try { const r = await api("/stale/scan", { method: "POST" }); await load(); setToast({ msg: r.new_alerts ? `${r.new_alerts} new alert(s)` : "No new stale approvals", kind: "ok" }); }
    catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
    setBusy(false);
  };
  const dismiss = async (id: number) => {
    try { await api(`/stale/${id}/dismiss`, { method: "POST", body: { note: notes[id] || "" } }); await load(); setToast({ msg: "Alert dismissed and logged", kind: "ok" }); }
    catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
  };
  return (
    <Shell>
      <div className="mx-auto max-w-5xl space-y-5">
        <ScheduleCard />
        <div data-tour="stale-intro" className="space-y-5">
        <header>
          <h1 className="text-3xl font-extrabold">Stale approvals</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-800">
            When a fact changes or expires, BrandProof re-checks every approved asset against the current Fact Vault. Nothing is changed automatically: the asset stays approved until a person adds a new version or explains why it is still fine.
          </p>
        </header>
        <div className="no-print"><button className="btn btn-ghost" disabled={busy} onClick={scan}>{busy ? "Scanning…" : "Scan approved assets now"}</button></div>
        </div>
        <div data-tour="stale-list">
        {!rows ? <p className="text-sm text-slate-600">Loading…</p> : rows.length === 0 ? <Empty>No open alerts. Every approved asset still matches the current facts.</Empty> : (
          <ul className="space-y-3">{rows.map((x) => (
            <li key={x.id} className="card">
              <div className="flex flex-wrap items-center gap-2">
                <Chip tone="red">{x.now.toUpperCase()}</Chip>
                <Link className="font-bold underline" href={`/assets/${x.asset_id}`}>{x.asset_title || `Asset #${x.asset_id}`}</Link>
                <span className="text-xs text-slate-700">v{x.version}, was {x.was}{x.fact ? `, now judged by ${x.fact}` : ""}</span>
              </div>
              <p className="mt-2 text-sm"><b>Claim:</b> “{x.claim}”</p>
              {x.reason && <p className="mt-1 text-sm text-slate-800">{x.reason}</p>}
              <p className="mt-1 text-xs text-slate-600">Raised by: {x.trigger}</p>
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <label className="flex-1 text-sm"><span className="font-semibold">Still fine? Say why (logged)</span>
                  <input className="input mt-1 w-full" value={notes[x.id] || ""} onChange={(e) => setNotes({ ...notes, [x.id]: e.target.value })} placeholder="e.g. Legal confirmed the old rate applies to this campaign" /></label>
                <button className="btn btn-ghost" onClick={() => dismiss(x.id)}>Dismiss with reason</button>
                <Link className="btn btn-primary" href={`/assets/${x.asset_id}`}>Open asset to add a new version</Link>
              </div>
            </li>))}</ul>)}
        </div>
        <Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} />
      </div>
    </Shell>
  );
}