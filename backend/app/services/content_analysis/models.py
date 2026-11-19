from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Word:
    start: float; end: float; text: str

@dataclass
class Segment:
    start: float; end: float; text: str
    words: List[Word] = field(default_factory=list)

@dataclass
class Transcript:
    segments: List[Segment]
    @property
    def duration(self): return self.segments[-1].end if self.segments else 0.0
    def text_between(self, a, b):
        return " ".join(s.text.strip() for s in self.segments if s.end > a and s.start < b)

@dataclass
class Candidate:
    start: float; end: float
    hook: str = ""; main_message: str = ""; why: str = ""
    audience: str = ""; title: str = ""; titles: List[str] = field(default_factory=list)
    caption: str = ""; edit_style: str = ""; category: str = ""
    llm_scores: dict = field(default_factory=dict)   # 0-10 per dimension
    score: float = 0.0; score_breakdown: dict = field(default_factory=dict)
    penalties: dict = field(default_factory=dict)
    heur: float = 0.0; viral_pct: float = 0.0; quality: float = 0.0
    sources: int = 1
    @property
    def duration(self): return self.end - self.start
