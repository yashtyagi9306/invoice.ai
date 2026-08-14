import json
import logging
from typing import Any, Optional

import httpx
from openai import OpenAI
from pydantic import BaseModel

from backend.ai.prompts import RISK_SYSTEM_PROMPT, SYSTEM_PROMPT, build_risk_prompt, build_user_prompt
from backend.config import get_settings
from backend.models.extraction import InvoiceExtraction
from backend.models.risk import RiskAssessment

import time

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o-mini"
# Groq exposes an OpenAI-compatible endpoint at api.groq.com/openai/v1
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"  # fast 8B Llama, good for structured extraction
OLLAMA_TIMEOUT_S = 180.0  # local 3B model can take 30-60s on first load
MAX_RETRIES = 2


# Small reminder appended to Ollama prompts; small local models occasionally
# add prose around JSON, so this nudges them back on track.
_OLLAMA_JSON_REMINDER = " Respond with a single JSON object only — no prose, no markdown fences."


def _client() -> Optional[OpenAI]:
    """Return an OpenAI-compatible client based on `settings.llm_provider`.

    Both OpenAI and Groq speak the same OpenAI SDK protocol; only the base URL
    and API key differ. Ollama is not an OpenAI-compatible endpoint, so this
    returns None when Ollama is selected — that path is handled separately by
    `_call_ollama_json`.
    """
    settings = get_settings()
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            return None
        return OpenAI(
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
            timeout=30.0,
            max_retries=0,
        )
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
    return None


def _model_name() -> str:
    """Return the model identifier to use with the OpenAI-compatible API."""
    settings = get_settings()
    if settings.llm_provider == "groq":
        return settings.groq_model or GROQ_DEFAULT_MODEL
    return OPENAI_MODEL


