"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip, Empty, PageHeader } from "@/components/ui";
import { ROLE_LABEL } from "@/lib/api";
import { tourStartIndex } from "@/components/Tour";

type Faq = { q: string; a: string; cat: string };

const QUICK: Record<string, string[]> = {
  creator: [
    "Choose New submission, paste your text or upload a file, and write your intent in one line.",
    "Open the result. Each finding names the rule or approved fact behind it.",
    "For each suggested fix, choose Accept fix, Edit or Reject. Nothing changes until you click.",
    "When the findings are resolved, choose Submit for review.",
  ],
  external: [
    "Choose New submission and upload your file with a one-line intent.",
    "Read the findings. You only ever see your own assets.",
    "Accept or edit the suggested fixes, then submit for review.",
  ],
  manager: [
    "Open the Review queue on the Dashboard. Items marked Ready for you can be approved by you.",
    "Open an asset, read the findings, and comment on any line.",
    "Choose Approve, or Request changes with a short reason.",
    "High-risk items go to an authorised reviewer. You cannot approve those.",
  ],
  reviewer: [
    "Open an item marked Needs authorised reviewer in the Review queue.",
    "Check each high-severity claim in the Claim Ledger against its approved fact.",
    "Waive a claim only with a written reason. It is recorded in the audit log.",
    "Choose Approve. BrandProof then issues a signed receipt with the Proof Pack.",
  ],
  owner: [
    "Open Guidelines and facts to add or edit rules, dated facts and approved terms.",
    "Open Rulebook health and choose Run red-team on a rule to find loopholes.",
    "Review the tighter wording. Choose Approve tighter rule to re-test it.",
    "Answer fact requests from creators under Guidelines and facts.",
  ],
};

const WHERE: { href: string; title: string; text: string; roles?: string[] }[] = [
  { href: "/", title: "Dashboard", text: "Your assets by status, the review queue and repeated mistakes." },
  { href: "/new", title: "New submission", text: "Upload or paste content for a check before it is published.", roles: ["creator", "external", "manager", "reviewer"] },
  { href: "/governance", title: "Guidelines and facts", text: "Approved rules, dated facts, terms, colours and fact requests." },
  { href: "/rulebook", title: "Rulebook health", text: "Find loopholes and unclear rules, then approve tighter wording." },
  { href: "/stale", title: "Stale approvals", text: "Approved assets that no longer match the current facts.", roles: ["manager", "reviewer", "owner"] },
  { href: "/trust", title: "Trust Layer tests", text: "Attack files used to test hidden-text and injection defences." },
  { href: "/evaluation", title: "Evaluation", text: "Precision and recall, including the misses." },
  { href: "/disclosure", title: "AI disclosure", text: "Which services see which data, and every call made." },
  { href: "/audit", title: "Audit log", text: "A tamper-evident history of every action.", roles: ["manager", "reviewer", "owner"] },
  { href: "/verify", title: "Verify a receipt", text: "Check a Proof Pack receipt code. No sign-in needed." },
];

