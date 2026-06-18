"""Flask 入口 — 替换 Streamlit。"""
from __future__ import annotations

import json
import os
import sys

# Windows 中文终端默认 GBK 编码，打印含 emoji 的启动横幅/日志会触发
# UnicodeEncodeError 而导致进程崩溃。统一把 stdout/stderr 切到 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from flask import Flask, Response, render_template, request, jsonify, session

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = os.urandom(24)


# 禁用所有响应缓存（开发期）— 避免浏览器旧 JS/HTML 缓存导致功能"点不动"
@app.after_request
def _no_cache(resp):
    # SSE 流式响应保留它自己的 Cache-Control 头
    if resp.mimetype == "text/event-stream":
        return resp
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.template_filter("tojson_zh")
def _tojson_zh(value, indent: int = 2):
    return json.dumps(value, ensure_ascii=False, indent=indent)


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
    from datetime import datetime
    from src.db.engine import get_engine
    from src.db.repositories.teacher_repo import TeacherRepository, TeacherScheduleRepository
    engine = get_engine()
    teachers = TeacherRepository(engine=engine).list_all()
    sched_repo = TeacherScheduleRepository(engine=engine)

    all_dates = sched_repo.list_distinct_dates()
    today = datetime.now().strftime("%Y-%m-%d")
    # 优先用 query param 指定的日期；否则用今天（若今天有数据）；否则用最近的一个有数据日期
    sel_date = (request.args.get("date") or "").strip()
    if sel_date not in all_dates:
        if today in all_dates:
            sel_date = today
        elif all_dates:
            # 找 today 之后的第一个，否则取最后一个
            future = [d for d in all_dates if d >= today]
            sel_date = future[0] if future else all_dates[-1]
        else:
            sel_date = today

    # 按 teacher_id 聚合当天时段
    day_slots = sched_repo.list_by_date(sel_date) if sel_date in all_dates else []
    slots_by_tid: dict[int, list[dict]] = {t["id"]: [] for t in teachers}
    for s in day_slots:
        slots_by_tid.setdefault(s["teacher_id"], []).append(s)

    return render_template(
        "schedule.html",
        teachers=teachers,
        slots_by_tid=slots_by_tid,
        sel_date=sel_date,
        all_dates=all_dates,
        today=today,
    )


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

    # 细分计数：从 SQL 拿权威数据
    doc_counts = {"schools": 0, "programs": 0, "teachers": 0, "internal_files": 0,
                  "schools_chunks": 0, "programs_chunks": 0}
    try:
        from sqlalchemy import text as _t
        from sqlalchemy.orm import sessionmaker
        from src.db.engine import get_engine
        with sessionmaker(bind=get_engine())() as s:
            doc_counts["schools"] = s.execute(_t("SELECT COUNT(*) FROM schools")).scalar() or 0
            doc_counts["programs"] = s.execute(_t("SELECT COUNT(*) FROM school_programs")).scalar() or 0
            doc_counts["teachers"] = s.execute(_t("SELECT COUNT(*) FROM teachers")).scalar() or 0
    except Exception:
        pass

    # internal_docs 文件数（按 Chroma metadata.source 去重）
    try:
        from src.rag.collections import CollectionName, get_collection
        col = get_collection(CollectionName.INTERNAL_DOCS)
        res = col.get(limit=2000, include=["metadatas"])
        sources = set()
        for meta in (res.get("metadatas") or []):
            if meta and meta.get("source"):
                sources.add(meta["source"])
        doc_counts["internal_files"] = len(sources)
    except Exception:
        pass

    # schools collection 内细分（school_overview / program）
    try:
        from src.rag.collections import CollectionName, get_collection
        col = get_collection(CollectionName.SCHOOLS)
        res = col.get(limit=2000, include=["metadatas"])
        for meta in (res.get("metadatas") or []):
            ct = (meta or {}).get("chunk_type", "")
            if ct == "school_overview":
                doc_counts["schools_chunks"] += 1
            elif ct == "program":
                doc_counts["programs_chunks"] += 1
    except Exception:
        pass

    return render_template("knowledge.html", counts=counts, doc_counts=doc_counts)


