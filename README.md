# Paper Ingest V1

目标只有一个：

> **PDF → DeepSeek 一次结构化解析 → 标签校验 → 飞书多维表格一行**

它不替代 Scholaread。  
Scholaread 继续负责 PDF 云端保存、阅读、批注和对话；本工具只消灭“固定 Prompt + 复制粘贴 + 手动打标签”的机械工作。

## 1. V1 边界

包含：
- PyMuPDF 提取论文文本
- 选择摘要/引言/方法/实验/结论等高价值正文页
- DeepSeek 一次返回结构化 JSON
- 固定 Task / Domain / 场景表示 / Method 词表
- Pydantic 校验
- SHA256 去重
- 本地 AI 结果缓存
- 飞书多维表格字段 Schema 校验
- 新增 / 覆盖更新记录
- Windows 拖拽 PDF 到 `.bat`

不包含：
- Scholaread API 同步
- OCR
- 图表视觉理解
- RAG / 向量数据库
- Web UI / FastAPI / Docker
- 多 Agent
- 自动抓 arXiv

这些都不是当前效率瓶颈。

---

## 2. 飞书表最终字段

### AI 自动填充

| 字段 | 飞书字段类型 | 说明 |
|---|---|---|
| 标题 | 多行文本/文本 | 正式标题 |
| 简称 | 文本 | 常用简称 |
| 年份 | 文本 | V1 用文本最省事 |
| 作者 | 多行文本 | 作者列表 |
| 会议 / 期刊 | 文本 | Venue |
| DOI / arXiv | 文本 | DOI 或 arXiv ID |
| 研究问题 | 多行文本 | What / Why |
| 核心思想 | 多行文本 | 核心解决思路 |
| 技术路线 | 多行文本 | 输入→模块→中间结果→输出→目的 |
| 关键创新 | 多行文本 | 2–4条 |
| 主要结果 / 结论 | 多行文本 | 实验支持的结论 |
| 不足之处 | 多行文本 | 局限 |
| 待解决疑点 | 多行文本 | 2–5个精读问题 |
| 感悟启发 | 多行文本 | 与“重建→世界模型”主线的关联 |
| Task | **多选** | 固定词表 |
| Domain | **多选** | 固定词表 |
| 场景表示 | **多选** | 固定词表 |
| Method | **多选** | 固定词表 |
| 文献类型 | **单选** | 研究论文/综述等 |
| 文献角色 | **单选** | 基础/方法/基准 |

### 由你维护

建议另外保留：
- 阅读状态（单选：待读 / 速览 / 精读中 / 已精读 / 暂缓）
- 优先级（单选：P0 核心 / P1 重要 / P2 一般 / P3 备查）
- 复现状态
- 飞书精读笔记（链接）
- 复现记录（链接）

### 隐藏的技术字段

必须创建：
- `PaperHash`：文本
- `AI解析状态`：文本或单选（至少允许“已解析”）
- `解析版本`：文本
- `原文件名`：文本

这些字段平时可以在视图里隐藏。

---

## 3. 飞书权限准备

你不需要飞书 CLI。

流程是：

1. 飞书开放平台创建 **企业自建应用**。
2. 给应用开通多维表格相关的读取/写入权限。
3. 发布/启用应用，使权限生效。
4. 确保该应用能访问目标多维表格。
5. 获得：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_APP_TOKEN`
   - `FEISHU_TABLE_ID`

你的多维表格 URL 通常类似：

```text
https://xxx.feishu.cn/base/<app_token>?table=<table_id>&view=<view_id>
```

V1 不需要 view_id。

---

## 4. DeepSeek 配置

复制：

```bash
copy .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=填当前 API 控制台可用模型

FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
FEISHU_APP_TOKEN=...
FEISHU_TABLE_ID=...

DRY_RUN=1
```

代码不把模型名写死，是为了避免以后模型升级后又改代码。

---

## 5. 安装

建议单独虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 6. 第一次测试：先不要写飞书

`.env`：

```env
DRY_RUN=1
```

运行：

```bash
python paper_ingest.py "D:\papers\OmniRe.pdf"
```

第一次会：
1. 算 PDF hash
2. PyMuPDF 抽文本
3. DeepSeek 分析
4. 把完整结果缓存到 `cache/<hash>.json`
5. 打印分类预览
6. **不写飞书**

如果结果没问题，再把：

```env
DRY_RUN=0
```

然后重新运行。因为有缓存，这次**不会再次调用 DeepSeek**，直接写飞书。

---

## 7. 日常使用

Windows 最省事：

> 直接把 PDF 拖到 `导入论文.bat`

如果已存在相同 PDF：
- 默认跳过
- 要覆盖飞书：

```bash
python paper_ingest.py paper.pdf --update
```

如果改了 Prompt / Schema，确实想重新调用 AI：

```bash
python paper_ingest.py paper.pdf --force-ai --update
```

---

## 8. 为什么使用 Hash + Cache

### Hash
避免同一 PDF 被重复分析、重复入库。

### Cache
飞书写失败、改字段、换表格时，不需要再次付一次模型调用费。

因此完整流程是：

```text
PDF
 ↓
SHA256
 ↓
有 cache? ──是──→ 直接复用
 ↓否
PDF 文本
 ↓
DeepSeek
 ↓
cache JSON
 ↓
飞书
```

---

## 9. 当前标签设计

标签词表都集中在 `schema.py`，不要散落到 Prompt 和代码各处。

以后你真的开始系统读：
- World Model
- JEPA
- VLA
- Latent Dynamics
- Model-Based RL

只需要修改 `schema.py` 的词表，Prompt 会自动使用最新词表。

原则仍然是：

> 出现稳定研究簇、有检索价值后再加标签，不为了“学术上完整”而无限扩词。

---

## 10. V1 的重要限制

### 扫描版 PDF
如果 PyMuPDF 抽不到足够正文，V1 会报错，不自动 OCR。

### 图表
V1 会读图注文本，但不会“看图”。复杂 Framework、消融表格、公式推导仍建议在 Scholaread / ChatGPT 精读。

### PDF 文本顺序
双栏论文的 PDF 文本抽取偶尔会错序。对“总库结构化整理”通常够用；不把它当最终精读结果。

---

## 11. 推荐的真实工作流

```text
发现论文
  ↓
Scholaread 收藏 / 阅读
  ↓
值得正式收录？
  ├─ 否 → 只留 Scholaread
  └─ 是
      ↓
拖 PDF → 导入论文.bat
      ↓
DeepSeek 自动结构化 + 分类
      ↓
飞书总库
      ↓
值得精读？
  ├─ 否 → 停
  └─ 是 → 飞书精读文档
             ↓
           值得复现？
             ↓
           复现记录
```

