"""Offline, self-contained tutoring-session HTML renderer (presentation layer).

No external requests: data is embedded as JSON, styling is inline, and a small
vanilla-JS block handles answer reveal + scoring. Swapping the renderer (e.g. a
React app) touches only this file.
"""
from __future__ import annotations

import html
import json
from typing import Any


def _esc(s: Any) -> str:
    return html.escape(str(s))


def render_session_html(session: dict[str, Any]) -> str:
    data = json.dumps(session, ensure_ascii=False).replace("</", "<\\/")
    title = _esc(session.get("title", "Tutoring Session"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --fg:#1a1a2e; --muted:#566; --accent:#3a5bd9; --bg:#f7f8fc;
           --card:#fff; --line:#e3e6f0; --good:#1c8a4a; --bad:#c0392b; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;
          color:var(--fg); background:var(--bg); }}
  main {{ max-width:820px; margin:0 auto; padding:32px 20px 80px; }}
  h1 {{ font-size:28px; margin:0 0 4px; }}
  h2 {{ font-size:20px; margin:32px 0 10px; border-bottom:2px solid var(--line);
        padding-bottom:6px; }}
  h3 {{ font-size:17px; margin:18px 0 6px; }}
  .sub {{ color:var(--muted); margin:0 0 8px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
           padding:16px 18px; margin:12px 0; }}
  .obj li {{ margin:4px 0; }}
  .term {{ font-weight:600; color:var(--accent); }}
  pre {{ background:#0f1226; color:#e7e9ff; padding:12px 14px; border-radius:8px;
         overflow-x:auto; font-size:14px; }}
  .eq {{ font-family:ui-monospace,Consolas,monospace; }}
  .ref {{ font-size:12px; color:var(--muted); margin-top:6px; }}
  .gap {{ background:#fff4e5; border-left:4px solid #e08a00; padding:8px 12px;
          border-radius:4px; margin:8px 0; }}
  button {{ font:inherit; cursor:pointer; border:1px solid var(--line);
            background:#eef1fb; border-radius:6px; padding:6px 12px; }}
  .ans {{ display:none; margin-top:10px; padding:10px 12px; border-radius:6px;
          background:#eef7f0; border:1px solid #cfe8d6; }}
  .ans.show {{ display:block; }}
  .choices label {{ display:block; padding:6px 8px; border:1px solid var(--line);
                    border-radius:6px; margin:4px 0; cursor:pointer; }}
  .score {{ position:sticky; bottom:0; background:var(--card); border-top:1px solid var(--line);
            padding:12px; text-align:center; font-weight:600; }}
  .whitespace {{ white-space:pre-wrap; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="sub" id="meta"></p>
  <section id="objectives"></section>
  <section id="sections"></section>
  <section id="equations"></section>
  <section id="worked"></section>
  <section id="checks"></section>
  <section id="practice"></section>
  <section id="gaps"></section>
</main>
<div class="score" id="scorebar">Assessment score: <span id="score">0</span> / <span id="total">0</span></div>
<script id="data" type="application/json">{data}</script>
<script>
const S = JSON.parse(document.getElementById('data').textContent);
const el = (t,c,h)=>{{const e=document.createElement(t); if(c)e.className=c; if(h!=null)e.innerHTML=h; return e;}};
const esc = s => String(s).replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]));
const refLine = r => (r&&r.length)? `<div class="ref">Source: ${{r.map(esc).join(', ')}}</div>`:'';

// metadata
const m = S.metadata||{{}};
document.getElementById('meta').textContent =
  [m.chapter, m.source_ref].filter(Boolean).join('  -  ');

// objectives
if((S.objectives||[]).length){{
  const sec=document.getElementById('objectives');
  sec.appendChild(el('h2',null,'Learning Objectives'));
  const ul=el('ul','obj'); S.objectives.forEach(o=>ul.appendChild(el('li',null,esc(o))));
  sec.appendChild(ul);
}}
// lesson sections
if((S.sections||[]).length){{
  const sec=document.getElementById('sections');
  sec.appendChild(el('h2',null,'Lesson'));
  S.sections.forEach(s=>{{
    const c=el('div','card');
    c.appendChild(el('h3',null,esc(s.title)));
    c.appendChild(el('div','whitespace',esc(s.content)));
    c.appendChild(el('div',null,refLine(s.sourceRefs)));
    sec.appendChild(c);
  }});
}}
// equations
if((S.equations||[]).length){{
  const sec=document.getElementById('equations');
  sec.appendChild(el('h2',null,'Key Equations'));
  S.equations.forEach(e=>{{
    const c=el('div','card');
    c.appendChild(el('pre','eq',esc(e.expression)));
    c.appendChild(el('div',null,esc(e.meaning)));
    c.appendChild(el('div',null,refLine(e.sourceRefs)));
    sec.appendChild(c);
  }});
}}
// worked examples
if((S.workedExamples||[]).length){{
  const sec=document.getElementById('worked');
  sec.appendChild(el('h2',null,'Worked Examples'));
  S.workedExamples.forEach(w=>{{
    const c=el('div','card');
    c.appendChild(el('div',null,'<strong>'+esc(w.question)+'</strong>'));
    if((w.steps||[]).length){{const ol=el('ol'); w.steps.forEach(st=>ol.appendChild(el('li',null,esc(st)))); c.appendChild(ol);}}
    c.appendChild(el('div',null,'<strong>Answer:</strong> '+esc(w.answer)));
    c.appendChild(el('div',null,refLine(w.sourceRefs)));
    sec.appendChild(c);
  }});
}}
// assessment (checks + practice) with reveal + scoring
let total=0, score=0;
function renderQuestions(list, mount, heading){{
  if(!(list||[]).length) return;
  const sec=document.getElementById(mount);
  sec.appendChild(el('h2',null,heading));
  list.forEach((q,i)=>{{
    total++;
    const c=el('div','card');
    c.appendChild(el('div',null,'<strong>Q'+(i+1)+'.</strong> '+esc(q.question)));
    if((q.choices||[]).length){{
      const box=el('div','choices');
      q.choices.forEach(ch=>{{
        const lab=el('label'); lab.innerHTML='<input type="radio" name="'+mount+i+'"> '+esc(ch);
        box.appendChild(lab);
      }});
      c.appendChild(box);
    }}
    const ans=el('div','ans');
    ans.innerHTML='<div><strong>Answer:</strong> '+esc(q.answer)+'</div>'+
                  '<div>'+esc(q.explanation)+'</div>'+refLine(q.sourceRefs);
    const btn=el('button',null,'Reveal answer');
    let counted=false;
    btn.onclick=()=>{{ans.classList.add('show'); if(!counted){{counted=true; score++; document.getElementById('score').textContent=score;}}}};
    c.appendChild(btn); c.appendChild(ans);
    sec.appendChild(c);
  }});
}}
renderQuestions(S.checks,'checks','Concept Checks');
renderQuestions(S.practiceQuestions,'practice','Practice Questions');
document.getElementById('total').textContent=total;
// source gaps
if((S.sourceGaps||[]).length){{
  const sec=document.getElementById('gaps');
  sec.appendChild(el('h2',null,'Source Gaps'));
  S.sourceGaps.forEach(g=>sec.appendChild(el('div','gap',esc(g))));
}}
</script>
</body>
</html>
"""
