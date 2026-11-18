"use client";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty, Sev, Tabs, Toast } from "@/components/ui";
import { api } from "@/lib/api";

function daysLeft(d: string | null) {
  if (!d) return null;
  return Math.round((new Date(d).getTime() - Date.now()) / 86400000);
}

export default function Governance() {
  const { user } = useUser();
  const owner = user?.role === "owner";
  const [tab, setTab] = useState("rules");
  const [rules, setRules] = useState<any[]>([]);
  const [facts, setFacts] = useState<any[]>([]);
  const [lib, setLib] = useState<any[]>([]);
  const [edit, setEdit] = useState<any>(null);
  const [fedit, setFedit] = useState<any>(null);
  const [importText, setImportText] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [item, setItem] = useState({ kind: "term", name: "", hex: "" });
  const [toast, setToast] = useState({ msg: "", kind: "ok" as "ok" | "error" });
  const say = (msg: string, kind: "ok" | "error" = "ok") => setToast({ msg, kind });
  const load = async () => { setRules(await api("/rules")); setFacts(await api("/facts")); setLib(await api("/library")); };
  useEffect(() => { if (user) load().catch((e) => say(e.message, "error")); }, [user]);
  const run = async (fn: () => Promise<any>, ok: string) => { try { await fn(); await load(); say(ok); } catch (e: any) { say(e.message, "error"); } };

  const saveRule = () => run(async () => {
    let params = {};
    try { params = JSON.parse(edit.paramsText || "{}"); } catch { throw new Error("Params must be valid JSON"); }
    const body = { title: edit.title, category: edit.category, severity: edit.severity, description: edit.description, method: edit.method, params, rule_id: edit.rule_id };
    await api(edit.isNew ? "/rules" : `/rules/${edit.rule_id}`, { method: edit.isNew ? "POST" : "PUT", body });
    setEdit(null);
  }, "Rule saved as a new version");
  const saveFact = () => run(async () => {
    const j = (s: string, d: any) => { try { return JSON.parse(s || JSON.stringify(d)); } catch { throw new Error("Numeric and rewrite fields must be valid JSON"); } };
    const body = { id: fedit.id, statement: fedit.statement, kind: fedit.kind, keywords: fedit.keywords.split(",").map((s: string) => s.trim()).filter(Boolean),
      supports: j(fedit.supports, []), contradicts: j(fedit.contradicts, []), numeric: j(fedit.numeric, {}), qualifier: fedit.qualifier, rewrite: j(fedit.rewrite, []),
      source: fedit.source, owner: fedit.owner, valid_from: fedit.valid_from || null, valid_to: fedit.valid_to || null };
    await api(`/facts/${fedit.id}`, { method: "PUT", body });
    setFedit(null);
  }, "Fact saved");
  const importGuide = () => run(async () => {
    const form = new FormData(); form.append("text", importText); if (importFile) form.append("file", importFile);
    const r = await api("/guidelines/import", { form });
    setTab("rules"); say(`${r.length} draft rule(s) created. Review and approve them below.`);
  }, "Imported");

  const drafts = rules.filter((r) => r.status === "draft");
  return (
    <Shell>
      <h1 className="mb-5 text-3xl font-extrabold">Guidelines, facts and assets</h1>
      <p className="mb-3 mt-1 text-sm text-slate-800">The Brand Constitution (versioned rules), the dated Fact Vault and the approved library. {owner ? "You can change them." : "Only the guideline owner can change them."}</p>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "rules", label: `Rules (${rules.filter((r) => r.is_current).length})` }, { id: "facts", label: `Fact Vault (${facts.length})` }, { id: "lib", label: "Library" }, ...(owner ? [{ id: "import", label: "Import guidelines" }] : [])]} />

      {tab === "rules" && (
        <div className="space-y-4">
          {drafts.length > 0 && (
            <div className="card border-amber-600"><h2 className="font-bold">Draft rules waiting for approval ({drafts.length})</h2>
              <ul className="mt-2 space-y-2">{drafts.map((r) => (
                <li key={r.pk} className="rounded border border-slate-300 p-2 text-sm"><b>{r.rule_id}</b> <Sev s={r.severity} /> <Chip>{r.method === "judgment" ? "needs AI judge" : r.method}</Chip> {r.title}
                  <div className="text-xs text-slate-700">Source: {r.source}</div>
                  {owner && <div className="mt-1 flex gap-2"><button className="btn btn-ok" onClick={() => run(() => api(`/rules/${r.pk}/decision`, { body: { action: "approve" } }), "Rule approved and live")}>Approve</button>
                    <button className="btn btn-danger" onClick={() => run(() => api(`/rules/${r.pk}/decision`, { body: { action: "reject" } }), "Rule rejected")}>Reject</button></div>}</li>))}</ul></div>)}
          {owner && <button className="btn btn-primary" onClick={() => setEdit({ isNew: true, rule_id: "", title: "", category: "messaging", severity: "medium", description: "", method: "phrase", paramsText: '{"phrases": []}' })}>New rule</button>}
          <div className="card overflow-x-auto p-0"><table className="w-full"><thead><tr><th className="th">ID</th><th className="th">Rule</th><th className="th">Category</th><th className="th">Severity</th><th className="th">Method</th><th className="th">Version</th><th className="th"></th></tr></thead>
            <tbody>{rules.filter((r) => r.is_current).map((r) => (
              <tr key={r.pk}><td className="td font-bold">{r.rule_id}</td><td className="td">{r.title}<div className="text-xs text-slate-700">{r.description}</div></td><td className="td">{r.category}</td><td className="td"><Sev s={r.severity} /></td>
                <td className="td text-xs">{r.method}</td><td className="td">v{r.version}</td>
                <td className="td">{owner && <button className="btn btn-ghost" onClick={() => setEdit({ ...r, paramsText: JSON.stringify(r.params, null, 2) })}>Edit</button>}</td></tr>))}</tbody></table></div>
          {edit && (
            <div className="card max-w-2xl space-y-3" role="dialog" aria-label="Edit rule">
              <h2 className="font-bold">{edit.isNew ? "New rule" : `Edit ${edit.rule_id} (saves as v${edit.version + 1})`}</h2>
              {edit.isNew && <div><label className="label" htmlFor="rid">Rule ID</label><input id="rid" className="input" value={edit.rule_id} onChange={(e) => setEdit({ ...edit, rule_id: e.target.value })} /></div>}
              <div><label className="label" htmlFor="rt">Title</label><input id="rt" className="input" value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></div>
              <div className="grid grid-cols-3 gap-3">
                <div><label className="label" htmlFor="rs">Severity</label><select id="rs" className="input" value={edit.severity} onChange={(e) => setEdit({ ...edit, severity: e.target.value })}><option>low</option><option>medium</option><option>high</option></select></div>
                <div><label className="label" htmlFor="rc">Category</label><input id="rc" className="input" value={edit.category} onChange={(e) => setEdit({ ...edit, category: e.target.value })} /></div>
                <div><label className="label" htmlFor="rm">Method</label><input id="rm" className="input" value={edit.method} onChange={(e) => setEdit({ ...edit, method: e.target.value })} /></div></div>
              <div><label className="label" htmlFor="rd">Description</label><textarea id="rd" rows={2} className="input" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></div>
              <div><label className="label" htmlFor="rp">Settings (JSON)</label><textarea id="rp" rows={7} className="input font-mono text-xs" value={edit.paramsText} onChange={(e) => setEdit({ ...edit, paramsText: e.target.value })} /></div>
              <div className="flex gap-2"><button className="btn btn-primary" onClick={saveRule}>Save</button><button className="btn btn-ghost" onClick={() => setEdit(null)}>Cancel</button></div></div>)}
        </div>
      )}

      {tab === "facts" && (
        <div className="space-y-4">
          {owner && <button className="btn btn-primary" onClick={() => setFedit({ id: `F-${facts.length + 30}`, statement: "", kind: "general", keywords: "", supports: "[]", contradicts: "[]", numeric: "{}", qualifier: "", rewrite: "[]", source: "", owner: "", valid_from: "", valid_to: "" })}>New fact</button>}
          <div className="card overflow-x-auto p-0"><table className="w-full"><thead><tr><th className="th">ID</th><th className="th">Approved fact</th><th className="th">Source / owner</th><th className="th">Valid until</th><th className="th"></th></tr></thead>
            <tbody>{facts.map((f) => {
              const d = daysLeft(f.valid_to);
              return (<tr key={f.id}><td className="td font-bold">{f.id}</td><td className="td">{f.statement}<div className="text-xs text-slate-700">type: {f.kind}</div></td><td className="td text-xs">{f.source}<div>{f.owner}</div></td>
                <td className="td">{f.valid_to || "no expiry"} {d !== null && (d < 0 ? <Chip tone="red">EXPIRED</Chip> : d < 30 ? <Chip tone="amber">{d} days left</Chip> : null)}</td>
                <td className="td whitespace-nowrap">{owner && <><button className="btn btn-ghost" onClick={() => setFedit({ ...f, keywords: f.keywords.join(", "), supports: JSON.stringify(f.supports), contradicts: JSON.stringify(f.contradicts), numeric: JSON.stringify(f.numeric), rewrite: JSON.stringify(f.rewrite), valid_from: f.valid_from || "", valid_to: f.valid_to || "" })}>Edit</button>{" "}
                  <button className="btn btn-danger" onClick={() => confirm(`Delete ${f.id}?`) && run(() => api(`/facts/${f.id}`, { method: "DELETE" }), "Fact deleted")}>Delete</button></>}</td></tr>);
            })}</tbody></table></div>
          {fedit && (
            <div className="card max-w-3xl space-y-3" role="dialog" aria-label="Edit fact">
              <h2 className="font-bold">Fact {fedit.id}</h2>
              <div><label className="label" htmlFor="fs">Approved statement</label><textarea id="fs" rows={2} className="input" value={fedit.statement} onChange={(e) => setFedit({ ...fedit, statement: e.target.value })} /></div>
              <div className="grid gap-3 md:grid-cols-3">
                <div><label className="label" htmlFor="fsrc">Source (required)</label><input id="fsrc" className="input" value={fedit.source} onChange={(e) => setFedit({ ...fedit, source: e.target.value })} /></div>
                <div><label className="label" htmlFor="fo">Owner (required)</label><input id="fo" className="input" value={fedit.owner} onChange={(e) => setFedit({ ...fedit, owner: e.target.value })} /></div>
                <div><label className="label" htmlFor="fk">Type</label><input id="fk" className="input" value={fedit.kind} onChange={(e) => setFedit({ ...fedit, kind: e.target.value })} /></div>
                <div><label className="label" htmlFor="ff">Valid from</label><input id="ff" type="date" className="input" value={fedit.valid_from} onChange={(e) => setFedit({ ...fedit, valid_from: e.target.value })} /></div>
                <div><label className="label" htmlFor="ft">Valid until (blank = no expiry)</label><input id="ft" type="date" className="input" value={fedit.valid_to} onChange={(e) => setFedit({ ...fedit, valid_to: e.target.value })} /></div>
                <div><label className="label" htmlFor="fq">Qualifier (e.g. up to)</label><input id="fq" className="input" value={fedit.qualifier} onChange={(e) => setFedit({ ...fedit, qualifier: e.target.value })} /></div></div>
              <div><label className="label" htmlFor="fkw">Keywords (comma separated; a claim must contain one to match this fact)</label><input id="fkw" className="input" value={fedit.keywords} onChange={(e) => setFedit({ ...fedit, keywords: e.target.value })} /></div>
              <details><summary className="cursor-pointer text-sm font-semibold">Advanced matching (JSON)</summary>
                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  {["supports", "contradicts", "numeric", "rewrite"].map((k) => (
                    <div key={k}><label className="label" htmlFor={`fa-${k}`}>{k}</label><textarea id={`fa-${k}`} rows={2} className="input font-mono text-xs" value={fedit[k]} onChange={(e) => setFedit({ ...fedit, [k]: e.target.value })} /></div>))}</div></details>
              <div className="flex gap-2"><button className="btn btn-primary" onClick={saveFact}>Save fact</button><button className="btn btn-ghost" onClick={() => setFedit(null)}>Cancel</button></div></div>)}
        </div>
      )}

      {tab === "lib" && (
        <div className="space-y-4">
          <section className="card"><h2 className="font-bold">Palette</h2>
            <ul className="mt-2 flex flex-wrap gap-3">{lib.filter((i) => i.kind === "palette").map((i) => (
              <li key={i.id} className="flex items-center gap-2 text-sm"><span aria-hidden className="inline-block h-8 w-8 rounded border border-slate-400" style={{ background: i.value.hex }} /><span><b>{i.name}</b><br />{i.value.hex}</span></li>))}</ul></section>
          <section className="card"><h2 className="font-bold">Approved terms</h2><ul className="mt-2 list-disc pl-5 text-sm">{lib.filter((i) => i.kind === "term").map((i) => <li key={i.id}><b>{i.name}</b>: {i.value.note}</li>)}</ul></section>
          <section className="card"><h2 className="font-bold">Competitor names (never disparage)</h2><p className="mt-1 text-sm">{lib.filter((i) => i.kind === "competitor").map((i) => i.name).join(", ") || "None"}</p></section>
          <section className="card"><h2 className="font-bold">Logos</h2><p className="mt-1 text-sm">{lib.filter((i) => i.kind === "logo").map((i) => i.name).join(", ") || "None"}. Logo usage is not verified automatically in this version.</p></section>
          {owner && (
            <form className="card max-w-xl space-y-3" onSubmit={(e) => { e.preventDefault(); run(() => api("/library", { body: { kind: item.kind, name: item.name, value: item.kind === "palette" ? { hex: item.hex } : {} } }), "Added"); }}>
              <h2 className="font-bold">Add to library</h2>
              <div className="grid gap-3 md:grid-cols-3">
                <div><label className="label" htmlFor="ik">Type</label><select id="ik" className="input" value={item.kind} onChange={(e) => setItem({ ...item, kind: e.target.value })}><option value="term">term</option><option value="palette">palette colour</option><option value="competitor">competitor</option></select></div>
                <div><label className="label" htmlFor="in">Name</label><input id="in" required className="input" value={item.name} onChange={(e) => setItem({ ...item, name: e.target.value })} /></div>
                {item.kind === "palette" && <div><label className="label" htmlFor="ih">Hex (#0E7C7B)</label><input id="ih" className="input" value={item.hex} onChange={(e) => setItem({ ...item, hex: e.target.value })} /></div>}</div>
              <button className="btn btn-primary" type="submit">Add</button></form>)}
        </div>
      )}

      {tab === "import" && owner && (
        <div className="card max-w-3xl space-y-3">
          <h2 className="font-bold">Import a guideline document</h2>
          <p className="text-sm">Sentences with words like must, never, always or avoid become <b>draft</b> rules. Nothing is enforced until you approve each rule. Quoted phrases in a "never" sentence become checkable phrase rules; the rest need an AI judge.</p>
          <div><label className="label" htmlFor="it">Paste guideline text</label><textarea id="it" rows={8} className="input" value={importText} onChange={(e) => setImportText(e.target.value)} /></div>
          <div><label className="label" htmlFor="if">...or upload a PDF, .md or .txt</label><input id="if" type="file" accept=".pdf,.md,.txt" onChange={(e) => setImportFile(e.target.files?.[0] || null)} /></div>
          <button className="btn btn-primary" disabled={!importText.trim() && !importFile} onClick={importGuide}>Create draft rules</button>
        </div>
      )}
      {rules.length === 0 && <Empty>Loading...</Empty>}
      <Toast {...toast} onClose={() => setToast({ ...toast, msg: "" })} />
    </Shell>
  );
}
