import json, os, re, requests

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM = """You are the action planner for a black-box web testing agent.
You can ONLY choose from the currently observed elements. Never invent a selector.
Return ONLY valid JSON with this exact shape:
{"action":"click|type|select|press|scroll|finish","uix":number|null,"value":string|null,"key":string|null,"reasoning":string}
Rules:
- click: use a visible clickable element's uix.
- type: use a visible textbox/input's uix and put text in value.
- select: use a visible select/combobox uix and put an option value/text in value.
- press: use key such as Enter.
- scroll: value must be "down" or "up" and uix is null.
- finish only when the goal is visibly complete.
- Never type passwords unless the goal explicitly supplies them.
"""

def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I|re.S).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m: raise ValueError(f"Gemini did not return JSON: {text[:500]}")
    return json.loads(m.group(0))

def call_gemini(goal, elements, history):
    key = os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is not set")
    prompt = SYSTEM + "\nGOAL:\n" + goal + "\n\nCURRENT UI ELEMENTS:\n" + json.dumps(elements, ensure_ascii=False) + "\n\nRECENT HISTORY:\n" + json.dumps(history[-6:], ensure_ascii=False)
    r = requests.post(URL, headers={"x-goog-api-key": key, "Content-Type":"application/json"}, json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json"}}, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:1000]}")
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _extract_json(text)

def validate_api():
    key=os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is not set")
    r=requests.post(URL,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json={"contents":[{"parts":[{"text":"Reply with OK"}]}]},timeout=30)
    if r.status_code != 200: raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:800]}")
    return True
