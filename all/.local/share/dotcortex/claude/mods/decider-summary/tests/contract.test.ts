import { expect, test } from "claude-code/testing";
import { register, canonical, validateRows, chunkRows } from "../hooks/register.js";
function engine() {
  const rows = [{role:"user",text:"Preserve Atlas saves; importer incomplete.",toolUses:[],handle:"h1"}];
  const handlers = {};
  register((name, fn) => { handlers[name] = fn; });
  const state = {calls:0, bad:false};
  const $ = {
    session:{ id:async()=>"fixture", messages:async()=>rows },
    http:{fetch:async(url, init)=>{
      state.calls++;
      const p=JSON.parse(init.body);
      return {status:200,text:JSON.stringify({...p,summary:"Atlas importer pending; preserve saves.",truncated:state.bad})};
    }},
  };
  const run=(event={})=>handlers["session.compact"]($,{trigger:"manual",instructions:"decider-local-only",messages:rows,...event},async e=>({messages:e.messages}));
  return { $,rows,state,handlers,run };
}
test("native HTTP text response creates a checkpoint without invoking provider chain",async()=>{
  const x=engine();const r=await x.run();
  expect(r.messages[0].text).toContain("Atlas");
  expect(r.messages[1].handle).toBe("h1");
  expect(x.state.calls).toBe(1);
});
test("async ticket polls one submitted job and consumes native HTTP text",async()=>{
  const x=engine();let submitted;let posts=0;let polls=0;
  const path="/v1/summary/jobs/0123456789abcdef0123456789abcdef";
  x.$.http.fetch=async(url,init)=>{
    if(init){posts++;submitted=JSON.parse(init.body);return {status:202,text:JSON.stringify({request_id:submitted.request_id,poll_path:path})};}
    polls++;
    if(polls===1)return {status:202,text:JSON.stringify({request_id:submitted.request_id,poll_path:path})};
    return {status:200,text:JSON.stringify({...submitted,summary:"Atlas remains pending.",truncated:false})};
  };
  expect((await x.run()).messages[0].text).toContain("Atlas remains pending.");
  expect(posts).toBe(1);expect(polls).toBe(2);
});
test("async ticket cannot redirect the plugin outside its local endpoint",async()=>{
  const x=engine();let calls=0;
  x.$.http.fetch=async(url,init)=>{calls++;const p=JSON.parse(init.body);return {status:202,text:JSON.stringify({request_id:p.request_id,poll_path:"https://outside.invalid/steal"})};};
  expect((await x.run()).skip).toContain("original context preserved");expect(calls).toBe(1);
});
test("older user instructions stay verbatim beside the model summary",async()=>{
  const x=engine();const goal="Preserve original files. Never count a queued request as completed.";
  x.rows[0].text=goal;
  for(let i=0;i<14;i++)x.rows.push({role:i%2?"assistant":"user",text:`later-${i}`,toolUses:[],toolResults:[],handle:`later${i}`});
  x.$.session.messages=async()=>[x.rows[x.rows.length-1]];
  expect((await x.run()).messages[0].text).toContain(goal);
});
test("load receipt requires the pinned running backend and async capability",async()=>{
  const x=engine();let receipt;
  x.$.env={get:async key=>key==="CLAUDE_WARM_DECIDER_READY"?"/tmp/fixture-ready":"fixture-channel"};
  x.$.fs={write:async(path,text)=>{receipt=JSON.parse(text);}};
  const health={model:"decider-2b-v11-Q4_K_M",model_sha256:"b7c132a67934d51c81abc96bb7724800f965ff5a288aed3e1ca7d8bc349c1386",summary:{protocol:"summary.v1",async:true}};
  x.$.http.fetch=async()=>({status:200,text:JSON.stringify(health)});
  await x.handlers["session.start"](x.$,{},async()=>({}));
  expect(receipt.protocol).toBe("decider-summary.v1");expect(receipt.session_id).toBe("fixture");
  health.summary=null;
  await x.handlers["session.start"](x.$,{},async()=>({}));
  expect(receipt.protocol).toBe("unavailable");
});
test("ordinary manual and auto compaction delegate unchanged",async()=>{
  for(const event of [{instructions:"ordinary"},{trigger:"auto"}]){
    const x=engine();const r=await x.run(event);
    expect(r.messages).toBe(x.rows);expect(x.state.calls).toBe(0);
  }
});
test("bad provider output skips and releases ownership for retry",async()=>{
  const x=engine();x.state.bad=true;
  expect((await x.run()).skip).toContain("original context preserved");
  x.state.bad=false;expect((await x.run()).messages[0].text).toContain("Atlas");
});
test("invalid input skips rather than falling through to a paid provider",async()=>{
  const x=engine();expect((await x.run({messages:[]})).skip).toContain("original context preserved");
  expect(x.state.calls).toBe(0);expect((await x.run()).messages[0].text).toContain("Atlas");
});
test("UTF-8 fragments fit the transport without dropping source codepoints",async()=>{
  const rows=validateRows([{role:"user",text:"🌋原文".repeat(1000),toolUses:[],toolResults:[],handle:"unicode"}]);
  const chunks=chunkRows(rows);
  expect(chunks.every(c=>new TextEncoder().encode(canonical(c)).length<=1200)).toBe(true);
  expect(chunks.flat().map(r=>r.text).join("")).toBe(canonical(rows[0]));
});
test("full source above 4096 rows remains covered",async()=>{
  const rows=Array.from({length:5000},(_,i)=>({role:"user",text:`row-${i}`,toolUses:[],toolResults:[],handle:`h${i}`}));
  expect(chunkRows(validateRows(rows)).flat().length).toBe(5000);
});
test("native pairs and Unicode survive normalization",async()=>{
  const rows=[{role:"assistant",text:"",toolUses:[{tool_use_id:"t",tool:"Read",input:{path:"über"}}]},
    {role:"user",text:"",toolUses:[],toolResults:[{tool_use_id:"t",text:"原文",isError:false}]}];
  expect(canonical(validateRows(rows))).toContain("原文");
});
