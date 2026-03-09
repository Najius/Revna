"""Revna — Claude API calls, validation, and AI adaptation.

Adapted from coach/ai.py:
- httpx instead of urllib.request
- Settings instead of file-based API key
- Async-ready (still sync for now, will be async in Phase 3)
"""

import json
import logging
import time

import httpx

from backend.config import settings
from backend.core.prompts import (
    ANTI_HALLUCINATION_SUFFIX,
    validate_ai_message,
    strip_hallucination_sentences,
)

logger = logging.getLogger(__name__)


# ─── Claude API calls ────────────────────────────────────────────────────────

def call_claude_api(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int | None = None,
) -> dict | None:
    """Call Claude API and return parsed JSON response. Returns None on failure."""
    api_key = settings.anthropic_api_key
    if not api_key:
        logger.error("No Anthropic API key configured")
        return None

    payload = {
        "model": model or settings.claude_model_sonnet,
        "max_tokens": max_tokens or settings.claude_max_tokens,
        "temperature": 0.3,
        "system": [
            {"type": "text", "text": system_prompt,
             "cache_control": {"type": "ephemeral"}},
        ],
        "messages": [{"role": "user", "content": user_prompt}],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = httpx.post(
                settings.claude_api_url,
                json=payload,
                headers=headers,
                timeout=90,
            )
            resp.raise_for_status()
            result = resp.json()
            text = result.get("content", [{}])[0].get("text", "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return json.loads(text.strip())
        except httpx.HTTPError:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            logger.exception("Claude API request failed after retries")
            return None
        except (json.JSONDecodeError, KeyError, IndexError):
            logger.exception("Claude API response parse error")
            return None


def call_claude_notification(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 300,
    temperature: float = 0.4,
) -> str | None:
    """Call Claude API for a notification with hallucination retry."""
    text = _call_claude_once(system_prompt, user_prompt, max_tokens, temperature)
    if not text:
        return None

    is_valid, pattern = validate_ai_message(text)
    if is_valid:
        return text

    logger.warning("Hallucination detected: '%s' — retrying", pattern)
    retry_prompt = user_prompt + ANTI_HALLUCINATION_SUFFIX.format(pattern=pattern)
    text2 = _call_claude_once(system_prompt, retry_prompt, max_tokens, temperature)
    if not text2:
        return text

    is_valid2, pattern2 = validate_ai_message(text2)
    if is_valid2:
        logger.info("Retry succeeded — hallucination fixed")
        return text2

    logger.warning("Retry still has '%s' — stripping bad sentences", pattern2)
    cleaned = strip_hallucination_sentences(text2)
    return cleaned if cleaned.strip() else text


def _call_claude_once(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str | None:
    """Single Claude API call for notifications (uses Haiku)."""
    api_key = settings.anthropic_api_key
    if not api_key:
        return None

    payload = {
        "model": settings.claude_model_haiku,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": [
            {"type": "text", "text": system_prompt,
             "cache_control": {"type": "ephemeral"}},
        ],
        "messages": [{"role": "user", "content": user_prompt}],
    }

    try:
        resp = httpx.post(
            settings.claude_api_url,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        text = result.get("content", [{}])[0].get("text", "")
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = "\n".join(text.split("\n")[:-1])
        return text.strip() if text else None
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error("Claude API error: %s", e)
        return None


# ─── Response validation ─────────────────────────────────────────────────────

def validate_ai_response(ai_result: dict | None) -> bool:
    """Validate Claude's response: correct format."""
    if not ai_result or not isinstance(ai_result, dict):
        return False
    workouts = ai_result.get("workouts")
    if not isinstance(workouts, list) or not workouts:
        return False
    if not ai_result.get("adaptation_summary"):
        return False

    for w in workouts:
        for field in ("name", "sport", "type", "duration_minutes", "human_readable"):
            if field not in w:
                return False

    return True
