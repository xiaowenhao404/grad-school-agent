"""RAG 摄取流水线。"""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

from ..collections import CollectionName, get_collection
from .loaders import Document, load_file
from .splitter import split_documents


def _jieba_tokenize(text: str) -> list[str]:
    import jieba
    return [t for t in jieba.lcut(text) if t.strip()]


def _bm25_path(collection_name: CollectionName) -> Path:
    from src.utils.config_loader import load_settings
    base = Path(load_settings()["vector_store"]["persist_path"])
    p = base / collection_name.value
    p.mkdir(parents=True, exist_ok=True)
    return p / "bm25.pkl"


def _upsert_to_chroma(chunks: list[Document], collection_name: CollectionName) -> None:
    from src.llm.embedding_client import EmbeddingClient
    from src.utils.config_loader import load_settings
    cfg = load_settings()["embedding"]
    emb = EmbeddingClient(
        provider=cfg.get("provider", "local"),
        model=cfg.get("model", ""),
        api_key=cfg.get("api_key"),
        base_url=cfg.get("base_url"),
        local_model_name=cfg.get("local_model_name"),
        batch_size=cfg.get("batch_size", 32),
    )
    col = get_collection(collection_name)
    texts = [c.text for c in chunks]
    vectors = emb.embed(texts)
    ids = [c.metadata.get("chunk_id", hashlib.md5(c.text[:80].encode()).hexdigest()) for c in chunks]
    metadatas = [c.metadata for c in chunks]
    col.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)


def _save_bm25(chunks: list[Document], collection_name: CollectionName) -> None:
    tokens_list = [_jieba_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(tokens_list)
    ids = [c.metadata.get("chunk_id", hashlib.md5(c.text[:80].encode()).hexdigest()) for c in chunks]
    docs = {cid: c for cid, c in zip(ids, chunks)}
    with open(_bm25_path(collection_name), "wb") as f:
        pickle.dump({"bm25": bm25, "chunk_ids": ids, "docs": docs}, f)


# ── SQLite → chunk builders ──────────────────────────────────────────────────

def _build_school_chunks_from_sqlite() -> list[Document]:
    from src.db.engine import get_engine
    from src.db.models import School, SchoolProgram
    from sqlalchemy.orm import sessionmaker

    chunks = []
    with sessionmaker(bind=get_engine())() as s:
        schools = s.query(School).all()
        for school in schools:
            programs = s.query(SchoolProgram).filter_by(school_id=school.id).all()
            prog_summary = "; ".join(
                f"{(p.program_names or ['?'])[0]}({p.duration_months}月,{p.tuition_per_year}{p.currency})"
                for p in programs
            )
            names = school.names or []
            overview_text = (
                f"【学校】{names[0] if names else ''}（别名：{', '.join(names[1:])}）\n"
                f"国家：{school.country}（{school.country_en or ''}），城市：{school.city or ''}，QS：{school.qs_rank}\n"
                f"地址：{school.address or '—'}\n"
                f"官网：{school.official_site or ''}\n"
                f"简介：{school.intro or ''}\n"
                f"开设项目：{prog_summary}"
            )
            cid = f"school_overview_{school.id}"
            chunks.append(Document(
                text=overview_text,
                metadata={"chunk_id": cid, "chunk_type": "school_overview",
                          "school_id": school.id, "country": school.country,
                          "country_en": school.country_en, "qs_rank": school.qs_rank},
                source=f"school:{school.id}",
            ))
            for prog in programs:
                pnames = prog.program_names or []
                pshort = prog.program_short_names or []
                prog_text = (
                    f"【学校】{names[0] if names else ''}（{school.country}）\n"
                    f"【项目】{pnames[0] if pnames else ''}（简称：{', '.join(pshort)}）\n"
                    f"专业大类：{prog.major_category}，标签：{prog.tags}\n"
                    f"学制：{prog.duration_months} 个月，学费：{prog.tuition_per_year} {prog.currency}/年\n"
                    f"语言：IELTS ≥ {prog.ielts_min}，TOEFL ≥ {prog.toefl_min}\n"
                    f"申请链接：{prog.program_url or ''}\n"
                    f"描述：{prog.description_short or ''}"
                )
                pcid = f"program_{prog.id}"
                chunks.append(Document(
                    text=prog_text,
                    metadata={"chunk_id": pcid, "chunk_type": "program",
                              "school_id": school.id, "program_id": prog.id,
                              "major_category": prog.major_category,
                              "qs_rank": school.qs_rank,
                              "tuition_per_year": prog.tuition_per_year,
                              "country": school.country,
                              "tags": json.dumps(prog.tags or [], ensure_ascii=False)},
                    source=f"program:{prog.id}",
                ))
    return chunks


def _build_teacher_chunks_from_sqlite() -> list[Document]:
    from src.db.engine import get_engine
    from src.db.models import Teacher
    from sqlalchemy.orm import sessionmaker

    chunks = []
    with sessionmaker(bind=get_engine())() as s:
        for t in s.query(Teacher).all():
            text = (
                f"【老师】{t.name}（{t.gender}，评分 {t.rating}）\n"
                f"留学经历：{t.study_abroad or ''}\n"
                f"工作经历：{t.work_experience or ''}\n"
                f"擅长地区：{t.expertise_regions or ''}\n"
                f"擅长专业：{t.expertise_majors or ''}\n"
                f"简介：{t.bio or ''}"
            )
            cid = f"teacher_{t.id}"
            chunks.append(Document(
                text=text,
                metadata={"chunk_id": cid, "chunk_type": "teacher",
                          "teacher_id": t.id, "gender": t.gender,
                          "expertise_regions": t.expertise_regions or "",
                          "expertise_majors": t.expertise_majors or ""},
                source=f"teacher:{t.id}",
            ))
    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def ingest(source_path: str | Path | None, collection_name: CollectionName) -> dict:
    """执行一次摄取。

    - INTERNAL_DOCS: 从 source_path 目录/文件加载 PDF/MD，切分后摄取
    - SCHOOLS/TEACHERS: 从 SQLite 拼接 chunk，不走 splitter
    """
    from src.utils.config_loader import load_settings
    cfg = load_settings()["retrieval"]["splitter"]

    if collection_name == CollectionName.INTERNAL_DOCS:
        if source_path is None:
            raise ValueError("INTERNAL_DOCS 需要 source_path")
        p = Path(source_path)
        files = list(p.rglob("*")) if p.is_dir() else [p]
        raw_docs: list[Document] = []
        for f in files:
            raw_docs.extend(load_file(f))
        chunks = split_documents(raw_docs, cfg["chunk_size"], cfg["chunk_overlap"])
    elif collection_name == CollectionName.SCHOOLS:
        chunks = _build_school_chunks_from_sqlite()
    elif collection_name == CollectionName.TEACHERS:
        chunks = _build_teacher_chunks_from_sqlite()
    else:
        raise ValueError(f"Unknown collection: {collection_name}")

    if not chunks:
        return {"chunks": 0}

    _upsert_to_chroma(chunks, collection_name)
    _save_bm25(chunks, collection_name)
    return {"chunks": len(chunks)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", required=True, choices=["schools", "teachers", "internal_docs"])
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    col = CollectionName(args.collection)
    result = ingest(args.source, col)
    print(f"[pipeline] {col.value}: {result}")
