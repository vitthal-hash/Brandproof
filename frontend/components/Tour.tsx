"use client";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

// How a step works
//  route : the page this step lives on. If the person is on any other page the tour PAUSES (no dimming, no card,
//          only a small note) and resumes by itself the moment they reach the right page.
//  sel / text : what to spotlight (CSS selector, or visible text of a button/link/tab/heading).
//  adv   : "click" = move on when the highlighted item is clicked; "route" = move on when the person reaches page `to`.
//          A click that opens page `to` also moves on only once that page has really opened.
//  act   : the one thing the person should do now ("Your turn").
type Step = {
  ch: string; title: string; body: string; route?: string;
  sel?: string; text?: string; act?: string;
  adv?: "next" | "click" | "route"; to?: string;
  fill?: boolean; files?: boolean; wait?: string;
};

const SAMPLE = {
  title: "Diwali savings campaign", intent: "Announce Finora Save for Diwali",
  text: "Finora Save is the BEST savings account for Diwali!!! Earn guaranteed 8% returns every month, 100% safe and RBI approved. Open your account instantly in just 2 seconds. Get a free physical debit card with zero charges, plus a launch cashback of Rs 500. Tax-free interest, available to everyone including NRIs. Our support team is open 24x7. ACT NOW OR LOSE OUT FOREVER, unlike BankX who will rip you off. Call me on 9876543210 or mail riya@finora.example to join today.",
};

