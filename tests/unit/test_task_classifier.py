"""单测：TaskClassifier + ConsultantAgent。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


# ── TaskClassifier ────────────────────────────────────────────────────────────

def _make_state(user_input: str = "test") -> dict:
    return {"user_id": 1, "conversation_id": 1, "user_input": user_input,
            "user_profile": {}, "memory_enabled": True, "messages": []}


def _mock_llm_response(task_type: str):
    mock = MagicMock()
    mock.chat.return_value = {"content": json.dumps({"task_type": task_type}), "tool_calls": None}
    return mock


def test_classifier_routes_school(monkeypatch):
    from src.agents.task_classifier import TaskClassifier
    clf = TaskClassifier()
    monkeypatch.setattr(clf, "_get_llm", lambda: _mock_llm_response("school"))
    state = _make_state("我想了解美国 CS 硕士")
    out = clf.run(state)
    assert out["task_type"] == "school"


def test_classifier_invalid_falls_back_to_reject(monkeypatch):
    from src.agents.task_classifier import TaskClassifier
    clf = TaskClassifier()
    mock_llm = MagicMock()
    mock_llm.chat.return_value = {"content": '{"task_type": "unknown_xyz"}', "tool_calls": None}
    monkeypatch.setattr(clf, "_get_llm", lambda: mock_llm)
    state = _make_state("随便说点什么")
    out = clf.run(state)
    assert out["task_type"] == "reject"


def test_classifier_malformed_json_falls_back(monkeypatch):
    from src.agents.task_classifier import TaskClassifier
    clf = TaskClassifier()
    mock_llm = MagicMock()
    mock_llm.chat.return_value = {"content": "not json at all", "tool_calls": None}
    monkeypatch.setattr(clf, "_get_llm", lambda: mock_llm)
    state = _make_state("test")
    out = clf.run(state)
    assert out["task_type"] == "reject"


# ── ConsultantAgent ───────────────────────────────────────────────────────────

def test_consultant_prompt_contains_retrieved_context(monkeypatch):
    from src.agents.consultant_agent import ConsultantAgent
    from src.rag.retrieval.dense_retriever import RetrievalResult

    agent = ConsultantAgent()

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        RetrievalResult(chunk_id="c1", content="签证需要 I-20 表格", metadata={"source": "visa.pdf"},
                        score=0.9, source="dense")
    ]

    captured_prompt = {}

    def mock_render(**kw):
        captured_prompt.update(kw)
        return "rendered_prompt"

    monkeypatch.setattr(agent, "_render_prompt", mock_render)

    mock_llm = MagicMock()
    mock_llm.chat.return_value = {"content": "签证需要 I-20", "tool_calls": None}
    monkeypatch.setattr(agent, "_get_llm", lambda: mock_llm)

    with patch("src.rag.retrieval.retriever_factory.get_retriever", return_value=mock_retriever), \
         patch("src.runtime_skills.registry.skill_registry.collect_context", return_value=""):
        state = _make_state("F1 签证需要什么")
        out = agent.run(state)

    assert "I-20" in captured_prompt.get("retrieved_chunks", "")
    assert out["agent_response"] == "签证需要 I-20"
    assert any(m["role"] == "assistant" for m in out["messages"])
