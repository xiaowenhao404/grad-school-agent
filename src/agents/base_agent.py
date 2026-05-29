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

    def _get_llm(self):
        from src.llm.deepseek_client import DeepSeekClient
        from src.utils.config_loader import load_settings
        cfg = load_settings()["llm"]
        return DeepSeekClient(
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("base_url", "https://api.deepseek.com/v1"),
            model=cfg.get("model", "deepseek-chat"),
            temperature=cfg.get("temperature", 0.3),
            max_tokens=cfg.get("max_tokens", 2048),
        )

    @abstractmethod
    def run(self, state: "GraphState") -> "GraphState":
        raise NotImplementedError

