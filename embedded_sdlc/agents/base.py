"""Shared Claude API call used by all SDLC agents."""
import anthropic
from config import MODEL, MAX_TOKENS, EMBEDDED_DOMAIN_PROMPT

_client = anthropic.Anthropic()


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
    """
    collected: list[str] = []

    with _client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": EMBEDDED_DOMAIN_PROMPT,
                "cache_control": {"type": "ephemeral"},   # shared cache anchor
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
        print()  # trailing newline
    return "".join(collected)
