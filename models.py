from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Issue:
    key: str
    rule: str
    severity: str
    component: str       # "patient-repo:main.py"
    file_path: str       # "main.py"
    line: int
    message: str
    type: str
    tags: List[str]
    source_code: str     # full file source

@dataclass
class FixResult:
    fixed_code: str      # the complete fixed file
    explanation: str     # what was changed and why

@dataclass
class TestResult:
    test_code: str       # the pytest test code
    passed: bool         # did the tests pass?
    output: str          # stdout/stderr from test execution

@dataclass
class ReviewResult:
    readability_score: int   # 1-10
    maintainability_score: int
    suggestions: List[str]
    is_acceptable: bool

@dataclass
class EvalResult:
    correctness: int     # 1-10
    safety: int          # 1-10
    readability: int     # 1-10
    overall_score: float # weighted average
    verdict: str         # "PASS" | "RETRY" | "FAIL"
    reasoning: str

@dataclass
class PipelineResult:
    issue: Issue
    fix: FixResult
    test: TestResult
    review: ReviewResult
    evaluation: EvalResult
    attempts: int
