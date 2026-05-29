"""DeepSeek LLM 客户端（兼容 OpenAI SDK）。

详见 DEV_SPEC.md 3.3 节。
"""
from __future__ import annotations

from typing import Any


class DeepSeekClient:
    """DeepSeek API 客户端。通过 OpenAI 兼容接口调用。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = None  # 延迟实例化

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """调用 chat completion。

        Returns:
            {"content": str, "tool_calls": list[dict] | None, "raw": ...}
        """
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
        def _call():
            client = self._get_client()
            kw: dict[str, Any] = dict(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            if tools:
                kw["tools"] = tools
            if response_format:
                kw["response_format"] = response_format
            kw.update(kwargs)
            resp = client.chat.completions.create(**kw)
            msg = resp.choices[0].message
            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ]
            return {"content": msg.content or "", "tool_calls": tool_calls, "raw": resp}

        return _call()
