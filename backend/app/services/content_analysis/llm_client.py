"""Local Ollama client (stdlib only). Never falls back to any external service."""
import json, re, urllib.request, urllib.error

class OllamaError(RuntimeError): pass

def check_ollama(url: str, model: str) -> dict:
    try:
        with urllib.request.urlopen(url + "/api/tags", timeout=5) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
    except Exception as e:
        raise OllamaError("Ollama is not reachable at %s. Install from https://ollama.com/download "
                          "and start it. (%s)" % (url, e))
    if not any(n == model or n.split(":")[0] == model for n in names):
        raise OllamaError(f"Model '{model}' not installed. Run: ollama pull {model}")
    return {"ok": True, "models": names}

def parse_json(text: str) -> dict:
    """Tolerate Qwen3 <think> blocks, code fences and stray prose around the JSON object."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try: return json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a: return json.loads(text[a:b + 1])
        raise OllamaError("Model did not return valid JSON: " + text[:200])

def chat_json(url, model, system, user, idle_timeout=180, on_token=None) -> dict:
    """Streams the reply: fails only if the model is silent for `idle_timeout` s, not after a fixed total time."""
    body = json.dumps({"model": model, "stream": True, "format": "json", "think": False, "keep_alive": "30m",
        "options": {"temperature": 0.2, "num_ctx": 6144, "num_predict": 1800},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(url + "/api/chat", body, {"Content-Type": "application/json"})
    parts = []
    try:
        with urllib.request.urlopen(req, timeout=idle_timeout) as r:
            for line in r:
                if not line.strip(): continue
                d = json.loads(line)
                if d.get("error"): raise OllamaError(d["error"])
                tok = (d.get("message") or {}).get("content", "")
                if tok:
                    parts.append(tok)
                    if on_token: on_token(len(parts))
                if d.get("done"): break
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise OllamaError(f"Ollama stopped responding for {idle_timeout}s or failed ({e}). Run `ollama ps` and check PROCESSOR says GPU.")
    return parse_json("".join(parts))
