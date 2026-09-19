import os, sys, json, time, hashlib
from pathlib import Path
from datetime import datetime
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
from agent.agents import call_gemini, validate_api, MODEL

load_dotenv()
ROOT=Path(__file__).parent

def inventory(page):
    return page.evaluate("""
    () => {
      const els=[]; let n=0;
      const nodes=[...document.querySelectorAll('button,a,input,select,textarea,[role],summary')];
      for(const e of nodes){
        const r=e.getBoundingClientRect(), s=getComputedStyle(e);
        if(r.width<2||r.height<2||s.display==='none'||s.visibility==='hidden') continue;
        const tag=e.tagName.toLowerCase();
        let role=e.getAttribute('role')||({button:'button',a:'link',input:'textbox',select:'combobox',textarea:'textbox',summary:'button'}[tag]||tag);
        if(tag==='input' && e.type==='checkbox') role='checkbox';
        if(tag==='input' && e.type==='radio') role='radio';
        let name=(e.getAttribute('aria-label')||e.getAttribute('name')||e.innerText||e.value||e.placeholder||e.title||'').replace(/\\s+/g,' ').trim().slice(0,120);
        if(!name && e.id){ const l=document.querySelector(`label[for="${CSS.escape(e.id)}"]`); if(l) name=l.innerText.trim().slice(0,120); }
        els.push({uix:++n,role,name,tag,input_type:e.type||null,disabled:!!e.disabled,checked:e.checked===undefined?null:!!e.checked,value:(e.type==='password')?null:(e.value||null),href:e.href||null,box:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]});
      }
      return els.slice(0,100);
    }
    """)

def mark(page, elements):
    page.evaluate("""(els)=>{document.querySelectorAll('[data-pragyaan-mark]').forEach(x=>x.remove()); for(const e of els){const all=[...document.querySelectorAll('button,a,input,select,textarea,[role],summary')]; const x=all[e.uix-1]; if(!x)continue; const b=x.getBoundingClientRect(); const d=document.createElement('div'); d.dataset.pragyaanMark='1'; d.textContent=e.uix; Object.assign(d.style,{position:'fixed',left:b.left+'px',top:b.top+'px',background:'#ff3b30',color:'#fff',font:'bold 12px sans-serif',padding:'2px 5px',zIndex:2147483647,borderRadius:'4px',pointerEvents:'none'}); document.body.appendChild(d);}}""", elements)

def resolve(page, uix, elements):
    if uix is None: return None
    e=next((x for x in elements if x['uix']==uix),None)
    if not e: raise RuntimeError(f"UIX {uix} is not in current observation")
    return e

def execute(page, action, elements):
    typ = action.get('action')
    uix = action.get('uix')
    value = action.get('value')
    key = action.get('key')

    if typ == 'finish':
        return True

    if typ == 'scroll':
        page.mouse.wheel(0, 700 if value == 'down' else -700)
        return False

    e = resolve(page, uix, elements)

    if e['disabled']:
        raise RuntimeError('Selected element is disabled')

    candidates = page.locator(
        'button,a,input,select,textarea,[role],summary'
    ).all()

    visible = []

    for candidate in candidates:
        try:
            if candidate.is_visible():
                visible.append(candidate)
        except:
            pass

    if uix > len(visible):
        raise RuntimeError(
            f"UIX {uix} is not in current visible elements"
        )

    loc = visible[uix - 1]

    if typ == 'click':
        loc.click(timeout=8000)
    elif typ == 'type':
        loc.fill(str(value or ''), timeout=8000)
    elif typ == 'select':
        loc.select_option(label=str(value), timeout=8000)
    elif typ == 'press':
        loc.press(str(key or 'Enter'), timeout=8000)
    else:
        raise RuntimeError(f'Unsupported action {typ}')

    return False
def main(goal,url):
    try: validate_api()
    except Exception as e:
        print(f"[Gemini] FAILED: {e}"); sys.exit(2)
    runid=datetime.now().strftime('%Y%m%d_%H%M%S'); out=ROOT/'runs'/runid; out.mkdir(parents=True,exist_ok=True)
    history=[]; trace=[]
    print(f"[Pragyaan] Gemini model: {MODEL}")
    print(f"[Pragyaan] Goal: {goal}")
    with sync_playwright() as p:
      browser=p.chromium.launch(headless=False)
      page=browser.new_page(viewport={'width':1280,'height':800})
      page.goto(url,wait_until='domcontentloaded',timeout=30000); page.wait_for_timeout(800)
      for step in range(1,26):
        elements=inventory(page); mark(page,elements); page.screenshot(path=str(out/f'{step:02d}_before.png'))
        print(f"\n[Step {step}] URL: {page.url}")
        print(f"Observed {len(elements)} visible elements")
        try: action=call_gemini(goal,elements,history)
        except Exception as e:
          print(f"[Agent] FAILED: {e}"); break
        print(f"[Agent] Reason: {action.get('reasoning','')}")
        print(f"[Agent] Action: {action}")
        history.append(action)
        if action.get('action')=='finish':
          page.screenshot(path=str(out/f'{step:02d}_after.png')); trace.append({'step':step,'url':page.url,'action':action,'outcome':'finish'}); print('\n[Pragyaan] GOAL FINISHED'); break
        try:
          execute(page,action,elements); page.wait_for_timeout(700)
          page.screenshot(path=str(out/f'{step:02d}_after.png'))
          trace.append({'step':step,'url':page.url,'action':action,'outcome':'ok'})
        except Exception as e:
          print(f"[Executor] {e}"); trace.append({'step':step,'url':page.url,'action':action,'outcome':f'error: {e}'})
          history.append({'action':'error','reasoning':str(e)})
          page.wait_for_timeout(500)
      (out/'trace.json').write_text(json.dumps(trace,indent=2,ensure_ascii=False),encoding='utf-8')
      report='# Pragyaan Audit Report\n\n'
      report+=f'**Goal:** {goal}\n\n**Start URL:** {url}\n\n**Model:** {MODEL}\n\n**Steps:** {len(trace)}\n\n'
      for t in trace: report+=f"## Step {t['step']}\n- Action: `{json.dumps(t['action'],ensure_ascii=False)}`\n- Outcome: {t['outcome']}\n- Screenshot: `{t['step']:02d}_after.png`\n\n"
      (out/'report.md').write_text(report,encoding='utf-8')
      browser.close()
    print(f"\nEvidence saved to: {out}")

if __name__=='__main__':
    if len(sys.argv)!=3: print('Usage: py main.py "goal" "url"'); sys.exit(1)
    main(sys.argv[1],sys.argv[2])