const FAQS: Faq[] = [
  { cat: "Getting started", q: "What does BrandProof do?", a: "It checks text, images and PDFs against your approved guidelines and facts before you publish. It explains each problem, cites the rule or fact behind it, and suggests a fix that keeps your message. It never publishes or approves anything on its own." },
  { cat: "Getting started", q: "How do I check my first piece of content?", a: "Choose New submission in the menu. Give it a title, write your intent in one line (for example, announce our new savings account), say where it will be published, then paste the text or upload a file. The results open when the check finishes." },
  { cat: "Getting started", q: "Which files can I upload, and how big can they be?", a: "Text (.txt, .md), PDF, PNG and JPG. A file can be up to 10 MB and pasted text up to 100,000 characters. The form checks the type and size before uploading, and the server checks the file contents too, so a renamed file is refused." },
  { cat: "Rules and facts", q: "How do I update many facts at once?", a: "Guideline owners open Guidelines and facts, then Fact Vault, and use Import facts from a file. Upload a CSV or JSON file, check the preview, then apply it. Existing facts are updated by ID, and facts missing from the file are never deleted. Approved assets are re-checked afterwards." },
  { cat: "Rules and facts", q: "Can facts update automatically?", a: "Yes, if your administrator connects a feed (a CSV or JSON address) on the server. BrandProof pulls it on a schedule and re-checks approved assets every day. A feed can supply facts, never the matching rules, and it is paused in confidential mode. The Automatic checks card on the Stale approvals page shows the last and next run." },
  { cat: "Getting started", q: "Can I check text without leaving the page I am writing on?", a: "Yes, with the BrandProof browser extension. Select text on a page, click the icon, write what it is for, and press Check. It shows findings and verified suggestions, and it never approves anything. It does not work inside Google Docs or Figma, so paste text into the popup there." },
  { cat: "Reading results", q: "Does BrandProof check logos and colours in pictures?", a: "Partly. It finds the uploaded approved logo in a picture and flags a stretched or very small logo and busy content inside its clear space. It also flags large colour areas that are not in the approved palette. It only recognises flat, unrotated, same-colour logos, and photos can confuse the colour estimate, so the Proof Pack lists these limits." },
  { cat: "Getting started", q: "What is the guided tour and how do I restart it?", a: "The tour is a step-by-step walkthrough that points at the exact button to use. Use the Start the guided tour button on this page, or the Guided tour button at the bottom right of any page." },

  { cat: "Reading results", q: "What do the verdicts mean?", a: "Supported: an approved, in-date fact backs the claim. Contradicted: an approved fact says the opposite. Outdated: the fact or offer has expired. Unsupported: no approved fact covers the claim. Needs human: BrandProof was not sure and sent it to a person." },
  { cat: "Reading results", q: "What do the badges Rule, Claims, AI and Heuristic mean?", a: "They show how a finding was produced. Rule and Claims are exact code checks. AI is a model judgment that must cite a rule. Heuristic is a basic offline check used when no AI service is connected." },
  { cat: "Reading results", q: "What is a Proof Pack?", a: "A receipt for an asset. It lists what was checked, what was not checked, who approved, and which AI saw what. Open it from the asset page. Approved assets also get a signed receipt code and a PDF export." },
  { cat: "Reading results", q: "Why does a finding say Needs human?", a: "BrandProof is built to say so when it is unsure instead of guessing. A manager or reviewer makes the call, and the finding keeps its cited rule so they can see why it was raised." },
  { cat: "Reading results", q: "What does Intent Lock passed mean?", a: "The suggested fix still says what you meant. BrandProof keeps a short list of must-keep elements from your intent (the subject, the audience, the call to action). A fix that removes one of them is withheld and the lost element is named." },

  { cat: "Fixing and approving", q: "Will BrandProof change my content on its own?", a: "No. A suggested fix is shown as before and after. Only your click on Accept fix creates a new version, and that version is checked again." },
  { cat: "Fixing and approving", q: "Why was a suggested fix withheld?", a: "Every fix is re-checked before you see it. If it would break another rule or drop something you wanted to say, it is held back so you are not shown a worse option. You can still edit the copy yourself." },
  { cat: "Fixing and approving", q: "What do the statuses mean?", a: "Draft: not checked yet. Auto-reviewed: checked, with findings to handle. Changes requested: a reviewer asked for edits. In review: waiting for approval. Approved: a human signed it off." },
  { cat: "Fixing and approving", q: "Who can approve my content?", a: "A brand manager can approve normal items. High-risk items, such as a claim contradicted by an approved fact, must be approved by an authorised reviewer. The Dashboard queue shows which one an item needs." },
  { cat: "Fixing and approving", q: "A claim has no matching fact. What now?", a: "Use Request a fact from the owner on that claim. The guideline owner can approve it as a new dated fact, after which a re-run marks the claim Supported, or decline it with a reason. Until then, rewrite or remove the claim." },
  { cat: "Fixing and approving", q: "Can I undo an accepted fix?", a: "Yes. Every accept creates a new version. Open History on the asset to compare versions and use Show changes to see what moved." },

  { cat: "Rules and facts", q: "How do I add or change a rule?", a: "Guideline owners go to Guidelines and facts, then Import guidelines to turn a document into draft rules, or edit a rule directly. Every edit creates a new version. A rule applies only after the owner approves it." },
  { cat: "Rules and facts", q: "What is the Rulebook health page?", a: "It shows which rules reviewers keep overriding, which are unclear, and which can be dodged. Run red-team on a rule to see sneaky wordings that slip past it, and approve the tighter wording to re-test it." },
  { cat: "Rules and facts", q: "What are stale approvals?", a: "When a fact changes or expires, BrandProof re-checks assets that were already approved. If a claim is now wrong, the asset appears under Stale approvals. The asset stays approved until a person decides what to do." },

  { cat: "Privacy and trust", q: "Does my content go to an AI service?", a: "Only if an AI service is connected, and personal data such as emails, phone numbers, Aadhaar, PAN and card numbers is replaced by tokens first. The AI disclosure page lists every service, what data it gets and every call made." },
  { cat: "Privacy and trust", q: "Can I stop all external AI calls?", a: "Yes. A guideline owner can switch on Confidential mode on the AI disclosure page. It blocks every external call, and the checks that need no AI keep working. Some tone checks are weaker in this mode." },
  { cat: "Privacy and trust", q: "What is the Trust Layer?", a: "It looks for hidden text, invisible characters, look-alike letters and instructions aimed at AI reviewers inside a file. The raw and the cleaned versions are both reviewed, and if the verdicts differ the asset gets a manipulation flag." },
  { cat: "Privacy and trust", q: "How can someone verify a receipt?", a: "Open Verify a receipt, which needs no sign-in, and enter the receipt code from the Proof Pack. It checks the signature and the audit log, and shows whether the asset has changed since approval." },
  { cat: "Privacy and trust", q: "What does BrandProof not check?", a: "Every Proof Pack lists this per asset. In general: audio and video, logo and layout correctness, languages other than English and Hinglish, and some text inside small or low-contrast images." },

  { cat: "Problems", q: "My upload was refused. Why?", a: "The file is probably over 10 MB, a type that is not allowed, or its contents do not match its extension. Try exporting again as PDF, PNG, JPG or plain text." },
  { cat: "Problems", q: "I was signed out or see a 429 message.", a: "Signing in again fixes the first. A 429 means too many requests in a short time, so wait a minute and retry." },
  { cat: "Problems", q: "I cannot see the page or button I expected.", a: "Pages depend on your role. For example, only managers, reviewers and owners see Stale approvals and the Audit log, and external contributors see only their own assets. Check your role in the bottom left of the menu." },
  { cat: "Problems", q: "A finding looks wrong. What should I do?", a: "Comment on that finding or reject the fix, and tell your manager. Overrides are counted in Rulebook health, so repeated disagreements help the guideline owner fix unclear rules." },
];

