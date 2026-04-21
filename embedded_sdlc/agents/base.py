"""Shared Claude API call used by all SDLC agents."""
import os
import time
import anthropic
from config import MODEL, MAX_TOKENS, EMBEDDED_DOMAIN_PROMPT

_RETRY_DELAYS = [30, 60, 120, 240]  # seconds between retries on rate-limit


def _make_client() -> anthropic.Anthropic:
    # Standard env var wins
    if os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic()
    # Claude Code session token (CLAUDE_SESSION_INGRESS_TOKEN_FILE)
    token_file = os.environ.get("CLAUDE_SESSION_INGRESS_TOKEN_FILE")
    if token_file:
        token = open(token_file).read().strip()
        return anthropic.Anthropic(auth_token=token)
    return anthropic.Anthropic()


_client = _make_client()


def call_agent(
    role_prompt: str,
    user_prompt: str,
    max_tokens: int = MAX_TOKENS,
    *,
    stream_output: bool = True,
) -> str:
    """
    Call claude-opus-4-7 with adaptive thinking and prompt caching.

    The EMBEDDED_DOMAIN_PROMPT is marked cache_control=ephemeral so it is
    reused across all agent calls within the same session.
    Retries automatically on RateLimitError with exponential back-off.
    """
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            print(f"\n[rate-limit] waiting {delay}s before retry {attempt}…", flush=True)
            time.sleep(delay)
        try:
            collected: list[str] = []
            with _client.messages.stream(
                model=MODEL,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": EMBEDDED_DOMAIN_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": role_prompt,
                    },
                ],
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    if stream_output:
                        print(text, end="", flush=True)
                    collected.append(text)

            if stream_output:
                print()
            return "".join(collected)

        except anthropic.RateLimitError:
            if attempt >= len(_RETRY_DELAYS):
                raise
            continue

    raise RuntimeError("Exhausted all retries")
