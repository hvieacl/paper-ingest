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

新建一个飞书多维表格，并使用下面的提示词让飞书 AI 创建字段。

```text
请创建一个用于科研论文管理的多维表格，主表名为“文献总库”。

一、AI 自动填充字段

1. 标题：文本，作为主字段
2. 简称：文本
3. 年份：文本
4. 作者：多行文本
5. 会议 / 期刊：文本
6. DOI / arXiv：文本
7. 研究问题：多行文本
8. 核心思想：多行文本
9. 技术路线：多行文本
10. 关键创新：多行文本
11. 主要结果 / 结论：多行文本
12. 不足之处：多行文本
13. 待解决疑点：多行文本
14. 感悟启发：多行文本

二、分类字段

Task：多选，选项如下：
静态场景重建
动态场景 / 4D 重建
表面 / 网格重建
新视角合成
视角外推
三维物体 / 资产生成
场景生成
场景编辑 / 资产插入
深度估计
相机位姿估计
定位与建图
语义场景理解
语义 / 实例分割
语义占据预测
三维 / 点云补全
仿真与闭环评测
场景 / 驾驶情景 / 数据生成
未来帧 / 视频预测
世界状态预测
运动 / 轨迹预测
行为条件生成
交互式场景生成
规划与决策
多模态理解
动作预测 / 控制

Domain：多选，选项如下：
自动驾驶 / 城市道路
通用室外场景
室内场景
物体级场景
通用 / 多领域
机器人 / 具身环境
游戏 / 仿真环境
通用视频 / 互联网数据

Method：多选，选项如下：
3DGS
NeRF / 神经辐射场
网格 / 显式表面
点云
体素 / 占据表示
显式表示
隐式表示
Latent / Token 表示
多视图几何 / SfM / MVS
几何 / 光度优化
SLAM / BA
前馈式 / 泛化式重建
Diffusion / 视频扩散
生成式先验
深度先验
多模态 / 多传感器融合
实例级建模
时序建模
自监督学习
Transformer
JEPA / 表征预测
World Model / Latent Dynamics
VLM / VLA
Autoregressive Modeling
Model-Based RL
Tokenized World Representation

Type：单选，选项如下：
研究论文
综述 / 系统综述
技术报告
数据集 / 基准
开源代码 / 项目
书籍 / 章节
学位论文

Role：单选，选项如下：
基础 / 奠基工作
方法论文
基准 / 数据集工作

三、人工维护字段

阅读状态：单选
待读
速览
精读中
已精读
暂缓

优先级：单选
P0 核心
P1 重要
P2 一般
P3 备查

复现状态：单选
不复现
待复现
复现中
已复现
复现失败
搁置

飞书精读笔记：链接
复现记录：链接

四、技术字段

PaperHash：文本
AI解析状态：单选，至少包含“待解析”“已解析”“解析失败”“需重跑”
解析版本：文本
原文件名：文本

五、创建以下视图

1. 全部文献：显示所有记录
2. 阅读工作台：重点显示标题、简称、年份、Task、Domain、Method、Type、Role、阅读状态、优先级、核心思想、技术路线、待解决疑点、感悟启发
3. 待读论文：筛选“阅读状态 = 待读”
4. 核心论文：筛选“优先级 = P0 核心 或 P1 重要”
5. 待复现：筛选“复现状态 = 待复现 或 复现中”

PaperHash、AI解析状态、解析版本、原文件名默认放在最右侧或隐藏。
```

> 字段名需要和上面的文字保持一致，否则脚本会提示缺少字段。

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

> 如果你习惯用飞书 CLI 配置应用，可以按飞书官方 CLI / OpenAPI 指南完成应用创建和权限配置；本项目本身不依赖 CLI。

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

---

## 6. 常见问题

### `ModuleNotFoundError`

重新安装依赖：

```bash
pip install -r requirements.txt
```

### DeepSeek 偶尔返回非法 JSON

程序会自动重试。已经成功解析过的论文会优先使用本地缓存。

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

---

## 7. 推荐使用方式

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
