"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty, Method, Sev, Tabs, Toast, Verdict, statusTone } from "@/components/ui";
import { api } from "@/lib/api";

const sevOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
const markClass: Record<string, string> = {
  high: "bg-red-200 underline decoration-red-700 decoration-2",
  medium: "bg-amber-200 underline decoration-amber-700",
  low: "bg-slate-200 underline decoration-slate-600",
};

function Highlighted({ text, findings, selected, onSelect }: { text: string; findings: any[]; selected: number | null; onSelect: (id: number) => void }) {
  const spans = findings.filter((f) => f.start >= 0 && f.end > f.start && f.end <= text.length);
  const pts = Array.from(new Set([0, text.length, ...spans.flatMap((f) => [f.start, f.end])])).sort((a, b) => a - b);
  const out: any[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i], b = pts[i + 1];
    const cover = spans.filter((f) => f.start <= a && f.end >= b);
    const chunk = text.slice(a, b);
    if (!cover.length) { out.push(<span key={a}>{chunk}</span>); continue; }
    cover.sort((x, y) => sevOrder[x.severity] - sevOrder[y.severity]);
    const top = cover[0];
    const sel = cover.some((c) => c.id === selected);
    out.push(
      <mark key={a} role="button" tabIndex={0} aria-label={`${top.rule_id} finding: ${chunk}`}
        onClick={() => onSelect(top.id)} onKeyDown={(e) => e.key === "Enter" && onSelect(top.id)}
        className={`cursor-pointer rounded-sm ${markClass[top.severity]} ${sel ? "ring-2 ring-ink" : ""}`}>{chunk}</mark>
    );
  }
  return <div className="whitespace-pre-wrap break-words text-[15px] leading-7">{out}</div>;
}

function FactRef({ id, facts }: { id: string; facts: Record<string, any> }) {
  const f = facts[id];
  if (!f) return <Chip tone="navy">{id}</Chip>;
  return (
    <div className="mt-1 rounded border border-slate-300 bg-slate-50 p-2 text-xs">
      <Chip tone="navy">{f.id}</Chip> <span className="ml-1">{f.statement}</span>
      <div className="mt-1 text-slate-700">Owner: {f.owner} | Source: {f.source} | Valid until: {f.valid_to || "no expiry"}</div>
    </div>
  );
}

