import anthropic
import json
import os
import re

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions_config.json")


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_field_descriptions(config: dict) -> str:
    lines = []
    for q in config.get("questions", []):
        field_id = q["id"]
        options = " / ".join(opt["value"] for opt in q["options"])
        lines.append(f"- {field_id}: {options}")
    return "\n".join(lines)


def anonymize_answers(answers: dict) -> dict:
    return answers


def analyze_semantics(answers: dict, rule_issues: list) -> dict | None:
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        config = _load_config()
        field_descriptions = _build_field_descriptions(config)
        domain_label = config.get("domain_label", "consumer survey")

        client = anthropic.Anthropic(api_key=api_key)

        detected_rules = [issue["rule_name"] for issue in rule_issues]

        prompt = f"""You are a survey data quality expert. Analyze these {domain_label} survey responses for semantic inconsistencies that are NOT already detected by the rule-based system.

Survey responses (structured option keys):
{json.dumps(answers, indent=2)}

Already detected rule-based issues: {detected_rules if detected_rules else "none"}

Fields and their possible values:
{field_descriptions}

Look ONLY for additional semantic inconsistencies not already in the detected list above.

Respond with ONLY valid JSON (no markdown, no explanation outside JSON).
IMPORTANT: Write the "reason" value in Arabic language only.

{{"is_valid": true, "reason": "لا توجد تناقضات دلالية إضافية", "confidence": 95}}

OR if you find an additional inconsistency:
{{"is_valid": false, "reason": "وصف عربي مختصر للتناقض المكتشف", "confidence": 40}}"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = message.content[0].text.strip()
        result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
        result_text = re.sub(r'\s*```$', '', result_text)
        result = json.loads(result_text)
        return result
    except Exception:
        return None
