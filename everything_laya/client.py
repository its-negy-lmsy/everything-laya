"""everything_laya.client - Zero-overhead Python SDK for self-hosted Laya.

Provides clean, typed, high-level primitives over Laya's ModernBERT reflex engine.
Zero external dependencies (uses standard library urllib).
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple, Union


DEFAULT_LAYA_URL = "http://127.0.0.1:8080"


class LayaError(Exception):
    """Base exception for Laya client errors."""
    pass


class LayaConnectionError(LayaError):
    """Raised when unable to reach the local Laya server."""
    pass


class LayaClient:
    """Client for local Laya System-1 reflex inference."""

    def __init__(self, base_url: str = DEFAULT_LAYA_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.predict_url = f"{self.base_url}/predict"
        self.health_url = f"{self.base_url}/health"
        self.timeout = timeout

    def is_alive(self) -> bool:
        """Check if the local Laya daemon is reachable and responding."""
        try:
            req = urllib.request.Request(self.health_url, headers={"User-Agent": "everything-laya"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 204)
        except Exception:
            # Fallback check against root or predict if /health is not implemented
            try:
                req = urllib.request.Request(self.base_url, headers={"User-Agent": "everything-laya"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    return resp.status < 500
            except Exception:
                return False

    def predict(
        self,
        state: Union[str, Dict[str, Any], List[Any]],
        questions: Dict[str, Any],
        model: Optional[str] = "english",
    ) -> Dict[str, Any]:
        """Low-level call to /predict with arbitrary state and multi-head questions."""
        payload: Dict[str, Any] = {
            "state": state,
            "questions": questions,
        }
        if model:
            payload["model"] = model

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.predict_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "everything-laya/0.1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise LayaConnectionError(
                f"Failed to connect to Laya server at {self.predict_url}. "
                f"Ensure the daemon is running (python run_server.py). Error: {e}"
            ) from e
        except Exception as e:
            raise LayaError(f"Prediction failed: {e}") from e

    def noul(self, state: Union[str, dict], instructions: str) -> Tuple[bool, float]:
        """Binary System-1 decision (True/False) with confidence score."""
        q = {
            "query": {
                "type": "noul",
                "instructions": instructions,
            }
        }
        res = self.predict(state=state, questions=q)
        ans = res.get("answers", {}).get("query", {})
        noul_val = float(ans.get("noul", 0.0))
        conf = float(ans.get("confidence", noul_val))
        return (noul_val >= 0.5, conf)

    def choose(
        self,
        state: Union[str, dict],
        instructions: str,
        criteria: Dict[str, str],
    ) -> Tuple[str, float]:
        """Select the best matching option from a criteria dictionary.
        
        Returns:
            (selected_key, confidence)
        """
        if not criteria:
            raise ValueError("Criteria dictionary cannot be empty.")
            
        q = {
            "selection": {
                "type": "choice",
                "instructions": instructions,
                "criteria": criteria,
            }
        }
        res = self.predict(state=state, questions=q)
        ans = res.get("answers", {}).get("selection", {})
        choice = ans.get("choice")
        probs = ans.get("probabilities", {})
        conf = float(probs.get(choice, 0.0)) if choice else 0.0
        return (str(choice), conf)

    def score(
        self,
        state: Union[str, dict],
        instructions: str,
        levels: List[str],
    ) -> Tuple[int, str, float]:
        """Rank or score the state across an ordered list of criteria levels.
        
        Returns:
            (index, level_label, confidence)
        """
        if not levels:
            raise ValueError("Levels list cannot be empty.")

        q = {
            "score_eval": {
                "type": "score",
                "instructions": instructions,
                "criteria": levels,
            }
        }
        res = self.predict(state=state, questions=q)
        ans = res.get("answers", {}).get("score_eval", {})
        idx = int(ans.get("score", 0))
        label = levels[idx] if 0 <= idx < len(levels) else levels[0]
        probs = ans.get("probabilities", [])
        conf = float(probs[idx]) if isinstance(probs, list) and 0 <= idx < len(probs) else 0.0
        return (idx, label, conf)
