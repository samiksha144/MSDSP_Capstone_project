
"""
backend.py — extracted backend from the notebook, with safe fallbacks.

This module exposes a single high-level class `Services` that the Streamlit app can use.
It attempts to use the same ideas/functions that exist in the notebook (PDF/DOCX extract,
transformers/T5/BART summarization, optional OpenAI SOP generation) but degrades gracefully
when packages or API keys are missing.

Usage:
    from backend import Services
    svc = Services()
    summary = svc.summarize(text_or_bytes, filename="my.pdf")
    sop = svc.generate_sop("Create SOP for cleaning bioreactor vessels...")
"""



from __future__ import annotations
import os
import io
import re
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple, Union

# --- Hardcode your OpenAI API key here ---
OPENAI_API_KEY = "sk-proj"  
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------
log = logging.getLogger("regdocgpt.backend")
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    log.addHandler(h)
log.setLevel(logging.INFO)

# --------------------------------------------------------------------------------------
# Optional imports (safe fallbacks)
# --------------------------------------------------------------------------------------
def _try_import(name):
    try:
        module = __import__(name, fromlist=["*"])
        return module
    except Exception:
        return None

fitz = _try_import("fitz")            # PyMuPDF
docx2txt = _try_import("docx2txt")
textstat = _try_import("textstat")
spacy = _try_import("spacy")
transformers = _try_import("transformers")
torch = _try_import("torch")
openai = _try_import("openai")

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------
def _is_probably_text_bytes(b: bytes) -> bool:
    if not b:
        return False
    try:
        b.decode("utf-8")
        return True
    except Exception:
        return False

def _decode_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def extract_text_from_pdf_bytes(b: bytes) -> str:
    """Extract text from a PDF byte string using PyMuPDF if available; otherwise return empty string."""
    if fitz is None:
        log.warning("PyMuPDF not installed; returning empty text for PDF.")
        return ""
    try:
        doc = fitz.open(stream=b, filetype="pdf")
        parts = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts)
    except Exception as e:
        log.error(f"PDF extract failed: {e}")
        return ""

def extract_text_from_docx_bytes(b: bytes) -> str:
    """Extract text from DOCX bytes using docx2txt if available; otherwise naive decode."""
    if docx2txt is None:
        return _decode_text(b)
    try:
        # docx2txt expects a file path; write to a temp buffer on disk
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "tmp.docx"
            p.write_bytes(b)
            return docx2txt.process(str(p)) or ""
    except Exception as e:
        log.error(f"DOCX extract failed: {e}")
        return _decode_text(b)

def extract_text_from_upload(data: bytes, filename: Optional[str]) -> str:
    """Robust extractor based on extension; falls back to utf-8 decode."""
    ext = (os.path.splitext(filename or "")[1] or "").lower()
    if ext == ".pdf":
        return extract_text_from_pdf_bytes(data)
    if ext in (".docx", ".doc"):
        return extract_text_from_docx_bytes(data)
    # default: treat as text
    if _is_probably_text_bytes(data):
        return _decode_text(data)
    return ""

# --------------------------------------------------------------------------------------
# Notebook-inspired metrics (safe)
# --------------------------------------------------------------------------------------
def _clarity_metrics(text: str) -> Dict[str, Any]:
    # Lightweight metrics; if spaCy available, compute passive voice approximations.
    metrics = {
        "avg_sentence_length": 0.0,
        "long_sentence_count": 0,
        "passive_voice_count": 0,
    }
    if not text:
        return metrics
    sentences = re.split(r"[.!?]\s+", text.strip())
    words_per_sentence = [len(s.split()) for s in sentences if s]
    if words_per_sentence:
        metrics["avg_sentence_length"] = sum(words_per_sentence) / len(words_per_sentence)
        metrics["long_sentence_count"] = sum(1 for n in words_per_sentence if n > 20)

    if spacy is not None:
        try:
            nlp = spacy.load("en_core_web_sm")
            nlp.max_length = max(2_000_000, len(text) + 10)
            doc = nlp(text)
            metrics["passive_voice_count"] = sum(1 for t in doc if t.dep_ == "auxpass")
        except Exception:
            pass
    return metrics

def _readability(text: str) -> Dict[str, Any]:
    if not text or textstat is None:
        return {"flesch_reading_ease": None, "gunning_fog_index": None}
    try:
        return {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "gunning_fog_index": textstat.gunning_fog(text),
        }
    except Exception:
        return {"flesch_reading_ease": None, "gunning_fog_index": None}

# --------------------------------------------------------------------------------------
# Summarization backends
# --------------------------------------------------------------------------------------
def _hf_summarize(text: str) -> Optional[str]:
    """Use HuggingFace T5/BART if available; return None if unavailable or fails."""
    if not text or transformers is None:
        return None
    try:
        # Prefer small, commonly available models
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        model_name = os.environ.get("SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6")
        tok = AutoTokenizer.from_pretrained(model_name)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        inputs = tok([text], max_length=1024, truncation=True, return_tensors="pt")
        outputs = mdl.generate(
            **inputs,
            max_length=300,
            min_length=80,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True,
        )
        return tok.batch_decode(outputs, skip_special_tokens=True)[0].strip()
    except Exception as e:
        log.warning(f"HF summarize failed: {e}")
        return None

