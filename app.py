"""Flask 入口 — 替换 Streamlit。"""
from __future__ import annotations

import os
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = os.urandom(24)

USER_ID = 1


def _chat_svc():
    from src.services.chat_service import ChatService
    return ChatService()


# ── 页面路由 ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/teachers")
def teachers():
    from src.db.engine import get_engine
    from src.db.repositories.teacher_repo import TeacherRepository
    teachers = TeacherRepository(engine=get_engine()).list_all()
    return render_template("teachers.html", teachers=teachers)


@app.route("/schedule")
def schedule():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from src.db.engine import get_engine
    from src.db.repositories.teacher_repo import TeacherRepository
    engine = get_engine()
    teachers = TeacherRepository(engine=engine).list_all()
    slots = {}
    with sessionmaker(bind=engine)() as s:
        for t in teachers:
            rows = s.execute(
                text("SELECT * FROM teacher_schedule WHERE teacher_id=:tid ORDER BY date, time_slot"),
                {"tid": t["id"]}
            ).mappings().fetchall()
            slots[t["id"]] = [dict(r) for r in rows]
    return render_template("schedule.html", teachers=teachers, slots=slots)


@app.route("/behavior")
def behavior():
    from src.db.repositories.user_repo import UserRepository
    profile = UserRepository().get_profile(USER_ID)
    return render_template("behavior.html", profile=profile)


@app.route("/knowledge")
def knowledge():
    counts = {}
    try:
        from src.rag.collections import CollectionName, get_collection
        for col in CollectionName:
            try:
                counts[col.value] = get_collection(col).count()
            except Exception:
                counts[col.value] = "N/A"
    except Exception:
        pass
    return render_template("knowledge.html", counts=counts)


# ── API 路由 ──────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"error": "empty"}), 400
    conv_id = session.get("conv_id")
    result = _chat_svc().send_message(USER_ID, conv_id, msg)
    session["conv_id"] = result["conversation_id"]
    return jsonify(result)


@app.route("/api/clear", methods=["POST"])
def api_clear():
    _chat_svc().clear_conversation(USER_ID)
    session.pop("conv_id", None)
    return jsonify({"ok": True})


@app.route("/api/memory", methods=["POST"])
def api_memory():
    enabled = (request.json or {}).get("enabled", True)
    from src.db.repositories.user_repo import UserRepository
    UserRepository().set_memory_enabled(USER_ID, bool(enabled))
    return jsonify({"ok": True})


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    collection = (request.json or {}).get("collection", "internal_docs")
    source = (request.json or {}).get("source")
    try:
        from src.rag.collections import CollectionName
        from src.rag.ingestion.pipeline import ingest
        result = ingest(source, CollectionName(collection))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    import tempfile
    from pathlib import Path
    from src.rag.collections import CollectionName
    from src.rag.ingestion.pipeline import ingest
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "no files"}), 400
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            (Path(tmp) / f.filename).write_bytes(f.read())
        result = ingest(tmp, CollectionName.INTERNAL_DOCS)
    return jsonify({"chunks": result.get("chunks", 0)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
