# prompts

这个目录集中维护项目使用的提示词，方便后续独立调整。

- `paper_analysis_system.txt`：论文结构化分析 System Prompt。脚本运行时会直接读取这个文件。
- `feishu_bitable_setup.md`：创建飞书多维表格时使用的 Prompt。

修改 `paper_analysis_system.txt` 后，旧论文如需按新提示词重新分析，请使用：

```bash
python paper_ingest.py paper.pdf --force-ai --update
```
