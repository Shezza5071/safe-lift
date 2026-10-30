"""Gemma 4 via the Gemini API: retry, 20 s timeout, and a labelled on-disk cache as the demo fallback.

Every call returns (text, source) where source is "live" or "cache", so the UI can say which it showed.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from google import genai
from google.genai import types

MODEL = "gemma-4-26b-a4b-it"
CACHE = Path(__file__).parent / "cache"
_client = None


def _key():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    for line in (Path.home() / ".config/gemini/credentials.env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("GEMINI_API_KEY not set")


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=_key(), http_options=types.HttpOptions(timeout=20_000))
    return _client


def strip_fences(text):
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


def gemma(prompt, image=None, tools=None, retries=3):
    """Returns (text, source) or, with tools, (function_calls, source). Raises only if no cache exists."""
    parts = [prompt]
    if image:
        parts.insert(0, types.Part.from_bytes(data=Path(image).read_bytes(), mime_type="image/png"))
    key = hashlib.sha256((prompt + (Path(image).name if image else "") + str(bool(tools))).encode()).hexdigest()[:16]
    cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                                      tools=tools)
    err = None
    for attempt in range(retries):
        try:
            r = client().models.generate_content(model=MODEL, contents=parts, config=cfg)
            out = [{"name": c.name, "args": dict(c.args)} for c in (r.function_calls or [])] if tools else r.text
            CACHE.mkdir(exist_ok=True)
            (CACHE / f"{key}.json").write_text(json.dumps(out, ensure_ascii=False))
            return out, "live"
        except Exception as e:  # transient 500s were seen in testing
            err = e
            time.sleep(1.5 * 2 ** attempt)
    hit = CACHE / f"{key}.json"
    if hit.exists():
        return json.loads(hit.read_text()), "cache"
    raise RuntimeError(f"Gemma failed after {retries} tries: {err}")


def gemma_json(prompt, image=None):
    text, src = gemma(prompt + "\nReply with JSON only.", image)
    return json.loads(strip_fences(text)), src


def alarm_question(snapshot, task, trunk, twist):
    """One specific question about the red-alarm posture, answered by tapping 1 to 4."""
    return gemma_json(f"""You coach a care-worker trainee on a practice lift (task: {task}).
The image is a skeleton (stick figure) of their posture when a red alarm fired.
Measured: trunk flexion {trunk:.0f} deg, trunk twist {twist:.0f} deg (indicative, +/- 10 deg).
Ask ONE short, specific question about what caused this posture, naming what you see
(e.g. "Your trunk is bent and twisted left; were you reaching across the bed?").
Give exactly 4 short answer options; the last is "Something else".
Never blame the worker; causes are usually the task, the setup or missing equipment.
JSON: {{"question": str, "options": [str, str, str, str]}}""", snapshot)


def debrief(summary, guidance, language="English"):
    """Session debrief: one concrete fix, citing retrieved official guidance."""
    cites = "\n".join(f"[{i + 1}] {g['source']}: {g['text'][:600]}" for i, g in enumerate(guidance)) or "(none)"
    return gemma(f"""You are a manual handling trainer giving a 4-sentence debrief after a practice lift.
Session data: {json.dumps(summary, ensure_ascii=False)}
Official guidance excerpts:
{cites}
Write in {language}. Say what went well, the main risk moment, and ONE concrete fix that points
to equipment, setup or following the handling plan (not "try harder"). Cite guidance as [1], [2].
No medical advice. End with: "Training aid only; follow the resident's handling plan."
""")
