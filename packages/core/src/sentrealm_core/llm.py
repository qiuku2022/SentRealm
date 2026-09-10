"""LLM client protocol and implementations (ADR-005)."""

from __future__ import annotations

import logging
import math
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sentrealm_core.models import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是中文口播断句助手。任务：把用户给出的一行文本切成多行，便于朗读与字幕匹配。"
    "必须遵守："
    "1. 只切分，不改写：不得增删改任何字，标点也保持原样（仅通过换行切分）。"
    "2. 字数上限 N（用户给出）：每一行 countable 字数必须 ≤ N。"
    "只要还能在语义或语法边界切开，就禁止保留超长行；"
    "仅当段内完全找不到合理切点时，才允许单行略超 N。"
    "3. 最短行长 M（用户给出）：尽量每行 ≥ M；禁止单字成行"
    "（如单独的「的」「了」「是」「在」「被」「把」「和」等）；"
    "也不要拆出无意义的两字碎句。不要为凑长度而改写原文。"
    "4. 切在语义完整处：意群、短语、并列、分句成分之间；"
    "禁止拆开双音节词（如「现在」「已经」「中国」）与固定搭配；"
    "符合现代汉语语法与口播习惯。"
    "5. 在满足 ≤N 与避免过短的前提下，尽量少分行，并使各行长度接近。"
    "6. 英文与数字：不要在英文单词或连续数字中间断开。"
    "输出：仅输出切分后的多行文本，每行一条，不要编号、不要解释。"
)

_SECTION_RE = re.compile(r"^###\s*(\d+)\s*$")

# Outcomes for LineBreakResult.outcome
OUTCOME_PARSED = "parsed"
OUTCOME_EMPTY = "empty"
OUTCOME_TRUNCATED = "truncated"
OUTCOME_REQUEST_ERROR = "request_error"
OUTCOME_CONFIG_ERROR = "config_error"

_CONFIG_STATUS_CODES = frozenset({401, 403, 404})


@dataclass(frozen=True)
class LineBreakResult:
    """Per-line LLM break attempt result (no full transcript logging)."""

    parts: list[str]
    outcome: str
    finish_reason: str | None = None
    http_status: int | None = None


def parsed_line_break(parts: list[str]) -> LineBreakResult:
    return LineBreakResult(parts=list(parts), outcome=OUTCOME_PARSED)


class LlmClient(Protocol):
    """Break one or more over-length lines without rewriting wording."""

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
        wave: int = 1,
    ) -> list[LineBreakResult]: ...


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
        self.hint_calls: list[list[str | None] | None] = []

    def break_line(
        self,
        line: str,
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hint: str | None = None,
    ) -> LineBreakResult:
        hints = [retry_hint] if retry_hint is not None else None
        return self.break_lines(
            [line], max_chars, min_chars=min_chars, retry_hints=hints
        )[0]

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
        wave: int = 1,
    ) -> list[LineBreakResult]:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        del wave  # Mock ignores wave; production prompt uses it.
        self.calls.append(list(lines))
        self.hint_calls.append(list(retry_hints) if retry_hints is not None else None)
        if self._bad_remaining > 0:
            self._bad_remaining -= 1
            return [parsed_line_break(_corrupt_split(line)) for line in lines]
        return [
            parsed_line_break(_balanced_split(line, max_chars, min_chars=min_chars))
            for line in lines
        ]

    def ping(self) -> None:
        """No-op for tests; connectivity is exercised via break_lines when needed."""


