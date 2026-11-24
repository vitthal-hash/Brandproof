"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Shell from "@/components/Shell";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";


type Sample = {
  id: string; label: string; kind: "Text" | "PDF" | "Image"; blurb: string; expect: string;
  fields: { title: string; intent: string; channel: string; text: string; alt_text: string; ai_generated: boolean };
  file?: { url: string; name: string; type: string };
};
// Ready-made content for trying the app. Each one was run through the review engine; "expect" says what it should show.
const SAMPLES: Sample[] = [
  { id: "hinglish", label: "Hinglish festive post", kind: "Text", blurb: "Hindi-English wording is understood too.",
    expect: "About 6 findings: the guarantee-style claim (\"pakka munafa\") and \"sure shot returns\" are contradicted by the Fact Vault, and the pressure wording is caught.",
    fields: { title: "Festive offer (Hinglish)", intent: "Festive offer on Finora Save", channel: "social", alt_text: "", ai_generated: false,
      text: "Finora Save mein pakka munafa har mahine! Sure shot returns, koi risk nahi. Abhi hi karo, mauka mat chhodo, jaldi karo varna chhut jayega. Sabse best savings account." } },
  { id: "clean", label: "A clean post", kind: "Text", blurb: "Should pass: shows it does not flag everything.",
    expect: "No findings. Good copy goes through untouched, and a person still approves it.",
    fields: { title: "App update note", intent: "Tell customers about the Finora app update", channel: "web", alt_text: "", ai_generated: false,
      text: "The Finora app now lets you download your monthly statement as a PDF. Open Settings, choose Statements, and pick a month. Terms apply." } },
  { id: "flyer", label: "Flyer with hidden text", kind: "PDF", blurb: "White text tells an AI to approve it.",
    expect: "About 20 findings and a red warning: hidden text inside the PDF is found, shown, and removed before the review. Instructions aimed at an AI reviewer are reported, and the Proof Pack shows the raw and cleaned versions.",
    fields: { title: "Diwali flyer", intent: "Announce Finora Save for Diwali", channel: "print", text: "", alt_text: "", ai_generated: false },
    file: { url: "/samples/Diwali_Flyer_HIDDEN_TEXT.pdf", name: "Diwali_Flyer_HIDDEN_TEXT.pdf", type: "application/pdf" } },
  { id: "poster", label: "Poster with wrong colours", kind: "Image", blurb: "Off-palette colours, a logo problem, no alt text.",
    expect: "Visual findings: colours outside the approved palette, a logo that breaks the logo rule, and a missing alt text.",
    fields: { title: "Diwali poster", intent: "Announce Finora Save for Diwali", channel: "print", text: "", alt_text: "", ai_generated: false },
    file: { url: "/samples/Diwali_Poster_BAD_COLOURS.png", name: "Diwali_Poster_BAD_COLOURS.png", type: "image/png" } },
  { id: "faint", label: "Image with a faint hidden instruction", kind: "Image", blurb: "Grey text beside normal text, aimed at an AI.",
    expect: "A hidden-text warning and injection findings: the faint grey instruction to ignore the rules and approve is read out of the image and reported.",
    fields: { title: "Account banner", intent: "Invite people to open a Finora Save account", channel: "web", text: "", alt_text: "", ai_generated: false },
    file: { url: "/samples/Finora_Banner_FAINT_TEXT.png", name: "Finora_Banner_FAINT_TEXT.png", type: "image/png" } },
];
const BLANK = { title: "", intent: "", channel: "social", text: "", alt_text: "", ai_generated: false };

