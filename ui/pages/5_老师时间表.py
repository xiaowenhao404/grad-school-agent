"""页面 5：老师时间表。"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="老师时间表", page_icon="🗓️", layout="wide")
st.title("🗓️ 老师时间表")

from src.db.engine import get_engine
from src.db.repositories.teacher_repo import TeacherRepository, TeacherScheduleRepository
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

engine = get_engine()
teacher_repo = TeacherRepository(engine=engine)
schedule_repo = TeacherScheduleRepository(engine=engine)

teachers = teacher_repo.list_all()
if not teachers:
    st.info("暂无老师数据。")
else:
    selected_id = st.selectbox(
        "选择老师",
        [t["id"] for t in teachers],
        format_func=lambda x: next(t["name"] for t in teachers if t["id"] == x),
    )

    status_filter = st.radio("状态筛选", ["全部", "available", "booked", "blocked"], horizontal=True)

    with sessionmaker(bind=engine)() as s:
        q = "SELECT * FROM teacher_schedule WHERE teacher_id=:tid"
        params = {"tid": selected_id}
        if status_filter != "全部":
            q += " AND status=:status"
            params["status"] = status_filter
        q += " ORDER BY date, time_slot"
        rows = s.execute(text(q), params).mappings().fetchall()

    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        status_colors = {"available": "🟢", "booked": "🔴", "blocked": "⚫"}
        df["状态"] = df["status"].map(lambda x: f"{status_colors.get(x, '')} {x}")
        st.dataframe(df[["id", "date", "time_slot", "状态"]], use_container_width=True, hide_index=True)
        st.caption(f"共 {len(df)} 条记录")
    else:
        st.info("该老师暂无时间槽记录。")
