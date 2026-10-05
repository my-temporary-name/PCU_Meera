"""The model call of the text layer: OpenRouter through the OpenAI SDK, timeout from config, SDK retries 0. The key is read from the environment and never printed."""

import os
import time


def make_client(text_cfg: dict):
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv()
    return OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1", timeout=float(text_cfg["timeout_seconds"]), max_retries=int(text_cfg["sdk_retries"]))


def call(client, text_cfg: dict, messages: list[dict]) -> tuple[str | None, dict, str | None]:
    """One call. Returns (text, usage, error); usage always has wall seconds, and tokens (input, output, reasoning) when the call returned."""
    t0 = time.monotonic()
    try:
        resp = client.chat.completions.create(model=text_cfg["model"], messages=messages, response_format={"type": "json_object"},
                                              extra_body={"reasoning": {"effort": text_cfg["reasoning_effort"]}})
    except Exception as e:                                                   # timeout, 4xx / 5xx, connection: a failed attempt
        return None, {"wall_seconds": round(time.monotonic() - t0, 2)}, f"{type(e).__name__}: {str(e)[:200]}"
    u = resp.usage
    d = getattr(u, "completion_tokens_details", None)
    usage = {"input_tokens": getattr(u, "prompt_tokens", None), "output_tokens": getattr(u, "completion_tokens", None),
             "reasoning_tokens": getattr(d, "reasoning_tokens", None) if d else None, "wall_seconds": round(time.monotonic() - t0, 2)}
    return resp.choices[0].message.content, usage, None