def _corrupt_split(line: str) -> list[str]:
    """Intentionally break conservation so quality diagnose fails."""
    if len(line) < 2:
        return [line + "X"] if line else ["X"]
    mid = max(1, len(line) // 2)
    return [line[:mid] + "X", line[mid:]]


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
        retry_hint: str | None = None,
    ) -> LineBreakResult:
        hints = [retry_hint] if retry_hint is not None else None
        return self.break_lines(
            [line], max_chars, min_chars=min_chars, retry_hints=hints
        )[0]

    def break_lines(
        self,
        lines: list[str],
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hints: Sequence[str | None] | None = None,
        wave: int = 1,
    ) -> list[LineBreakResult]:
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
        results: list[LineBreakResult] = []
        config_status: int | None = None
        for index, line in enumerate(lines):
            if config_status is not None:
                results.append(
                    LineBreakResult(
                        parts=[],
                        outcome=OUTCOME_CONFIG_ERROR,
                        http_status=config_status,
                    )
                )
                continue
            hint = None
            if retry_hints is not None and index < len(retry_hints):
                hint = retry_hints[index]
            result = self._break_one_line(
                client,
                line,
                max_chars,
                min_chars=min_chars,
                retry_hint=hint,
                wave=wave,
            )
            results.append(result)
            if result.outcome == OUTCOME_CONFIG_ERROR:
                config_status = result.http_status
        return results

    def _break_one_line(
        self,
        client: object,
        line: str,
        max_chars: int,
        *,
        min_chars: int | None = None,
        retry_hint: str | None = None,
        wave: int = 1,
    ) -> LineBreakResult:
        from openai import APIConnectionError, APITimeoutError, AuthenticationError

        user_prompt = _build_batch_user_prompt(
            [line],
            max_chars,
            min_chars=min_chars,
            retry_hint=retry_hint,
            wave=wave,
        )
        max_tokens = _break_max_tokens(line)
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return self._complete_break(
                    client,
                    user_prompt,
                    line,
                    max_tokens=max_tokens,
                    allow_truncation_retry=True,
                )
            except AuthenticationError as exc:
                status = getattr(exc, "status_code", None) or 401
                logger.warning("LLM config error status=%s", status)
                return LineBreakResult(
                    parts=[],
                    outcome=OUTCOME_CONFIG_ERROR,
                    http_status=int(status) if status is not None else 401,
                )
            except APITimeoutError as exc:
                last_error = exc
                logger.warning("LLM timeout (attempt %s)", attempt + 1)
            except APIConnectionError as exc:
                last_error = exc
                logger.warning("LLM connection error (attempt %s)", attempt + 1)
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code in _CONFIG_STATUS_CODES:
                    logger.warning("LLM config error status=%s", status_code)
                    return LineBreakResult(
                        parts=[],
                        outcome=OUTCOME_CONFIG_ERROR,
                        http_status=int(status_code),
                    )
                if status_code is not None and status_code >= 500 and attempt == 0:
                    last_error = exc
                    logger.warning(
                        "LLM server error %s (attempt %s)", status_code, attempt + 1
                    )
                    continue
                if status_code is not None and 400 <= int(status_code) < 500:
                    logger.warning("LLM client error status=%s", status_code)
                    return LineBreakResult(
                        parts=[],
                        outcome=OUTCOME_REQUEST_ERROR,
                        http_status=int(status_code),
                    )
                logger.warning("LLM request failed: %s", type(exc).__name__)
                return LineBreakResult(
                    parts=[],
                    outcome=OUTCOME_REQUEST_ERROR,
                    http_status=int(status_code) if status_code is not None else None,
                )

        assert last_error is not None
        status_code = getattr(last_error, "status_code", None)
        logger.warning("LLM transport retries exhausted")
        return LineBreakResult(
            parts=[],
            outcome=OUTCOME_REQUEST_ERROR,
            http_status=int(status_code) if status_code is not None else None,
        )

    def _complete_break(
        self,
        client: object,
        user_prompt: str,
        line: str,
        *,
        max_tokens: int,
        allow_truncation_retry: bool,
    ) -> LineBreakResult:
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=max_tokens,
            extra_body=_disable_thinking_extra_body(),
        )
        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        content = _completion_message_content(choice.message)

        if finish_reason == "length" and allow_truncation_retry:
            bumped = min(4096, max(max_tokens * 2, max_tokens + 1))
            if bumped > max_tokens:
                logger.warning(
                    "LLM output truncated; retrying with max_tokens=%s", bumped
                )
                return self._complete_break(
                    client,
                    user_prompt,
                    line,
                    max_tokens=bumped,
                    allow_truncation_retry=False,
                )

        if not content.strip():
            return LineBreakResult(
                parts=[],
                outcome=OUTCOME_EMPTY,
                finish_reason=finish_reason,
            )

        parts = _parse_batch_break_response(content, [line])[0]
        if finish_reason == "length":
            return LineBreakResult(
                parts=parts,
                outcome=OUTCOME_TRUNCATED,
                finish_reason=finish_reason,
            )
        if not parts:
            return LineBreakResult(
                parts=[],
                outcome=OUTCOME_EMPTY,
                finish_reason=finish_reason,
            )
        return LineBreakResult(
            parts=parts,
            outcome=OUTCOME_PARSED,
            finish_reason=finish_reason,
        )


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
    retry_hint: str | None = None,
    wave: int = 1,
) -> str:
    from sentrealm_core.pipeline.llm_quality import resolve_min_chars

    floor = resolve_min_chars(max_chars, min_chars)
    n = len(lines)
    hint_block: list[str] = []
    if retry_hint:
        hint_block = [f"返工说明：{retry_hint}", ""]

    length_rules = [
        f"硬性目标：每行不超过 {max_chars} 字；能在语义边界切开则必须切开，勿保留可切开的超长行。",
        f"建议最短行长：不少于 {floor} 字；禁止单字成行。",
    ]
    if wave == 2:
        length_rules.append(
            "本条为长度返工（第 2 波）：在守恒前提下优先消除过短行与仍超长行，"
            "并保持各行相对均衡。"
        )

    if n == 1:
        return "\n".join(
            [
                *length_rules,
                "",
                *hint_block,
                "待切分文本：",
                lines[0],
                "",
            ]
        )

    parts = [
        *length_rules,
        f"共 {n} 条待切分。对每条分别切分；输出时用「### 1」…「### {n}」分隔，"
        "其下每行一条切分结果，不要解释。",
        "",
        *hint_block,
    ]
    for index, line in enumerate(lines, start=1):
        parts.append(f"### {index}")
        parts.append(line)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _parse_batch_break_response(content: str, originals: list[str]) -> list[list[str]]:
    """Parse ### N sections; missing sections yield [] (never silent original fallback)."""
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

    return [list(buckets.get(index) or []) for index in range(1, n + 1)]