export default function NewSubmission() {
  const router = useRouter();
  const [f, setF] = useState({ title: "", intent: "", channel: "social", text: "", alt_text: "", ai_generated: false });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [loaded, setLoaded] = useState<Sample | null>(null);
  const [loadingId, setLoadingId] = useState("");
  const set = (k: string, v: any) => setF((p) => ({ ...p, [k]: v }));  // functional update: several fields can be filled in one go (the tour does this)
  // Same limits as the server (10 MB, five file types) so the person hears about a problem before waiting for an upload.
  const pick = (picked: File | null) => {
    setErr("");
    if (picked && !/\.(pdf|png|jpe?g|txt|md)$/i.test(picked.name)) { setErr("That file type is not supported. Use PDF, PNG, JPG, TXT or MD."); setFile(null); return; }
    if (picked && picked.size > 10 * 1024 * 1024) { setErr("That file is larger than 10 MB. Export a smaller copy and try again."); setFile(null); return; }
    setFile(picked);
  };
  // Fill the form with a sample, and attach its file, so the next click can be "Check my content".
  const loadSample = async (smp: Sample) => {
    setErr(""); setLoadingId(smp.id);
    try {
      let attached: File | null = null;
      if (smp.file) {
        const res = await fetch(smp.file.url).catch(() => null);   // a dropped connection gives no response at all
        if (!res || !res.ok) throw new Error("The sample file could not be loaded. Check your connection and try again.");
        attached = new File([await res.blob()], smp.file.name, { type: smp.file.type });
      }
      setF({ ...smp.fields }); setFile(attached); setLoaded(smp);
      requestAnimationFrame(() => document.getElementById("check-btn")?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
    } catch (x: any) { setErr(x.message || "The sample could not be loaded."); }
    setLoadingId("");
  };
  const clearForm = () => { setF({ ...BLANK }); setFile(null); setLoaded(null); setErr(""); };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const form = new FormData();
      Object.entries(f).forEach(([k, v]) => form.append(k, String(v)));
      if (file) form.append("file", file);
      const a = await api("/assets", { form });
      router.push(`/assets/${a.id}`);
    } catch (x: any) { setErr(x.message); setBusy(false); }
  };
  return (
    <Shell>
      <PageHeader title="New submission" subtitle="Add your content and say what it is for. BrandProof checks it and suggests fixes. Nothing is applied or approved automatically." />
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <div className="space-y-6">
      <section className="card p-6" aria-labelledby="samples-h">
        <h2 id="samples-h" className="font-display text-base font-bold">Try it with a ready-made sample</h2>
        <p className="mt-1 text-sm text-slate-600">Pick one. It fills in the form (and attaches the file), then you press <b>Check my content</b> and see the result.</p>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {SAMPLES.map((smp) => (
            <li key={smp.id}><button type="button" onClick={() => loadSample(smp)} disabled={!!loadingId || busy} aria-pressed={loaded?.id === smp.id}
              className={`flex h-full w-full flex-col rounded-xl border p-3 text-left transition hover:-translate-y-px hover:border-brand hover:shadow-soft disabled:opacity-60 ${loaded?.id === smp.id ? "border-brand bg-brandbg/40" : "border-slate-200 bg-surface"}`}>
              <span className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{smp.label}</span><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">{smp.kind}</span></span>
              <span className="mt-0.5 text-xs text-slate-600">{loadingId === smp.id ? "Loading…" : smp.blurb}</span>
            </button></li>
          ))}
        </ul>
        {loaded && (
          <div role="status" aria-live="polite" className="mt-4 rounded-xl border border-brand/30 bg-brandbg/40 p-3 text-sm">
            <p className="font-semibold">Loaded: {loaded.label}. Now press <b>Check my content</b> below.</p>
            <p className="mt-1 text-slate-700"><b>What you should see:</b> {loaded.expect}</p>
            <button type="button" onClick={clearForm} className="btn btn-ghost mt-2 px-2.5 py-1 text-xs">Clear the form</button>
          </div>
        )}
      </section>
      <form onSubmit={submit} className="card space-y-5 p-6">
        <fieldset className="space-y-4"><legend className="mb-1 font-display text-base font-bold">1. What is it?</legend>
          <div><label htmlFor="title" className="label">Title</label><input id="title" required className="input" placeholder="Savings launch post" value={f.title} onChange={(e) => set("title", e.target.value)} /></div>
          <div><label htmlFor="intent" className="label">Your intent in one line</label>
            <input id="intent" required minLength={5} className="input" placeholder="Announce our new savings account" value={f.intent} onChange={(e) => set("intent", e.target.value)} />
            <p className="hint">Every suggested fix must keep this meaning (Intent Lock).</p></div>
          <div className="grid gap-4 md:grid-cols-2">
            <div><label htmlFor="channel" className="label">Where will it be published?</label>
              <select id="channel" className="input" value={f.channel} onChange={(e) => set("channel", e.target.value)}>
                {["social", "web", "email", "print", "sales deck"].map((c) => <option key={c}>{c}</option>)}</select></div>
            <div className="flex items-end"><label className="flex w-full cursor-pointer items-center gap-3 rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-semibold hover:bg-slate-50"><input type="checkbox" className="h-4 w-4 accent-teal-700" checked={f.ai_generated} onChange={(e) => set("ai_generated", e.target.checked)} /> Made with AI</label></div>
          </div>
        </fieldset>
        <fieldset className="space-y-4 border-t border-slate-100 pt-5"><legend className="mb-1 font-display text-base font-bold">2. Add the content</legend>
          <div><label htmlFor="text" className="label">Paste text</label><textarea id="text" rows={7} className="input" placeholder="Paste your copy here" value={f.text} onChange={(e) => set("text", e.target.value)} /></div>
          <div><label htmlFor="file" className="label">Or upload a file</label>
            <label htmlFor="file" className="flex cursor-pointer flex-col items-center gap-1 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center transition hover:border-brand hover:bg-brandbg/40">
              <span className="text-sm font-semibold">{file ? file.name : "Choose a PDF or image"}</span>
              <span className="text-xs text-slate-600">{file ? "Select again to replace it" : "PDF, PNG, JPG, TXT or MD"}</span>
            </label>
            <input id="file" type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg,.txt,.md" onChange={(e) => pick(e.target.files?.[0] || null)} /></div>
          <div><label htmlFor="alt" className="label">Alt text for images (optional)</label><input id="alt" className="input" placeholder="Describe the image for screen readers" value={f.alt_text} onChange={(e) => set("alt_text", e.target.value)} /></div>
        </fieldset>
        {err && <p role="alert" className="rounded-lg bg-stampbg px-3 py-2 text-sm font-semibold text-stamp">{err}</p>}
        <button id="check-btn" disabled={busy} className="btn btn-brand w-full py-3 text-base sm:w-auto" type="submit">{busy ? "Checking your content…" : "Check my content"}</button>
      </form>
      </div>
      <aside className="card h-fit bg-navy text-[#e2e8f0] lg:sticky lg:top-8" aria-label="What happens next">
        <h2 className="font-display text-base font-bold text-white">What happens next</h2>
        <ol className="mt-4 space-y-4 text-sm">
          {[["Safety scan", "Hidden text and prompt tricks are removed first."], ["Rules and facts", "Claims are checked against dated, approved sources."], ["You decide", "Accept, edit or reject each fix, then send to a reviewer."]].map(([t, d], i) => (
            <li key={t} className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand text-xs font-bold text-white">{i + 1}</span><span><b className="block text-white">{t}</b>{d}</span></li>
          ))}
        </ol>
      </aside>
      </div>
    </Shell>
  );
}