export const STEPS: Step[] = [
  { ch: "Start", title: "Welcome to BrandProof", body: "BrandProof checks content against your approved rules and dated facts before it goes live, and a person always decides. This tour points at the real buttons and waits for you, so go at your own pace.", route: "/login", act: "Press Next. You can end the tour any time and bring it back from the Guided tour button (bottom right)." },
  { ch: "Start", title: "Sign in with a demo account", body: "Each card is a different role with different powers. We start as the Creator, who submits content. (Prefer typing? creator@finora.example, password demo1234.)", route: "/login", sel: '[aria-label="Demo accounts"]', adv: "route", to: "/", act: "Click the Creator card. The tour continues as soon as you are in." },
  { ch: "Submit", title: "This is your workspace", body: "The menu on the left is your map. Work holds the dashboard and new submissions. Rules and trust holds the guidelines, AI disclosure and audit log.", route: "/", sel: "aside nav" },
  { ch: "Submit", title: "Your assets at a glance", body: "Every asset sits in one stage: draft, in review, approved and so on. Click a card to filter the list below it.", route: "/", sel: '[aria-label^="Status overview"]' },
  { ch: "Submit", title: "Start a new check", body: "Let us check some content.", route: "/", text: "New submission", adv: "click", to: "/new", act: "Click New submission." },
  { ch: "Submit", title: "Name it and say what it is for", body: "The one-line intent is locked in. Every fix BrandProof suggests must still say what you meant (Intent Lock). Tick Made with AI to see the AI-label rule fire.", route: "/new", sel: "form fieldset:first-of-type", fill: true, act: "Type a title and intent, or press the button below to fill them." },
  { ch: "Submit", title: "Paste your content", body: "Paste any copy here. The sample text has about 15 deliberate mistakes: false claims, an expired offer, pressure language and personal data.", route: "/new", sel: "#text", fill: true, act: "Press Paste sample text for me." },
  { ch: "Submit", title: "Or upload a file", body: "PDFs and images work too. The sample PDF hides white text that tells an AI to approve it. The Trust Layer should catch that. This step is optional.", route: "/new", sel: 'label[for="file"]', files: true },
  { ch: "Submit", title: "Run the check", body: "With AI switched on this can take up to a minute. Please wait and do not click twice. The tour continues when the review opens.", route: "/new", text: "Check my content", adv: "route", to: "/assets/", act: "Click Check my content." },
  { ch: "Review", title: "The review page", body: "Status, risk level, which AI ran, a progress bar and a Next step box that tells each role what to do.", route: "/assets/", sel: "main .card", wait: "Reviewing your content. This can take a minute..." },
  { ch: "Review", title: "Summary", body: "High and medium findings, items sent to a human because the AI was not sure, and fixes that passed re-verification.", route: "/assets/", sel: '[aria-label="Review summary"]' },
  { ch: "Review", title: "A finding, with proof", body: "Each finding cites the exact rule or dated fact, shows whether a rule or the AI found it, and offers a fix. You accept, edit or reject it. Nothing is applied automatically.", route: "/assets/", sel: ".border-l-4" },
  { ch: "Review", title: "Claim Ledger", body: "Every promotional claim gets a verdict (Supported, Contradicted, Outdated, Unsupported or Needs human), each tied to a fact in the vault.", route: "/assets/", text: "Claim Ledger", adv: "click", act: "Click the Claim Ledger tab." },
  { ch: "Review", title: "Trust Layer", body: "Looks for hidden text and prompt-injection tricks. The raw and the cleaned file are reviewed separately, and a different verdict raises a manipulation flag.", route: "/assets/", text: "Trust Layer", adv: "click", act: "Click the Trust Layer tab." },
  { ch: "Review", title: "Comments", body: "Reviewers and creators talk about the exact finding here, not in a separate email thread.", route: "/assets/", text: "Comments", adv: "click", act: "Click the Comments tab." },
  { ch: "Review", title: "History", body: "Every version is kept, with a before and after view of what changed.", route: "/assets/", text: "History", adv: "click", act: "Click the History tab." },
  { ch: "Approve", title: "Send it for review", body: "When you are happy with the findings, hand it to a person. (Accept or edit a fix first if you like.)", route: "/assets/", text: "Submit for review", adv: "click", act: "Click Submit for review." },
  { ch: "Approve", title: "Open the Proof Pack", body: "The Proof Pack is a receipt of what was checked, what was NOT checked, who approved, and which AI saw what.", route: "/assets/", text: "Proof Pack", adv: "click", to: "/proof", act: "Click Proof Pack." },
  { ch: "Approve", title: "The receipt", body: "Trust Layer result, checks run, claims, items not checked, human decisions and AI use. Approved assets also get a signed receipt code, a public verify link and a PDF.", route: "/proof", sel: "article, main .card" },
  { ch: "Approve", title: "Now switch roles: sign out", body: "Different roles see different powers. We will walk through three more, starting with the Brand manager.", route: "/proof", text: "Sign out", adv: "route", to: "/login", act: "Click Sign out." },
  { ch: "Approve", title: "Sign in as Brand manager", body: "Managers approve normal-risk items.", route: "/login", sel: '[aria-label="Demo accounts"]', adv: "route", to: "/", act: "Click the Brand manager card." },
  { ch: "Approve", title: "The review queue", body: "Items waiting for you are listed here.", route: "/", sel: '[aria-label="Review queue"], [aria-label="Assets"]', adv: "route", to: "/assets/", act: "Open the asset you submitted." },
  { ch: "Approve", title: "Approve, or ask for changes", body: "High-risk claims cannot be approved by a manager. They need an authorised reviewer. Try Approve and you will see it blocked with a clear reason.", route: "/assets/", text: "Approve" },
  { ch: "Approve", title: "Switch role again: sign out", body: "Next, the Authorised reviewer, who handles high-risk claims.", route: "/assets/", text: "Sign out", adv: "route", to: "/login", act: "Click Sign out." },
  { ch: "Approve", title: "Sign in as Authorised reviewer", body: "Reviewers decide high-risk claims and can waive a finding with a written reason.", route: "/login", sel: '[aria-label="Demo accounts"]', adv: "route", to: "/", act: "Click the Authorised reviewer card." },
  { ch: "Approve", title: "Find the high-risk asset", body: "Open the asset marked as needing an authorised reviewer.", route: "/", sel: '[aria-label="Review queue"], [aria-label="Assets"]', adv: "route", to: "/assets/", act: "Open the asset." },
  { ch: "Approve", title: "Decide it", body: "Waive a finding with a written reason, then approve. The Proof Pack and the audit log record you by name.", route: "/assets/", text: "Approve" },
  { ch: "Rules", title: "Last role: sign out", body: "The Guideline owner manages the rules, the facts and the red-team.", route: "/assets/", text: "Sign out", adv: "route", to: "/login", act: "Click Sign out." },
  { ch: "Rules", title: "Sign in as Guideline owner", body: "Owners control the rulebook. They do not submit content.", route: "/login", sel: '[aria-label="Demo accounts"]', adv: "route", to: "/", act: "Click the Guideline owner card." },
  { ch: "Rules", title: "Guidelines and facts", body: "Here are the approved rules, the dated Fact Vault, the asset library and guideline import.", route: "/", text: "Guidelines and facts", adv: "click", to: "/governance", act: "Click Guidelines and facts." },
  { ch: "Rules", title: "Rules, facts, library, import", body: "Every finding cites an item from here. Facts have an owner, a source and an expiry date, which is how outdated offers get caught.", route: "/governance", sel: '[role="tablist"]' },
  { ch: "Rules", title: "Rulebook health", body: "Shows which rules reviewers keep overriding and which ones can be dodged.", route: "/governance", text: "Rulebook health", adv: "click", to: "/rulebook", act: "Click Rulebook health." },
  { ch: "Rules", title: "Rulebook Red-Team", body: "An AI adversary writes sneaky content that tries to break a rule. Every miss becomes a loophole, with tighter wording for you to approve and re-test.", route: "/rulebook", text: "Run red-team", act: "Optional: press Run red-team on any rule." },
  { ch: "Rules", title: "AI disclosure", body: "Every model and service, what data each one receives, and every call made.", route: "/rulebook", text: "AI disclosure", adv: "click", to: "/disclosure", act: "Click AI disclosure." },
  { ch: "Rules", title: "What the AI saw", body: "Phone numbers and emails are swapped for tokens before anything leaves the server. Recent calls show the model, purpose and status.", route: "/disclosure", sel: "main table" },
  { ch: "Rules", title: "Audit log", body: "A hash-chained, tamper-evident record of every action.", route: "/disclosure", text: "Audit log", adv: "click", to: "/audit", act: "Click Audit log." },
  { ch: "Rules", title: "Verify the chain", body: "This recomputes every hash and tells you if anything was altered.", route: "/audit", text: "Verify chain", adv: "click", act: "Click Verify chain." },
  { ch: "Proof", title: "Stale approvals", body: "When a fact is edited or expires, every approved asset that is now wrong shows up here. Nothing is changed automatically.", route: "/audit", text: "Stale approvals", adv: "click", to: "/stale", act: "Click Stale approvals." },
  { ch: "Proof", title: "Stale approvals", body: "When a fact is edited or expires, every approved asset that is now wrong shows up here. Nothing is changed automatically. A manager, reviewer or owner can run a scan with the button below the heading.", route: "/stale", sel: '[data-tour="stale-intro"]' },
  { ch: "Proof", title: "The alerts list", body: "Each alert names the asset and how many claims no longer match, and you can open the asset to add a new version or dismiss the alert with a written reason. If this list is empty, every approved asset still matches today's facts.", route: "/stale", sel: '[data-tour="stale-list"]' },
  { ch: "Proof", title: "Trust Layer tests", body: "25 attack files and 8 clean files are generated and scored live.", route: "/stale", text: "Trust Layer tests", adv: "click", to: "/trust", act: "Click Trust Layer tests." },
  { ch: "Proof", title: "The scoreboard", body: "BrandProof generates attack files and clean files on the spot and scores its own Trust Layer. The first two boxes show how many attacks were caught and how many clean files were correctly left alone.", route: "/trust", sel: '[data-tour="trust-score"]', wait: "Running the attack files. This takes a few seconds..." },
  { ch: "Proof", title: "Known gaps are shown on purpose", body: "Two attacks are not caught, and this box says which and why. A scoreboard that hides its misses proves nothing.", route: "/trust", sel: '[aria-label="Known gaps"], [data-tour="trust-table"]', wait: "Running the attack files. This takes a few seconds..." },
  { ch: "Proof", title: "Evaluation", body: "Precision and recall on the seeded set, the held-out probe and the blind set, with confidence intervals.", route: "/trust", text: "Evaluation", adv: "click", to: "/evaluation", act: "Click Evaluation." },
  { ch: "Proof", title: "Scores with error bars", body: "Precision and recall for the hardest set first (the blind set, written after the engine was frozen). The intervals show how far a small sample can be trusted: 5 out of 5 is not proof of 100%.", route: "/evaluation", sel: '[data-tour="eval-stats"]', wait: "Loading the results..." },
  { ch: "Proof", title: "Misses and false positives are listed", body: "Every rule that was missed and every wrongly flagged item is named here instead of being tuned away. The held-out probe and the seeded set are listed below it on the same page.", route: "/evaluation", sel: '[data-tour="eval-misses"]', wait: "Loading the results..." },
  { ch: "Done", title: "That is everything", body: "You can sign in as any role and explore freely. The Guided tour button (bottom right) reopens this tour whenever you like." },
];
/** Where the tour should begin for someone who is already signed in (so an owner is not sent to buttons they do not have). */
export function tourStartIndex(role?: string): number {
  const find = (t: string) => Math.max(0, STEPS.findIndex((x) => x.title === t));
  if (!role) return 0;
  if (role === "owner") return find("Guidelines and facts");
  if (role === "reviewer") return find("Find the high-risk asset");
  if (role === "manager") return find("The review queue");
  return find("This is your workspace");
}
const CHAPTERS = ["Start", "Submit", "Review", "Approve", "Rules", "Proof"];
const KEY = "bp_tour";
const PAGE_NAME: Record<string, string> = {
  "/login": "the sign-in page", "/": "the Dashboard", "/new": "New submission", "/assets/": "an asset's review page", "/proof": "the Proof Pack",
  "/governance": "Guidelines and facts", "/rulebook": "Rulebook health", "/disclosure": "AI disclosure", "/audit": "the Audit log", "/stale": "Stale approvals",
  "/trust": "Trust Layer tests", "/evaluation": "Evaluation",
};

