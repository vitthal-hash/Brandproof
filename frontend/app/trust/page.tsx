"use client";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty } from "@/components/ui";
import { api } from "@/lib/api";

const EXPECT: Record<string, string> = { hidden: "Hidden content", lookalike: "Look-alike letters", injection: "AI-reviewer instruction", embedded: "Embedded file", clean: "Must stay clean" };

export default function TrustSuite() {
  const { user } = useUser();
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const run = () => { setBusy(true); setErr(""); api("/trust/suite").then(setR).catch((e) => setErr(e.message)).finally(() => setBusy(false)); };
  useEffect(() => { if (user) run(); }, [user]);
  return (
    <Shell>
      <div className="mx-auto max-w-5xl space-y-5">
        <header>
          <h1 className="text-3xl font-extrabold">Trust Layer tests</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-800">BrandProof generates attack files on the spot (hidden text, look-alike letters, instructions aimed at an AI reviewer) plus clean control files, and scores its own Trust Layer. Misses are shown, not hidden.</p>
        </header>
        {err && <p role="alert" className="font-semibold text-stamp">{err}</p>}
        {!r ? <p className="text-sm text-slate-600">Running the attack files…</p> : (<>
          <div className="grid gap-3 md:grid-cols-3" data-tour="trust-score">
            <div className="card"><div className="text-xs font-semibold uppercase text-slate-600">Attacks caught</div><div className="mt-1 text-3xl font-extrabold">{r.attacks.caught} / {r.attacks.total}</div></div>
            <div className="card"><div className="text-xs font-semibold uppercase text-slate-600">Clean controls left alone</div><div className="mt-1 text-3xl font-extrabold">{r.controls.clean} / {r.controls.total}</div></div>
            <div className="card"><div className="text-xs font-semibold uppercase text-slate-600">Local OCR</div><div className="mt-1 text-lg font-bold">{r.ocr ? "Available" : "Not installed"}</div><p className="mt-1 text-xs text-slate-700">Reads text inside images on this server. Nothing is sent out.</p></div>
          </div>
          {(r.unexpected_misses.length > 0 || r.false_alarms.length > 0) && <p role="alert" className="rounded-md border border-stamp bg-red-50 p-3 text-sm font-semibold text-stamp">Regression: {r.unexpected_misses.length} unexpected miss(es), {r.false_alarms.length} false alarm(s): {[...r.unexpected_misses, ...r.false_alarms].join(", ")}</p>}
          {r.known_gaps.length > 0 && (
            <section className="card" aria-label="Known gaps"><h2 className="font-bold">Known gaps, reported on purpose</h2>
              <ul className="mt-2 space-y-2 text-sm">{r.known_gaps.map((g: any) => <li key={g.id}><Chip tone={g.caught ? "green" : "amber"}>{g.id} {g.caught ? "caught" : "missed"}</Chip> <b>{g.name}.</b> {g.why}</li>)}</ul></section>)}
          <div className="no-print"><button className="btn btn-ghost" disabled={busy} onClick={run}>{busy ? "Running…" : "Run again"}</button></div>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-surface" data-tour="trust-table">
            <table className="w-full"><caption className="sr-only">Attack and control results</caption>
              <thead><tr><th className="th">ID</th><th className="th">Case</th><th className="th">Channel</th><th className="th">Expected</th><th className="th">Result</th></tr></thead>
              <tbody>{r.results.map((x: any) => (
                <tr key={x.id}><td className="td font-mono text-xs">{x.id}</td><td className="td">{x.name}</td><td className="td">{x.channel}</td><td className="td">{EXPECT[x.expect] || x.expect}</td>
                  <td className="td">{x.caught ? <Chip tone="green">{x.control ? "CLEAN" : "CAUGHT"}</Chip> : <Chip tone={x.gap ? "amber" : "red"}>{x.control ? "FALSE ALARM" : "MISSED"}</Chip>}{x.error && <span className="ml-1 text-xs text-stamp">{x.error}</span>}</td></tr>))}</tbody></table>
          </div>
          {r.results.length === 0 && <Empty>No cases.</Empty>}
        </>)}
      </div>
    </Shell>
  );
}