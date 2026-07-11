from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResolution:
    issue_type: str
    confidence: float
    matched_signals: tuple[str, ...]


_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "priority_policy_exception",
        (
            r"\b(priority|vip)\b.*\b(skip|bypass|exception|release)\b",
            r"\b(skip|bypass)\b.*\b(verification|kyc|policy)\b",
        ),
    ),
    (
        "cross_account_access",
        (
            r"\b(other|another|different) account\b",
            r"\b(other|different) (email|address)\b",
            r"\bbalance\b.*\b(other|another)\b",
        ),
    ),
    (
        "verification_restriction",
        (
            r"\b(kyc|verification|verify|selfie|identity document)\b",
            r"\b(restricted|blocked|unblock)\b.*\baccount\b",
            r"\baccount\b.*\b(restricted|blocked|unblock)\b",
        ),
    ),
    (
        "bonus_dispute",
        (
            r"\b(bonus|promo|promocode|reward|offer)\b",
        ),
    ),
    (
        "deposit_missing",
        (
            r"\b(deposit|upi)\b",
            r"\b(payment|transaction)\b.*\b(missing|not visible|not showing|pending)\b",
        ),
    ),
    (
        "withdrawal_processed_missing",
        (
            r"\b(withdrawal|withdraw|utr)\b",
            r"\b(bank)\b.*\b(not received|cannot find|missing|trace)\b",
        ),
    ),
)


def resolve_customer_support_intent(query: str | None) -> IntentResolution | None:
    normalized = " ".join((query or "").lower().split())
    if not normalized:
        return None

    for issue_type, patterns in _INTENT_RULES:
        matched = tuple(pattern for pattern in patterns if re.search(pattern, normalized))
        if matched:
            confidence = min(0.98, 0.82 + (0.08 * (len(matched) - 1)))
            return IntentResolution(issue_type=issue_type, confidence=confidence, matched_signals=matched)
    return None
