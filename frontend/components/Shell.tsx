"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { ROLE_LABEL } from "@/lib/api";

export function useUser() {
  const [user, setUser] = useState<any>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem("bp_user") || "null")); } catch { setUser(null); }
    setReady(true);
  }, []);
  return { user, ready };
}

const I = ({ d }: { d: string }) => (
  <svg aria-hidden viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
);
const ICON = {
  home: "M3 11l9-8 9 8v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z",
  plus: "M12 5v14M5 12h14",
  book: "M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2zM4 19a2 2 0 012-2h13",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 100 6 3 3 0 000-6z",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
};

export default function Shell({ children }: { children: ReactNode }) {
  const { user, ready } = useUser();
  const router = useRouter();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => { if (ready && !user) router.replace("/login"); }, [ready, user, router]);
  useEffect(() => setOpen(false), [path]);
  if (!ready || !user) return <div className="grid min-h-screen place-items-center text-sm text-slate-600">Loading your workspace…</div>;
  const groups = [
    { title: "Work", links: [
      { href: "/", label: "Dashboard", hint: "Your assets and queue", icon: ICON.home },
      ...(user.role !== "owner" ? [{ href: "/new", label: "New submission", hint: "Check content before publishing", icon: ICON.plus }] : []),
    ] },
    { title: "Rules and trust", links: [
      { href: "/governance", label: "Guidelines and facts", hint: "Approved rules and sources", icon: ICON.book },
      { href: "/rulebook", label: "Rulebook health", hint: "Loopholes and unclear rules", icon: ICON.shield },
      { href: "/disclosure", label: "AI disclosure", hint: "What AI sees and logs", icon: ICON.eye },
      ...(["manager", "reviewer", "owner"].includes(user.role) ? [{ href: "/audit", label: "Audit log", hint: "Tamper-evident history", icon: ICON.list }] : []),
    ] },
  ];
  const out = () => { localStorage.removeItem("bp_token"); localStorage.removeItem("bp_user"); router.replace("/login"); };
  const active = (h: string) => (h === "/" ? path === "/" : path.startsWith(h));
  const initials = String(user.name || "?").split(" ").map((w: string) => w[0]).slice(0, 2).join("");
  return (
    <div className="min-h-screen lg:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-2">Skip to content</a>
      <header className="sticky top-0 z-30 flex items-center justify-between bg-ink px-4 py-3 text-white lg:hidden">
        <Link href="/" className="font-display text-lg font-extrabold">BrandProof</Link>
        <button onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="side" className="rounded-lg border border-white/30 px-3 py-1.5 text-sm font-semibold">{open ? "Close" : "Menu"}</button>
      </header>
      <aside id="side" className={`${open ? "flex" : "hidden"} z-20 w-full flex-col bg-ink text-slate-200 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-72 lg:shrink-0`}>
        <Link href="/" className="hidden items-center gap-2.5 px-6 pb-2 pt-6 lg:flex">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand text-white"><svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M8.5 12l2.5 2.5 4.5-5" /></svg></span>
          <span className="font-display text-xl font-extrabold text-white">BrandProof</span>
        </Link>
        <nav aria-label="Main" className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          {groups.map((g) => (
            <div key={g.title}>
              <p className="mb-1.5 px-3 text-xs font-semibold text-slate-400">{g.title}</p>
              {g.links.map((l) => (
                <Link key={l.href} href={l.href} aria-current={active(l.href) ? "page" : undefined}
                  className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${active(l.href) ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white"}`}>
                  <span className={active(l.href) ? "text-teal-300" : "text-slate-400 group-hover:text-teal-300"}><I d={l.icon} /></span>
                  <span><span className="block text-sm font-semibold leading-tight">{l.label}</span><span className="block text-xs text-slate-400">{l.hint}</span></span>
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="m-3 flex items-center gap-3 rounded-xl bg-white/5 p-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand text-sm font-bold text-white">{initials}</span>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-white">{user.name}</p><p className="truncate text-xs text-slate-400">{ROLE_LABEL[user.role]}</p></div>
          <button onClick={out} className="rounded-lg border border-white/20 px-2.5 py-1 text-xs font-semibold hover:bg-white/10">Sign out</button>
        </div>
      </aside>
      <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-8 lg:py-10"><div className="mx-auto max-w-6xl">{children}</div></main>
    </div>
  );
}