const GLOSSARY: [string, string][] = [
  ["Fact Vault", "The dated, sourced facts claims are checked against."],
  ["Claim Ledger", "Every promotional claim in an asset with its verdict and evidence."],
  ["Intent Lock", "A check that a fix still says what the creator meant."],
  ["Proof Pack", "A receipt of what was checked, what was not, and who approved."],
  ["Red-team", "An adversary that tries to get around a rule, to find loopholes."],
  ["Manipulation flag", "Raised when the raw and cleaned versions of a file get different verdicts."],
];

function Item({ f, open, onToggle, id }: { f: Faq; open: boolean; onToggle: () => void; id: string }) {
  return (
    <div className="border-b border-slate-100 last:border-b-0">
      <h3>
        <button onClick={onToggle} aria-expanded={open} aria-controls={id} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-[15px] font-semibold hover:text-brand">
          {f.q}
          <svg aria-hidden viewBox="0 0 24 24" className={`h-4 w-4 shrink-0 text-slate-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
        </button>
      </h3>
      <div id={id} role="region" data-open={open} className="reveal"><div><p className="max-w-3xl px-5 pb-5 text-sm leading-relaxed text-slate-700">{f.a}</p></div></div>
    </div>
  );
}

export default function Help() {
  const { user } = useUser();
  const [query, setQuery] = useState("");
  const [openQ, setOpenQ] = useState<string | null>(FAQS[0].q);
  const role = user?.role || "creator";
  const cats = useMemo(() => Array.from(new Set(FAQS.map((f) => f.cat))), []);
  const q = query.trim().toLowerCase();
  const shown = FAQS.filter((f) => !q || (f.q + " " + f.a).toLowerCase().includes(q));
  const places = WHERE.filter((w) => !w.roles || w.roles.includes(role));
  const tour = () => { try { sessionStorage.setItem("bp_tour", JSON.stringify({ i: user ? tourStartIndex(user.role) : 0, on: true })); } catch {} window.location.href = user ? "/" : "/login"; };  // already signed in: skip the sign-in steps

  return (
    <Shell>
      <PageHeader title="Help and FAQ" subtitle="Learn how BrandProof works, find where things are, and get answers without asking anyone.">
        <button onClick={tour} className="btn btn-brand">Start the guided tour</button>
      </PageHeader>

      <div className="card mb-8 flex flex-wrap items-center justify-between gap-4 p-5">
        <div className="max-w-2xl"><h2 className="font-display text-base font-bold">Browser extension: check text while you write</h2>
          <p className="mt-1 text-sm text-slate-700">Select text on any web page and check it against your guidelines without leaving the page. It never approves or publishes anything. Install: unzip, open chrome://extensions, switch on Developer mode, choose Load unpacked and pick the unzipped folder. Then enter <b>{typeof window !== "undefined" ? window.location.origin : "this site's address"}</b> as the server.</p></div>
        <a href="/downloads/BrandProof_browser_extension.zip" download className="btn btn-brand">Download the extension</a>
      </div>

      <div className="relative mb-8">
        <label htmlFor="help-search" className="sr-only">Search help</label>
        <svg aria-hidden viewBox="0 0 24 24" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
        <input id="help-search" type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search help, for example approve, hidden text, receipt" className="input py-3.5 pl-12 text-base shadow-soft" />
      </div>

      {!q && (
        <>
          <section aria-labelledby="qs" className="mb-10">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <h2 id="qs" className="text-xl font-bold">Quick start</h2>
              <Chip tone="blue">{ROLE_LABEL[role] || "Your role"}</Chip>
            </div>
            <ol className="stagger grid gap-3 md:grid-cols-2">
              {(QUICK[role] || QUICK.creator).map((s, i) => (
                <li key={i} className="card flex gap-4">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brandbg font-display text-sm font-extrabold text-brand">{i + 1}</span>
                  <p className="text-sm leading-relaxed text-slate-800">{s}</p>
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="where" className="mb-10">
            <h2 id="where" className="mb-3 text-xl font-bold">Where is what</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {places.map((w) => (
                <Link key={w.href} href={w.href} className="card card-link block">
                  <p className="font-semibold">{w.title}</p>
                  <p className="mt-1 text-sm text-slate-600">{w.text}</p>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}

      <section aria-labelledby="faq" className="mb-10">
        <h2 id="faq" className="mb-3 text-xl font-bold">{q ? `Results for “${query.trim()}”` : "Frequently asked questions"}</h2>
        {shown.length === 0 ? (
          <Empty action={<button onClick={() => setQuery("")} className="btn btn-ghost">Clear search</button>}>No answers match that search. Try a shorter word, or ask your brand manager.</Empty>
        ) : (
          cats.map((c) => {
            const list = shown.filter((f) => f.cat === c);
            if (!list.length) return null;
            return (
              <div key={c} className="mb-5">
                <h3 className="mb-2 text-sm font-semibold text-slate-600">{c}</h3>
                <div className="card p-0">
                  {list.map((f, i) => <Item key={f.q} f={f} id={`faq-${c.replace(/\W/g, "")}-${i}`} open={!!q || openQ === f.q} onToggle={() => setOpenQ(openQ === f.q ? null : f.q)} />)}
                </div>
              </div>
            );
          })
        )}
      </section>

      {!q && (
        <section aria-labelledby="gl" className="mb-10">
          <h2 id="gl" className="mb-3 text-xl font-bold">Key terms</h2>
          <dl className="card grid gap-x-8 gap-y-4 sm:grid-cols-2">
            {GLOSSARY.map(([t, d]) => (<div key={t}><dt className="text-sm font-semibold">{t}</dt><dd className="text-sm text-slate-600">{d}</dd></div>))}
          </dl>
        </section>
      )}

      <section className="card flex flex-wrap items-center justify-between gap-3 bg-brandbg/60">
        <p className="max-w-xl text-sm text-slate-800"><b>Still stuck?</b> Ask your brand manager or guideline owner. Comments on a finding go straight to the people who can change the rule.</p>
        <Link href="/" className="btn btn-ghost">Back to dashboard</Link>
      </section>
    </Shell>
  );
}