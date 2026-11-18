"use client";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty, Toast } from "@/components/ui";
import { api } from "@/lib/api";

export default function Rulebook() {
  const { user } = useUser();
  const [rb, setRb] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState({ msg: "", kind: "ok" as "ok" | "error" });
  const owner = user?.role === "owner";
  const load = async () => { setRb(await api("/rulebook")); setRuns(await api("/redteam/runs")); };
  useEffect(() => { if (user) load().catch((e) => setToast({ msg: e.message, kind: "error" })); }, [user]);
  const call = async (key: string, path: string, body?: any, ok?: string) => {
    setBusy(key);
    try { await api(path, { body: body ?? {} }); await load(); if (ok) setToast({ msg: ok, kind: "ok" }); }
    catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
    setBusy("");
  };
  if (!rb) return <Shell><p className="text-sm text-slate-600">Loading…</p><Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} /></Shell>;
  const latestByRule: Record<string, any> = {};
  runs.forEach((r) => { if (!latestByRule[r.rule_id]) latestByRule[r.rule_id] = r; });
  return (
    <Shell>
      <h1 className="mb-5 text-3xl font-extrabold">Rulebook health</h1>
      <p className="mt-1 max-w-3xl text-sm text-slate-800">Which rules are hit, overridden, ambiguous or easy to dodge. The red-team writes rule-bending content; every miss becomes a loophole with a tighter rule for the guideline owner to approve and re-test.</p>

      <div className="card mt-4 overflow-x-auto p-0"><table className="w-full">
        <thead><tr><th className="th">Rule</th><th className="th">Hits</th><th className="th">Overridden</th><th className="th">Ambiguity</th><th className="th">Red-team</th><th className="th">Action</th></tr></thead>
        <tbody>{rb.rules.map((r: any) => (
          <tr key={r.rule_id}>
            <td className="td"><b>{r.rule_id}</b> <span className="text-xs text-slate-700">v{r.version}</span><div className="text-xs">{r.title}</div></td>
            <td className="td">{r.hits}<div className="text-xs text-slate-700">{r.assets} asset(s)</div></td>
            <td className="td">{r.decided ? `${Math.round(r.override_rate * 100)}%` : "-"}<div className="text-xs text-slate-700">{r.rejected} rejected, {r.waived} waived of {r.decided} decided</div></td>
            <td className="td">{r.ambiguous ? <Chip tone="amber" title="Reviewers and creators often override this rule: the wording may be unclear">UNCLEAR RULE</Chip> : <Chip>ok</Chip>}</td>
            <td className="td">{r.redteam ? <span>{r.redteam.caught}/{r.redteam.total} caught <span className="text-xs">(v{r.redteam.rule_version})</span></span> : r.eligible ? <span className="text-xs text-slate-700">not tested</span> : <span className="text-xs text-slate-700">n/a in v1</span>}</td>
            <td className="td">{r.eligible && owner && <button className="btn btn-ghost" disabled={busy === r.rule_id} onClick={() => call(r.rule_id, "/redteam/run", { rule_id: r.rule_id }, `Red-team finished for ${r.rule_id}`)}>{busy === r.rule_id ? "Running..." : "Run red-team"}</button>}</td>
          </tr>))}</tbody></table></div>

      <h2 className="mb-2 mt-6 text-lg font-bold">Repeated mistakes by team</h2>
      {rb.repeated_by_team.length === 0 ? <Empty>No team has broken the same rule in two or more assets yet.</Empty> : (
        <div className="card overflow-x-auto p-0"><table className="w-full"><thead><tr><th className="th">Team</th><th className="th">Rule</th><th className="th">Assets</th></tr></thead>
          <tbody>{rb.repeated_by_team.map((x: any) => <tr key={x.team + x.rule_id}><td className="td font-semibold">{x.team}</td><td className="td">{x.rule_id} <span className="text-xs">{x.title}</span></td><td className="td">{x.assets}</td></tr>)}</tbody></table></div>)}

      <h2 className="mb-2 mt-6 text-lg font-bold">Red-team runs and loophole reports</h2>
      {runs.length === 0 ? <Empty>No red-team run yet. {owner ? "Pick a rule above and press Run red-team." : "The guideline owner can run it."}</Empty> : runs.slice(0, 6).map((r) => {
        const p = r.proposal;
        return (
          <section key={r.id} className="card mb-4" aria-label={`Red-team run ${r.id}`}>
            <div className="flex flex-wrap items-center gap-2"><h3 className="font-bold">{r.rule_id} v{r.rule_version}</h3>
              <Chip tone={r.summary.missed ? "red" : "green"}>{r.summary.caught}/{r.summary.total} variants caught</Chip>
              <span className="text-xs text-slate-700">{r.created_at.replace("T", " ")} by {r.created_by} | {r.summary.sources.join(" + ")}</span></div>
            <details className="mt-2"><summary className="cursor-pointer text-sm font-semibold">Show all {r.results.length} variants</summary>
              <table className="mt-2 w-full"><thead><tr><th className="th">Variant</th><th className="th">Trick</th><th className="th">Result</th></tr></thead>
                <tbody>{r.results.map((v: any, i: number) => <tr key={i}><td className="td font-mono text-xs">{v.text}</td><td className="td text-xs">{v.technique}</td><td className="td">{v.caught ? <Chip tone="green">CAUGHT</Chip> : <Chip tone="red">LOOPHOLE</Chip>}</td></tr>)}</tbody></table></details>
            {p && (
              <div className="mt-3 rounded-md border border-slate-300 bg-slate-50 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2"><b>Proposed tighter rule</b> <Chip tone={p.status === "approved" ? "green" : p.status === "rejected" ? "gray" : "amber"}>{p.status.toUpperCase()}</Chip></div>
                <p className="mt-1">{p.rationale}.</p>
                {p.retest && <p className="mt-1"><b>Re-test:</b> {p.retest.before_caught}/{p.retest.total} caught before, <b>{p.retest.after_caught}/{p.retest.total}</b> after. False positives on normal copy: {p.retest.false_positives.length}.
                  {p.retest.still_missed.length > 0 && <span> Still missed: {p.retest.still_missed.join(" | ")}</span>}</p>}
                <details className="mt-1"><summary className="cursor-pointer text-xs font-semibold">Proposed rule settings</summary><pre className="overflow-x-auto text-xs">{JSON.stringify(p.proposed_params, null, 2)}</pre></details>
                {owner && p.status === "pending" && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button className="btn btn-ok" disabled={!!busy} onClick={() => call("p" + p.id, `/redteam/proposals/${p.id}/decision`, { action: "approve" }, "Rule updated to a new version")}>Approve tighter rule</button>
                    <button className="btn btn-ghost" disabled={!!busy} onClick={() => call("r" + p.id, `/redteam/proposals/${p.id}/retest`, {}, "Re-test complete")}>Re-test</button>
                    <button className="btn btn-danger" disabled={!!busy} onClick={() => call("x" + p.id, `/redteam/proposals/${p.id}/decision`, { action: "reject" })}>Reject</button>
                  </div>)}
              </div>)}
          </section>);
      })}
      <Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} />
    </Shell>
  );
}