// Does the current path belong to this route? ("/assets/" = a review page but not its Proof Pack; "/proof" = a Proof Pack.)
function matches(route: string | undefined, path: string): boolean {
  if (!route) return true;
  if (route === "/") return path === "/";
  if (route === "/assets/") return path.startsWith("/assets/") && !path.endsWith("/proof");
  if (route === "/proof") return path.endsWith("/proof");
  return path.startsWith(route);
}

function findTarget(s: Step): HTMLElement | null {
  if (s.sel) { try { for (const el of Array.from(document.querySelectorAll<HTMLElement>(s.sel))) if (el.offsetParent !== null || getComputedStyle(el).position === "fixed") return el; } catch {} }
  if (s.text) {
    // Prefer tabs, then the page content, then the rest of the page (the sidebar). Otherwise the sidebar link
    // "Trust Layer tests" would be picked instead of the "Trust Layer" tab on an asset page.
    const vis = (e: HTMLElement) => e.offsetParent !== null && (e.textContent || "").trim().startsWith(s.text!);
    const q = (root: ParentNode, sel: string) => Array.from(root.querySelectorAll<HTMLElement>(sel)).find(vis) || null;
    const all = "button,a,[role=tab],h1,h2,label";
    return q(document, "[role=tab]") || (document.querySelector("main") ? q(document.querySelector("main")!, all) : null) || q(document, all);
  }
  return null;
}
function setVal(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null, v: string) {
  if (!el) return;
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value")!.set!.call(el, v);
  el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
}

