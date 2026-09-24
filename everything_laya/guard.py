"""everything_laya.guard - Sub-35ms security & action safety guard for coding agents.

Protects filesystems, databases, and git histories from dangerous autonomous tool executions.
Combines 0.0ms hard deterministic filters with sub-35ms Laya ModernBERT System-1 probabilistic gating.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from everything_laya.client import LayaClient, DEFAULT_LAYA_URL


# Critical patterns that must be blocked with 0.0ms latency without needing model inference
CRITICAL_PATTERNS = [
    re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f?|-f?[a-zA-Z]*r)\s+[/~]", re.I),
    re.compile(r"\brmdir\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=.*of=/dev/(sd[a-z]|nvme|disk)", re.I),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.I),
    re.compile(r"\b(DROP\s+DATABASE|DROP\s+SCHEMA|TRUNCATE\s+TABLE)\b", re.I),
    re.compile(r"\bgit\s+push\b(?=.*(\s--force|\s-f\b))(?=.*(\smain|\smaster\b))", re.I),
    re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|powershell|pwsh)\b", re.I),
    re.compile(r"\b(npm|yarn|pnpm)\s+publish\s+--force\b", re.I),
]

# Warning patterns: safe in development but should alert or require confirmation in production
WARN_PATTERNS = [
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-fdx?\b", re.I),
    re.compile(r"\bDROP\s+TABLE\b", re.I),
    re.compile(r"\bDELETE\s+FROM\b(?!\s+WHERE\b)", re.I),
    re.compile(r"\bchmod\s+(-R\s+)?777\b", re.I),
]


@dataclass
class GuardDecision:
    command: str
    disposition: str  # ALLOW | WARN | BLOCK
    risk_score: int   # 0 (harmless), 1 (safe mod), 2 (elevated), 3 (destructive)
    risk_label: str
    confidence: float
    latency_ms: float
    reason: str
    is_hard_override: bool = False

    @property
    def is_allowed(self) -> bool:
        return self.disposition == "ALLOW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LayaGuard:
    """Intelligent action & command safety guard for agents."""

    def __init__(self, client: Optional[LayaClient] = None, base_url: str = DEFAULT_LAYA_URL):
        self.client = client or LayaClient(base_url=base_url)

    def check(self, command: str) -> GuardDecision:
        """Evaluate whether a shell command or tool invocation is safe to execute."""
        cmd_clean = command.strip()
        t0 = time.perf_counter()

        # 1. 0.0ms Deterministic Hard Safety Filters
        for pat in CRITICAL_PATTERNS:
            if pat.search(cmd_clean):
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return GuardDecision(
                    command=cmd_clean,
                    disposition="BLOCK",
                    risk_score=3,
                    risk_label="destructive, irreversible, or security risk",
                    confidence=1.0,
                    latency_ms=elapsed_ms,
                    reason=f"Matched critical safety rule: {pat.pattern}",
                    is_hard_override=True,
                )

        for pat in WARN_PATTERNS:
            if pat.search(cmd_clean):
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return GuardDecision(
                    command=cmd_clean,
                    disposition="WARN",
                    risk_score=2,
                    risk_label="elevated modification or config change",
                    confidence=1.0,
                    latency_ms=elapsed_ms,
                    reason=f"Matched caution rule: {pat.pattern}",
                    is_hard_override=True,
                )

        # 2. Sub-35ms Probabilistic Laya System-1 Reflex Evaluation
        state_payload = {
            "command": cmd_clean,
            "type": "shell_or_tool_execution",
        }

        questions_payload = {
            "risk": {
                "type": "score",
                "instructions": f"What is the safety risk level of executing this command: `{cmd_clean}`?",
                "criteria": [
                    "harmless inspection or read-only (ls, git status, cat, pwd, echo, pytest)",
                    "safe modification or file creation (mkdir, touch, writing code, formatting)",
                    "elevated modification or config change (pip install, git checkout, deleting single file)",
                    "destructive, irreversible, or security risk (rm -rf, formatting disk, dropping db, force push)",
                ],
            },
            "disposition": {
                "type": "choice",
                "instructions": f"Should an autonomous agent execute this command: `{cmd_clean}`?",
                "criteria": {
                    "ALLOW": "safe to execute automatically without interruption",
                    "WARN": "requires user confirmation or review before proceeding",
                    "BLOCK": "dangerous, destructive, or security risk",
                },
            },
        }

        try:
            res = self.client.predict(state=state_payload, questions=questions_payload)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            answers = res.get("answers", {})
            risk_ans = answers.get("risk", {})
            disp_ans = answers.get("disposition", {})

            risk_score = int(risk_ans.get("score", 0))
            criteria_levels = questions_payload["risk"]["criteria"]
            risk_label = criteria_levels[risk_score] if 0 <= risk_score < len(criteria_levels) else "unknown"

            disposition = str(disp_ans.get("choice", "ALLOW"))
            probs = disp_ans.get("probabilities", {})
            confidence = float(probs.get(disposition, 0.9))

            # Safety fallback: elevated risk score forces at least WARN
            if risk_score >= 3 and disposition == "ALLOW":
                disposition = "BLOCK"
            elif risk_score == 2 and disposition == "ALLOW":
                disposition = "WARN"

            return GuardDecision(
                command=cmd_clean,
                disposition=disposition,
                risk_score=risk_score,
                risk_label=risk_label,
                confidence=confidence,
                latency_ms=elapsed_ms,
                reason=f"Laya System-1 evaluated risk={risk_score} ({risk_label})",
                is_hard_override=False,
            )

        except Exception as e:
            # Fallback if server is not reachable: default allow benign inspection, warn everything else
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            is_read_only = bool(re.match(r"^(git\s+status|git\s+diff|git\s+log|ls|dir|cat|type|pwd|echo|find|grep)\b", cmd_clean, re.I))
            disp = "ALLOW" if is_read_only else "WARN"
            return GuardDecision(
                command=cmd_clean,
                disposition=disp,
                risk_score=0 if is_read_only else 1,
                risk_label="heuristic fallback (laya server offline)",
                confidence=0.7,
                latency_ms=elapsed_ms,
                reason=f"Heuristic fallback: {e}",
                is_hard_override=False,
            )
