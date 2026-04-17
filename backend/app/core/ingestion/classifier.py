"""Keyword-based clause classifier.

Local implementation of BaseClassifier using weighted keyword scoring.
Will be replaced by GeminiClassifier for GCP production.
"""

import logging
import re

from app.core.interfaces import BaseClassifier, ClassificationResult
from app.models.clause import ClauseType

logger = logging.getLogger(__name__)

# Weighted keyword mappings per clause type.
# Each keyword contributes its weight to the total score for that type.
CLAUSE_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    ClauseType.EXCLUSIVITY: [
        ("exclusive", 3.0),
        ("exclusivity", 3.0),
        ("sole right", 2.5),
        ("only supplier", 2.0),
        ("exclusive right", 3.0),
        ("non-exclusive", -2.0),  # negative weight — opposite signal
        ("sole and exclusive", 3.5),
    ],
    ClauseType.INDEMNITY: [
        ("indemnif", 3.0),
        ("hold harmless", 3.0),
        ("defend", 1.5),
        ("indemnification", 3.0),
        ("indemnity", 3.0),
        ("losses and damages", 2.0),
        ("shall indemnify", 3.5),
    ],
    ClauseType.TERMINATION: [
        ("terminat", 3.0),
        ("expir", 2.0),
        ("end of term", 2.5),
        ("notice period", 2.0),
        ("termination", 3.0),
        ("right to terminate", 3.0),
        ("upon termination", 2.5),
        ("cancel", 1.5),
    ],
    ClauseType.GOVERNING_LAW: [
        ("governed by", 3.0),
        ("jurisdiction", 2.5),
        ("courts of", 2.5),
        ("governing law", 3.5),
        ("applicable law", 2.5),
        ("laws of the state", 3.0),
        ("venue", 1.5),
        ("dispute resolution", 2.0),
    ],
    ClauseType.RENEWAL: [
        ("renew", 3.0),
        ("auto-renew", 3.5),
        ("extension", 2.0),
        ("successive", 2.0),
        ("renewal", 3.0),
        ("automatically renew", 3.5),
        ("option to renew", 3.0),
    ],
    ClauseType.PAYMENT: [
        ("payment", 2.5),
        ("compensation", 2.5),
        ("fee", 2.0),
        ("amount due", 2.5),
        ("invoice", 2.0),
        ("royalt", 2.5),
        ("net amount", 2.0),
        ("gross revenue", 2.0),
    ],
    ClauseType.IP_OWNERSHIP: [
        ("intellectual property", 3.5),
        ("copyright", 3.0),
        ("trademark", 3.0),
        ("patent", 2.5),
        ("license", 2.0),
        ("ownership of", 2.0),
        ("work product", 2.5),
        ("ip rights", 3.0),
    ],
    ClauseType.LIABILITY_CAP: [
        ("liability", 2.5),
        ("cap", 1.5),
        ("limitation of liability", 3.5),
        ("aggregate liability", 3.0),
        ("shall not exceed", 3.0),
        ("maximum liability", 3.5),
        ("consequential damages", 2.5),
        ("direct damages", 2.0),
    ],
    ClauseType.CONFIDENTIALITY: [
        ("confidential", 3.0),
        ("non-disclosure", 3.5),
        ("proprietary information", 3.0),
        ("trade secret", 3.0),
        ("confidentiality", 3.5),
        ("not disclose", 2.5),
        ("keep confidential", 3.0),
    ],
}

# Maximum possible score for normalization (sum of top positive weights)
MAX_SCORE_PER_TYPE = {
    ctype: sum(w for _, w in keywords if w > 0)
    for ctype, keywords in CLAUSE_KEYWORDS.items()
}

# Regex patterns for extracting entities
PARTY_PATTERN = re.compile(
    r"\b(?:between|by and between|party|parties)\b[:\s]+([A-Z][A-Za-z\s,&.]+?)(?:\(|,\s*a\b|\band\b)",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})\b"
)


class KeywordClassifier(BaseClassifier):
    """Classify clauses using weighted keyword matching.

    Scores each clause type by summing the weights of matched keywords,
    then returns the highest-scoring type with a normalized confidence.
    """

    async def classify(self, text: str) -> ClassificationResult:
        """Classify a raw clause text.

        Args:
            text: The raw text of the clause.

        Returns:
            ClassificationResult with the best-matching type.
        """
        return classify_clause(text)


def classify_clause(raw_text: str) -> ClassificationResult:
    """Classify a clause using keyword scoring.

    Args:
        raw_text: The raw text of the clause to classify.

    Returns:
        ClassificationResult with type, confidence, parties, dates.
    """
    text_lower = raw_text.lower()
    scores: dict[str, float] = {}

    for clause_type, keywords in CLAUSE_KEYWORDS.items():
        score = 0.0
        for keyword, weight in keywords:
            if keyword.lower() in text_lower:
                score += weight
        scores[clause_type] = max(score, 0.0)

    # Find best match
    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_type]

    if best_score == 0:
        clause_type = ClauseType.OTHER
        confidence = 0.0
    else:
        clause_type = ClauseType(best_type)
        max_possible = MAX_SCORE_PER_TYPE.get(best_type, 1.0)
        confidence = min(best_score / max_possible, 1.0)

    # Extract entities
    parties = [m.group(1).strip() for m in PARTY_PATTERN.finditer(raw_text)]
    dates = DATE_PATTERN.findall(raw_text)

    logger.debug(
        "Classified as %s (confidence=%.2f, score=%.1f)",
        clause_type,
        confidence,
        best_score,
    )

    return ClassificationResult(
        clause_type=clause_type.value,
        confidence=confidence,
        extracted_parties=parties,
        extracted_dates=dates,
    )
