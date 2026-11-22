"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ROLE_LABEL } from "@/lib/api";
import ThemeToggle from "@/components/ThemeToggle";

const ROLE_HINT: Record<string, string> = {
  creator: "Submit content and accept fixes", external: "See only your own assets", manager: "Approve normal items",
  reviewer: "Approve high-risk claims", owner: "Manage rules and facts",
};

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<any[]>([]);
  const [demoState, setDemoState] = useState<"loading" | "ready" | "failed">("loading");
  const [secs, setSecs] = useState(0);
  const [attempt, setAttempt] = useState(0);

  // Load demo accounts. The free server may be asleep, so retry every 5 s for about a minute.
  useEffect(() => {
    let alive = true, tries = 0;
    setDemoState("loading"); setSecs(0);
    const load = () => {
      api("/demo-users")
        .then((d) => { if (alive) { setDemo(Array.isArray(d) ? d : []); setDemoState("ready"); } })
        .catch(() => {
          if (!alive) return;
          if (++tries < 12) setTimeout(load, 5000);
          else setDemoState("failed");
        });
    };
    load();
    return () => { alive = false; };
  }, [attempt]);

  // Seconds counter shown while waiting.
  useEffect(() => {
    if (demoState !== "loading") return;
    const t = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [demoState]);

  const submit = async (e?: React.FormEvent, em = email, pw = password) => {
    e?.preventDefault();
    setErr(""); setBusy(true);
    try {
      const r = await api("/auth/login", { body: { email: em, password: pw } });
      localStorage.setItem("bp_token", r.token); localStorage.setItem("bp_user", JSON.stringify(r.user));
      router.replace("/");
    } catch (x: any) { setErr(x.message); setBusy(false); }
  };
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative flex flex-col justify-between overflow-hidden bg-navy p-8 text-white sm:p-12">
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-brand/30 blur-3xl" aria-hidden />
        <p className="font-display text-xl font-extrabold">BrandProof</p>
        <div className="rise relative my-12">
          <h1 className="max-w-lg text-4xl font-extrabold leading-[1.1] sm:text-5xl">Every claim gets proof. Every verdict gets a receipt.</h1>
          <p className="mt-4 max-w-md text-base text-[#cbd5e1]">Check content against your approved rules and facts before it goes live. A person always makes the final call.</p>
          <div className="mt-8 max-w-sm rotate-[-1.5deg] rounded-2xl bg-surface p-5 text-ink shadow-2xl">
            <div className="flex items-center justify-between"><p className="text-sm font-bold">Proof Pack</p><span className="rounded-full bg-okbg px-2.5 py-0.5 text-xs font-semibold text-ok">Human approved</span></div>
            <ul className="stagger mt-3 space-y-2 text-sm">
              <li className="flex gap-2"><span className="text-ok" aria-hidden>&#10003;</span>3 claims checked against dated facts</li>
              <li className="flex gap-2"><span className="text-ok" aria-hidden>&#10003;</span>No hidden text in the file</li>
              <li className="flex gap-2"><span className="text-warn" aria-hidden>!</span>2 checks sent to a human</li>
            </ul>
          </div>
        </div>
        <p className="relative text-xs text-[#94a3b8]">Fictional brand &ldquo;Finora&rdquo; for demonstration.</p>
      </section>
      <section className="relative flex items-center justify-center p-6 sm:p-12">
        <ThemeToggle className="absolute right-5 top-5" />
        <div className="w-full max-w-md">
          <h2 className="text-3xl font-extrabold">Welcome back</h2>
          <p className="mt-1 text-sm text-slate-600">Pick a demo account to explore, or use your own email.</p>

          {/* Wrapper keeps aria-label="Demo accounts" in every state so the guided tour can always find it. */}
          <div aria-label="Demo accounts" role="group" className="mt-5">
            {demoState === "loading" && (
              <div role="status" aria-live="polite">
                <p className="text-sm font-semibold">Loading demo accounts… {secs}s</p>
                <p className="mt-1 text-xs text-slate-600">
                  The free demo server is waking up. The first load can take up to a minute.
                  Please wait: your accounts will appear here automatically.
                </p>
                <div className="mt-3 grid gap-2" aria-hidden>
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="h-14 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
                  ))}
                </div>
              </div>
            )}
            {demoState === "failed" && (
              <div role="alert" className="rounded-xl border border-slate-200 p-4 text-sm">
                <p className="font-semibold">The server is taking longer than usual.</p>
                <p className="mt-1 text-xs text-slate-600">You can still sign in with the email form below, or try again.</p>
                <button type="button" className="btn btn-primary mt-3" onClick={() => setAttempt((a) => a + 1)}>Try again</button>
              </div>
            )}
            {demoState === "ready" && demo.length > 0 && (
              <ul className="stagger grid gap-2">
                {demo.map((u) => (
                  <li key={u.id}><button disabled={busy} className="group flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-surface p-3 text-left transition hover:-translate-y-px hover:border-brand hover:shadow-soft" onClick={() => submit(undefined, u.email, process.env.NEXT_PUBLIC_DEMO_PASSWORD || "demo1234")}>
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brandbg text-sm font-bold text-brand">{String(u.name)[0]}</span>
                    <span className="flex-1"><span className="block text-sm font-semibold">{u.name}</span><span className="block text-xs text-slate-600">{ROLE_LABEL[u.role]}: {ROLE_HINT[u.role] || ""}</span></span>
                    <span className="text-sm font-semibold text-brand opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">Enter</span>
                  </button></li>
                ))}
              </ul>
            )}
            {demoState === "ready" && demo.length === 0 && (
              <p className="text-xs text-slate-600">Demo accounts are switched off. Sign in with your email below.</p>
            )}
          </div>

          {busy && <p role="status" className="mt-3 text-xs text-slate-600">Signing in… if the server was asleep this can take up to a minute. Please don&rsquo;t click again.</p>}

          <div className="my-6 flex items-center gap-3 text-xs text-[#94a3b8]"><span className="h-px flex-1 bg-slate-200" />or use email<span className="h-px flex-1 bg-slate-200" /></div>
          <form onSubmit={submit} className="space-y-4">
            <div><label htmlFor="email" className="label">Email</label><input id="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></div>
            <div><label htmlFor="pw" className="label">Password</label><div className="relative"><input id="pw" type={show ? "text" : "password"} className="input pr-16" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /><button type="button" onClick={() => setShow(!show)} aria-pressed={show} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs font-semibold text-brand hover:bg-brandbg">{show ? "Hide" : "Show"}</button></div></div>
            {err && <p role="alert" className="rounded-lg bg-stampbg px-3 py-2 text-sm font-semibold text-stamp">{err}</p>}
            <button className="btn btn-primary w-full py-2.5" type="submit" disabled={busy}>{busy ? "Signing in… (can take up to a minute)" : "Sign in"}</button>
          </form>
        </div>
      </section>
    </main>
  );
}