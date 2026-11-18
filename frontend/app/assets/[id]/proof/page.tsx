"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Verdict } from "@/components/ui";
import { api } from "@/lib/api";

function Row({ k, children }: { k: string; children: any }) {
  return <div className="grid gap-1 border-b border-dashed border-slate-200 py-4 last:border-b-0 md:grid-cols-4"><div className="text-sm font-bold text-brand">{k}</div><div className="text-sm md:col-span-3">{children}</div></div>;
}

export default function Proof() {
  const { id } = useParams<{ id: string }>();
  const { user } = useUser();
  const [p, setP] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { if (user) api(`/assets/${id}/proofpack`).then(setP).catch((e) => setErr(e.message)); }, [user, id]);
  if (err) return <Shell><p role="alert" className="font-semibold text-stamp">{err}</p></Shell>;
  if (!p) return <Shell><p className="text-sm text-slate-600">Loading Proof Pack…</p></Shell>;
  const s = p.summary, c = p.checks || {};
  const open = p.findings.filter((f: any) => f.status === "open" || f.status === "rejected");
  return (
    <Shell>
      <div className="no-print mb-3 flex gap-2"><Link href={`/assets/${id}`} className="btn btn-ghost">Back to review</Link><button className="btn btn-brand" onClick={() => window.print()}>Print or save as PDF</button></div>
      <article className="rise mx-auto max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
        <header className="mb-3 flex flex-wrap items-center gap-3 border-b-2 border-ink pb-4">
          <h1 className="text-3xl font-extrabold">Proof Pack</h1>
          <Chip tone={p.asset.status === "Approved" ? "green" : "amber"}>{p.asset.status}</Chip>
          <span className="ml-auto text-xs text-slate-700">Generated {p.generated_at.replace("T", " ")} | v{p.version.n} | sha256 {p.version.sha256.slice(0, 16)}</span>
        </header>
        <Row k="Asset"><b>{p.asset.title}</b> ({p.asset.channel}) by {p.asset.creator}, team {p.asset.team}</Row>
        <Row k="Creator intent">{p.asset.intent}</Row>
        <Row k="Trust Layer">
          {p.trust.has_hidden ? <Chip tone="red">{p.trust.hidden.length} hidden item(s) found and removed</Chip> : <Chip tone="green">No hidden text</Chip>}{" "}
          {p.trust.injections?.length ? <Chip tone="red">{p.trust.injections.length} injection pattern(s), not obeyed</Chip> : <Chip tone="green">0 injection signals</Chip>}
          <div className="mt-1">Raw vs cleaned review: {!p.differential.ran ? "identical, single review" : p.differential.agree ? "ran, verdicts agree" : "ran, VERDICTS DIFFER (manipulation flag)"}</div>
        </Row>
        <Row k="Checks run">{c.deterministic_rules} deterministic rules, {c.file_checks} file checks, {c.claims_judged} claims judged, {c.judgment_rules} tone/messaging rules via <b>{c.judgment_method}</b>.
          <div><b>{s.abstained}</b> finding(s) were routed to a human because the reviewer was not confident.</div></Row>
        <Row k="Claim Ledger">{p.claim_ledger.length === 0 ? "No promotional claims." : (
          <table className="w-full"><tbody>{p.claim_ledger.map((x: any) => (
            <tr key={x.label}><td className="py-1 pr-2 font-bold">{x.label}</td><td className="pr-2">{x.text}</td><td className="pr-2"><Verdict v={x.verdict} /></td><td>{x.fact || "no fact"}</td></tr>))}</tbody></table>)}</Row>
        <Row k="Findings">{p.findings.length} total, {open.length} still open. Fixes proposed {s.fixes.proposed}, verified {s.fixes.verified}, withheld {s.fixes.withheld}.
          <ul className="mt-1 list-disc pl-5 text-xs">{p.findings.slice(0, 40).map((f: any) => <li key={f.id}>#{f.id} {f.rule} [{f.severity}, {f.method}] {f.title} - <b>{f.status}</b>{f.decided_by ? ` by ${f.decided_by}` : ""}</li>)}</ul></Row>
        <Row k="NOT checked"><ul className="list-disc pl-5">{p.not_checked.map((n: string) => <li key={n}>{n}</li>)}</ul><p className="mt-1 text-xs">Facts were valid as of {s.facts_as_of}.</p></Row>
        <Row k="Humans">{p.humans.length === 0 ? "No human decisions recorded yet." : <ul className="list-disc pl-5">{p.humans.map((h: any, i: number) => <li key={i}>{h.ts.replace("T", " ")} {h.actor}: {h.action}{h.detail?.note ? ` ("${h.detail.note}")` : ""}{h.detail?.rule ? ` [${h.detail.rule}]` : ""}</li>)}</ul>}
          {p.waived.length > 0 && <div className="mt-1"><b>Waived by a reviewer:</b><ul className="list-disc pl-5">{p.waived.map((w: string) => <li key={w}>{w}</li>)}</ul></div>}
          <p className="mt-1 text-xs">Nothing was applied or approved by AI.</p></Row>
        <Row k="AI use">Provider: <b>{p.ai_use.provider}</b> {p.ai_use.model ? `(${p.ai_use.model})` : ""}; {p.ai_use.calls} external call(s); {p.ai_use.redactions} personal-data item(s) redacted. <div className="text-xs">{p.ai_use.note}</div></Row>
        <Row k="Version history"><ul className="list-disc pl-5">{p.versions.map((v: any) => <li key={v.n}>v{v.n}: {v.note} ({v.by}, sha256 {v.sha256})</li>)}</ul></Row>
        <Row k="Audit chain">{p.audit_chain.ok ? <Chip tone="green">Tamper-evident log verified: {p.audit_chain.entries} entries</Chip> : <Chip tone="red">Audit log FAILED verification at entry {p.audit_chain.first_bad_id}</Chip>}
          <div className="mt-1 font-mono text-xs">head {p.audit_chain.head}</div></Row>
      </article>
    </Shell>
  );
}
