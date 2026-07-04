# -*- coding: utf-8 -*-
"""Shared Azure AI helpers. Reads credentials from ../../aiconfig.json (kept out of the repo)."""
import json
import os
import time
import urllib.request
import urllib.error

_HERE = os.path.dirname(os.path.abspath(__file__))
_CFG_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "aiconfig.json"))

with open(_CFG_PATH, encoding="utf-8") as f:
    _CFG = json.load(f)

AOAI_ENDPOINT = _CFG["aoai"]["endpoint"].rstrip("/")
API_KEY = _CFG["aoai"]["apiKeyEnv"]
CHAT_DEPLOYMENT = _CFG["aoai"]["chat"]["deployment"]
SPEECH_REGION = "eastus2"  # AI Services resource region (verified via issued token)


def _post(url, headers, body, timeout=300, retries=4):
    data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            payload = e.read()[:500]
            last_err = f"HTTP {e.code}: {payload}"
            if e.code in (429, 500, 502, 503, 504):
                wait = min(2 ** attempt * 3, 30)
                time.sleep(wait)
                continue
            raise RuntimeError(last_err)
        except Exception as e:  # timeouts, connection resets
            last_err = str(e)
            time.sleep(min(2 ** attempt * 3, 30))
    raise RuntimeError(f"request failed after {retries} tries: {last_err}")


def chat(messages, max_completion_tokens=16000, reasoning_effort="low", json_mode=False):
    """Call the chat deployment; returns assistant text content."""
    url = f"{AOAI_ENDPOINT}/openai/deployments/{CHAT_DEPLOYMENT}/chat/completions?api-version=2024-12-01-preview"
    body = {
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
        "reasoning_effort": reasoning_effort,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    raw = _post(url, {"api-key": API_KEY, "Content-Type": "application/json"}, body)
    out = json.loads(raw)
    choice = out["choices"][0]
    content = choice["message"]["content"]
    if not content:
        raise RuntimeError(f"empty content, finish_reason={choice.get('finish_reason')}")
    return content


def chat_json(messages, **kw):
    """chat() but parses a JSON object out of the reply."""
    text = chat(messages, json_mode=True, **kw)
    return json.loads(text)


def tts(text, out_path, voice="en-US-AvaMultilingualNeural", rate=None):
    """Synthesize speech to an MP3 file via Azure Speech REST API."""
    prosody_open = f"<prosody rate='{rate}'>" if rate else ""
    prosody_close = "</prosody>" if rate else ""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ssml = (
        "<speak version='1.0' xml:lang='en-US'>"
        f"<voice name='{voice}'>{prosody_open}{safe}{prosody_close}</voice></speak>"
    )
    url = f"https://{SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "en-learning",
    }
    audio = _post(url, headers, ssml.encode("utf-8"), timeout=60)
    if len(audio) < 400:
        raise RuntimeError(f"suspiciously small audio ({len(audio)} bytes) for: {text[:50]}")
    with open(out_path, "wb") as f:
        f.write(audio)
    return len(audio)


def gen_image(prompt, out_path, size="1024x1024", quality="medium"):
    """Generate an image with the gpt-image-2 deployment; saves PNG."""
    import base64
    url = f"{AOAI_ENDPOINT}/openai/deployments/gpt-image-2/images/generations?api-version=2025-04-01-preview"
    body = {"prompt": prompt, "size": size, "quality": quality, "n": 1, "output_format": "png"}
    raw = _post(url, {"api-key": API_KEY, "Content-Type": "application/json"}, body, timeout=300)
    out = json.loads(raw)
    b64 = out["data"][0]["b64_json"]
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
    return os.path.getsize(out_path)
