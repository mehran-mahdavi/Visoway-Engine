import json
import logging
import re
from typing import Any, Dict, List

import requests
from django.conf import settings
from django.db import transaction
from visas.models import (
    RequiredDocument,
    Visa,
    VisaFAQ,
    VisaRoadmapStep,
    VisaTip,
)
from visas.utils.validators import validate_visa_data

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

class AIError(Exception):
    pass


def _extract_json(text: str) -> Dict[str, Any]:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"AI returned invalid JSON: {raw[:1000]}")
        raise AIError("Model did not return valid JSON.") from exc


def _call_openrouter(system_prompt: str, user_prompt: str, retries: int = 1) -> Dict[str, Any]:
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or ""
    if not api_key:
        raise AIError("OPENROUTER_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = getattr(settings, "OPENROUTER_HTTP_REFERER", None) or ""
    if referer:
        headers["Referer"] = referer
    app_title = getattr(settings, "OPENROUTER_APP_TITLE", None)
    if app_title:
        headers["X-Title"] = app_title

    payload = {
        "model": DEFAULT_MODEL,
        "temperature": 0.2,
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=getattr(settings, "OPENROUTER_TIMEOUT", 120),
        )
    except requests.RequestException as e:
        logger.exception("OpenRouter request failed")
        raise AIError("Network error while contacting OpenRouter.") from e

    if not response.ok:
        logger.error(f"OpenRouter Error {response.status_code}: {response.text[:1000]}")
        raise AIError(f"OpenRouter API error: {response.status_code}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        return _extract_json(content)
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Unexpected response structure: {data}")
        raise AIError("Invalid response format from OpenRouter.") from e
    except AIError as e:
        if retries > 0:
            logger.warning("JSON parsing failed, retrying...")
            return _call_openrouter(system_prompt, user_prompt, retries=retries - 1)
        raise e


def suggest_visa_types(country_name: str, existing_types: List[str]) -> List[str]:
    """Suggest missing visa types for a country."""
    system = (
        "You are an expert immigration consultant. Return ONLY a valid JSON array of strings representing "
        "visa types (e.g., ['Tourist', 'Digital Nomad']). Do not include explanations."
    )
    user = (
        f"Country: {country_name}.\n"
        f"Existing visas we already have: {', '.join(existing_types) if existing_types else 'None'}.\n"
        "Suggest up to 5 other popular visa types this country offers that are NOT in the existing list. "
        "Output ONLY a JSON array of strings."
    )
    data = _call_openrouter(system, user)
    if isinstance(data, list):
        return [str(v) for v in data]
    if isinstance(data, dict) and "visas" in data:
        return [str(v) for v in data["visas"]]
    return []


def _get_visa_system_prompt() -> str:
    return (
        "You are a senior immigration data architect and expert visa consultant.\n"
        "Your job is to generate COMPLETE, STRUCTURED, AND RELATIONAL visa data.\n"
        "You MUST follow the schema strictly. No omissions are allowed.\n"
        "\n"
        "# ⚠️ CRITICAL RULES (HIGHEST PRIORITY)\n"
        "1. You MUST always generate ALL of the following sections:\n"
        "   * visa_roadmap_steps\n"
        "   * required_documents\n"
        "   * visa_tips\n"
        "   * visa_faqs\n"
        "2. NEVER return empty arrays.\n"
        "3. NEVER skip any section.\n"
        "4. NEVER return partial data.\n"
        "5. NEVER use placeholders like 'N/A' or 'etc'.\n"
        "6. Output MUST be valid JSON ONLY (no markdown, no explanation).\n"
        "\n"
        "# 🧠 BEHAVIOR RULES\n"
        "* All content MUST be realistic and consistent with the country.\n"
        "* All steps MUST be practical and sequential.\n"
        "* All documents MUST reflect real embassy/immigration requirements.\n"
        "* All tips MUST be actionable and useful for applicants.\n"
        "* All FAQs MUST reflect real user concerns.\n"
        "\n"
        "# 🔒 VALIDATION RULES (IMPORTANT)\n"
        "* visa_roadmap_steps MUST have 5–8 items minimum.\n"
        "* required_documents MUST have 5–12 items minimum.\n"
        "* visa_tips MUST have 4–8 items minimum.\n"
        "* visa_faqs MUST have 5–10 items minimum.\n"
        "If you cannot meet minimum items -> REGENERATE internally (do not return incomplete output).\n"
        "\n"
        "# 🚫 FORBIDDEN\n"
        "* Do not omit any section.\n"
        "* Do not merge sections.\n"
        "* Do not return null values.\n"
        "* Do not return empty arrays.\n"
        "* Do not include 'country' field in output.\n"
        "\n"
        "# 📦 OUTPUT SCHEMA (STRICT)\n"
        "{\n"
        '  "name": "string",\n'
        '  "type": "string",\n'
        '  "description": "string",\n'
        '  "cost": 0,\n'
        '  "currency": "string",\n'
        '  "stay_duration_days": 0,\n'
        '  "process_time_days": 0,\n'
        '  "difficulty": "Easy | Medium | Hard",\n'
        '  "visa_roadmap_steps": [{"order": 0, "title": "string", "description": "string", "is_optional": false}],\n'
        '  "required_documents": [{"order": 0, "name": "string", "description": "string", "is_mandatory": true}],\n'
        '  "visa_tips": [{"order": 0, "title": "string", "description": "string"}],\n'
        '  "visa_faqs": [{"order": 0, "question": "string", "answer": "string"}]\n'
        "}"
    )


def generate_visa_data(country: Any, visa_type: str) -> Dict[str, Any]:
    """Generate full structured visa data from scratch for a given country and type."""
    system = _get_visa_system_prompt()
    user = (
        f"Country: {country.name} ({country.code})\n"
        f"Visa Type: {visa_type}\n"
    )
    raw_data = _call_openrouter(system, user)
    return validate_visa_data(raw_data)


def fill_partial_data(country: Any, partial_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fill incomplete visa data using existing partial data."""
    system = _get_visa_system_prompt()
    user = (
        f"Country: {country.name} ({country.code})\n"
        "I have a partially completed visa profile. Fill in the missing details and expand on existing ones.\n"
        "Here is the current data:\n"
        f"{json.dumps(partial_data, indent=2)}"
    )
    raw_data = _call_openrouter(system, user)
    return validate_visa_data(raw_data)


@transaction.atomic
def save_generated_relations(visa: Visa, ai_data: Dict[str, Any]):
    """Bulk create related objects for a saved Visa instance based on validated AI data."""
    if "roadmap_steps" in ai_data:
        VisaRoadmapStep.objects.filter(visa=visa).delete()
        steps = []
        for i, step in enumerate(ai_data["roadmap_steps"], start=1):
            steps.append(
                VisaRoadmapStep(
                    visa=visa,
                    order=i,
                    title=step.get("title", "")[:200],
                    description=step.get("description", ""),
                    is_optional=step.get("is_optional", False),
                )
            )
        VisaRoadmapStep.objects.bulk_create(steps)

    if "required_documents" in ai_data:
        RequiredDocument.objects.filter(visa=visa).delete()
        docs = []
        for i, doc in enumerate(ai_data["required_documents"], start=1):
            docs.append(
                RequiredDocument(
                    visa=visa,
                    order=i,
                    name=doc.get("name", "")[:200],
                    description=doc.get("description", ""),
                    is_mandatory=doc.get("is_mandatory", True),
                )
            )
        RequiredDocument.objects.bulk_create(docs)

    if "tips" in ai_data:
        VisaTip.objects.filter(visa=visa).delete()
        tips = []
        for i, tip in enumerate(ai_data["tips"], start=1):
            tips.append(
                VisaTip(
                    visa=visa,
                    order=i,
                    title=tip.get("title", "")[:200],
                    description=tip.get("description", ""),
                )
            )
        VisaTip.objects.bulk_create(tips)

    if "faqs" in ai_data:
        VisaFAQ.objects.filter(visa=visa).delete()
        faqs = []
        for i, faq in enumerate(ai_data["faqs"], start=1):
            faqs.append(
                VisaFAQ(
                    visa=visa,
                    order=i,
                    question=faq.get("question", "")[:300],
                    answer=faq.get("answer", ""),
                )
            )
        VisaFAQ.objects.bulk_create(faqs)