# ── API 路由 ──────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"error": "empty"}), 400
    conv_id = session.get("conv_id")
    try:
        result = _chat_svc().send_message(USER_ID, conv_id, msg)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"{type(e).__name__}: {e}",
            "agent_response": f"⚠️ 后端处理出错：{type(e).__name__}: {e}",
            "agent_name": "system",
            "task_type": "error",
        }), 200
    session["conv_id"] = result["conversation_id"]
    return jsonify(result)


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    from flask import stream_with_context
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"error": "empty"}), 400

    # 流式响应不能在 yield 中读写 session，先在主线程把 conversation 建好
    conv_id = session.get("conv_id")
    if conv_id is None:
        from src.db.repositories.conversation_repo import ConversationRepository
        conv_id = ConversationRepository().start(USER_ID)
        session["conv_id"] = conv_id

    svc = _chat_svc()

    def _gen():
        for ev in svc.stream_message(USER_ID, conv_id, msg):
            line = "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
            yield line.encode("utf-8")  # direct_passthrough 要求 bytes

    return Response(stream_with_context(_gen()), mimetype="text/event-stream",
                    direct_passthrough=True,
                    headers={
                        "Cache-Control": "no-cache, no-transform",
                        "X-Accel-Buffering": "no",
                        # 注意：不能加 Connection 头 — Waitress (PEP 3333) 会拒绝
                        "Content-Type": "text/event-stream; charset=utf-8",
                    })


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
    """上传文件 → 永久保存到 data/raw_docs/internal/ → 摄取全目录。

    Why: 之前用 tempfile，进程退出后原文件丢失，重启后知识库与文件不一致。
    """
    from datetime import datetime
    from pathlib import Path
    import re as _re
    from src.rag.collections import CollectionName
    from src.rag.ingestion.pipeline import ingest

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "no files"}), 400

    target_dir = Path("data/raw_docs/internal").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    saved = []
    for f in files:
        # 清洗文件名，禁止路径穿越
        orig = _re.sub(r"[\\/:*?\"<>|]+", "_", f.filename or "upload.dat")
        # 加时间戳避免重名覆盖
        dest = target_dir / f"{ts}-{orig}"
        dest.write_bytes(f.read())
        saved.append(dest.name)

    # 重新摄取整个 internal 目录，让 Chroma 与文件保持一致
    try:
        result = ingest(str(target_dir), CollectionName.INTERNAL_DOCS)
    except Exception as e:
        return jsonify({
            "error": f"已保存文件但摄取失败：{e}",
            "saved": saved,
        }), 500
    return jsonify({
        "saved": saved,
        "saved_dir": str(target_dir),
        "chunks": result.get("chunks", 0),
    })


# ── Teacher CRUD ─────────────────────────────────────────────────────────────

@app.route("/api/teachers", methods=["POST"])
def api_teacher_create():
    from src.db.repositories.teacher_repo import TeacherRepository
    data = request.json or {}
    try:
        tid = TeacherRepository().create(data)
        return jsonify({"ok": True, "id": tid})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/teachers/<int:tid>", methods=["PUT", "DELETE"])
def api_teacher_modify(tid: int):
    from src.db.repositories.teacher_repo import TeacherRepository
    repo = TeacherRepository()
    if request.method == "DELETE":
        ok = repo.delete(tid)
        return jsonify({"ok": ok}), (200 if ok else 404)
    data = request.json or {}
    ok = repo.update(tid, data)
    return jsonify({"ok": ok}), (200 if ok else 404)


# ── 详情查询 API（供对话中"📖 完整介绍"弹窗使用） ─────────────────

@app.route("/api/teacher/<int:tid>")
def api_teacher_detail(tid: int):
    from src.db.repositories.teacher_repo import TeacherRepository
    t = TeacherRepository().get(tid)
    if not t:
        return jsonify({"error": "teacher not found"}), 404
    return jsonify(t)


@app.route("/api/program/<int:pid>")
def api_program_detail(pid: int):
    from src.db.repositories.school_repo import SchoolProgramRepository
    p = SchoolProgramRepository().get_program_with_school(pid)
    if not p:
        return jsonify({"error": "program not found"}), 404
    # 反序列化 JSON 字符串字段（SQLite 把 JSON 列存为字符串）
    import json as _json
    for k in ("program_names", "program_short_names", "tags", "names"):
        v = p.get(k)
        if isinstance(v, str):
            try:
                p[k] = _json.loads(v)
            except Exception:
                pass
    return jsonify(p)


# ── MCP-like tools 服务（演示项目内置的 MCP-like server） ────────────────────

@app.route("/api/mcp/tools")
def api_mcp_list_tools():
    """**MCP 标准接口**：返回 server 暴露的所有工具的 schema 列表。

    用法等同 Anthropic MCP SDK 的 `mcp.list_tools()`。
    """
    from src.tools.registry import registry, autoload_tools
    autoload_tools()
    return jsonify({
        "server": registry.SERVER_NAME,
        "protocol": registry.PROTOCOL_VERSION,
        "tools": registry.list_tools(),
    })


