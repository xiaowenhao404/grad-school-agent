"""单测：DeepSeek client + Chroma collections 初始化。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── DeepSeek client ──────────────────────────────────────────────────────────

def test_chat_returns_content(monkeypatch):
    from src.llm.deepseek_client import DeepSeekClient

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "hello"
    mock_resp.choices[0].message.tool_calls = None

    mock_openai = MagicMock()
    mock_openai.return_value.chat.completions.create.return_value = mock_resp

    with patch("openai.OpenAI", mock_openai):
        client = DeepSeekClient(api_key="test", base_url="http://x")
        result = client.chat([{"role": "user", "content": "hi"}])

    assert result["content"] == "hello"
    assert result["tool_calls"] is None


def test_chat_retries_on_error(monkeypatch):
    from src.llm.deepseek_client import DeepSeekClient

    call_count = 0

    def flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("transient")
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "ok"
        mock_resp.choices[0].message.tool_calls = None
        return mock_resp

    mock_openai = MagicMock()
    mock_openai.return_value.chat.completions.create.side_effect = flaky

    with patch("openai.OpenAI", mock_openai):
        client = DeepSeekClient(api_key="test", base_url="http://x")
        result = client.chat([{"role": "user", "content": "hi"}])

    assert result["content"] == "ok"
    assert call_count == 3


# ── Chroma collections ────────────────────────────────────────────────────────

def test_init_all_collections(tmp_path, monkeypatch):
    import chromadb
    from src.rag import collections as col_mod

    # 用临时目录隔离
    col_mod._client = None
    monkeypatch.setattr(
        "src.rag.collections.get_chroma_client",
        lambda: chromadb.PersistentClient(path=str(tmp_path)),
    )

    from src.rag.collections import CollectionName, get_collection
    names = [get_collection(n).name for n in CollectionName]
    assert set(names) == {"schools", "teachers", "internal_docs"}
