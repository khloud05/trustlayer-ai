import json
import os
from typing import List

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions_config.json")


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _make_issue(rule: dict) -> dict:
    return {
        "issue_type": rule["issue_type"],
        "rule_name": rule["name"],
        "severity": rule["severity"],
        "deduction": rule["deduction"],
        "field_names": rule.get("field_names", []),
        "ar_message": rule["ar_message"],
        "ar_explanation": rule["ar_explanation"],
        "ar_action_suggested": rule["ar_action_suggested"],
    }


def run_rules(answers: dict, response_time_seconds: int) -> List[dict]:
    config = _load_config()
    issues = []

    for rule in config.get("rules", []):
        rule_type = rule["type"]

        if rule_type == "field_value_conflict":
            val_a = answers.get(rule["field_a"])
            val_b = answers.get(rule["field_b"])
            if val_a in rule["values_a"] and val_b in rule["values_b"]:
                issues.append(_make_issue(rule))

        elif rule_type == "field_inequality":
            val_a = answers.get(rule["field_a"])
            val_b = answers.get(rule["field_b"])
            if val_a and val_b and val_a != val_b:
                issues.append(_make_issue(rule))

        elif rule_type == "response_time":
            if response_time_seconds < rule["threshold_seconds"]:
                issues.append(_make_issue(rule))

    return issues
