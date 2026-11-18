"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ROLE_LABEL } from "@/lib/api";

const ROLE_HINT: Record<string, string> = {
  creator: "Submit content and accept fixes", external: "See only your own assets", manager: "Approve normal items",
  reviewer: "Approve high-risk claims", owner: "Manage rules and facts",
};

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [demo, setDemo] = useState<any[]>([]);
  useEffect(() => { api("/demo-users").then(setDemo).catch(() => {}); }, []);
  const submit = async (e?: React.FormEvent, em = email, pw = password) => {
    e?.preventDefault();
    setErr("");
    try {
      const r = await api("/auth/login", { body: { email: em, password: pw } });
      localStorage.setItem("bp_token", r.token); localStorage.setItem("bp_user", JSON.stringify(r.user));
      router.replace("/");
    } catch (x: any) { setErr(x.message); }
  };
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative flex flex-col justify-between overflow-hidden bg-ink p-8 text-white sm:p-12">
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-brand/30 blur-3xl" aria-hidden />
        <p className="font-display text-xl font-extrabold">BrandProof</p>
        <div className="rise relative my-12">
          <h1 className="max-w-lg text-4xl font-extrabold leading-[1.1] sm:text-5xl">Every claim gets proof. Every verdict gets a receipt.</h1>
          <p className="mt-4 max-w-md text-base text-slate-300">Check content against your approved rules and facts before it goes live. A person always makes the final call.</p>
          <div className="mt-8 max-w-sm rotate-[-1.5deg] rounded-2xl bg-white p-5 text-ink shadow-2xl">
            <div className="flex items-center justify-between"><p className="text-sm font-bold">Proof Pack</p><span className="rounded-full bg-okbg px-2.5 py-0.5 text-xs font-semibold text-ok">Human approved</span></div>
            <ul className="mt-3 space-y-2 text-sm">
              <li className="flex gap-2"><span className="text-ok" aria-hidden>&#10003;</span>3 claims checked against dated facts</li>
              <li className="flex gap-2"><span className="text-ok" aria-hidden>&#10003;</span>No hidden text in the file</li>
              <li className="flex gap-2"><span className="text-warn" aria-hidden>!</span>2 checks sent to a human</li>
            </ul>
          </div>
        </div>
        <p className="relative text-xs text-slate-400">Fictional brand &ldquo;Finora&rdquo; for demonstration.</p>
      </section>
      <section className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <h2 className="text-2xl font-extrabold">Sign in</h2>
          <p className="mt-1 text-sm text-slate-600">Pick a demo account to explore, or use your own email.</p>
          <ul className="mt-5 grid gap-2" aria-label="Demo accounts">
            {demo.map((u) => (
              <li key={u.id}><button className="group flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left transition hover:border-brand hover:shadow-soft" onClick={() => submit(undefined, u.email, process.env.NEXT_PUBLIC_DEMO_PASSWORD || "demo1234")}>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brandbg text-sm font-bold text-brand">{String(u.name)[0]}</span>
                <span className="flex-1"><span className="block text-sm font-semibold">{u.name}</span><span className="block text-xs text-slate-600">{ROLE_LABEL[u.role]}: {ROLE_HINT[u.role] || ""}</span></span>
                <span className="text-sm font-semibold text-brand opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">Enter</span>
              </button></li>
            ))}
          </ul>
          <div className="my-6 flex items-center gap-3 text-xs text-slate-500"><span className="h-px flex-1 bg-slate-200" />or use email<span className="h-px flex-1 bg-slate-200" /></div>
          <form onSubmit={submit} className="space-y-4">
            <div><label htmlFor="email" className="label">Email</label><input id="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></div>
            <div><label htmlFor="pw" className="label">Password</label><input id="pw" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></div>
            {err && <p role="alert" className="rounded-lg bg-stampbg px-3 py-2 text-sm font-semibold text-stamp">{err}</p>}
            <button className="btn btn-primary w-full py-2.5" type="submit">Sign in</button>
          </form>
        </div>
      </section>
    </main>
  );
}
