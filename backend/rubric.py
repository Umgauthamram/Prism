from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class RubricResult:
    score: float
    reasoning: str
    dimensions: Dict[str, float]

class PrismRubric:
    """
    OpenEnv-compliant Rubric system for Prism.
    Evaluates agents on Accuracy, Reliability, and Efficiency.
    """
    def __init__(self, name: str):
        self.name = name
        self.dimensions = ["Accuracy", "Reliability", "Efficiency"]

    def _clamp(self, x: float) -> float:
        return max(0.001, min(0.999, x))

    def evaluate(self, answer: str, task_data: dict, history: List[dict] = None) -> RubricResult:
        # Default implementation
        return RubricResult(score=self._clamp(0.1), reasoning="Base evaluation", dimensions={"Accuracy": self._clamp(0.1), "Reliability": self._clamp(0.1), "Efficiency": self._clamp(0.1)})

class DebuggingRubric(PrismRubric):
    def evaluate(self, answer: str, task_data: dict, history: List[dict] = None) -> RubricResult:
        answer_lower = answer.lower()
        dims = {"Accuracy": 0.1, "Reliability": 0.5, "Efficiency": 0.5}
        
        # Accuracy Dimension
        keywords = task_data.get("fix_keywords", [])
        matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
        if keywords:
            dims["Accuracy"] = round(min(0.9, 0.1 + (matches / len(keywords)) * 0.8), 2)
            
        # Reliability Dimension (Inferred from answer quality/detail)
        if any(kw in answer_lower for kw in ["added", "fixed", "check", "edge case"]):
            dims["Reliability"] += 0.2
            
        # Overall Score (Weighted)
        total_score = 0.6 * dims["Accuracy"] + 0.2 * dims["Reliability"] + 0.2 * dims["Efficiency"]
        
        return RubricResult(
            score=self._clamp(round(total_score, 3)),
            reasoning=f"Matched {matches}/{len(keywords)} fix keywords.",
            dimensions={k: self._clamp(v) for k, v in dims.items()}
        )

class MarketResearchRubric(PrismRubric):
    def evaluate(self, answer: str, task_data: dict, history: List[dict] = None) -> RubricResult:
        answer_lower = answer.lower()
        dims = {"Accuracy": 0.1, "Reliability": 0.1, "Efficiency": 0.1}
        
        # Word count contribution
        word_count = len(answer.split())
        dims["Accuracy"] = min(0.9, word_count / 100.0)
        
        # Citations contribution
        if any(kw in answer_lower for kw in ["source:", "http", "cited"]):
            dims["Reliability"] += 0.4
            
        # Confidence contribution
        if "confidence:" in answer_lower:
            dims["Efficiency"] += 0.4
            
        total_score = 0.5 * dims["Accuracy"] + 0.3 * dims["Reliability"] + 0.2 * dims["Efficiency"]
        
        return RubricResult(
            score=self._clamp(round(total_score, 3)),
            reasoning=f"Report length: {word_count} words with citations.",
            dimensions={k: self._clamp(v) for k, v in dims.items()}
        )
