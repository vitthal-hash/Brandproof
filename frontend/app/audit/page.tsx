"use client";
import { useEffect, useState } from "react";
import Shell, { useUser } from "@/components/Shell";
import { Chip } from "@/components/ui";
import { api } from "@/lib/api";

export default function Audit() {
  const { user } = useUser();
  const [rows, setRows] = useState<any[]>([]);
  const [v, setV] = useState<any>(null);
  const [err, setErr] = useState("");
  const load = () => api("/audit").then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { if (user) load(); }, [user]);
  const verify = () => api("/audit/verify").then(setV).catch((e) => setErr(e.message));
  return (
    <Shell>
      <h1 className="mb-5 text-3xl font-extrabold">Audit log</h1>
      <p className="mt-1 text-sm text-slate-800">Every action is chained to the previous one by a hash. Changing or deleting an entry breaks the chain.</p>
      <div className="mt-3 flex items-center gap-3"><button className="btn btn-primary" onClick={verify}>Verify chain</button>
        {v && (v.ok ? <Chip tone="green">Chain intact: {v.entries} entries</Chip> : <Chip tone="red">Broken at entry {v.first_bad_id}</Chip>)}</div>
      {err && <p role="alert" className="mt-2 font-semibold text-stamp">{err}</p>}
      <div className="card mt-3 overflow-x-auto p-0"><table className="w-full"><thead><tr><th className="th">#</th><th className="th">Time (UTC)</th><th className="th">Actor</th><th className="th">Action</th><th className="th">Entity</th><th className="th">Detail</th><th className="th">Hash</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td className="td">{r.id}</td><td className="td whitespace-nowrap">{r.ts.replace("T", " ")}</td><td className="td">{r.actor}</td><td className="td font-semibold">{r.action}</td>
          <td className="td">{r.entity} {r.entity_id}</td><td className="td font-mono text-xs">{JSON.stringify(r.detail)}</td><td className="td font-mono text-xs">{r.hash}</td></tr>)}</tbody></table></div>
    </Shell>
  );
}
