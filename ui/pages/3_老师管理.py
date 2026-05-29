"""页面 3：老师管理。"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="老师管理", page_icon="👨‍🏫", layout="wide")
st.title("👨‍🏫 老师管理")

from src.db.engine import get_engine
from src.db.repositories.teacher_repo import TeacherRepository

repo = TeacherRepository(engine=get_engine())
teachers = repo.list_all()

if not teachers:
    st.info("暂无老师数据，请先运行 `python -m src.db.init_db` 导入 seed 数据。")
else:
    df = pd.DataFrame(teachers)
    display_cols = [c for c in ["id", "name", "gender", "rating", "expertise_regions",
                                 "expertise_majors", "study_abroad"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("老师详情")
    selected_id = st.selectbox("选择老师", [t["id"] for t in teachers],
                                format_func=lambda x: next(t["name"] for t in teachers if t["id"] == x))
    detail = repo.get(selected_id)
    if detail:
        c1, c2 = st.columns(2)
        c1.write(f"**姓名**：{detail['name']}")
        c1.write(f"**性别**：{detail['gender']}")
        c1.write(f"**评分**：{detail.get('rating', 'N/A')}")
        c2.write(f"**擅长地区**：{detail.get('expertise_regions', '')}")
        c2.write(f"**擅长专业**：{detail.get('expertise_majors', '')}")
        st.write(f"**留学经历**：{detail.get('study_abroad', '')}")
        st.write(f"**简介**：{detail.get('bio', '')}")
