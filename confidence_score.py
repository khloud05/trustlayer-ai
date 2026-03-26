def calculate_score(issues: list) -> int:
    total_deduction = sum(issue.get("deduction", 0) for issue in issues)
    score = max(0, min(100, 100 - total_deduction))
    return score


def get_quality_level(score: int) -> str:
    if score >= 90:
        return "High"
    elif score >= 70:
        return "Medium"
    else:
        return "Low"
