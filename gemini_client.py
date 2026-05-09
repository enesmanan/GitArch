import os
import re
import time
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3-flash-preview"
THINKING_LEVEL = types.ThinkingLevel.MINIMAL  # Lowest. If tool-using agents underperform, try LOW.
MAX_RETRIES = 5
RETRYABLE_CODES = {"429", "500", "503"}
RETRYABLE_MESSAGES = {
    "server disconnected",
    "connection reset",
    "connection error",
    "read timeout",
    "remote end closed",
    "eof occurred",
}
logger = logging.getLogger(__name__)

_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]:\s*['\"](\d+)")


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        any(code in msg for code in RETRYABLE_CODES)
        or any(phrase in msg for phrase in RETRYABLE_MESSAGES)
    )


def _parse_retry_delay(exc: Exception) -> float | None:
    """Extract the server-suggested retry delay from a 429 error message."""
    match = _RETRY_DELAY_RE.search(str(exc))
    if match:
        return float(match.group(1))
    return None


def _get_delay(attempt: int, exc: Exception) -> float:
    server_delay = _parse_retry_delay(exc)
    if server_delay is not None:
        return server_delay + 2  # small buffer on top of server-suggested delay
    return min(4 * (2 ** attempt), 60)  # exponential backoff capped at 60s


def _extract_text(candidate) -> str:
    """Extract only real text parts from a response, skipping thinking/thought parts."""
    texts = []
    if not candidate or not candidate.content or not candidate.content.parts:
        return ""
    for part in candidate.content.parts:
        if hasattr(part, "thought") and part.thought:
            continue
        if hasattr(part, "text") and part.text is not None:
            texts.append(part.text)
    return "".join(texts)


class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise ValueError("GEMINI_API_KEY not set in .env file")
        self.client = genai.Client(api_key=api_key)

    def _call_with_retry(self, fn, label: str = "API call"):
        for attempt in range(MAX_RETRIES + 1):
            try:
                return fn()
            except Exception as e:
                if attempt < MAX_RETRIES and _is_retryable(e):
                    delay = _get_delay(attempt, e)
                    logger.warning(
                        f"{label}: retry {attempt + 1}/{MAX_RETRIES} "
                        f"waiting {delay:.0f}s — {type(e).__name__}"
                    )
                    time.sleep(delay)
                else:
                    raise

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._call_with_retry(
                lambda: self.client.models.generate_content(
                    model=MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3,
                        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
                    ),
                ),
                label="generate",
            )
            return _extract_text(response.candidates[0])
        except Exception as e:
            logger.error(f"LLM generate error: {e}")
            return f"*Analysis failed: {e}*"

    def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_declarations: list,
        tool_executor,
        max_steps: int = 10,
    ) -> str:
        try:
            return self._tool_loop(
                system_prompt, user_prompt, tool_declarations, tool_executor, max_steps
            )
        except Exception as e:
            logger.error(f"LLM tool-calling error: {e}")
            return f"*Analysis failed: {e}*"

    def _tool_loop(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_declarations: list,
        tool_executor,
        max_steps: int,
    ) -> str:
        tools = types.Tool(function_declarations=tool_declarations)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            )
        ]

        accumulated_text = ""

        for step in range(max_steps):
            response = self._call_with_retry(
                lambda: self.client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=[tools],
                        temperature=0.3,
                        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
                    ),
                ),
                label=f"tool_loop step {step + 1}",
            )

            if not response.candidates:
                return accumulated_text
            candidate = response.candidates[0]
            parts = candidate.content.parts if candidate.content else []

            text_this_turn = _extract_text(candidate)
            if text_this_turn:
                accumulated_text = text_this_turn

            fn_call = None
            for part in parts:
                if hasattr(part, "function_call") and part.function_call:
                    fn_call = part.function_call
                    break

            if fn_call is None:
                return accumulated_text

            args = dict(fn_call.args) if fn_call.args is not None else {}
            result = tool_executor.execute(fn_call.name, args)

            contents.append(candidate.content)
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=fn_call.name,
                            response={"result": str(result)},
                        )
                    ],
                )
            )

        if accumulated_text:
            return accumulated_text

        # max_steps exhausted with no final text — ask model for a summary without tools
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(
                    text="Please provide your final answer now based on all the information gathered."
                )],
            )
        )
        response = self._call_with_retry(
            lambda: self.client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
                ),
            ),
            label="tool_loop final",
        )
        if response.candidates:
            return _extract_text(response.candidates[0])
        return accumulated_text
