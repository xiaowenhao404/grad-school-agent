# 数据库 Schema 与 Seed 数据设计

> 日期：2026-05-29
> 状态：已批准实施

## 1. 背景

本次设计针对 Grad-School-Agent 项目的数据库 Schema 优化和 Seed 数据构造，主要变更：
- 院校和项目的中英文多名称支持
- 项目多简称和多标签支持
- 增强院校地址信息
- 删除 `deadline` 字段，增加 `program_url`
- 扩展老师表字段

## 2. Schema 变更

### 2.1 schools 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK | 学校 ID |
| `names` | JSON | NOT NULL | 名称变体数组，含中英文全称、简称等 |
| `country` | VARCHAR(32) | NOT NULL | 所在国家（中文） |
| `country_en` | VARCHAR(32) | NULL | 所在国家（英文） |
| `city` | VARCHAR(64) | NULL | 所在城市 |
| `address` | VARCHAR(255) | NULL | 详细地址 |
| `qs_rank` | INTEGER | NULL | QS 综合排名 |
| `official_site` | VARCHAR(255) | NULL | 官网 URL |
| `intro` | TEXT | NULL | 学校总介绍 |
| `created_at` | DATETIME | 默认 now | 创建时间 |

**变更说明**：
- `name` → `names`（JSON 数组，支持多语言多简称）
- 删除 `short_name`（并入 `names`）

### 2.2 school_programs 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK | 项目 ID |
| `school_id` | INTEGER | FK→schools.id | 所属学校 |
| `program_names` | JSON | NOT NULL | 项目中英文全称 |
| `program_short_names` | JSON | NULL | 项目多简称变体 |
| `tags` | JSON | NULL | 分类标签（如 ["CS", "AI", "泛计算机"]） |
| `major_category` | VARCHAR(32) | NOT NULL | 专业大类 |
| `duration_months` | INTEGER | NOT NULL | 学制（月） |
| `tuition_per_year` | FLOAT | NOT NULL | 学费/年 |
| `currency` | VARCHAR(8) | NOT NULL | 币种 |
| `ielts_min` | FLOAT | NULL | 雅思最低要求 |
| `toefl_min` | FLOAT | NULL | 托福最低要求 |
| `program_url` | VARCHAR(255) | NULL | 学院官网项目链接 |
| `description_short` | TEXT | NULL | 项目简介 |
| `created_at` | DATETIME | 默认 now | 创建时间 |

**变更说明**：
- `program_full_name` → `program_names`（JSON）
- `program_short_name` → `program_short_names`（JSON）
- 删除 `deadline`
- 新增 `tags`、`program_url`

### 2.3 teachers 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK | 老师 ID |
| `name` | VARCHAR(64) | NOT NULL | 姓名 |
| `gender` | VARCHAR(8) | NOT NULL | 性别 |
| `bio` | TEXT | NULL | 简介 |
| `study_abroad` | VARCHAR(255) | NULL | 留学经历 |
| `work_experience` | TEXT | NULL | 工作经历 |
| `expertise_regions` | VARCHAR(255) | NULL | 擅长地区 |
| `expertise_majors` | VARCHAR(255) | NULL | 擅长专业 |
| `avatar_url` | VARCHAR(255) | NULL | 头像 URL |
| `rating` | FLOAT | NULL | 评分（如 4.8） |

**新增字段**：`avatar_url`、`rating`

## 3. Seed 数据规模

| 数据类型 | 数量 | 说明 |
|---------|------|------|
| 学校 | ~50 所 | QS 前 50（美英新港澳欧+内地） |
| 项目 | ~150-200 个 | 每校 2-4 个主流项目 |
| 老师 | 20 个 | Fake profiles |
| 内部文档 | 25 份 | 签证/服务/申请/行前/FAQ |

## 4. 内部文档清单（25 份）

### 签证指南（10 份）
1. 美国 F-1 学生签证申请指南
2. 英国 Student Visa 申请指南
3. 新加坡 Student Pass 申请指南
4. 香港 Student Visa 申请指南
5. 加拿大 Study Permit 申请指南
6. 澳洲 Student Visa 申请指南
7. 瑞士学生签证指南
8. 法国学生签证指南
9. 德国学生签证指南
10. 荷兰学生签证指南

### 公司服务（4 份）
11. 公司介绍（无忧留学服务公司）
12. 服务项目与收费标准
13. 服务协议模板
14. 隐私政策与退款条款

### 申请材料（5 份）
15. 选校策略指南
16. PS/SOP 写作指南
17. 推荐信准备指南
18. 成绩单 & WES 认证指南
19. 语言考试备考建议

### 行前准备（4 份）
20. 行前 checklist
21. 住宿安排指南
22. 外汇 & 银行卡指南
23. 保险购买指南

### 常见问题（2 份）
24. 申请常见问题 FAQ
25. 签证 & 行前 FAQ

## 5. 数据格式示例

### schools.json
```json
{
  "id": 1,
  "names": ["Massachusetts Institute of Technology", "MIT", "麻省理工学院"],
  "country": "美国",
  "country_en": "USA",
  "city": "Cambridge",
  "address": "77 Massachusetts Avenue, Cambridge, MA 02139, USA",
  "qs_rank": 1,
  "official_site": "https://www.mit.edu",
  "intro": "MIT is a private land-grant research university..."
}
```

### school_programs.json
```json
{
  "id": 1,
  "school_id": 1,
  "program_names": ["Master of Engineering in EECS", "EECS 工程硕士"],
  "program_short_names": ["MEng EECS", "EECS", "电气工程与计算机科学硕士"],
  "tags": ["CS", "EE", "泛计算机"],
  "major_category": "CS",
  "duration_months": 12,
  "tuition_per_year": 60000,
  "currency": "USD",
  "ielts_min": 7.0,
  "toefl_min": 100,
  "program_url": "https://www.mit.edu/degrees/eecs/",
  "description_short": "MIT EECS 一年制硕士项目..."
}
```

### teachers.json
```json
{
  "id": 1,
  "name": "李老师",
  "gender": "male",
  "bio": "深耕北美 CS 申请咨询 8 年，帮助 200+ 学员拿到 Top 30 录取...",
  "study_abroad": "Carnegie Mellon University, MS in CS, 2014-2016",
  "work_experience": "前 Google 工程师；现金牌咨询顾问",
  "expertise_regions": "美国,加拿大",
  "expertise_majors": "CS,EE,DS",
  "avatar_url": null,
  "rating": 4.8
}
```

## 6. 实施步骤

1. 修改 `src/db/models.py` - 更新 ORM 定义
2. 更新 `docs/DB_SCHEMA.md` - 同步文档
3. 生成 `data/seed/schools.json` - QS 前 50 学校
4. 生成 `data/seed/programs.json` - 项目数据
5. 生成 `data/seed/teachers.json` - 20 个老师
6. 生成 `data/raw_docs/internal/*.md` - 25 份内部文档
7. 更新 `src/db/init_db.py` - 适配新 schema
