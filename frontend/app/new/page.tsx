"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Shell from "@/components/Shell";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";

export default function NewSubmission() {
  const router = useRouter();
  const [f, setF] = useState({ title: "", intent: "", channel: "social", text: "", alt_text: "", ai_generated: false });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
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
            <input id="file" type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg,.txt,.md" onChange={(e) => setFile(e.target.files?.[0] || null)} /></div>
          <div><label htmlFor="alt" className="label">Alt text for images (optional)</label><input id="alt" className="input" placeholder="Describe the image for screen readers" value={f.alt_text} onChange={(e) => set("alt_text", e.target.value)} /></div>
        </fieldset>
        {err && <p role="alert" className="rounded-lg bg-stampbg px-3 py-2 text-sm font-semibold text-stamp">{err}</p>}
        <button disabled={busy} className="btn btn-brand w-full py-3 text-base sm:w-auto" type="submit">{busy ? "Checking your content…" : "Check my content"}</button>
      </form>
      <aside className="card h-fit bg-ink text-slate-200 lg:sticky lg:top-8" aria-label="What happens next">
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
