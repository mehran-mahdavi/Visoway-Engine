from typing import Any, Dict

def _parse_int(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def _parse_float(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def validate_visa_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and sanitizes AI-generated visa data.
    Ensures difficulty is 1, 2, or 3. Removes invalid entries.
    """
    if not isinstance(raw_data, dict):
        return {}

    validated = {}

    # Scalars
    for key in ["name", "type", "description", "roadmap", "currency"]:
        if key in raw_data and isinstance(raw_data[key], str):
            validated[key] = raw_data[key].strip()

    # Numerics
    cost = _parse_float(raw_data.get("cost"))
    if cost is not None and cost >= 0:
        validated["cost"] = cost

    stay = _parse_int(raw_data.get("stay_duration_days"))
    if stay is not None and stay > 0:
        validated["stay_duration_days"] = stay

    process = _parse_int(raw_data.get("process_time_days"))
    if process is not None and process > 0:
        validated["process_time_days"] = process

    # Difficulty (1=Easy, 2=Medium, 3=Hard)
    diff = raw_data.get("difficulty")
    if isinstance(diff, str):
        diff = diff.strip().lower()
        if "easy" in diff:
            validated["difficulty"] = 1
        elif "hard" in diff:
            validated["difficulty"] = 3
        else:
            validated["difficulty"] = 2
    else:
        difficulty = _parse_int(diff)
        if difficulty in [1, 2, 3]:
            validated["difficulty"] = difficulty
        else:
            validated["difficulty"] = 2  # Default to Medium

    # Arrays
    if "visa_roadmap_steps" in raw_data and isinstance(raw_data["visa_roadmap_steps"], list):
        steps = []
        for step in raw_data["visa_roadmap_steps"]:
            if isinstance(step, dict) and "title" in step:
                steps.append({
                    "title": str(step["title"]),
                    "description": str(step.get("description", "")),
                    "is_optional": bool(step.get("is_optional", False))
                })
        if steps:
            validated["roadmap_steps"] = steps
            
    if "roadmap_steps" in raw_data and isinstance(raw_data["roadmap_steps"], list):
        steps = []
        for step in raw_data["roadmap_steps"]:
            if isinstance(step, dict) and "title" in step:
                steps.append({
                    "title": str(step["title"]),
                    "description": str(step.get("description", "")),
                    "is_optional": bool(step.get("is_optional", False))
                })
        if steps:
            validated["roadmap_steps"] = steps

    if "required_documents" in raw_data and isinstance(raw_data["required_documents"], list):
        docs = []
        for doc in raw_data["required_documents"]:
            if isinstance(doc, dict) and "name" in doc:
                docs.append({
                    "name": str(doc["name"]),
                    "description": str(doc.get("description", "")),
                    "is_mandatory": bool(doc.get("is_mandatory", True))
                })
        if docs:
            validated["required_documents"] = docs

    if "visa_tips" in raw_data and isinstance(raw_data["visa_tips"], list):
        tips = []
        for tip in raw_data["visa_tips"]:
            if isinstance(tip, dict) and ("title" in tip or "description" in tip):
                tips.append({
                    "title": str(tip.get("title", "")),
                    "description": str(tip.get("description", ""))
                })
        if tips:
            validated["tips"] = tips
            
    if "tips" in raw_data and isinstance(raw_data["tips"], list):
        tips = []
        for tip in raw_data["tips"]:
            if isinstance(tip, dict) and ("title" in tip or "description" in tip):
                tips.append({
                    "title": str(tip.get("title", "")),
                    "description": str(tip.get("description", ""))
                })
        if tips:
            validated["tips"] = tips

    if "visa_faqs" in raw_data and isinstance(raw_data["visa_faqs"], list):
        faqs = []
        for faq in raw_data["visa_faqs"]:
            if isinstance(faq, dict) and ("question" in faq or "answer" in faq):
                faqs.append({
                    "question": str(faq.get("question", "")),
                    "answer": str(faq.get("answer", ""))
                })
        if faqs:
            validated["faqs"] = faqs
            
    if "faqs" in raw_data and isinstance(raw_data["faqs"], list):
        faqs = []
        for faq in raw_data["faqs"]:
            if isinstance(faq, dict) and ("question" in faq or "answer" in faq):
                faqs.append({
                    "question": str(faq.get("question", "")),
                    "answer": str(faq.get("answer", ""))
                })
        if faqs:
            validated["faqs"] = faqs

    return validated
