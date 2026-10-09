# paper-ingest

把本地论文 PDF 自动整理后写入飞书多维表格。

> **PDF → DeepSeek 分析 → 自动分类 → 飞书入库**

支持单篇 PDF、多篇 PDF 和整个文件夹批处理。

## 1. 安装

建议使用 Python 3.10+。

```bash
git clone https://github.com/hvieacl/paper-ingest.git
cd paper-ingest

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 配置

复制配置文件：

```bash
copy .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash

FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=你的_App_Secret
FEISHU_APP_TOKEN=你的_App_Token
FEISHU_TABLE_ID=你的_Table_ID

# 1 = 只预览，不写入飞书
# 0 = 正式写入飞书
DRY_RUN=1
```

飞书多维表格链接一般类似：

```text
https://xxx.feishu.cn/base/APP_TOKEN?table=TABLE_ID&view=VIEW_ID
```

对应：

```env
FEISHU_APP_TOKEN=APP_TOKEN
FEISHU_TABLE_ID=TABLE_ID
```

`view=` 后面的内容不需要填写。

## 3. 飞书权限

本项目使用应用身份调用飞书 API。

请确认飞书自建应用具备以下能力：

- 读取多维表格记录
- 读取字段
- 新增记录
- 更新记录

如果出现 `403 Forbidden`，优先检查：

- 是否开的是**应用身份权限**
- 权限修改后是否已发布应用新版本
- 目标 Base 是否允许该应用访问
- Base 高级权限是否允许该应用写入

## 4. 第一次测试

先保持：

```env
DRY_RUN=1
```

运行：

```bash
python paper_ingest.py "D:\papers\paper.pdf"
```

确认终端里的标题、分类和摘要结果正常后，把：

```env
DRY_RUN=0
```

再运行一次即可写入飞书。

## 5. 日常使用

### Windows 拖拽

直接把内容拖到：

```text
load_paper.bat
```

支持：

- 一篇 PDF
- 多篇 PDF 一起拖入
- 一个包含 PDF 的文件夹

文件夹会按文件名顺序处理第一层 PDF。

### 命令行

单篇：

```bash
python paper_ingest.py paper.pdf
```

多篇：

```bash
python paper_ingest.py paper1.pdf paper2.pdf paper3.pdf
```

整个文件夹：

```bash
python paper_ingest.py "D:\papers"
```

更新已有记录：

```bash
python paper_ingest.py paper.pdf --update
```

强制重新调用 DeepSeek：

```bash
python paper_ingest.py paper.pdf --force-ai --update
```

## 6. 飞书表字段

请在目标多维表格中建立以下字段。

### 自动填充

| 字段 | 类型 |
|---|---|
| 标题 | 文本 |
| 简称 | 文本 |
| 年份 | 文本 |
| 作者 | 多行文本 |
| 会议 / 期刊 | 文本 |
| DOI / arXiv | 文本 |
| 研究问题 | 多行文本 |
| 核心思想 | 多行文本 |
| 技术路线 | 多行文本 |
| 关键创新 | 多行文本 |
| 主要结果 / 结论 | 多行文本 |
| 不足之处 | 多行文本 |
| 待解决疑点 | 多行文本 |
| 感悟启发 | 多行文本 |
| Task | 多选 |
| Domain | 多选 |
| Method | 多选 |
| Type | 单选 |
| Role | 单选 |

### 技术字段

| 字段 | 类型 |
|---|---|
| PaperHash | 文本 |
| AI解析状态 | 文本 / 单选 |
| 解析版本 | 文本 |
| 原文件名 | 文本 |

字段名需要与上表保持一致。

## 7. 常见问题

### `ModuleNotFoundError`

重新安装依赖：

```bash
pip install -r requirements.txt
```

### DeepSeek 偶尔返回非法 JSON

程序会自动重试。已经成功解析过的论文会优先使用本地缓存。

### PDF 出现 MuPDF annotation 警告

只要后面仍然正常显示页数和提取字符数，一般可以忽略。

### 飞书写入失败

查看：

```text
logs/latest.log
```

并优先检查飞书应用权限和 Base 写入权限。

## 8. 推荐使用方式

```text
Scholaread 阅读论文
        ↓
本地 PDF
        ↓
拖到 load_paper.bat
        ↓
自动分析并写入飞书
        ↓
在飞书继续整理 / 精读 / 复现
```
