"""Agent 抽象基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import GraphState


class BaseAgent(ABC):
    name: str = "base"
    prompt_file: str | None = None

    def _render_prompt(self, **kw) -> str:
        if not self.prompt_file:
            raise ValueError(f"{self.name}: prompt_file not set")
        path = Path(__file__).resolve().parents[2] / "config" / "prompts" / self.prompt_file
        template = path.read_text(encoding="utf-8")
        # 用简单字符串替换，避免 .format() 把 JSON 示例里的 {} 当占位符
        for key, val in kw.items():
            template = template.replace("{" + key + "}", str(val))
        return template

    def _append_message(self, state: "GraphState", role: str, content: str) -> None:
        msgs = state.setdefault("messages", [])
        msgs.append({"role": role, "agent_name": self.name if role == "assistant" else "",
                     "content": content, "created_at": datetime.utcnow().isoformat()})

    # 中文展示标签 — 子类可覆盖
    label_zh: str = "助手"

    def _trace(self, state: "GraphState", text: str) -> None:
        """追加一条工作流可视化日志（前端按顺序流式展示）。"""
        trace = state.setdefault("trace", [])
        trace.append({"agent": self.name, "label": self.label_zh, "text": text})

    def _get_llm(self):
        from src.llm.deepseek_client import DeepSeekClient
        from src.utils.config_loader import load_settings
        cfg = load_settings()["llm"]
        # base_url 必须以 /v1 结尾（OpenAI SDK 兼容标准）
        base_url = cfg.get("base_url", "https://api.deepseek.com/v1")
        if base_url and not base_url.rstrip("/").endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        # 浏览器 UA — Claude proxy 等代理需要伪装才放行
        ua = cfg.get("user_agent") or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        return DeepSeekClient(
            api_key=cfg.get("api_key", ""),
            base_url=base_url,
            model=cfg.get("model", "deepseek-chat"),
            temperature=cfg.get("temperature", 0.3),
            max_tokens=cfg.get("max_tokens", 2048),
            timeout=cfg.get("timeout", 45),
            user_agent=ua,
        )

    def _safe_llm_chat(self, state: "GraphState", messages: list, **kwargs) -> dict | None:
        """统一的 LLM 调用 + 异常 trace。失败时往 trace 写"⚠️ ..."并返回 None。"""
        try:
            return self._get_llm().chat(messages, **kwargs)
        except Exception as e:
            self._trace(state, f"⚠️ LLM 调用失败：{type(e).__name__}: {str(e)[:120]}（已重试4次）")
            return None

    @staticmethod
    def _extract_json(content: str) -> dict:
        """从 LLM 回复中提取 JSON 对象。
        Claude/某些模型会在 JSON 前后加说明文字或 markdown 代码块，需要兼容处理。
        """
        import json as _json
        import re as _re
        if not content:
            return {}
        # 先试直接解析
        try:
            return _json.loads(content)
        except Exception:
            pass
        # 试 markdown 代码块（```json ... ``` 或 ``` ... ```)
        m = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, _re.DOTALL)
        if m:
            try:
                return _json.loads(m.group(1))
            except Exception:
                pass
        # 抓第一个 {...} 块
        m = _re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return _json.loads(m.group(0))
            except Exception:
                pass
        return {}

    @abstractmethod
    def run(self, state: "GraphState") -> "GraphState":
        raise NotImplementedError

