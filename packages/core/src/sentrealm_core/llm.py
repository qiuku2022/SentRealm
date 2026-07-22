"""LLM client protocol and implementations (ADR-005)."""

from __future__ import annotations

import logging
import math
import os
import re
from typing import Protocol

from sentrealm_core.models import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是中文口播断句助手。任务：把用户给出的一行文本切成多行，便于朗读与字幕匹配。"
    "必须遵守："
    "1. 只切分，不改写：不得增删改任何字，标点也保持原样（仅通过换行切分）。"
    "2. 切在语义完整处：意群、短语、并列、分句成分之间；可以在长句中间断开，"
    "但避免无意义的碎句（不要一个字一行）。"
    "3. 符合现代汉语语法与口播习惯：每行读起来自然，不要拆破固定搭配。"
    "4. 英文与数字：不要在英文单词中间断开。"
    "用户会给出参考上限 N 字：尽量让每行不超过 N，但若语义需要可略超；优先保证语义与守恒。"
    "输出：仅输出切分后的多行文本，每行一条，不要编号、不要解释。"
)

_SECTION_RE = re.compile(r"^###\s*(\d+)\s*$")


class LlmClient(Protocol):
    """Break one or more over-length lines without rewriting wording."""

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[list[str]]: ...


def llm_api_key() -> str | None:
    key = os.environ.get("SENTREALM_LLM_API_KEY", "").strip()
    return key or None


def is_llm_configured(settings: Settings) -> bool:
    """True when settings and env satisfy ADR-005 enablement conditions."""
    return (
        settings.llm_enabled
        and bool(settings.llm_endpoint.strip())
        and bool(settings.llm_model.strip())
        and llm_api_key() is not None
    )


class MockLlmClient:
    """Deterministic splitter for unit tests (dependency injection only)."""

    def __init__(self, *, bad_results_before_ok: int = 0) -> None:
        """If bad_results_before_ok > 0, first N break_lines calls return failing splits."""
        self._bad_remaining = bad_results_before_ok
        self.calls: list[list[str]] = []

    def break_line(
        self,
        line: str,
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[str]:
        return self.break_lines([line], max_chars, min_chars=min_chars)[0]

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[list[str]]:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        self.calls.append(list(lines))
        if self._bad_remaining > 0:
            self._bad_remaining -= 1
            return [_corrupt_split(line) for line in lines]
        return [_balanced_split(line, max_chars, min_chars=min_chars) for line in lines]

    def ping(self) -> None:
        """No-op for tests; connectivity is exercised via break_lines when needed."""


def _corrupt_split(line: str) -> list[str]:
    """Intentionally break conservation so quality_ok fails."""
    if not line:
        return [""]
    return [line[:-1] + ("X" if not line.endswith("X") else "Y")]


def _balanced_split(
    line: str,
    max_chars: int,
    *,
    min_chars: int | None = None,
) -> list[str]:
    from sentrealm_core.pipeline.line_count import count_line_chars, index_after_char_count
    from sentrealm_core.pipeline.llm_quality import llm_quality_ok, resolve_min_chars

    if count_line_chars(line) <= max_chars:
        return [line]

    floor = resolve_min_chars(max_chars, min_chars)
    segments: list[str] = []
    remaining = line
    while count_line_chars(remaining) > max_chars:
        total = count_line_chars(remaining)
        segments_needed = max(1, math.ceil(total / max_chars))
        ideal = total / segments_needed
        target = int(round(ideal))
        target = min(max_chars, max(floor, target))
        if segments_needed > 1:
            max_left = total - floor
            target = min(target, max_left, max_chars)
            target = max(target, floor)
        cut = index_after_char_count(remaining, target)
        if cut <= 0 or cut >= len(remaining):
            cut = index_after_char_count(remaining, max_chars)
        left = remaining[:cut].rstrip()
        remaining = remaining[cut:].lstrip()
        if not left:
            break
        segments.append(left)
    if remaining:
        segments.append(remaining)

    if llm_quality_ok(line, segments):
        return segments
    return _greedy_max_split(line, max_chars)


def _greedy_max_split(line: str, max_chars: int) -> list[str]:
    from sentrealm_core.pipeline.line_count import count_line_chars, index_after_char_count

    segments: list[str] = []
    remaining = line
    while count_line_chars(remaining) > max_chars:
        cut = index_after_char_count(remaining, max_chars)
        segments.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        segments.append(remaining)
    return segments


def format_llm_connection_error(exc: Exception) -> str:
    """Map LLM client failures to user-facing Chinese messages."""
    from openai import APIConnectionError, APITimeoutError, AuthenticationError

    if isinstance(exc, APITimeoutError):
        return "连接 LLM 超时，请检查端点地址与服务是否已启动。"
    if isinstance(exc, APIConnectionError):
        return "无法连接 LLM 端点，请检查地址、端口与网络。"
    if isinstance(exc, AuthenticationError):
        return "LLM 认证失败，请检查 SENTREALM_LLM_API_KEY 是否与端点要求一致。"

    status_code = getattr(exc, "status_code", None)
    if status_code == 401:
        return "LLM 认证失败，请检查 SENTREALM_LLM_API_KEY 是否与端点要求一致。"
    if status_code == 404:
        return "LLM 模型或端点路径不存在，请检查 llm_model 与 llm_endpoint。"

    message = str(exc).strip()
    if message:
        return f"LLM 连接失败：{message}"
    return "LLM 连接失败，请检查设置中的端点、模型与环境变量密钥。"


def check_llm_connection(
    settings: Settings,
    *,
    llm_client: LlmClient | None = None,
    timeout: float = 10.0,
) -> str | None:
    """Return None when LLM is disabled or reachable; else a user-facing error."""
    if not is_llm_configured(settings):
        return None

    if llm_client is not None:
        try:
            ping = getattr(llm_client, "ping", None)
            if callable(ping):
                ping()
            else:
                llm_client.break_lines(
                    ["连通测试"],
                    min(settings.max_chars, 10),
                    min_chars=min(settings.min_chars, 10),
                )
            return None
        except Exception as exc:
            return format_llm_connection_error(exc)

    api_key = llm_api_key()
    if api_key is None:
        return None

    client = OpenAILlmClient(
        endpoint=settings.llm_endpoint,
        model=settings.llm_model,
        api_key=api_key,
        timeout=timeout,
    )
    try:
        client.ping()
        return None
    except Exception as exc:
        return format_llm_connection_error(exc)


class OpenAILlmClient:
    """Production client using OpenAI-compatible chat completions."""

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    def ping(self) -> None:
        """Verify endpoint/model/key with a minimal chat completion."""
        from openai import OpenAI

        client = OpenAI(
            base_url=self._endpoint,
            api_key=self._api_key,
            timeout=self._timeout,
        )
        client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
            extra_body=_disable_thinking_extra_body(),
        )

    def break_line(
        self,
        line: str,
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[str]:
        return self.break_lines([line], max_chars, min_chars=min_chars)[0]

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[list[str]]:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        if not lines:
            return []
        if len(lines) > 10:
            raise ValueError("break_lines accepts at most 10 lines per batch")

        from openai import OpenAI

        client = OpenAI(
            base_url=self._endpoint,
            api_key=self._api_key,
            timeout=self._timeout,
        )
        return [
            self._break_one_line(client, line, max_chars, min_chars=min_chars)
            for line in lines
        ]

    def _break_one_line(
        self,
        client: object,
        line: str,
        max_chars: int,
        *,
        min_chars: int | None = None,
    ) -> list[str]:
        from openai import APIConnectionError, APITimeoutError

        user_prompt = _build_batch_user_prompt([line], max_chars, min_chars=min_chars)
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                    max_tokens=_break_max_tokens(line),
                    extra_body=_disable_thinking_extra_body(),
                )
                content = _completion_message_content(response.choices[0].message)
                return _parse_batch_break_response(content, [line])[0]
            except APITimeoutError as exc:
                last_error = exc
                logger.warning("LLM timeout (attempt %s)", attempt + 1)
            except APIConnectionError as exc:
                last_error = exc
                logger.warning("LLM connection error (attempt %s)", attempt + 1)
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code is not None and status_code >= 500 and attempt == 0:
                    last_error = exc
                    logger.warning("LLM server error %s (attempt %s)", status_code, attempt + 1)
                    continue
                raise

        assert last_error is not None
        raise last_error


