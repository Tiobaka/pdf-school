import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ContentChunk(BaseModel):
    chunk_id: str
    source_file: str
    page_start: int
    page_end: int
    section_title: str | None = None
    text: str
    figures: list[str] = Field(default_factory=list)


class ExamStyleProfile(BaseModel):
    style_name: str = "default_mastery"
    stem_type: str = "vignette"  # "direct_recall", "short_vignette", "long_case"
    option_count: int = 5
    allows_negative_stems: bool = False
    allows_multiple_select: bool = False
    focus_areas: list[str] = Field(default_factory=list)
    exemplars: list[dict[str, str]] = Field(default_factory=list)
    system_prompt_override: str | None = None


class QBankQuestion(BaseModel):
    id: str
    topic: str
    subtopic: str | None = None
    source_ref: dict[str, str] = Field(default_factory=dict)
    difficulty_hammer: int = Field(default=3, ge=1, le=5)
    cognitive_level: str = "2nd_order_application"  # "1st_order_recall", "2nd_order_application", "3rd_order_synthesis"
    figures: list[str] = Field(default_factory=list)
    vignette: str
    lead_in: str
    options: dict[str, str]
    correct_key: str
    educational_objective: str
    distractor_analysis: dict[str, str]
    refutational_hints: dict[str, str] = Field(default_factory=dict)
    comparison_table: str | None = None

    @model_validator(mode="after")
    def verify_correct_key_exists(self) -> "QBankQuestion":
        if self.correct_key not in self.options:
            raise ValueError(
                f"correct_key '{self.correct_key}' must be present in options: {list(self.options.keys())}"
            )
        return self


class HistoryRecord(BaseModel):
    record_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    question_id: str
    selected_key: str
    correct_key: str
    is_correct: bool
    time_spent_seconds: float
    confidence_rating: str = "certain"  # "certain", "educated_guess", "blind_guess"
    switched_answer: bool = False
    original_selection: str | None = None
    error_category: str | None = None  # "knowledge_gap", "misconception", "execution_error"
    user_note: str | None = None
    fsrs_state: dict[str, Any] | None = None

    def compute_record_id(self) -> str:
        if self.record_id:
            return self.record_id
        raw = f"{self.timestamp}|{self.question_id}|{self.selected_key}|{self.time_spent_seconds}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class DailySchedule(BaseModel):
    date: str
    due_reviews: list[str] = Field(default_factory=list)
    new_questions: list[str] = Field(default_factory=list)
    target_date: str | None = None