@app.route("/api/mcp/call/<name>", methods=["POST"])
def api_mcp_call_tool(name: str):
    """**MCP 标准接口**：调用指定工具并返回结果。

    用法等同 Anthropic MCP SDK 的 `mcp.call_tool(name, arguments)`。
    """
    from src.tools.registry import registry, autoload_tools
    autoload_tools()
    args = request.json or {}
    try:
        result = registry.call_tool(name, **args)
        return jsonify({"server": registry.SERVER_NAME, "tool": name,
                        "arguments": args, "result": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


# ── Schedule slot CRUD ───────────────────────────────────────────────────────

@app.route("/api/schedule", methods=["POST"])
def api_schedule_add():
    from src.db.repositories.teacher_repo import TeacherScheduleRepository
    data = request.json or {}
    tid = data.get("teacher_id")
    date = (data.get("date") or "").strip()
    time_slot = (data.get("time_slot") or "").strip()
    if not (tid and date and time_slot):
        return jsonify({"error": "缺少 teacher_id / date / time_slot"}), 400
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return jsonify({"error": "date 必须为 YYYY-MM-DD"}), 400
    if not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", time_slot):
        return jsonify({"error": "time_slot 必须为 HH:MM-HH:MM"}), 400
    sid = TeacherScheduleRepository().add_slot(int(tid), date, time_slot)
    if sid == -1:
        return jsonify({"error": "该时段已存在"}), 409
    return jsonify({"ok": True, "id": sid})


@app.route("/api/schedule/<int:sid>", methods=["PATCH"])
def api_schedule_set_status(sid: int):
    from src.db.repositories.teacher_repo import TeacherScheduleRepository
    status = (request.json or {}).get("status", "")
    try:
        ok = TeacherScheduleRepository().set_status(sid, status)
        return jsonify({"ok": ok}), (200 if ok else 404)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/schedule/snapshot")
def api_schedule_snapshot():
    """轻量 polling 端点：返回指定日期所有时段的 (id, status) 列表，
    供 schedule 页面前端比对以决定是否 reload（预约后自动反映）。"""
    from src.db.repositories.teacher_repo import TeacherScheduleRepository
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"items": []})
    try:
        items = TeacherScheduleRepository().list_by_date(date)
        # 仅返回 id + status，最小化网络流量
        return jsonify({"items": [{"id": s["id"], "status": s["status"]} for s in items]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Knowledge details ────────────────────────────────────────────────────────

@app.route("/api/knowledge/<kind>")
def api_knowledge_list(kind: str):
    """返回知识库分类详情列表：schools / programs / teachers / internal_docs"""
    from sqlalchemy import text as _t
    from sqlalchemy.orm import sessionmaker
    from src.db.engine import get_engine

    if kind == "schools":
        from src.db.repositories.school_repo import SchoolRepository
        return jsonify({"items": SchoolRepository().list_all()})
    if kind == "teachers":
        from src.db.repositories.teacher_repo import TeacherRepository
        return jsonify({"items": TeacherRepository().list_all()})
    if kind == "programs":
        with sessionmaker(bind=get_engine())() as s:
            rows = s.execute(_t(
                "SELECT p.id, p.program_names, p.major_category, p.duration_months, "
                "p.tuition_per_year, p.currency, p.ielts_min, p.toefl_min, "
                "p.program_url, s.names AS school_names, s.country, s.qs_rank "
                "FROM school_programs p JOIN schools s ON p.school_id=s.id "
                "ORDER BY s.qs_rank"
            )).mappings().fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    if kind == "internal_docs":
        # 从 Chroma 按 source 聚合：preview（前 200 字）+ full（全文 = 该 source 所有 chunks 拼接）
        from src.rag.collections import CollectionName, get_collection
        col = get_collection(CollectionName.INTERNAL_DOCS)
        try:
            res = col.get(limit=2000, include=["metadatas", "documents"])
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        # 按 source 聚合所有 chunks
        grouped: dict = {}
        for i, _id in enumerate(res.get("ids", [])):
            meta = (res.get("metadatas") or [{}])[i] or {}
            src = meta.get("source") or _id
            doc = (res.get("documents") or [""])[i] or ""
            g = grouped.setdefault(src, {"chunks": [], "metadata": meta})
            g["chunks"].append({"id": _id, "doc": doc, "meta": meta})
        items = []
        for src, g in grouped.items():
            # 用 chunk_index（若有）或 id 字典序排序
            g["chunks"].sort(key=lambda c: (c["meta"].get("chunk_index", 0), c["id"]))
            full = "\n\n".join(c["doc"] for c in g["chunks"])
            items.append({
                "source": src,
                "preview": full[:200],
                "full": full,
                "chunks_count": len(g["chunks"]),
                "metadata": g["metadata"],
            })
        # 按 source 字母序排序（稳定输出）
        items.sort(key=lambda x: x["source"])
        return jsonify({"items": items})
    return jsonify({"error": "unknown kind"}), 400


if __name__ == "__main__":
    # 优先用 Waitress（生产级纯 Python WSGI server）
    # Flask 内置 dev server (Werkzeug) 在 Windows 上做 SSE 长连接 +
    # 大量 chunked transfer 时容易触发 ERR_CONNECTION_RESET。
    # Waitress 没有这个问题，且支持 streaming。
    try:
        from waitress import serve
        print("=" * 60)
        print(" 🚀 Grad-School-Agent running on http://127.0.0.1:5000")
        print("    (using Waitress for stable SSE on Windows)")
        print("=" * 60)
        # threads 必须 >= 2（一个跑请求、一个跑 SSE 心跳）；ident 用于日志
        serve(app, host="127.0.0.1", port=5000, threads=8,
              channel_timeout=300, cleanup_interval=30, ident="grad-school-agent")
    except ImportError:
        print("[WARN] waitress 未安装，回退到 Flask dev server（Windows 下 SSE 不稳定）。")
        print("       安装：pip install waitress")
        app.run(debug=True, port=5000, threaded=True)