def _disable_thinking_extra_body() -> dict[str, dict[str, bool]]:
    """Best-effort disable thinking for LM Studio / Qwen-style chat templates."""
    return {"chat_template_kwargs": {"enable_thinking": False}}


def _break_max_tokens(line: str) -> int:
    """Cap generation so thinking models cannot run unbounded on break requests."""
    from sentrealm_core.pipeline.line_count import count_line_chars

    # Rough upper bound: output is at most ~2x source length in chars/tokens.
    return min(4096, max(256, count_line_chars(line) * 2))


def _completion_message_content(message: object) -> str:
    """Return assistant text; ignore reasoning-only payloads from thinking models."""
    content = getattr(message, "content", None) or ""
    if content.strip():
        return content
    return ""


def _build_batch_user_prompt(
    lines: list[str],
    max_chars: int,
    *,
    min_chars: int | None = None,
) -> str:
    del min_chars  # rule-break only; LLM prompt uses max_chars as a soft reference
    n = len(lines)
    if n == 1:
        return "\n".join(
            [
                f"参考上限（每行尽量不超过）：{max_chars} 字",
                "",
                "待切分文本：",
                lines[0],
                "",
            ]
        )

    parts = [
        f"参考上限（每行尽量不超过）：{max_chars} 字",
        f"共 {n} 条待切分。对每条分别切分；输出时用「### 1」…「### {n}」分隔，"
        "其下每行一条切分结果，不要解释。",
        "",
    ]
    for index, line in enumerate(lines, start=1):
        parts.append(f"### {index}")
        parts.append(line)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _parse_batch_break_response(content: str, originals: list[str]) -> list[list[str]]:
    """Parse ### N sections; tolerate headerless single-item and trailing ### markers."""
    n = len(originals)
    buckets: dict[int, list[str]] = {i: [] for i in range(1, n + 1)}
    orphan_lines: list[str] = []
    current: int | None = None

    for raw in content.strip().splitlines():
        line = raw.strip()
        if not line:
            continue

        match = _SECTION_RE.match(line)
        if match:
            current = int(match.group(1))
            continue

        inline = re.match(r"^(.*?)(?:###\s*(\d+)\s*)$", line)
        if inline and inline.group(2):
            body = inline.group(1).strip()
            section_num = int(inline.group(2))
            if body and 1 <= section_num <= n:
                buckets[section_num].append(body)
            current = section_num
            continue

        if current is not None and 1 <= current <= n:
            buckets[current].append(line)
        else:
            orphan_lines.append(line)

    if n == 1:
        if buckets[1] and orphan_lines:
            buckets[1] = orphan_lines + buckets[1]
        elif not buckets[1] and orphan_lines:
            buckets[1] = list(orphan_lines)

    result: list[list[str]] = []
    for index, original in enumerate(originals, start=1):
        parts = buckets.get(index) or []
        if not parts:
            result.append([original])
        else:
            result.append(parts)
    return result
