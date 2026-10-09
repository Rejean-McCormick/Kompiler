import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Capabilities = { snapshot_id: string; targets: Array<{target_id:string;adapter:{id:string;version:string};source:{state_id?:string};operations:Array<{operation_id:string;description:string}>}> };
type Pack = { context_pack_id:string; status:string; summary:Record<string,unknown>; records:unknown[]; conflicts:unknown[]; gaps:unknown[] };
const API = localStorage.getItem("kompiler.api") || "http://127.0.0.1:7788";

async function api(path:string, init?:RequestInit) {
  const token=localStorage.getItem("kompiler.token");
  const headers=new Headers(init?.headers); headers.set("Content-Type","application/json"); if(token) headers.set("Authorization",`Bearer ${token}`);
  const r=await fetch(`${API}${path}`,{...init,headers}); const body=await r.json(); if(!r.ok) throw new Error(JSON.stringify(body,null,2)); return body;
}

function App(){
 const [caps,setCaps]=useState<Capabilities|null>(null); const [query,setQuery]=useState<string>(`{\n  "protocol":"kompiler.query",\n  "version":"1.0",\n  "request_id":"session-001",\n  "operations":[]\n}`); const [pack,setPack]=useState<Pack|null>(null); const [error,setError]=useState(""); const [running,setRunning]=useState(false); const [tab,setTab]=useState<"query"|"pack">("query");
 useEffect(()=>{api("/v1/capabilities").then(setCaps).catch(e=>setError(String(e)))},[]);
 const operationCount=useMemo(()=>{try{return JSON.parse(query).operations?.length??0}catch{return 0}},[query]);
 async function run(){setError("");setRunning(true);try{const q=JSON.parse(query); if(caps&&!q.capability_snapshot_id) q.capability_snapshot_id=caps.snapshot_id; const out=await api("/v1/runs",{method:"POST",body:JSON.stringify(q)}); setPack(out);setTab("pack")}catch(e){setError(String(e))}finally{setRunning(false)}}
 async function copy(value:unknown){await navigator.clipboard.writeText(typeof value==="string"?value:JSON.stringify(value,null,2))}
 function loadFile(file:File){const r=new FileReader();r.onload=()=>setQuery(String(r.result));r.readAsText(file)}
 return <main>
   <header><div><h1>Kompiler</h1><p>Local Context Compiler</p></div><div className="status">{caps?`${caps.targets.length} targets · ${caps.snapshot_id.slice(0,22)}…`:"runtime offline"}</div></header>
   <nav><button className={tab==="query"?"active":""} onClick={()=>setTab("query")}>Query Inbox</button><button className={tab==="pack"?"active":""} onClick={()=>setTab("pack")}>Context Pack</button></nav>
   {error&&<pre className="error">{error}</pre>}
   {tab==="query"&&<section className="grid">
     <aside><h2>Capabilities</h2>{caps?.targets.map(t=><details key={t.target_id}><summary>{t.target_id}</summary><small>{t.adapter.id}@{t.adapter.version}</small>{t.operations.map(o=><div className="op" key={o.operation_id}><b>{o.operation_id}</b><span>{o.description}</span></div>)}</details>)}<button onClick={()=>copy(caps)}>Copy capabilities</button></aside>
     <article><div className="bar"><b>Query Plan</b><span>{operationCount} operations</span><label className="file">Open JSON<input type="file" accept=".json,application/json" onChange={e=>e.target.files?.[0]&&loadFile(e.target.files[0])}/></label></div><textarea value={query} onChange={e=>setQuery(e.target.value)} spellCheck={false}/><div className="actions"><button onClick={()=>copy(query)}>Copy</button><button className="primary" disabled={running} onClick={run}>{running?"Running…":"Run locally"}</button></div></article>
   </section>}
   {tab==="pack"&&<section>{pack?<><div className="packHead"><div><h2>{pack.context_pack_id}</h2><p>Status: {pack.status}</p></div><button onClick={()=>copy(pack)}>Copy full pack</button></div><div className="cards">{Object.entries(pack.summary||{}).map(([k,v])=><div className="card" key={k}><span>{k}</span><strong>{typeof v==="object"?JSON.stringify(v):String(v)}</strong></div>)}</div><details open><summary>Records ({pack.records?.length||0})</summary><pre>{JSON.stringify(pack.records,null,2)}</pre></details><details><summary>Conflicts ({pack.conflicts?.length||0})</summary><pre>{JSON.stringify(pack.conflicts,null,2)}</pre></details><details><summary>Gaps ({pack.gaps?.length||0})</summary><pre>{JSON.stringify(pack.gaps,null,2)}</pre></details></>:<div className="empty">Run a query to compile a Context Pack.</div>}</section>}
 </main>
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
