"use client";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip } from "@/components/ui";
import { api } from "@/lib/api";

const pct = (x: number | null | undefined) => (x === null || x === undefined ? "n/a" : `${Math.round(x * 100)}%`);
const ci = (c?: number[]) => (c ? `${pct(c[0])} to ${pct(c[1])}` : "");

function Stat({ label, value, interval, hint }: { label: string; value: string; interval?: number[]; hint?: string }) {
  return (
    <div className="card">
      <div className="text-xs font-semibold uppercase text-slate-600">{label}</div>
      <div className="mt-1 text-3xl font-extrabold">{value}</div>
      {interval && <div className="text-xs text-slate-700">95% interval: {ci(interval)}</div>}
      {hint && <p className="mt-1 text-xs text-slate-700">{hint}</p>}
    </div>
  );
}

function SetCard({ title, blurb, d }: { title: string; blurb: string; d: any }) {
  if (!d) return null;
  const lists: [string, string[], string][] = [
    ["Missed rules", d.misses || [], "red"], ["False positives", d.false_positives || [], "amber"], ["Claim verdict misses", d.claim_misses || [], "red"],
  ];
  return (
    <section className="space-y-3" aria-label={title}>
      <div><h2 className="text-xl font-extrabold">{title}</h2><p className="max-w-3xl text-sm text-slate-800">{blurb}</p></div>
      <div className="grid gap-3 md:grid-cols-4" data-tour="eval-stats">
        <Stat label="Items" value={String(d.items)} />
        <Stat label="Precision" value={pct(d.precision)} interval={d.precision_ci} />
        <Stat label="Recall" value={pct(d.recall)} interval={d.recall_ci} />
        <Stat label="Attacks caught" value={d.injection_resistance} interval={d.attack_ci} hint={`Clean controls left alone: ${d.clean_controls_with_zero_findings}`} />
      </div>
      <div className="grid gap-3 md:grid-cols-3" data-tour="eval-misses">
        {lists.map(([name, rows, tone]) => (
          <div key={name} className="card">
            <h3 className="font-bold">{name} <Chip tone={rows.length ? tone : "green"}>{rows.length}</Chip></h3>
            {rows.length === 0 ? <p className="mt-1 text-sm text-slate-700">None in this set.</p> :
              <ul className="mt-2 space-y-1 text-sm">{rows.map((x) => <li key={x} className="font-mono text-xs">{x}</li>)}</ul>}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function Evaluation() {
  const { user } = useUser();
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { if (user) api("/eval").then(setR).catch((e) => setErr(e.message)); }, [user]);
  return (
    <Shell>
      <div className="mx-auto max-w-6xl space-y-8">
        <header>
          <h1 className="text-3xl font-extrabold">Evaluation</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-800">
            BrandProof scores itself on three sets and publishes the misses. Intervals show how much a small sample can be trusted: 5 of 5 is not proof of 100%.
          </p>
        </header>
        {err && <p role="alert" className="font-semibold text-stamp">{err}</p>}
        {!r ? <p className="text-sm text-slate-600">Loading results…</p> : (<>
          <p className="rounded-md border border-slate-300 bg-surface p-3 text-sm">{r.note}</p>
          <SetCard title="Blind set (hardest, engine not tuned to it)" blurb="Written after the engine was frozen. Expected labels follow what a human reviewer would flag, not what the engine flags. Team-written, so not independent." d={r.blind} />
          <SetCard title="Held-out probe" blurb="Written after the freeze. One miss (HO9, a double exclamation mark) was later fixed as a counting bug, so treat it as partly tuned. Smaller." d={r.heldout} />
          <SetCard title="Seeded set (regression safety only)" blurb="Written alongside the engine. A high score here shows coverage and regression safety, not accuracy on real content." d={r.seeded} />
        </>)}
      </div>
    </Shell>
  );
}