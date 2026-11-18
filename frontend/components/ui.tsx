"use client";
import { ReactNode } from "react";

export function Chip({ children, tone = "gray", title }: { children: ReactNode; tone?: string; title?: string }) {
  const tones: Record<string, string> = {
    gray: "bg-slate-100 text-slate-700 ring-slate-200", red: "bg-stampbg text-stamp ring-red-200", green: "bg-okbg text-ok ring-emerald-200",
    amber: "bg-warnbg text-warn ring-amber-200", navy: "bg-ink text-white ring-ink", blue: "bg-sky-50 text-sky-800 ring-sky-200",
  };
  return <span title={title} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${tones[tone] || tones.gray}`}>{children}</span>;
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children?: ReactNode }) {
  return (
    <div className="rise mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-3xl font-extrabold">{title}</h1>{subtitle && <p className="mt-1 max-w-2xl text-sm text-slate-600">{subtitle}</p>}</div>
      {children && <div className="flex gap-2">{children}</div>}
    </div>
  );
}

export const sevTone = (s: string) => (s === "high" ? "red" : s === "medium" ? "amber" : "gray");
export const verdictTone = (v: string) =>
  v === "Supported" ? "green" : v === "Contradicted" || v === "Outdated" ? "red" : v === "Unsupported" ? "amber" : "gray";
export const statusTone = (s: string) =>
  s === "Approved" ? "green" : s === "In review" ? "blue" : s === "Changes requested" ? "amber" : "gray";

export function Sev({ s }: { s: string }) { return <Chip tone={sevTone(s)}><span className="capitalize">{s} severity</span></Chip>; }
export function Verdict({ v }: { v: string }) { return v ? <Chip tone={verdictTone(v)}>{v}</Chip> : null; }
export function Method({ m }: { m: string }) {
  const label: Record<string, string> = { rule: "Rule", claims: "Claims", ai: "AI", heuristic: "Heuristic", trust: "Trust" };
  const tone: Record<string, string> = { rule: "navy", claims: "navy", ai: "blue", heuristic: "amber", trust: "red" };
  return <Chip tone={tone[m] || "gray"} title="How this finding was produced">{label[m] || m}</Chip>;
}

export function Tabs({ tabs, value, onChange }: { tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div role="tablist" className="mb-4 inline-flex max-w-full flex-wrap gap-1 rounded-xl bg-slate-200/60 p-1">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={`rounded-lg px-3.5 py-1.5 text-sm font-semibold transition ${value === t.id ? "bg-white text-ink shadow-sm" : "text-slate-600 hover:text-ink"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Toast({ msg, kind, onClose }: { msg: string; kind: "error" | "ok"; onClose: () => void }) {
  if (!msg) return null;
  return (
    <div role="alert" className={`fixed bottom-5 left-1/2 z-50 flex max-w-xl -translate-x-1/2 items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg ${kind === "error" ? "border-red-200 bg-stampbg text-stamp" : "border-emerald-200 bg-okbg text-ok"}`}>
      <span className="font-semibold">{msg}</span>
      <button onClick={onClose} className="font-bold opacity-70 hover:opacity-100" aria-label="Dismiss">&times;</button>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-8 text-center text-sm text-slate-600">{children}</div>;
}