function FindingCard({ f, ctx }: { f: any; ctx: any }) {
  const { user, data, facts, comments, busy, act, selected, setSelected, postComment } = ctx;
  const [mode, setMode] = useState<string | null>(null);
  const [val, setVal] = useState("");
  const asset = data.asset, perm = data.permissions;
  const isOwner = user.email === asset.owner_email;
  const live = data.version.is_latest && asset.status !== "Approved";
  const undecided = f.status === "open" || f.status === "rejected";
  const fx = f.fix;
  const mine = comments.filter((c: any) => c.finding_id === f.id);
  const canWaive = live && perm.can_waive && undecided;
  const waiveBlocked = f.severity === "high" && user.role !== "reviewer";
  const done = (action: string, text?: string, note?: string) => { act(`/findings/${f.id}/decision`, { action, text, note }); setMode(null); setVal(""); };
  return (
    <article id={`finding-${f.id}`} className={`card border-l-4 ${f.severity === "high" ? "border-l-stamp" : f.severity === "medium" ? "border-l-amber-500" : "border-l-slate-300"} ${selected === f.id ? "ring-2 ring-brand" : ""} ${!undecided ? "opacity-75" : ""}`}
      onClick={() => setSelected(f.id)} aria-label={`${f.rule_id} finding`}>
      <div className="flex flex-wrap items-center gap-2">
        <Sev s={f.severity} /> <Method m={f.method} />
        {f.verdict && <Verdict v={f.verdict} />}
        {f.needs_human && <Chip tone="amber" title="The reviewer was not confident enough to decide">NEEDS HUMAN</Chip>}
        {f.status !== "open" && <Chip tone={f.status === "accepted" || f.status === "edited" ? "green" : "gray"}>{f.status.toUpperCase()}</Chip>}
        <span className="ml-auto text-xs text-slate-700">confidence {Math.round(f.confidence * 100)}%</span>
      </div>
      <h3 className="mt-2 text-sm font-bold">{f.title}</h3>
      {f.quote && <blockquote className="mt-1 border-l-4 border-slate-400 pl-2 text-sm italic">{f.quote}</blockquote>}
      <p className="mt-2 text-sm">{f.explanation}</p>
      <div className="mt-2 text-xs text-slate-800">
        <span className="font-semibold">Cited:</span>{" "}
        {(f.citation.rules || []).map((r: string) => <Chip key={r} tone="gray">{r}</Chip>)}{" "}
        {(f.citation.facts || []).map((id: string) => <FactRef key={id} id={id} facts={facts} />)}
      </div>

      {fx && fx.status === "verified" && (
        <div className="mt-3 rounded-md border border-ok bg-okbg p-3 text-sm">
          <div className="mb-1 flex flex-wrap items-center gap-2"><Chip tone="green">VERIFIED FIX</Chip>
            <Chip tone="green" title="Re-reviewed: finding gone, nothing new introduced">Re-checked</Chip>
            <Chip tone="green" title={`kept: ${(fx.verification.intent_lock.kept || []).join(", ")}`}>Intent Lock passed</Chip></div>
          <p><span className="font-semibold">Before:</span> {fx.before}</p>
          <p><span className="font-semibold">After:</span> {fx.after || "(removed)"}</p>
        </div>
      )}
      {fx && fx.status === "withheld" && (
        <p className="mt-3 rounded-md border border-slate-300 bg-slate-50 p-2 text-xs text-slate-800">
          <b>Suggested fix withheld:</b> {fx.reason}. It was not shown as safe, so a person should decide.
        </p>
      )}
      {!fx && f.method !== "trust" && <p className="mt-3 text-xs text-slate-700">No automatic fix for this finding{f.start < 0 ? ". It is about the file or design: update it and upload a new version." : ". Please edit the copy yourself."}</p>}

      {f.decided_by && <p className="mt-2 text-xs text-slate-700">Decided by {f.decided_by}{f.decided_note ? `: "${f.decided_note}"` : ""}</p>}

      {live && undecided && (
        <div className="no-print mt-3 flex flex-wrap gap-2">
          {isOwner && fx?.status === "verified" && <button disabled={busy} className="btn btn-ok" onClick={() => done("accept_fix")}>Accept fix</button>}
          {isOwner && f.start >= 0 && <button className="btn btn-ghost" onClick={() => { setMode("edit"); setVal(fx?.replacement || ""); }}>Edit</button>}
          {f.status === "open" && (isOwner || ["manager", "reviewer"].includes(user.role)) && <button className="btn btn-danger" onClick={() => { setMode("reject"); setVal(""); }}>Reject</button>}
          {canWaive && <button className="btn btn-ghost" disabled={waiveBlocked} title={waiveBlocked ? "High-severity findings can only be waived by an authorised reviewer" : ""} onClick={() => { setMode("waive"); setVal(""); }}>Waive</button>}
          <button className="btn btn-ghost" onClick={() => { setMode("comment"); setVal(""); }}>Comment</button>
        </div>
      )}
      {mode && (
        <div className="mt-2 space-y-2">
          <label className="label" htmlFor={`in-${f.id}`}>{mode === "edit" ? "Your replacement text (leave empty to remove the highlighted words)" : mode === "comment" ? "Comment" : "Reason (required)"}</label>
          <textarea id={`in-${f.id}`} rows={2} className="input" value={val} onChange={(e) => setVal(e.target.value)} />
          <div className="flex gap-2">
            <button className="btn btn-primary" disabled={busy || (mode !== "edit" && mode !== "comment" && val.trim().length < 3) || (mode === "comment" && !val.trim())}
              onClick={() => mode === "edit" ? done("edit_fix", val) : mode === "comment" ? (postComment(val, f.id), setMode(null), setVal("")) : done(mode, undefined, val)}>Confirm</button>
            <button className="btn btn-ghost" onClick={() => setMode(null)}>Cancel</button>
          </div>
        </div>
      )}
      {mine.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-slate-200 pt-2 text-xs">
          {mine.map((c: any) => <li key={c.id}><b>{c.author}</b> ({c.role}): {c.body}</li>)}
        </ul>
      )}
    </article>
  );
}

