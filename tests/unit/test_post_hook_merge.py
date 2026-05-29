"""单测：post_hook 偏好合并逻辑。"""
from __future__ import annotations

from src.db.repositories.user_repo import _merge_prefs


def test_merge_list_dedup():
    old = {"keywords": ["美国", "CS"]}
    new = {"keywords": ["CS", "英国"]}
    result = _merge_prefs(old, new)
    assert result["keywords"] == ["美国", "CS", "英国"]


def test_merge_range_union():
    old = {"tuition_range_usd": [50000, 100000]}
    new = {"tuition_range_usd": [80000, 150000]}
    result = _merge_prefs(old, new)
    assert result["tuition_range_usd"] == [50000, 150000]


def test_merge_scalar_overwrite():
    old = {"country": "美国"}
    new = {"country": "英国"}
    result = _merge_prefs(old, new)
    assert result["country"] == "英国"


def test_merge_null_skipped():
    old = {"country": "美国"}
    new = {"country": None, "keywords": ["CS"]}
    result = _merge_prefs(old, new)
    assert result["country"] == "美国"
    assert result["keywords"] == ["CS"]
