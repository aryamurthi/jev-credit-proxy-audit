"""Minimal client for OpenRouter's Decisions API, pinned to one model, with retries, a budget guard and an
append-only raw log. The API key is read from the environment or from a .env file and is never logged."""
import json
import os
import threading
import time
import urllib.error
import urllib.request

import config as C

RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529}  # 52x: Cloudflare edge errors (520 seen in the noise phase)


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    for path in (os.environ.get("JEV_AUDIT_ENV_FILE"), os.path.join(os.path.dirname(__file__), "..", ".env")):
        if path and os.path.exists(path):
            for line in open(path):
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY not found (environment, JEV_AUDIT_ENV_FILE, or .env)")


def build_request(state, instructions, order):
    criteria = {name: C.CHOICES[name] for name in C.ORDERS[order]}  # insertion order = option order sent
    return {
        "model": C.MODEL,
        "state": state,
        "questions": {C.QUESTION_KEY: {"type": "choice", "instructions": instructions, "criteria": criteria}},
        "provider": {"allow_fallbacks": False, "data_collection": "deny"},
    }


class Budget:
    def __init__(self, spent=0.0):
        self.spent = spent
        self.lock = threading.Lock()

    def add(self, cost):
        with self.lock:
            self.spent += cost or 0.0
            return self.spent

    def exhausted(self):
        with self.lock:
            return self.spent >= C.STOP_AT_USD


class RawLog:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(self, record):
        line = json.dumps(record, sort_keys=True) + "\n"
        with self.lock, open(self.path, "a") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def call(key, body, max_retries=6, timeout=60):
    """Returns (http_status, response_text, retry_count, elapsed_s). Never raises for HTTP errors."""
    data = json.dumps(body).encode()
    retries, delay = 0, 1.0
    while True:
        req = urllib.request.Request(C.ENDPOINT, data=data, method="POST",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode(), retries, round(time.time() - t0, 3)
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode(errors="replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            status, text = -1, f"{type(e).__name__}: {e}"
        if (status in RETRYABLE or status == -1) and retries < max_retries:
            time.sleep(delay)
            retries, delay = retries + 1, min(delay * 2, 60)
            continue
        return status, text, retries, round(time.time() - t0, 3)


def parse(text):
    """Extract the fields the analysis needs; returns None when the body is not a usable answer."""
    try:
        obj = json.loads(text)
        ans = obj["answers"][C.QUESTION_KEY]
        probs = ans["probabilities"]
        return {"model_returned": obj.get("model"), "request_id": obj.get("id"), "provider": obj.get("provider"),
                "choice": ans.get("choice"), "confidence": ans.get("confidence"),
                "p_APPROVE": probs.get("APPROVE"), "p_MANUAL_REVIEW": probs.get("MANUAL_REVIEW"),
                "p_DENY": probs.get("DENY"), "cost": (obj.get("usage") or {}).get("cost"),
                "input_tokens": (obj.get("usage") or {}).get("input_tokens"),
                "output_tokens": (obj.get("usage") or {}).get("output_tokens")}
    except (ValueError, KeyError, TypeError):
        return None
