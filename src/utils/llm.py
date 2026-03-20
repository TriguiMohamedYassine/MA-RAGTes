from langchain_openai import ChatOpenAI
import os
import random
import time
from dotenv import load_dotenv

load_dotenv()

_LLM_STATS = {
    "calls": 0,
    "total_time_seconds": 0.0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
}

def get_llm():
    llm_model = os.getenv("LLM_MODEL", "codestral-latest")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    mistral_base_url = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
    mistral_api_key = os.getenv("MISTRAL_API_KEY", "")

    if not mistral_api_key:
        raise ValueError(
            "Missing MISTRAL_API_KEY environment variable for Codestral API access."
        )

    # Request JSON object responses from the model.
    return ChatOpenAI(
        model=llm_model,
        temperature=temperature,
        api_key=mistral_api_key,
        base_url=mistral_base_url,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def reset_llm_stats():
    _LLM_STATS["calls"] = 0
    _LLM_STATS["total_time_seconds"] = 0.0
    _LLM_STATS["prompt_tokens"] = 0
    _LLM_STATS["completion_tokens"] = 0
    _LLM_STATS["total_tokens"] = 0


def get_llm_stats():
    return {
        "calls": _LLM_STATS["calls"],
        "total_time_seconds": round(_LLM_STATS["total_time_seconds"], 3),
        "prompt_tokens": _LLM_STATS["prompt_tokens"],
        "completion_tokens": _LLM_STATS["completion_tokens"],
        "total_tokens": _LLM_STATS["total_tokens"],
    }


def _extract_token_usage(result):
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None

    usage_metadata = getattr(result, "usage_metadata", None)
    if isinstance(usage_metadata, dict):
        prompt_tokens = usage_metadata.get("input_tokens")
        completion_tokens = usage_metadata.get("output_tokens")
        total_tokens = usage_metadata.get("total_tokens")

    response_metadata = getattr(result, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage", {})
        if isinstance(token_usage, dict):
            prompt_tokens = token_usage.get("prompt_tokens", prompt_tokens)
            completion_tokens = token_usage.get("completion_tokens", completion_tokens)
            total_tokens = token_usage.get("total_tokens", total_tokens)

    if total_tokens is None and isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        total_tokens = prompt_tokens + completion_tokens

    return prompt_tokens, completion_tokens, total_tokens


def _is_rate_limited_error(error):
    message = str(error).lower()
    return (
        "429" in message
        or "rate limit" in message
        or "rate_limited" in message
        or "too many requests" in message
    )


def _compute_retry_delay(attempt, default_delay_seconds, is_rate_limited):
    if is_rate_limited:
        base = float(os.getenv("LLM_RATE_LIMIT_BASE_DELAY_SECONDS", "2.0"))
        cap = float(os.getenv("LLM_RATE_LIMIT_MAX_DELAY_SECONDS", "30.0"))
        jitter = random.uniform(0.0, base * 0.3)
        return min(cap, (base * (2 ** (attempt - 1))) + jitter)

    return default_delay_seconds * attempt


def invoke_with_retry(chain, payload, retries=3, delay_seconds=1.0):
    """Invoke a chain with lightweight retries for transient API failures."""
    retries = int(os.getenv("LLM_RETRIES", str(retries)))
    delay_seconds = float(os.getenv("LLM_RETRY_DELAY_SECONDS", str(delay_seconds)))

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            started = time.perf_counter()
            result = chain.invoke(payload)
            elapsed = time.perf_counter() - started

            prompt_tokens, completion_tokens, total_tokens = _extract_token_usage(result)

            _LLM_STATS["calls"] += 1
            _LLM_STATS["total_time_seconds"] += elapsed
            if isinstance(prompt_tokens, int):
                _LLM_STATS["prompt_tokens"] += prompt_tokens
            if isinstance(completion_tokens, int):
                _LLM_STATS["completion_tokens"] += completion_tokens
            if isinstance(total_tokens, int):
                _LLM_STATS["total_tokens"] += total_tokens

            return result
        except Exception as e:
            last_error = e
            if attempt < retries:
                is_rate_limited = _is_rate_limited_error(e)
                sleep_for = _compute_retry_delay(attempt, delay_seconds, is_rate_limited)
                reason = "rate-limited" if is_rate_limited else "transient-error"
                print(
                    f"LLM invoke failed (attempt {attempt}/{retries}, {reason}): {e}. "
                    f"Retrying in {sleep_for:.2f}s"
                )
                time.sleep(sleep_for)
    raise last_error