def _strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a JSON Schema for `model` that OpenAI's strict structured-output
    mode will accept.

    OpenAI's strict mode requires, on every object node:
      - `additionalProperties: false`
      - `required` to list every key in `properties` (Pydantic only marks
        non-default fields as required, so we re-add any missing ones)

    Pydantic's default `model_json_schema()` omits the first and is permissive
    on the second, so this walker rewrites the schema accordingly.
    """
    schema = model.model_json_schema()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if (node.get("type") == "object" or "properties" in node) and isinstance(
                node.get("properties"), dict
            ):
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(schema)
    return schema


def _ollama_schema_template(model: type[BaseModel]) -> dict[str, Any]:
    """Build a JSON skeleton of `model` with empty values for every field.

    Small local models (3B, 1B) struggle to produce structured JSON from a
    system prompt alone — they need an explicit template. This returns a dict
    that mirrors `model`'s shape but with safe placeholder values, so the model
    can fill each field rather than invent its own structure.

    For `InvoiceExtraction`, the `line_items` array is omitted from the template
    because the small 3B model produces unreliable output for it; the
    downstream pipeline already handles empty `line_items` gracefully.
    """
    schema = _strict_schema(model)
    properties = dict(schema.get("properties", {}))

    # Drop line_items from the template — too unreliable on small models.
    properties.pop("line_items", None)

    def empty_for(node: dict[str, Any]) -> Any:
        node_type = node.get("type")
        if node_type == "string":
            return ""
        if node_type == "number" or node_type == "integer":
            return 0
        if node_type == "boolean":
            return False
        if node_type == "array":
            item = empty_for(node.get("items", {}))
            return [item] if item != "" else []
        if node_type == "object" or "properties" in node:
            return {k: empty_for(v) for k, v in node.get("properties", {}).items()}
        return None

    return {k: empty_for(v) for k, v in properties.items()}


def _extract_line_items_from_text(text: str) -> list[dict[str, str]]:
    """Fallback regex-based extractor for line items.

    The 3B Ollama model produces unreliable line_items output. The invoice text
    is usually clean enough for a regex like
    `1. <description> ......... <amount>` to extract them deterministically.
    """
    import re

    pattern = re.compile(
        r"^\s*(\d+)\.\s+(.+?)\s+(?:\.{3,}|…+|\s{3,})\s*([\d,]+(?:\.\d+)?)\s*$",
        re.MULTILINE,
    )
    items = []
    for match in pattern.finditer(text):
        items.append(
            {
                "description": match.group(2).strip(),
                "quantity": "",
                "unit_price": "",
                "amount": match.group(3).replace(",", ""),
            }
        )
    return items


# Pydantic field names whose values are `FieldExtraction` (i.e. the small
# model should nest them as {value, confidence} but may flatten them to a
# bare string). Derived once at import from `extraction.InvoiceExtraction`.
_NESTED_FIELDS: set[str] = set()
_LINE_ITEM_FIELDS: set[str] = {"description", "quantity", "unit_price", "amount"}


def _normalize_flat_invoice(data: dict[str, Any]) -> dict[str, Any]:
    """Rewrite the small-model's flat response into the nested Pydantic shape.

    Common drift the 3B model produces:
      - `{"vendor_name": "Acme"}` instead of `{"vendor_name": {"value": "Acme", "confidence": 0.9}}`
      - `{"subtotal": 6370.00}` (number) instead of `{"subtotal": {"value": "6370.00", "confidence": 0.9}}`
      - line items with extra/missing fields
      - entirely missing top-level fields (model forgets keys)
    """
    from backend.models.extraction import InvoiceExtraction

    if not _NESTED_FIELDS:
        nested_props = _strict_schema(InvoiceExtraction).get("properties", {})
        # Pydantic emits nested models as `$ref` in `$defs`, so we can't tell
        # which props are nested just by their inline schema. The known list
        # (everything except `line_items`) is short enough to hardcode — and
        # safer than introspecting JSON Schema with refs.
        _NESTED_FIELDS.update(
            k for k in nested_props.keys() if k != "line_items"
        )

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if key in _NESTED_FIELDS:
            if isinstance(value, dict):
                # Already nested — keep as-is, but ensure confidence exists.
                if "value" in value and "confidence" not in value:
                    value = {**value, "confidence": 0.9}
                normalized[key] = value
            elif value is None:
                normalized[key] = {"value": None, "confidence": 0.0}
            else:
                # Small model sometimes concatenates repeated values like
                # "573.30,573.30" for fields that occur more than once in the
                # invoice (e.g. CGST + SGST). Split on comma and keep the first.
                if isinstance(value, str) and "," in value:
                    value = value.split(",")[0].strip()
                normalized[key] = {"value": str(value), "confidence": 0.9}
        else:
            normalized[key] = value

    # Fill any missing nested-field with a safe default so the Pydantic schema
    # (which requires every field) doesn't reject the response.
    for key in _NESTED_FIELDS:
        if key not in normalized:
            normalized[key] = {"value": None, "confidence": 0.0}

    # Normalize line_items: keep only known fields; ensure each is a dict and
    # coerce numeric/string fields to strings (the `LineItem` schema is all
    # `Optional[str]` — small models often return numbers). If anything goes
    # wrong here, default to an empty list rather than failing the whole
    # extraction — line items are useful but not required.
    if "line_items" in normalized and isinstance(normalized["line_items"], list):
        clean_items = []
        for item in normalized["line_items"]:
            if not isinstance(item, dict):
                continue
            clean_item = {}
            for k in _LINE_ITEM_FIELDS:
                if k in item:
                    v = item[k]
                    if isinstance(v, dict):
                        # Small model nested a FieldExtraction-style sub-object
                        # inside a line item — flatten to its `value`.
                        v = v.get("value")
                    clean_item[k] = None if v is None else (str(v) if not isinstance(v, str) else v)
            if any(clean_item.values()):
                clean_items.append(clean_item)
        normalized["line_items"] = clean_items
    else:
        normalized["line_items"] = []

    return normalized


def _call_ollama_json(
    system_prompt: str,
    user_prompt: str,
    schema: Optional[type[BaseModel]] = None,
) -> str:
    """Call Ollama's /api/chat with `format: "json"` and return the raw JSON
    text. Pydantic validation happens in the caller.

    When `schema` is supplied, an empty template matching the Pydantic model is
    prepended to the user prompt — small local models need an explicit template
    to produce structured output reliably.

    Raises httpx.HTTPError on transport failure, or ValueError if the response
    is empty / not JSON.
    """
    settings = get_settings()
    effective_user_prompt = user_prompt
    if schema is not None:
        template = json.dumps(_ollama_schema_template(schema), indent=2)
        effective_user_prompt = (
            f"Return a JSON object matching this exact schema "
            f"(fill every value, keep every key, return only the JSON object):\n"
            f"{template}\n\n{user_prompt}"
        )

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt + _OLLAMA_JSON_REMINDER},
            {"role": "user", "content": effective_user_prompt},
        ],
        "stream": False,
        "format": "json",
    }
    if schema is not None:
        logger.info(
            "Ollama request: model=%s url=%s schema=%s",
            settings.ollama_model,
            settings.ollama_base_url,
            schema.__name__,
        )

    with httpx.Client(timeout=OLLAMA_TIMEOUT_S) as client:
        response = client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    content = (data.get("message") or {}).get("content", "")
    if not content:
        raise ValueError("Empty response from Ollama")
    # Some small models still wrap JSON in prose despite format=json — try to
    # extract a JSON object from the response before giving up.
    content = content.strip()
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = content[start : end + 1]
            json.loads(candidate)  # raises if still bad
            logger.warning("Ollama wrapped JSON in prose; extracted substring")
            return candidate
        raise ValueError(f"Ollama returned non-JSON content: {content[:200]!r}")


def _call_openai_json(prompt_messages: list[dict], schema: type[BaseModel], schema_name: str) -> str:
    """Call an OpenAI-compatible chat API (OpenAI or Groq) with strict JSON
    schema output and return the raw JSON text. Pydantic validation happens
    in the caller.
    """
    settings = get_settings()
    client = _client()
    if client is None:
        raise RuntimeError(
            f"{settings.llm_provider} provider selected but its API key is not set"
        )

    if settings.llm_provider == "openai":
        # OpenAI supports the strict Responses API with json_schema.
        response = client.responses.create(
            model=_model_name(),
            temperature=0,
            input=prompt_messages,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": _strict_schema(schema),
                }
            },
        )
        if not response.output_text:
            raise ValueError("Empty response from model")
        return response.output_text

    # Groq (and any other OpenAI-compatible API without the Responses API):
    # use chat.completions with json_object response_format. Groq requires the word
    # 'json' in messages when using response_format={"type": "json_object"}.
    # We pass the strict JSON schema in the system message to guide extraction.
    groq_messages = list(prompt_messages)
    schema_str = json.dumps(_strict_schema(schema), indent=2)
    groq_messages.append(
        {
            "role": "system",
            "content": f"Respond ONLY with a valid JSON object adhering strictly to this JSON Schema:\n{schema_str}",
        }
    )

    response = client.chat.completions.create(
        model=_model_name(),
        temperature=0,
        messages=groq_messages,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from model")
    return content



def _call_model(invoice_text: str) -> str:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return _call_ollama_json(SYSTEM_PROMPT, build_user_prompt(invoice_text), InvoiceExtraction)

    return _call_openai_json(
        prompt_messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(invoice_text)},
        ],
        schema=InvoiceExtraction,
        schema_name="invoice_extraction",
    )


def _call_risk_model(invoice_json: str, validation_summary: str) -> str:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return _call_ollama_json(
            RISK_SYSTEM_PROMPT,
            build_risk_prompt(invoice_json, validation_summary),
            RiskAssessment,
        )

    return _call_openai_json(
        prompt_messages=[
            {"role": "system", "content": RISK_SYSTEM_PROMPT},
            {"role": "user", "content": build_risk_prompt(invoice_json, validation_summary)},
        ],
        schema=RiskAssessment,
        schema_name="risk_assessment",
    )


def extract_invoice_data(invoice_text: str) -> InvoiceExtraction:
    last_error: Exception | None = None
    raw: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        logger.info("AI extraction started (attempt %s)", attempt + 1)
        try:
            raw = _call_model(invoice_text)
            data = InvoiceExtraction.model_validate_json(raw)
            logger.info("AI extraction validated successfully")
            return data
        except Exception as exc:  # noqa: BLE001 - bad JSON, schema mismatch, API/network errors
            # Models (Ollama or Groq) may return flat or slightly drifted schema shapes;
            # normalize then revalidate.
            if raw is not None:
                try:
                    flat = json.loads(raw)
                    normalized = _normalize_flat_invoice(flat)

                    # If the model returned no line items, fall back to a
                    # regex pass over the original text — small models are
                    # too unreliable for nested arrays.
                    if not normalized.get("line_items"):
                        regex_items = _extract_line_items_from_text(invoice_text)
                        if regex_items:
                            normalized["line_items"] = regex_items
                            logger.info(
                                "Filled %d line items via regex fallback",
                                len(regex_items),
                            )
                    data = InvoiceExtraction.model_validate_json(json.dumps(normalized))
                    logger.info("AI extraction validated after shape normalization")
                    return data
                except Exception as norm_exc:  # noqa: BLE001
                    logger.warning(
                        "Shape normalization failed: %s", type(norm_exc).__name__
                    )
            last_error = exc
            logger.warning(
                "AI extraction failed on attempt %s: %s. Retrying in %ss...",
                attempt + 1,
                type(exc).__name__,
                2.0 * (attempt + 1),
            )
            time.sleep(2.0 * (attempt + 1))

    raise RuntimeError("AI extraction failed after retry") from last_error


def analyze_risk(invoice: InvoiceExtraction, validation_summary: str) -> RiskAssessment:
    last_error: Exception | None = None
    invoice_json = invoice.model_dump_json()

    for attempt in range(MAX_RETRIES + 1):
        logger.info("AI risk analysis started (attempt %s)", attempt + 1)
        try:
            raw = _call_risk_model(invoice_json, validation_summary)
            data = RiskAssessment.model_validate_json(raw)
            logger.info("AI risk analysis validated successfully")
            return data
        except Exception as exc:  # noqa: BLE001 - bad JSON, schema mismatch, API/network errors
            last_error = exc
            logger.warning(
                "AI risk analysis failed on attempt %s: %s",
                attempt + 1,
                type(exc).__name__,
            )

    raise RuntimeError("AI risk analysis failed after retry") from last_error