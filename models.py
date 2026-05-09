from dataclasses import dataclass
from typing import List, Optional, Literal
from pydantic import BaseModel, computed_field

@dataclass
class Issue:
    key: str
    rule: str
    severity: str
    component: str       
    file_path: str      
    line: int
    message: str
    type: str
    tags: List[str]
    source_code: str     

@dataclass
class FixResult:
    fixed_code: str      
    explanation: str     

@dataclass
class TestResult:
    test_code: str      
    passed: bool         
    output: str          

class ReviewResult(BaseModel):
    readability_score: int
    maintainability_score: int
    suggestions: List[str]
    is_acceptable: bool

class EvalResult(BaseModel):
    correctness_score: int
    safety_score: int
    readability_score: int
    verdict: Literal["PASS", "RETRY", "FAIL"]
    reasoning: str

    @computed_field
    @property
    def overall_score(self) -> float:
        return round((self.correctness_score + self.safety_score + self.readability_score) / 3.0, 1)

@dataclass
class PipelineResult:
    issue: Issue
    fix: FixResult
    test: TestResult
    review: ReviewResult
    evaluation: EvalResult
    attempts: int