export default function Tour() {
  const path = usePathname() || "/";
  const router = useRouter();
  const [i, setI] = useState(0);
  const [on, setOn] = useState(false);
  const [menu, setMenu] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [missing, setMissing] = useState(false);
  const [settled, setSettled] = useState(false);
  const [showPaused, setShowPaused] = useState(false);
  const [cardH, setCardH] = useState(270);
  const cardRef = useRef<HTMLDivElement>(null);
  const scrolled = useRef(-1);
  const lastRect = useRef("");
  const misses = useRef(0);
  const started = useRef(false);
  const step = STEPS[i];
  const onPage = matches(step.route, path);

  const save = (n: number, a: boolean) => { try { sessionStorage.setItem(KEY, JSON.stringify({ i: n, on: a })); } catch {} };
  const go = useCallback((n: number) => { const k = Math.max(0, Math.min(STEPS.length - 1, n)); setI(k); setOn(true); setMenu(false); setRect(null); setMissing(false); setSettled(false); scrolled.current = -1; lastRect.current = ""; save(k, true); }, []);
  const stop = () => { setOn(false); setMenu(false); save(i, false); };

  useEffect(() => {  // Escape ends the tour
    if (!on) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") { setOn(false); setMenu(false); save(i, false); } };
    document.addEventListener("keydown", k);
    return () => document.removeEventListener("keydown", k);
  }, [on, i]);

  useEffect(() => {  // restore, or auto-start once per browser session on the login page
    if (started.current) return;
    let st: any = null; try { st = JSON.parse(sessionStorage.getItem(KEY) || "null"); } catch {}
    if (st && typeof st.i === "number" && st.i >= 0 && st.i < STEPS.length) { started.current = true; setI(st.i); setOn(!!st.on); }
    else if (path.startsWith("/login")) { started.current = true; setOn(true); save(0, true); }
  }, [path]);

  useEffect(() => {  // FOLLOW THE PERSON: move on when they reach the target page, even if they got there their own way
    if (!on) return;
    if (step.adv === "route" && step.to && matches(step.to, path)) { go(i + 1); return; }
    if (step.adv === "click" && step.to && matches(step.to, path) && !onPage) { go(i + 1); return; }
    if (!onPage) {  // they went somewhere else (for example signed in by typing): pick up at the next step that belongs to this page
      for (let k = 1; k <= 6 && i + k < STEPS.length; k++) if (STEPS[i + k].route && matches(STEPS[i + k].route, path)) { go(i + k); return; }
    }
  }, [on, i, path, step, onPage, go]);

  useEffect(() => {  // on the right page: find the target, scroll to it and keep the spotlight on it
    if (!on || !onPage) { setRect(null); return; }
    lastRect.current = ""; misses.current = 0;
    setSettled(!(step.sel || step.text));          // steps that point at nothing (welcome, finish) show at once
    const apply = () => {
      const el = findTarget(step);
      if (!el) {                                   // page still loading, or the element re-rendered for a moment:
        if (++misses.current >= 8) { lastRect.current = ""; setRect(null); }   // let go of the spotlight only after ~2 s
        return;
      }
      misses.current = 0;
      if (scrolled.current !== i) { scrolled.current = i; const r0 = el.getBoundingClientRect(); const vh = window.innerHeight; if (r0.top < 80 || r0.bottom > vh - 240) window.scrollBy({ top: r0.top - (window.innerWidth < 640 ? 90 : vh * 0.28), behavior: "smooth" }); }
      const r = el.getBoundingClientRect();
      const key = [r.left, r.top, r.width, r.height].map(Math.round).join(",");
      if (key !== lastRect.current) { lastRect.current = key; setRect(r); }   // only re-render when the target really moved
      setMissing(false);
    };
    apply(); const t = setInterval(apply, 250);
    let raf = 0; const follow = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(apply); };  // keep the spotlight glued to the target while scrolling
    window.addEventListener("scroll", follow, true); window.addEventListener("resize", follow);
    const settle = setTimeout(() => setSettled(true), 1500);
    const miss = setTimeout(() => setMissing(true), step.wait ? 9000 : 4500);
    const click = (e: MouseEvent) => {
      if (step.adv !== "click" || step.to) return;   // clicks that open another page advance when that page opens (effect above)
      const el = findTarget(step);
      if (el && el.contains(e.target as Node)) setTimeout(() => go(i + 1), 350);
    };
    document.addEventListener("click", click, true);
    return () => { clearInterval(t); clearTimeout(settle); clearTimeout(miss); cancelAnimationFrame(raf); window.removeEventListener("scroll", follow, true); window.removeEventListener("resize", follow); document.removeEventListener("click", click, true); };
  }, [on, i, onPage, step, go]);

  useEffect(() => {  // measure the real card height so it is never placed partly off-screen
    const h = cardRef.current?.offsetHeight;
    if (h && Math.abs(h - cardH) > 2) setCardH(h);
  });

  useEffect(() => {  // show "Tour paused" only if the person is still on another page after a moment (the tour often catches up by itself)
    if (!(on && !onPage)) { setShowPaused(false); return; }
    const t = setTimeout(() => setShowPaused(true), 700);
    return () => clearTimeout(t);
  }, [on, onPage, i, path]);

  const fill = () => {
    setVal(document.querySelector("#title"), SAMPLE.title); setVal(document.querySelector("#intent"), SAMPLE.intent); setVal(document.querySelector("#text"), SAMPLE.text);
    const cb = document.querySelector<HTMLInputElement>('input[type="checkbox"]'); if (cb && !cb.checked) cb.click();
  };
  const skipToHere = () => {  // jump to the step that matches the page the person is on now
    let j = -1;
    for (let k = i + 1; k < STEPS.length && j < 0; k++) if (matches(STEPS[k].route, path)) j = k;
    for (let k = 0; k < i && j < 0; k++) if (matches(STEPS[k].route, path)) j = k;
    if (j >= 0) go(j); else stop();
  };

  const btn = "rounded-lg px-3 py-1.5 text-sm font-semibold";
  const fab = (
    <div className="no-print fixed bottom-4 right-4 z-[70] flex flex-col items-end">
      {on && !onPage && showPaused && (  // PAUSED: nothing dims the page; the person is free to click around
        <div role="status" className="mb-2 w-72 rounded-2xl border border-slate-200 bg-surface p-3 text-sm shadow-xl">
          <p className="font-semibold text-ink">Tour paused</p>
          <p className="mt-0.5 text-slate-700">It carries on by itself when you open {PAGE_NAME[step.route || "/"] || "the next page"}.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {step.route && step.route !== "/assets/" && step.route !== "/proof" && <button onClick={() => router.push(step.route!)} className={`${btn} bg-navy text-white`}>Take me there</button>}
            <button onClick={skipToHere} className={`${btn} bg-brandbg text-brand hover:bg-teal-100`}>Continue from this page</button>
            <button onClick={stop} className={`${btn} text-slate-600 hover:bg-slate-100`}>End</button>
          </div>
        </div>)}
      {menu && (
        <div className="mb-2 w-60 rounded-2xl border border-slate-200 bg-surface p-2 text-sm shadow-xl">
          <p className="px-2 py-1 text-xs font-semibold text-slate-500">Jump to a chapter</p>
          {CHAPTERS.map((c) => <button key={c} className="block w-full rounded-lg px-3 py-2 text-left font-semibold hover:bg-slate-100" onClick={() => go(STEPS.findIndex((s) => s.ch === c))}>{c === "Start" ? "1. Sign in" : c === "Submit" ? "2. Submit content" : c === "Review" ? "3. Read the review" : c === "Approve" ? "4. Approvals and roles" : "5. Rules, AI and audit"}</button>)}
          <button className="mt-1 block w-full rounded-lg px-3 py-2 text-left font-semibold text-brand hover:bg-brandbg" onClick={() => { sessionStorage.removeItem(KEY); go(0); if (!path.startsWith("/login")) router.push("/login"); }}>Restart from the beginning</button>
        </div>)}
      <button onClick={() => (on ? setMenu(!menu) : go(i))} aria-expanded={menu} className="flex items-center gap-2 rounded-full bg-brand px-4 py-2.5 text-sm font-bold text-white shadow-lg hover:bg-teal-800">
        <span aria-hidden>?</span>{on ? `Guided tour ${i + 1}/${STEPS.length}` : "Guided tour"}
      </button>
    </div>);
  if (!on || !onPage) return fab;
  // Target not on screen yet (page or data still loading): never show a card in the middle that later jumps next to the target.
  // Show nothing for a moment, then a small corner note, and only give up with the centred card after a longer wait.
  if (!rect && (step.sel || step.text) && !missing) {
    return (<>
      {settled && <div role="status" className="no-print fixed bottom-20 right-4 z-[70] w-72 rounded-2xl border border-slate-200 bg-surface p-3 text-sm shadow-xl">
        <p className="font-semibold text-ink">{step.title}</p>
        <p className="mt-0.5 text-slate-700">{step.wait || "Getting this page ready..."}</p>
      </div>}
      {fab}
    </>);
  }

  const center = !rect;
  const vw = typeof window !== "undefined" ? window.innerWidth : 1200, vh = typeof window !== "undefined" ? window.innerHeight : 800;
  const cardW = Math.min(380, vw - 24);
  let pos: React.CSSProperties = { left: "50%", top: "50%", transform: "translate(-50%,-50%)" };
  if (!center && rect) {
    if (vw < 640) pos = { left: 12, right: 12, bottom: 76, width: "auto" };
    else {
      const left = Math.max(12, Math.min(vw - cardW - 12, rect.left));
      if (rect.bottom + 14 + cardH < vh - 12) pos = { left, top: rect.bottom + 14 };                      // room below the target
      else if (rect.top - cardH > 12) pos = { left, top: rect.top - 14 - cardH };                // room above it
      else if (rect.right + cardW + 24 < vw) pos = { left: rect.right + 14, top: Math.max(12, Math.min(rect.top, vh - cardH - 12)) };  // room to its right
      else if (rect.left - cardW - 24 > 0) pos = { left: rect.left - cardW - 14, top: Math.max(12, Math.min(rect.top, vh - cardH - 12)) };  // room to its left (sign-in page)
      else pos = { left: Math.max(12, vw - cardW - 12), bottom: 76 };                           // target fills the screen: dock the card low, out of the way
    }
  }
  const ring = rect ? { top: Math.max(rect.top - 6, 4), left: Math.max(rect.left - 6, 4) } : null;   // never draw the highlight off-screen
  const ringH = rect && ring ? Math.min(rect.bottom + 6, vh - 4) - ring.top : 0;
  const ringW = rect && ring ? Math.min(rect.right + 6, vw - 4) - ring.left : 0;
  const last = i === STEPS.length - 1;
  const act = step.act || (step.adv === "click" ? "Click the highlighted item to continue." : "");
  return (
    <>
      {rect && <div aria-hidden className="no-print pointer-events-none fixed z-[60] rounded-xl ring-4 ring-teal-300 transition-all duration-200" style={{ left: ring!.left, top: ring!.top, width: ringW, height: ringH, boxShadow: "0 0 0 9999px rgba(11,27,58,.62)" }} />}
      {center && <div aria-hidden className="no-print pointer-events-none fixed inset-0 z-[60] bg-navy/60" />}
      <div ref={cardRef} role="dialog" aria-live="polite" aria-label={step.title} className="no-print fixed z-[65] rounded-2xl bg-surface p-5 shadow-2xl transition-[top,left] duration-200" style={{ width: vw < 640 ? undefined : cardW, ...pos }}>
        <div className="mb-1 flex items-center justify-between text-xs font-semibold text-brand"><span>{step.ch}: step {i + 1} of {STEPS.length}</span><button onClick={stop} aria-label="End the guided tour" className="rounded-md border border-slate-300 px-2 py-0.5 text-slate-700 hover:bg-slate-100 hover:text-ink">End tour</button></div>
        <div className="mb-2 h-1 w-full overflow-hidden rounded bg-slate-200" role="progressbar" aria-valuemin={1} aria-valuemax={STEPS.length} aria-valuenow={i + 1} aria-label="Tour progress"><div className="h-full bg-brand" style={{ width: `${((i + 1) / STEPS.length) * 100}%` }} /></div>
        <h2 className="font-display text-lg font-extrabold">{step.title}</h2>
        <p className="mt-1 text-sm text-slate-700">{missing && !rect ? (step.wait || "Looking for it on this page. If you cannot see it, open the Menu (top right), or check that you are signed in as the role named in the last step.") : step.body}</p>
        {act && (rect || (!step.sel && !step.text)) && <p className="mt-3 rounded-lg bg-brandbg px-3 py-2 text-sm font-semibold text-brand">Your turn: {act}</p>}
        {step.fill && <button onClick={fill} className={`${btn} mt-3 bg-brandbg text-brand hover:bg-teal-100`}>Paste sample text for me</button>}
        {step.files && <p className="mt-3 flex flex-wrap gap-2 text-sm font-semibold"><a className="rounded-lg bg-brandbg px-3 py-1.5 text-brand" href="/samples/Diwali_Flyer_HIDDEN_TEXT.pdf" download>Sample PDF (hidden text)</a><a className="rounded-lg bg-brandbg px-3 py-1.5 text-brand" href="/samples/Diwali_Poster_BAD_COLOURS.png" download>Sample image</a></p>}
        <div className="mt-4 flex items-center justify-between gap-2">
          <button disabled={i === 0} onClick={() => go(i - 1)} className={`${btn} text-slate-600 hover:bg-slate-100 disabled:opacity-30`}>Back</button>
          {last ? <button onClick={stop} className={`${btn} bg-brand text-white`}>Finish</button>
            : <button onClick={() => go(i + 1)} className={`${btn} ${!step.adv || step.adv === "next" ? "bg-navy text-white" : "bg-slate-100 text-slate-700"}`}>{!step.adv || step.adv === "next" ? "Next" : "Skip this step"}</button>}
        </div>
      </div>
      {fab}
    </>
  );
}