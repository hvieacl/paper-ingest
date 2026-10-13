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

## 2. 配置 DeepSeek

复制配置文件：

```bash
copy .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

---

## 3. 配置飞书

### 3.1 创建多维表格

新建一个飞书多维表格，然后使用项目中提供的建表 Prompt：

```text
prompts/feishu_bitable_setup.md
```

把其中的 Prompt 复制给飞书 AI 即可创建字段、分类选项和常用视图。

> 字段名需要和 Prompt 保持一致，否则脚本会提示缺少字段。

### 3.2 创建飞书自建应用

进入飞书开放平台，创建一个**企业自建应用**。

获取：

```env
FEISHU_APP_ID=
FEISHU_APP_SECRET=
```

### 3.3 开通应用身份权限

本项目使用 `tenant_access_token`，因此需要开的是**应用身份权限**，不是只有用户身份权限。

至少确保应用可以：

- 读取多维表格记录
- 读取字段
- 新增记录
- 更新记录

如果使用较宽的多维表格权限，可以直接开通应用身份的：

```text
bitable:app
```

修改权限后记得**发布应用新版本**。

### 3.4 配置目标 Base 的访问权限

除了开放平台里的 API 权限，还要确保这个应用本身有权访问目标多维表格。

如果目标 Base 开启了高级权限，请把应用加入有**读写权限**的角色。

典型现象：

- 能读取记录，但新增记录时报 `403 Forbidden`
- 通常说明 API 权限已开，但 Base 侧写入权限还没给到应用

### 3.5 获取 APP_TOKEN 和 TABLE_ID

打开目标多维表格，URL 一般类似：

```text
https://xxx.feishu.cn/base/APP_TOKEN?table=TABLE_ID&view=VIEW_ID
```

对应：

```env
FEISHU_APP_TOKEN=APP_TOKEN
FEISHU_TABLE_ID=TABLE_ID
```

`view=` 后面的内容不需要填写。

最终把飞书配置补到 `.env`：

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=你的_App_Secret
FEISHU_APP_TOKEN=你的_App_Token
FEISHU_TABLE_ID=你的_Table_ID
```

---

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

---

## 5. 日常使用

```text
本地 PDF
        ↓
拖到 load_paper.bat/ 命令行运行 paper_ingest.py
        ↓
自动分析并写入飞书多维表格
```

### Windows 右键菜单（推荐）

如果不想每次跨窗口拖拽，可以直接安装资源管理器右键菜单。

双击运行：

```text
install_context_menu.bat
```

安装后，PDF 右键会提供三个入口：

- **导入到 paper-ingest**：正常导入；有缓存时复用缓存，飞书已有相同 PaperHash 时默认跳过
- **使用缓存覆盖飞书**：复用现有 AI 缓存，不重新调用 DeepSeek，只覆盖飞书中的同 PaperHash 记录
- **重新分析并覆盖飞书**：忽略现有缓存，重新调用 DeepSeek，覆盖本地 cache，并覆盖飞书中的同 PaperHash 记录

文件夹右键仅提供：

- **使用 paper-ingest 处理此文件夹**

为避免一次误操作重跑整个文件夹，文件夹菜单不会提供“重新分析并覆盖”。

脚本会自动使用当前仓库路径，不需要手动写死项目目录。

Windows 11 如果没有直接显示该菜单，请点击：

```text
显示更多选项
```

如需移除右键菜单，双击：

```text
uninstall_context_menu.bat
```

### Windows 拖拽

也可以继续把内容拖到：

```text
load_paper.bat
```

支持：

- 一篇 PDF
- 多篇 PDF 一起拖入
- 一个包含 PDF 的文件夹

文件夹会按文件名顺序处理第一层 PDF。


### 重新分析 / 覆盖已有论文

当论文已经入库，但你修改了 Prompt、输出语言或分析规则时，不需要手动打开命令行。

右键单篇 PDF：

```text
重新分析并覆盖飞书
```

它等价于：

```bash
python paper_ingest.py paper.pdf --force-ai --update
```

处理逻辑：

```text
同一 PDF
  ↓
PaperHash 不变
  ↓
忽略旧 AI cache
  ↓
重新调用 DeepSeek
  ↓
覆盖本地 cache
  ↓
更新飞书中相同 PaperHash 的原记录
```

不会新增一条重复论文，但会产生新的 DeepSeek API 消耗。

如果只想把已有缓存重新写进飞书，而不重新调用 AI，使用：

```text
使用缓存覆盖飞书
```

它等价于：

```bash
python paper_ingest.py paper.pdf --update
```

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

---

## 6. 常见问题

### `ModuleNotFoundError`

重新安装依赖：

```bash
pip install -r requirements.txt
```

### DeepSeek 偶尔返回非法 JSON

程序会自动重试。已经成功解析过的论文会优先使用本地缓存。

如果检测到输出因长度被截断，程序会自动提高 `max_tokens` 后再次请求。默认从 12000 开始，最多扩容到 24000。

### PDF 出现 MuPDF annotation 警告

只要后面仍然正常显示页数和提取字符数，一般可以忽略。

### 飞书读取时报权限错误

确认：

- 权限类型是**应用身份**
- 权限修改后已经发布新版本
- 应用能访问目标 Base

### 飞书能读但写入 403

重点检查目标 Base 的角色权限 / 高级权限，确保应用拥有写入权限。

### 查看完整日志

```text
logs/latest.log
```
