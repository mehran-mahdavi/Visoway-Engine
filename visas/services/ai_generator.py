"""
OpenRouter-backed content generation for admin "Fill with AI" actions.

Uses HTTP requests only (no OpenAI SDK). API key must be set via environment:
 OPENROUTER_API_KEY
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

from visas.models import RequiredDocument, Visa, VisaFAQ, VisaRoadmapStep, VisaTip

logger = logging.getLogger(__name__)

OPENROUTER_URL = getattr(
    settings,
    "OPENROUTER_API_URL",
    "https://openrouter.ai/api/v1/chat/completions",
)
DEFAULT_MODEL = getattr(
    settings,
    "OPENROUTER_MODEL",
    "nvidia/nemotron-3-super-120b-a12b:free",
)


class OpenRouterError(Exception):
    """Raised when OpenRouter returns an error or unusable payload."""


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output; tolerate ```json fences```."""
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("AI returned non-JSON: %s", raw[:2000])
        raise OpenRouterError("Model did not return valid JSON.") from exc


def _openrouter_chat(*, user_prompt: str, system_prompt: str | None = None) -> str:
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or ""
    if not api_key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY is not configured. Set it in the environment."
        )

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # OpenRouter recommends optional attribution headers in production.
    referer = getattr(settings, "OPENROUTER_HTTP_REFERER", None) or ""
    if referer:
        headers["Referer"] = str(referer)
    if getattr(settings, "OPENROUTER_APP_TITLE", None):
        headers["X-Title"] = str(settings.OPENROUTER_APP_TITLE)

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=getattr(settings, "OPENROUTER_TIMEOUT", 120),
        )
    except requests.RequestException as exc:
        logger.exception("OpenRouter request failed: %s", exc)
        raise OpenRouterError("Could not reach OpenRouter.") from exc

    if not response.ok:
        logger.error(
            "OpenRouter HTTP %s: %s",
            response.status_code,
            response.text[:2000],
        )
        raise OpenRouterError(
            f"OpenRouter error (HTTP {response.status_code})."
        )

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected OpenRouter response: %s", data)
        raise OpenRouterError("Unexpected response shape from OpenRouter.") from exc


def _visa_context_lines(visa: Visa) -> str:
    return (
        f"Country: {visa.country.name} ({visa.country.code})\n"
        f"Visa name: {visa.name}\n"
        f"Visa slug: {visa.slug}\n"
        f"Visa type: {visa.type}\n"
    )


def generate_fields_for_instance(instance: Any) -> dict[str, Any]:
    """
    Dispatch generation by model class. Returns a dict of field_name -> value
    suitable for setattr + save (only whitelisted fields).
    """
    system = (
        "You are an expert immigration and visa copywriter. "
        "Answer with a single JSON object only—no markdown, no commentary."
    )

    if isinstance(instance, Visa):
        user = (
            _visa_context_lines(instance)
            + "\nGenerate concise, accurate marketing copy and an overview roadmap.\n"
            + "Return JSON with exactly these keys:\n"
            + '  "description": string (2–4 short paragraphs, plain text, \\n between paragraphs),\n'
            + '  "roadmap": string (high-level bullet-style overview as plain text lines starting with "- ").\n'
            + "Do not invent specific government fees or legal guarantees; use cautious wording where uncertain."
        )
        content = _openrouter_chat(system_prompt=system, user_prompt=user)
        data = _extract_json_object(content)
        out: dict[str, Any] = {}
        if "description" in data:
            out["description"] = str(data["description"]).strip()
        if "roadmap" in data:
            out["roadmap"] = str(data["roadmap"]).strip()
        return out

    if isinstance(instance, VisaRoadmapStep):
        visa = instance.visa
        user = (
            _visa_context_lines(visa)
            + f"Roadmap step order: {instance.order}\n"
            + f"Current title (may improve): {instance.title}\n"
            + f"Current description (may replace): {instance.description}\n\n"
            + "Return JSON with keys:\n"
            + '  "title": string (<= 200 chars),\n'
            + '  "description": string (detailed, plain text).\n'
        )
        content = _openrouter_chat(system_prompt=system, user_prompt=user)
        data = _extract_json_object(content)
        return {
            "title": str(data.get("title", instance.title))[:200],
            "description": str(data.get("description", "")).strip(),
        }

    if isinstance(instance, RequiredDocument):
        visa = instance.visa
        user = (
            _visa_context_lines(visa)
            + f"Document order: {instance.order}\n"
            + f"Current name: {instance.name}\n"
            + f"Current description: {instance.description}\n\n"
            + "Return JSON with keys:\n"
            + '  "name": string (clear document name, <= 200 chars),\n'
            + '  "description": string (what it is, how to obtain, formatting notes; plain text).\n'
        )
        content = _openrouter_chat(system_prompt=system, user_prompt=user)
        data = _extract_json_object(content)
        return {
            "name": str(data.get("name", instance.name))[:200],
            "description": str(data.get("description", "")).strip(),
        }

    if isinstance(instance, VisaTip):
        visa = instance.visa
        user = (
            _visa_context_lines(visa)
            + f"Tip order: {instance.order}\n"
            + f"Current title: {instance.title}\n"
            + f"Current description: {instance.description}\n\n"
            + "Return JSON with keys:\n"
            + '  "title": string (short, helpful, <= 200 chars),\n'
            + '  "description": string (actionable tip, plain text).\n'
        )
        content = _openrouter_chat(system_prompt=system, user_prompt=user)
        data = _extract_json_object(content)
        return {
            "title": str(data.get("title", ""))[:200],
            "description": str(data.get("description", "")).strip(),
        }

    if isinstance(instance, VisaFAQ):
        visa = instance.visa
        user = (
            _visa_context_lines(visa)
            + f"FAQ order: {instance.order}\n"
            + f"Current question: {instance.question}\n"
            + f"Current answer: {instance.answer}\n\n"
            + "Return JSON with keys:\n"
            + '  "question": string (<= 300 chars),\n'
            + '  "answer": string (clear, plain text; cautious if requirements vary).\n'
        )
        content = _openrouter_chat(system_prompt=system, user_prompt=user)
        data = _extract_json_object(content)
        return {
            "question": str(data.get("question", instance.question))[:300],
            "answer": str(data.get("answer", "")).strip(),
        }

    raise OpenRouterError(f"Unsupported model for AI generation: {type(instance)!r}")