export default function AssetPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useUser();
  const [data, setData] = useState<any>(null);
  const [facts, setFacts] = useState<Record<string, any>>({});
  const [comments, setComments] = useState<any[]>([]);
  const [tab, setTab] = useState("findings");
  const [selected, setSelected] = useState<number | null>(null);
  const [show, setShow] = useState("open");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ msg: string; kind: "error" | "ok" }>({ msg: "", kind: "ok" });
  const [preview, setPreview] = useState("");
  const [note, setNote] = useState("");
  const [panel, setPanel] = useState<string | null>(null);
  const [newText, setNewText] = useState("");
  const [newFile, setNewFile] = useState<File | null>(null);
  const [diff, setDiff] = useState<any[] | null>(null);
  const [commentText, setCommentText] = useState("");

  const load = useCallback(async (n?: number) => {
    try {
      const d = await api(`/assets/${id}${n ? `?n=${n}` : ""}`);
      setData(d);
      setComments(await api(`/assets/${id}/comments`));
    } catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
  }, [id]);
  useEffect(() => { if (user) { load(); api("/facts").then((fs) => setFacts(Object.fromEntries(fs.map((f: any) => [f.id, f])))).catch(() => {}); } }, [user, load]);

  const kind = data?.version?.kind, vn = data?.version?.n;
  useEffect(() => {
    let url = "";
    setPreview("");
    if (data && (kind === "pdf" || kind === "image") && !data.version.purged) {
      api(`/assets/${id}/preview?n=${vn}`, { blob: true }).then((b) => { url = URL.createObjectURL(b); setPreview(url); }).catch(() => {});
    }
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [id, kind, vn, data?.version?.purged]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (path: string, body?: any, okMsg?: string) => {
    setBusy(true);
    try {
      const d = await api(path, { body });
      setData(d); setComments(await api(`/assets/${id}/comments`));
      if (okMsg) setToast({ msg: okMsg, kind: "ok" });
    } catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
    setBusy(false);
  };
  const postComment = async (body: string, finding_id?: number) => {
    try { await api(`/assets/${id}/comments`, { body: { body, finding_id } }); setComments(await api(`/assets/${id}/comments`)); }
    catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
  };
  const workflow = (action: string, n = "") => act(`/assets/${id}/workflow`, { action, note: n }, action === "approve" ? "Approved. Proof Pack is ready." : undefined);

  const findings = useMemo(() => {
    if (!data) return [];
    const fs = [...data.findings].sort((a, b) => sevOrder[a.severity] - sevOrder[b.severity] || a.start - b.start);
    return show === "all" ? fs : fs.filter((f) => f.status === "open" || f.status === "rejected");
  }, [data, show]);

  if (!user || !data) return <Shell><p>Loading...</p><Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} /></Shell>;
  const { asset, permissions: perm, run, version } = data;
  const sum = run?.summary || {};
  const isOwner = user.email === asset.owner_email;
  const ctx = { user, data, facts, comments, busy, act, selected, setSelected: (i: number) => { setSelected(i); document.getElementById(`finding-${i}`)?.scrollIntoView({ block: "center" }); }, postComment };
  const approveDisabled = busy || (asset.risk === "high" && user.role !== "reviewer");

  const submitVersion = async () => {
    setBusy(true);
    try {
      const form = new FormData();
      form.append("text", newText); form.append("note", "Edited by creator");
      if (newFile) form.append("file", newFile);
      const d = await api(`/assets/${id}/versions`, { form });
      setData(d); setPanel(null); setNewText(""); setNewFile(null);
      setToast({ msg: "New version reviewed", kind: "ok" });
    } catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
    setBusy(false);
  };
  const showDiff = async () => {
    try { setDiff(await api(`/assets/${id}/diff?a=${version.n - 1}&b=${version.n}`)); } catch (e: any) { setToast({ msg: e.message, kind: "error" }); }
  };

  return (
    <Shell>
      <nav aria-label="Breadcrumb" className="mb-3 text-sm text-slate-600"><Link href="/" className="font-semibold hover:text-brand hover:underline">Dashboard</Link> / <span>{asset.title}</span></nav>
      <div className="card rise p-6">
        <div className="flex flex-wrap items-start gap-3">
          <div className="min-w-0">
            <h1 className="text-3xl font-extrabold">{asset.title}</h1>
            <p className="mt-1 text-sm text-slate-600">Intent: <i className="text-ink">{asset.intent}</i></p>
            <p className="text-xs text-slate-500">{asset.owner} ({asset.team}) on {asset.channel}</p>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <Chip tone={statusTone(asset.status)}>{asset.status}</Chip>
            {asset.risk === "high" ? <Chip tone="red">High risk: needs authorised reviewer</Chip> : <Chip>Normal risk</Chip>}
            <Chip tone={run?.provider === "offline" ? "amber" : "blue"} title={run?.model}>{run?.provider === "offline" ? "Offline heuristic" : `AI: ${run?.provider}`}</Chip>
          </div>
        </div>
        <ol aria-label="Progress" className="mt-5 grid grid-cols-4 gap-2 text-xs font-semibold">
          {["Draft", "Auto-reviewed", "In review", "Approved"].map((st, i) => {
            const order = ["Draft", "Auto-reviewed", "Changes requested", "In review", "Approved"];
            const cur = Math.max(0, order.indexOf(asset.status)); const idx = order.indexOf(st);
            const done = idx <= cur;
            return <li key={st} className="min-w-0"><div className={`h-1.5 rounded-full ${done ? "bg-brand" : "bg-slate-200"}`} /><span className={`mt-1.5 block truncate ${done ? "text-ink" : "text-slate-500"}`}>{st}</span></li>;
          })}
        </ol>
        <p className="mt-4 rounded-xl bg-brandbg px-4 py-3 text-sm text-teal-900"><b>Next step: </b>
          {asset.status === "Approved" ? "This asset is approved. Open the Proof Pack to see the receipt."
            : asset.status === "Changes requested" ? (isOwner ? "Fix the open findings below, then upload a new version." : "Waiting for the creator to revise.")
            : asset.status === "In review" ? (perm.can_approve ? "Check the open findings, then approve or request changes." : "Waiting for a reviewer to decide.")
            : isOwner ? "Go through each finding: accept the fix, edit it, or reject it. Then submit for review." : "Waiting for the creator to submit."}</p>
      </div>

      <div className="no-print sticky top-0 z-10 -mx-1 mt-4 flex flex-wrap items-center gap-2 rounded-2xl bg-paper/90 px-1 py-2 backdrop-blur">
        {perm.can_submit && <button className="btn btn-brand" disabled={busy} onClick={() => workflow("submit")}>Submit for review</button>}
        {perm.can_approve && <button className="btn btn-ok" disabled={approveDisabled} title={approveDisabled && asset.risk === "high" ? "An authorised reviewer must approve high-risk assets" : ""} onClick={() => workflow("approve")}>Approve</button>}
        {perm.can_request_changes && <button className="btn btn-danger" onClick={() => setPanel(panel === "changes" ? null : "changes")}>Request changes</button>}
        {(isOwner || user.role === "manager") && asset.status !== "Approved" && <button className="btn btn-ghost" disabled={busy} onClick={() => act(`/assets/${id}/rerun`, undefined, "Review re-run")}>Re-run review</button>}
        {isOwner && <button className="btn btn-ghost" onClick={() => setPanel(panel === "version" ? null : "version")}>{asset.status === "Approved" ? "Reopen with new version" : "Upload new version"}</button>}
        <Link className="btn btn-ghost" href={`/assets/${id}/proof`}>Proof Pack</Link>
      </div>

      {panel === "changes" && (
        <div className="card mt-3 max-w-xl space-y-2"><label htmlFor="note" className="label">What needs to change?</label>
          <textarea id="note" className="input" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn btn-danger" disabled={note.trim().length < 3} onClick={() => { workflow("request_changes", note); setPanel(null); setNote(""); }}>Send back to creator</button></div>
      )}
      {panel === "version" && (
        <div className="card mt-3 max-w-2xl space-y-2"><label htmlFor="nt" className="label">Revised text (or upload a revised PDF or image)</label>
          <textarea id="nt" className="input" rows={5} value={newText} onChange={(e) => setNewText(e.target.value)} />
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setNewFile(e.target.files?.[0] || null)} aria-label="Revised file" />
          <div><button className="btn btn-primary" disabled={busy || (!newText.trim() && !newFile)} onClick={submitVersion}>Save and review new version</button></div></div>
      )}

      <section aria-label="Review summary" className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[["High", sum.severity?.high || 0, "text-stamp"], ["Medium", sum.severity?.medium || 0, "text-warn"], ["Need a human", sum.abstained || 0, "text-ink"], ["Verified fixes", sum.fixes?.verified || 0, "text-ok"]].map(([l, n, c]: any) => (
          <div key={l} className="card p-4"><div className={`font-display text-3xl font-extrabold ${c}`}>{n}</div><div className="text-xs font-semibold text-slate-600">{l}</div></div>))}
      </section>
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        <Chip>{sum.severity?.low || 0} low</Chip><Chip>{sum.fixes?.withheld || 0} fixes withheld</Chip>
        {run?.trust?.has_hidden && <Chip tone="red">Hidden content found</Chip>}
        {run?.differential?.ran && !run.differential.agree && <Chip tone="red">Manipulation flag</Chip>}
        <Chip>Version {version.n}{version.is_latest ? " (latest)" : " (older)"}</Chip>
      </div>
      {!version.is_latest && <p className="mt-2 rounded border border-amber-600 bg-warnbg p-2 text-sm">You are viewing an older version. Decisions apply only to the latest version. <button className="underline font-semibold" onClick={() => load()}>Go to latest</button></p>}

      <div className="mt-5 grid gap-5 lg:grid-cols-5">
        <section aria-label="Document" className="card lg:sticky lg:top-4 lg:col-span-2 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto">
          <h2 className="mb-2 font-display text-base font-bold">Annotated content</h2>
          {preview && <img src={preview} alt={`Preview of ${asset.title}`} className="mb-3 max-h-80 w-full rounded border border-slate-300 object-contain" />}
          {version.purged ? <Empty>Content was deleted by the retention policy after approval. The Proof Pack is kept.</Empty>
            : version.text ? <Highlighted text={version.text} findings={data.findings} selected={selected} onSelect={ctx.setSelected} />
            : <Empty>No readable text in this file{kind === "image" ? " (text inside images is read only when an AI vision model is enabled)" : ""}.</Empty>}
          {version.raw_differs && <p className="mt-3 rounded border border-stamp bg-stampbg p-2 text-xs font-semibold text-stamp">The submitted file contained hidden content. It was removed from this view and from the review. See the Trust tab.</p>}
        </section>

        <section aria-label="Review details" className="lg:col-span-3">
          <Tabs value={tab} onChange={setTab} tabs={[
            { id: "findings", label: `Findings (${data.findings.length})` }, { id: "claims", label: `Claim Ledger (${data.claims.length})` },
            { id: "trust", label: "Trust Layer" }, { id: "comments", label: `Comments (${comments.length})` }, { id: "history", label: `History (${data.versions.length})` }]} />

          {tab === "findings" && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm"><label htmlFor="show" className="font-semibold">Show</label>
                <select id="show" className="input w-auto" value={show} onChange={(e) => setShow(e.target.value)}><option value="open">Open items</option><option value="all">All items</option></select></div>
              {findings.length === 0 ? <Empty>{data.findings.length ? "All findings are decided." : "No findings. Every check passed."}</Empty> : findings.map((f: any) => <FindingCard key={f.id} f={f} ctx={ctx} />)}
            </div>
          )}

          {tab === "claims" && (
            <div className="card overflow-x-auto p-0">
              {data.claims.length === 0 ? <Empty>No promotional claims found.</Empty> : (
                <table className="w-full"><thead><tr><th className="th">#</th><th className="th">Claim</th><th className="th">Verdict</th><th className="th">Evidence</th></tr></thead>
                  <tbody>{data.claims.map((c: any) => (
                    <tr key={c.label}><td className="td font-bold">{c.label}</td>
                      <td className="td"><div className="font-semibold">{c.text}</div><div className="text-xs text-slate-700">{c.kind} | confidence {Math.round(c.confidence * 100)}%</div></td>
                      <td className="td"><Verdict v={c.verdict} /></td>
                      <td className="td text-xs">{c.explanation}{c.fact_id && <FactRef id={c.fact_id} facts={facts} />}</td></tr>))}</tbody></table>)}
            </div>
          )}

          {tab === "trust" && (
            <div className="space-y-3">
              <div className="card"><h3 className="font-bold">Differential review</h3>
                <p className="mt-1 text-sm">{!run.differential.ran ? "The raw and cleaned file are identical, so one review was enough."
                  : run.differential.agree ? "The file was reviewed raw and cleaned. Both gave the same verdict."
                  : "The raw file and the cleaned file gave DIFFERENT verdicts. Treat this file as possibly manipulated."}</p>
                {run.differential.ran && !run.differential.agree && <ul className="mt-2 list-disc pl-5 text-xs">
                  {run.differential.only_in_raw.map((x: string) => <li key={"r" + x}>Only when hidden content is included: {x}</li>)}
                  {run.differential.only_in_clean.map((x: string) => <li key={"c" + x}>Only when hidden content is removed: {x}</li>)}</ul>}</div>
              <div className="card"><h3 className="font-bold">Hidden content ({run.trust.hidden.length})</h3>
                {run.trust.hidden.length === 0 ? <p className="mt-1 text-sm">None found.</p> : (
                  <table className="mt-2 w-full"><thead><tr><th className="th">Reason</th><th className="th">Text</th><th className="th">Page</th></tr></thead>
                    <tbody>{run.trust.hidden.map((h: any, i: number) => <tr key={i}><td className="td">{h.reason}</td><td className="td font-mono text-xs">{h.text}</td><td className="td">{h.page ?? "-"}</td></tr>)}</tbody></table>)}</div>
              <div className="card"><h3 className="font-bold">Instructions aimed at AI reviewers ({run.trust.injections.length})</h3>
                {run.trust.injections.length === 0 ? <p className="mt-1 text-sm">None found.</p> : <ul className="mt-2 space-y-1 text-sm">
                  {run.trust.injections.map((x: any, i: number) => <li key={i}><Chip tone="red">{x.hidden ? "HIDDEN" : "VISIBLE"}</Chip> <span className="font-mono text-xs">{x.snippet}</span> <span className="text-xs">(not obeyed)</span></li>)}</ul>}</div>
              <div className="card"><h3 className="font-bold">What this review did not check</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{run.not_checked.map((n: string) => <li key={n}>{n}</li>)}</ul>
                {run.trust.notes?.length > 0 && <ul className="mt-2 list-disc pl-5 text-xs">{run.trust.notes.map((n: string) => <li key={n}>{n}</li>)}</ul>}</div>
            </div>
          )}

          {tab === "comments" && (
            <div className="card space-y-3">
              {comments.length === 0 ? <Empty>No comments yet.</Empty> : <ul className="space-y-2 text-sm">{comments.map((c) => (
                <li key={c.id} className="rounded border border-slate-200 p-2"><b>{c.author}</b> <span className="text-xs text-slate-700">({c.role}, {c.created_at.replace("T", " ")})</span>
                  {c.finding_id && <Chip tone="gray">on finding #{c.finding_id}</Chip>}<div>{c.body}</div></li>))}</ul>}
              <div><label htmlFor="cm" className="label">Add a comment</label><textarea id="cm" rows={2} className="input" value={commentText} onChange={(e) => setCommentText(e.target.value)} />
                <button className="btn btn-primary mt-2" disabled={!commentText.trim()} onClick={() => { postComment(commentText); setCommentText(""); }}>Post comment</button></div>
            </div>
          )}

          {tab === "history" && (
            <div className="card space-y-3">
              <ul className="space-y-2 text-sm">{data.versions.map((v: any) => (
                <li key={v.n} className="flex flex-wrap items-center gap-2"><button className={`btn ${v.n === version.n ? "btn-primary" : "btn-ghost"}`} onClick={() => { setDiff(null); load(v.n); }}>v{v.n}</button>
                  <span>{v.note}</span><span className="text-xs text-slate-700">by {v.by} | {v.created_at.replace("T", " ")} | sha256 {v.sha256}</span>{v.purged && <Chip>content deleted</Chip>}</li>))}</ul>
              {version.n > 1 && <button className="btn btn-ghost" onClick={showDiff}>Show changes from v{version.n - 1} to v{version.n}</button>}
              {diff && <pre className="overflow-x-auto rounded border border-slate-300 bg-slate-50 p-2 text-xs">{diff.map((d, i) => <div key={i}>{d.op === "add" ? "+ " : d.op === "del" ? "- " : "  "}{d.text}</div>)}</pre>}
            </div>
          )}
        </section>
      </div>
      <Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} />
    </Shell>
  );
}
