# paper-ingest

A lightweight local workflow for turning research PDFs into structured records in Feishu Bitable.

> **PDF → DeepSeek → structured JSON → Feishu Bitable**

This project is intentionally small. It does not replace Scholaread or build another paper reader.  
It only automates the repetitive part of literature management: extracting key information, classifying papers, and writing the result into Feishu.

---

## Features

- Parse research PDFs with PyMuPDF
- Analyze papers with DeepSeek in a single structured call
- Classify papers with a fixed taxonomy:
  - **Task**
  - **Domain**
  - **Method**
  - **Type**
- Keep **Role** as an auxiliary literature tag
- Validate model output with Pydantic
- Cache AI results locally
- Use SHA256 to avoid duplicate imports
- Write records directly to Feishu Bitable through OpenAPI
- Windows drag-and-drop support via `load_paper.bat`
- Progress output and local error logs

---

## Workflow

```text
PDF
 ↓
PyMuPDF
 ↓
DeepSeek
 ↓
structured JSON
 ↓
taxonomy validation
 ↓
local cache
 ↓
Feishu Bitable
```

Recommended division of labor:

- **Scholaread**: reading, highlights, paper Q&A
- **paper-ingest**: automated structuring and import
- **Feishu Bitable**: literature database
- **Feishu Docs**: deep-reading notes and reproduction records

---

## Requirements

- Python 3.10+
- DeepSeek API key
- Feishu self-built app with Bitable read/write permissions

Install Python dependencies:

```bash
pip install -r requirements.txt
```

A virtual environment is recommended:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/hvieacl/paper-ingest.git
cd paper-ingest
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create local config

Copy the template:

```bash
copy .env.example .env
```

Then edit `.env`:

```env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=your_model

FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=your_secret
FEISHU_APP_TOKEN=base_xxx
FEISHU_TABLE_ID=tbl_xxx

MAX_ANALYSIS_CHARS=120000

# 1 = preview only
# 0 = write to Feishu
DRY_RUN=1
```

Do not commit `.env`. It is already ignored by `.gitignore`.

### 4. First test

Keep:

```env
DRY_RUN=1
```

Then run:

```bash
python paper_ingest.py "D:\papers\paper.pdf"
```

The program will:

1. parse the PDF
2. call DeepSeek
3. validate the structured result
4. cache it locally
5. print a preview
6. stop before writing to Feishu

### 5. Enable Feishu write

After confirming the preview, change:

```env
DRY_RUN=0
```

Run the same PDF again:

```bash
python paper_ingest.py "D:\papers\paper.pdf"
```

The cached AI result will be reused, so DeepSeek is normally not called again.

---

## Windows Drag-and-Drop

After dependencies and `.env` are configured, drag a PDF directly onto:

```text
load_paper.bat
```

The command window will stay open and show progress:

```text
[0/5] configuration
[1/5] read PDF
[2/5] parse/cache
[3/5] DeepSeek analysis
[4/5] preview
[5/5] Feishu write
```

If something fails, the latest log is written to:

```text
logs/latest.log
```

---

## Feishu Bitable Schema

The target table should contain these fields.

### Auto-filled fields

| Field | Type |
|---|---|
| 标题 | Text |
| 简称 | Text |
| 年份 | Text |
| 作者 | Long text |
| 会议 / 期刊 | Text |
| DOI / arXiv | Text |
| 研究问题 | Long text |
| 核心思想 | Long text |
| 技术路线 | Long text |
| 关键创新 | Long text |
| 主要结果 / 结论 | Long text |
| 不足之处 | Long text |
| 待解决疑点 | Long text |
| 感悟启发 | Long text |
| Task | Multi-select |
| Domain | Multi-select |
| Method | Multi-select |
| Type | Single-select |
| Role | Single-select |

### Technical fields

| Field | Type | Purpose |
|---|---|---|
| PaperHash | Text | Duplicate detection |
| AI解析状态 | Text / Single-select | Parse status |
| 解析版本 | Text | Schema version |
| 原文件名 | Text | Original PDF filename |

Field names must match exactly.

---

## Taxonomy

The main classification system is:

### Task
What problem the paper solves.

Examples:

- 静态场景重建
- 动态场景 / 4D 重建
- 新视角合成
- 世界状态预测
- 规划与决策

### Domain
Where the method is applied.

Examples:

- 自动驾驶 / 城市道路
- 通用室外场景
- 室内场景
- 机器人 / 具身环境

### Method
What representation, modeling paradigm, or core technique is used.

Examples:

- 3DGS
- NeRF / 神经辐射场
- SLAM / BA
- Diffusion / 视频扩散
- Transformer
- JEPA / 表征预测
- World Model / Latent Dynamics
- VLM / VLA

### Type
What kind of resource it is.

Examples:

- 研究论文
- 综述 / 系统综述
- 技术报告
- 数据集 / 基准

### Role
Auxiliary literature role.

Examples:

- 基础 / 奠基工作
- 方法论文
- 基准 / 数据集工作

All taxonomy values are maintained in:

```text
schema.py
```

---

## CLI

Normal import:

```bash
python paper_ingest.py paper.pdf
```

Overwrite an existing Feishu record:

```bash
python paper_ingest.py paper.pdf --update
```

Force a new DeepSeek analysis:

```bash
python paper_ingest.py paper.pdf --force-ai --update
```

---

## Cache

AI results are saved under:

```text
cache/<sha256>.json
```

This prevents unnecessary repeated API calls.

If the schema version changes, old cache entries are automatically treated as stale and regenerated.

---

## Feishu IDs

A Feishu Bitable URL usually looks like:

```text
https://xxx.feishu.cn/base/APP_TOKEN?table=TABLE_ID&view=VIEW_ID
```

Use:

```env
FEISHU_APP_TOKEN=APP_TOKEN
FEISHU_TABLE_ID=TABLE_ID
```

The `view` value is not required.

---

## Security

Never commit:

- `.env`
- DeepSeek API keys
- Feishu App Secret
- local cache files

The repository already ignores:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
cache/*.json
```

You can verify:

```bash
git check-ignore -v .env
```

---

## Project Structure

```text
paper-ingest/
├── paper_ingest.py      # main entry
├── pdf_parser.py        # PDF text extraction
├── analyzer.py          # DeepSeek structured analysis
├── schema.py            # taxonomy + output schema
├── feishu.py            # Feishu Bitable client
├── load_paper.bat       # Windows drag-and-drop launcher
├── requirements.txt
├── .env.example
├── cache/
└── logs/
```

---

## Limitations

V1 is designed for fast literature indexing, not full paper understanding.

It does not currently provide:

- OCR for scanned PDFs
- figure-level visual understanding
- detailed table extraction
- formula reasoning
- RAG / vector search
- Scholaread synchronization
- automatic arXiv crawling

For deep reading, figures, formulas, and reproduction work, continue using Scholaread / ChatGPT / Feishu Docs.

---

## Troubleshooting

### `ModuleNotFoundError`

Dependencies are not installed.

Run:

```bash
pip install -r requirements.txt
```

If using the virtual environment:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### Feishu 403

Check:

- app permissions
- whether permissions have been published
- whether the app can access the target Bitable
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_APP_TOKEN`
- `FEISHU_TABLE_ID`

### PDF text is too short

The PDF may be scanned or have a broken text layer. V1 does not run OCR.

### DeepSeek returns empty output

Check:

- API key
- base URL
- model name

---

## Design Principle

Keep the workflow small:

> **Scholaread for reading, paper-ingest for structuring, Feishu for accumulation.**

The goal is to reduce literature-management overhead, not create another system to maintain.
