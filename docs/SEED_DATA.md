# Seed 数据来源建议

> 目标量级（大型）：30 老师 / 80 学校 / 200 项目 / 20 内部文档。详见 [`DEV_SPEC.md` 附录 B](../DEV_SPEC.md#附录-bseed-数据来源建议)。
>
> 数据准备与代码开发并行。首期可用小型数据（5 学校/3 老师/2 文档）打通流程，demo 前补足。

## 数据文件位置

```
data/
├── seed/
│   ├── teachers.json
│   ├── schools.json
│   ├── programs.json
│   └── teacher_schedule.json
└── raw_docs/
    ├── schools/         # 各校招生简章 PDF / Markdown
    ├── teachers/        # 老师详细背景资料
    └── internal/        # 签证指南、公司介绍、服务说明
```

## 数据 schema

### `teachers.json` 示例

```json
[
  {
    "id": 1,
    "name": "李老师",
    "gender": "male",
    "bio": "深耕北美 CS 申请咨询 8 年，帮助 200+ 学员拿到 Top 30 录取...",
    "study_abroad": "Carnegie Mellon University, MS in CS, 2014-2016",
    "work_experience": "前 Google 工程师；现金牌咨询顾问",
    "expertise_regions": "美国,加拿大",
    "expertise_majors": "CS,EE,DS"
  }
]
```

### `schools.json` 示例

```json
[
  {
    "id": 1,
    "name": "Massachusetts Institute of Technology",
    "short_name": "MIT",
    "country": "美国",
    "qs_rank": 1,
    "official_site": "https://www.mit.edu",
    "intro": "麻省理工学院位于美国马萨诸塞州..."
  }
]
```

### `programs.json` 示例

```json
[
  {
    "id": 1,
    "school_id": 1,
    "program_full_name": "Master of Engineering in EECS",
    "program_short_name": "MEng EECS",
    "major_category": "CS",
    "duration_months": 12,
    "tuition_per_year": 60000,
    "currency": "USD",
    "ielts_min": 7.0,
    "toefl_min": 100,
    "deadline": "12-15",
    "description_short": "MIT EECS 一年制硕士项目，强调研究与课程并重..."
  }
]
```

### `teacher_schedule.json` 示例

```json
[
  { "teacher_id": 1, "date": "2026-06-01", "time_slot": "10:00-11:00", "status": "available" },
  { "teacher_id": 1, "date": "2026-06-01", "time_slot": "14:00-15:00", "status": "available" }
]
```

## 采集建议

### 老师（~30）

**方法**：LLM 批量合成 fake profiles，用户审核去重。

提示词模板：

```
请生成 5 位留学申请咨询老师的 fake profile，输出 JSON 数组。
字段：name, gender, bio (50-100 字), study_abroad, work_experience, expertise_regions, expertise_majors。
要求：
- 性别分布 男:女 ≈ 1:1
- 擅长地区覆盖 美国/英国/加拿大/澳洲/欧洲
- 擅长专业覆盖 CS/EE/DS/Business/Engineering/Law
- bio 中体现真实背景细节，不要全是套话
```

跑 6 轮 = 30 位。

### 学校（~80）

**方法**：从 QS Top 100 公开排名表整理。

参考来源：
- QS World University Rankings 官网（公开）
- 维基百科各校词条（简介与官网链接）

写脚本提取 csv → 转 json，注意 country 字段中文化。

### 项目（~200）

**方法**：每校手动列 2-3 个主流项目。

聚焦专业：
- CS / DS / AI 相关
- EE / ECE
- Business / MBA / MFin
- 部分文科（如 East Asian Studies、Public Policy）

学费数据来源：各校官网 Tuition 页面（公开）。

### 内部文档（~20 PDF）

**类型组合**：

| 文档类型 | 数量 | 来源建议 |
|---------|------|---------|
| 美国/英国/加拿大签证指南 | 3 | USCIS、UK Gov、IRCC 公开 PDF |
| 申请文书写作指导 | 4 | 公开范文集合（脱敏） |
| 公司服务介绍 | 3 | 用 LLM 合成 |
| 营业时间/联系方式 | 2 | 合成 |
| 常见问题 FAQ | 4 | 合成 |
| 政策解读（OPT/PSW/学签） | 4 | 公开政策摘要 |

## 导入

```powershell
uv run python -m src.db.init_db
```

`init_db` 会自动读取 `data/seed/*.json` 写入 SQLite，并触发 `data/raw_docs/internal/*.pdf` 的摄取。

## 数据质量准则

- 不要提交可识别的个人信息（PII）。老师 profile 用 fake name + fake background。
- 不要提交付费/版权内容（如出版社教材）。
- 学校官网链接验证可访问，避免 404。
- 数据导入失败时 `init_db` 应清晰列出失败行号。
