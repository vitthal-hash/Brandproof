"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty, PageHeader, Sev, statusTone } from "@/components/ui";
import { api } from "@/lib/api";

export default function Dashboard() {
  const { user } = useUser();
  const [assets, setAssets] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [ins, setIns] = useState<any>(null);
  const [filter, setFilter] = useState("all");
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!user) return;
    api("/assets").then(setAssets).catch((e) => setErr(e.message));
    api("/queue").then(setQueue).catch(() => {});
    api("/insights").then(setIns).catch(() => {});
  }, [user]);
  const NEXT: Record<string, string> = {
    creator: "Submit content for a check, then accept, edit or reject each suggested fix.",
    external: "Submit content for a check. You only see your own assets.",
    manager: "Open the review queue below and approve items that are ready.",
    reviewer: "High-risk claims are waiting for your decision in the review queue.",
    owner: "Keep rules and facts current, then test them in Rulebook health.",
  };
  const DOT: Record<string, string> = { Draft: "bg-slate-400", "Auto-reviewed": "bg-sky-500", "Changes requested": "bg-amber-500", "In review": "bg-brand", Approved: "bg-ok" };
  const statuses = ["Draft", "Auto-reviewed", "Changes requested", "In review", "Approved"];
  const counts: Record<string, number> = {};
  assets.forEach((a) => (counts[a.status] = (counts[a.status] || 0) + 1));
  const shown = assets.filter((a) => filter === "all" || a.status === filter);
  return (
    <Shell>
      <PageHeader title={`Welcome back, ${String(user?.name || "").split(" ")[0]}`} subtitle={NEXT[user?.role] || "Here is where your content stands."}>
        {user && user.role !== "owner" && <Link href="/new" className="btn btn-brand">New submission</Link>}
      </PageHeader>
      {err && <p role="alert" className="mt-2 text-sm font-semibold text-stamp">{err}</p>}
      <section aria-label="Status overview. Select a status to filter." className="mt-2 grid grid-cols-2 gap-3 md:grid-cols-5">
        {statuses.map((s) => (
          <button key={s} onClick={() => setFilter(filter === s ? "all" : s)} aria-pressed={filter === s}
            className={`card text-left transition hover:-translate-y-0.5 ${filter === s ? "ring-2 ring-brand" : ""}`}>
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-700"><span className={`h-2 w-2 rounded-full ${DOT[s]}`} />{s}</div>
            <div className="mt-2 font-display text-4xl font-extrabold">{counts[s] || 0}</div>
          </button>
        ))}
      </section>

      {queue.length > 0 && (
        <section className="mt-6" aria-label="Review queue">
          <h2 className="mb-3 text-lg font-bold">Review queue</h2>
          <div className="card overflow-x-auto p-0">
            <table className="w-full"><thead><tr><th className="th">Asset</th><th className="th">Creator</th><th className="th">Risk</th><th className="th">Routing</th></tr></thead>
              <tbody>{queue.map((q) => (
                <tr key={q.id}><td className="td"><Link className="font-semibold text-ink hover:text-brand hover:underline" href={`/assets/${q.id}`}>{q.title}</Link></td>
                  <td className="td">{q.owner}</td><td className="td">{q.risk === "high" ? <Sev s="high" /> : <Chip>NORMAL</Chip>}</td>
                  <td className="td">{q.route === "needs reviewer" ? <Chip tone="red">Needs authorised reviewer</Chip> : <Chip tone="green">Ready for you</Chip>}</td></tr>
              ))}</tbody></table>
          </div>
        </section>
      )}

      <section className="mt-6" aria-label="Assets">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-bold">{filter === "all" ? "All assets" : filter}{filter !== "all" && <button onClick={() => setFilter("all")} className="ml-3 text-sm font-semibold text-brand underline">Clear filter</button>}</h2>
          </div>
        {shown.length === 0 ? <Empty>{filter === "all" ? "No assets yet. Start with a new submission and BrandProof will check it in seconds." : `No assets are ${filter.toLowerCase()} right now.`}</Empty> : (
          <div className="card overflow-x-auto p-0">
            <table className="w-full"><thead><tr><th className="th">Title</th><th className="th">Status</th><th className="th">Risk</th><th className="th">Findings</th><th className="th">Creator</th><th className="th">Version</th></tr></thead>
              <tbody>{shown.map((a) => {
                const s = a.summary?.severity || {};
                return (
                  <tr key={a.id}>
                    <td className="td"><Link className="font-semibold text-ink hover:text-brand hover:underline" href={`/assets/${a.id}`}>{a.title}</Link><div className="text-xs text-slate-700">{a.intent}</div></td>
                    <td className="td"><Chip tone={statusTone(a.status)}>{a.status}</Chip></td>
                    <td className="td">{a.risk === "high" ? <Sev s="high" /> : <Chip>NORMAL</Chip>}</td>
                    <td className="td text-xs">{a.summary?.findings ?? 0} total ({s.high || 0} high, {s.medium || 0} medium, {s.low || 0} low)</td>
                    <td className="td">{a.owner}<div className="text-xs text-slate-700">{a.team}</div></td>
                    <td className="td">v{a.current_version}</td>
                  </tr>);
              })}</tbody></table>
          </div>
        )}
      </section>

      {ins && ins.repeated_by_team?.length > 0 && (
        <section className="mt-6" aria-label="Repeated mistakes">
          <h2 className="mb-3 text-lg font-bold">Repeated mistakes</h2>
          <div className="card">
            <ul className="space-y-1 text-sm">
              {ins.repeated_by_team.slice(0, 6).map((r: any) => (
                <li key={r.team + r.rule_id}><b>{r.team}</b> broke <b>{r.rule_id}</b> ({r.title}) in {r.assets} assets</li>
              ))}
            </ul>
            <Link href="/rulebook" className="btn btn-ghost mt-4">Review rules in Rulebook health</Link>
          </div>
        </section>
      )}
    </Shell>
  );
}