def _openai_summarize(text: str) -> Optional[str]:
    if not text or openai is None or not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        client = openai.OpenAI() if hasattr(openai, "OpenAI") else openai
        # Compatible w/ both old and new SDKs
        if hasattr(client, "chat"):
            resp = client.chat.completions.create(
                model=os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a pharma regulatory compliance assistant."},
                    {"role": "user", "content": "Summarize the following SOP in concise pharma-specific language, covering purpose, scope, responsibilities, key steps, and records.\n\n" + text},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            return resp.choices[0].message.content.strip()
        else:
            resp = client.ChatCompletion.create(
                model=os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a pharma regulatory compliance assistant."},
                    {"role": "user", "content": "Summarize the following SOP in concise pharma-specific language, covering purpose, scope, responsibilities, key steps, and records.\n\n" + text},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning(f"OpenAI summarize failed: {e}")
        return None

def _fallback_summarize(text: str) -> str:
    """Very simple fallback: first ~350 chars of normalized text."""
    cleaned = " ".join(text.split())
    return (cleaned[:350] + "…") if len(cleaned) > 350 else cleaned

# --------------------------------------------------------------------------------------
# SOP generation
# --------------------------------------------------------------------------------------
SOP_SECTION_HEADERS = ["Objective", "Scope", "Responsibility", "Procedure", "Records", "Appendix"]

def _openai_generate_sop(prompt: str) -> Optional[Dict[str, Any]]:
    if openai is None or not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        client = openai.OpenAI() if hasattr(openai, "OpenAI") else openai
        messages = [
            {"role": "system", "content": "You generate structured, regulatory-compliant SOPs for the pharmaceutical industry."},
            {"role": "user", "content":
                f"""Generate a professional SOP. Use JSON output only with keys: {SOP_SECTION_HEADERS}.
If the user prompt is a short brief, expand it into complete sections with step-by-step procedure and typical compliance language.

Brief:
\"\"\"{prompt.strip()}\"\"\""""}
        ]
        if hasattr(client, "chat"):
            resp = client.chat.completions.create(
                model=os.environ.get("OPENAI_SOP_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.3,
                max_tokens=900,
                response_format={"type": "json_object"} if os.environ.get("OPENAI_JSON", "1") == "1" else None,
            )
            content = resp.choices[0].message.content
        else:
            resp = client.ChatCompletion.create(
                model=os.environ.get("OPENAI_SOP_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.3,
                max_tokens=900,
            )
            content = resp["choices"][0]["message"]["content"]

        # Try parse JSON
        try:
            data = json.loads(content)
            return {k: data.get(k, "") for k in SOP_SECTION_HEADERS}
        except Exception:
            # If not JSON, wrap into a single section
            return {"Objective": content, "Scope": "", "Responsibility": "", "Procedure": "", "Records": "", "Appendix": ""}
    except Exception as e:
        log.warning(f"OpenAI SOP generation failed: {e}")
        return None

def _template_generate_sop(prompt: str) -> Dict[str, Any]:
    steps = [
        "Prepare prerequisites and materials.",
        "Execute the task following controlled steps.",
        "Record outputs and deviations.",
        "Perform review and approval.",
        "Archive records per retention policy."
    ]
    return {
        "Objective": f"Define and standardize the process for: {prompt.strip()}",
        "Scope": "This SOP applies to relevant departments and personnel involved in the described process.",
        "Responsibility": "- Process Owner: Operations\n- Approver: Quality Assurance\n- Executor: Trained Associates",
        "Procedure": "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)),
        "Records": "Checklist, logbook entries, electronic records, and approvals maintained per data integrity (ALCOA+).",
        "Appendix": "Related SOPs, forms, and references (e.g., ISO 9001, internal policy)."
    }

# --------------------------------------------------------------------------------------
# Public facade
# --------------------------------------------------------------------------------------
@dataclass
class SummarizeResult:
    text: str
    readability: Dict[str, Any]
    clarity: Dict[str, Any]

class Services:
    """Main integration surface for the app."""
    def __init__(self) -> None:
        self._nlp_loaded = False

    # --- Summarization entrypoints -----------------------------------------------------
    def summarize(self, data_or_text: Union[bytes, str], filename: Optional[str] = None) -> SummarizeResult:
        if isinstance(data_or_text, (bytes, bytearray)):
            raw_text = extract_text_from_upload(bytes(data_or_text), filename)
            if not raw_text:
                raw_text = _decode_text(bytes(data_or_text))
        else:
            raw_text = str(data_or_text or "")

        if not raw_text.strip():
            return SummarizeResult(text="", readability={"flesch_reading_ease": None, "gunning_fog_index": None}, clarity=_clarity_metrics(""))

        # Try in order: OpenAI -> HF -> fallback
        summary = _openai_summarize(raw_text) or _hf_summarize(raw_text) or _fallback_summarize(raw_text)

        return SummarizeResult(
            text=summary,
            readability=_readability(raw_text),
            clarity=_clarity_metrics(raw_text),
        )

    # --- SOP generation ----------------------------------------------------------------
    def generate_sop(self, prompt: str) -> Dict[str, Any]:
        sop = _openai_generate_sop(prompt) or _template_generate_sop(prompt)
        return sop

    # --- Simple structure check --------------------------------------------------------
    def quick_structure_check(self, text: str) -> Dict[str, Any]:
        required = ["purpose", "scope", "responsib", "procedure", "record"]
        found = {k: bool(re.search(k, text, re.I)) for k in required}
        return {"required_sections_present": sum(found.values()), "details": found}
