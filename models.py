from pydantic import BaseModel
from typing import Dict, List, Optional


class ValidateRequest(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    response_id: str
    source: str
    answers: Dict[str, str]
    response_time_seconds: int


class ValidationIssue(BaseModel):
    issue_type: str
    rule_name: str
    severity: str
    deduction: int
    field_names: List[str]
    ar_message: str
    ar_explanation: str
    ar_action_suggested: str


class ValidateResponse(BaseModel):
    response_id: str
    is_valid: bool
    confidence_score: int
    quality_level: str
    issues: List[ValidationIssue]


class CorrectionAction(BaseModel):
    field_name: str
    previous_value: str
    updated_value: str


class SubmitRequest(BaseModel):
    response_id: str
    source: str
    answers: Dict[str, str]
    response_time_seconds: int
    confidence_score: int
    quality_level: str
    issues: List[ValidationIssue]
    correction_actions: List[CorrectionAction] = []
    final_confirmed: bool = True
