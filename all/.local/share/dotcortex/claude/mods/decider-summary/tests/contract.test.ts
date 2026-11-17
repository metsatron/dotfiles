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
test("full source above 4096 rows remains covered",async()=>{
  const rows=Array.from({length:5000},(_,i)=>({role:"user",text:`row-${i}`,toolUses:[],toolResults:[],handle:`h${i}`}));
  expect(chunkRows(validateRows(rows)).flat().length).toBe(5000);
});
test("native pairs and Unicode survive normalization",async()=>{
  const rows=[{role:"assistant",text:"",toolUses:[{tool_use_id:"t",tool:"Read",input:{path:"über"}}]},
    {role:"user",text:"",toolUses:[],toolResults:[{tool_use_id:"t",text:"原文",isError:false}]}];
  expect(canonical(validateRows(rows))).toContain("原文");
});
